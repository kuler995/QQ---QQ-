# -*- coding: utf-8 -*-
"""天气查询接口封装

三层优先级：
1. 和风专属 Host（如果用户在设置里配了 api_host，仍走和风官方）
2. wttr.in（免费免 KEY 全球服务，坐标定位河南理工大学焦作校区）
3. mock 占位（前两层都失败的极端情况）
"""
import time
import requests
from typing import Tuple, Dict, Any

from src.config import CONFIG
from src.utils.logger import logger

# 河南理工大学焦作校区坐标（wttr.in 用）
HPU_COORDS = "35.23,113.62"
HPU_CITY_CN = "焦作"


def _mock_weather() -> Dict[str, Any]:
    """占位假数据（仅在前两层 API 都失败时兜底用）"""
    return {
        "city": HPU_CITY_CN,
        "temp": "26",
        "feels_like": "28",
        "text": "晴",
        "wind_dir": "东南风",
        "wind_scale": "2",
        "humidity": "55",
        "update_time": time.strftime("%H:%M"),
        "_is_mock": True
    }


def _fetch_from_qweather(api_host: str, key: str, location_id: str) -> Tuple[bool, Dict, str]:
    """和风天气 v7 API 调用（用户配了专属 Host 才走）"""
    host = api_host.rstrip("/")
    if not host.startswith("https://"):
        host = f"https://{host}"
    url = f"{host}/v7/weather/now"
    headers = {"X-QW-Api-Key": key}
    params = {"location": location_id, "lang": "zh", "unit": "m"}

    try:
        t0 = time.time()
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        elapsed = time.time() - t0
        logger.info(f"🌤️ 和风天气请求完成 HTTP {resp.status_code} 耗时 {elapsed:.1f}s")

        if resp.status_code == 200:
            data = resp.json()
            code = data.get("code")
            if str(code) == "200":
                now = data.get("now", {})
                weather = {
                    "city": CONFIG.get("weather", {}).get("city", HPU_CITY_CN),
                    "temp": now.get("temp", ""),
                    "feels_like": now.get("feelsLike", ""),
                    "text": now.get("text", ""),
                    "wind_dir": now.get("windDir", ""),
                    "wind_scale": now.get("windScale", ""),
                    "humidity": now.get("humidity", ""),
                    "update_time": data.get("updateTime", ""),
                    "_is_mock": False,
                    "_source": "qweather"
                }
                return True, weather, "获取成功（和风）"
            msg = f"和风返回错误码: {code}"
            logger.error(f"❌ {msg}")
            return False, {}, msg

        msg = f"HTTP {resp.status_code}: {resp.text[:200]}"
        logger.error(f"❌ {msg}")
        return False, {}, msg
    except Exception as e:
        logger.error(f"❌ 和风天气异常: {e}", exc_info=True)
        return False, {}, str(e)


# 风向 16 点英文 → 中文
_WIND_DIR_CN = {
    "N": "北风", "NNE": "北东北风", "NE": "东北风", "ENE": "东东北风",
    "E": "东风", "ESE": "东东南风", "SE": "东南风", "SSE": "南东南风",
    "S": "南风", "SSW": "南西南风", "SW": "西南风", "WSW": "西西南风",
    "W": "西风", "WNW": "西西北风", "NW": "西北风", "NNW": "北西北风",
}


def _wttr_desc_to_cn(desc: str) -> str:
    """wttr.in 英文天气描述 → 中文"""
    mapping = {
        "Clear": "晴", "Sunny": "晴", "Partly cloudy": "多云",
        "Cloudy": "阴", "Overcast": "阴", "Mist": "薄雾",
        "Fog": "雾", "Light rain": "小雨", "Light drizzle": "小雨",
        "Patchy rain possible": "小雨可能", "Patchy light rain": "零星小雨",
        "Moderate rain": "中雨", "Heavy rain": "大雨",
        "Light snow": "小雪", "Moderate snow": "中雪", "Heavy snow": "大雪",
        "Thunder": "雷", "Thunderstorm": "雷雨", "Patchy light snow": "零星小雪",
        "Smoky haze": "霾", "Haze": "霾", "Smoke": "烟",
    }
    if not desc:
        return "未知"
    # 精确匹配
    if desc in mapping:
        return mapping[desc]
    # 包含匹配（先长后短）
    for k in sorted(mapping.keys(), key=len, reverse=True):
        if k.lower() in desc.lower():
            return mapping[k]
    return desc


def _fetch_from_wttr() -> Tuple[bool, Dict, str]:
    """wttr.in 调用（免 KEY 兜底，用河南理工大学坐标）"""
    url = f"https://wttr.in/{HPU_COORDS}"
    params = {"format": "j1", "lang": "zh"}
    headers = {"Accept-Language": "zh-CN,zh;q=0.9"}

    try:
        t0 = time.time()
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        elapsed = time.time() - t0
        logger.info(f"🌤️ wttr.in 请求完成 HTTP {resp.status_code} 耗时 {elapsed:.1f}s")

        if resp.status_code != 200:
            return False, {}, f"HTTP {resp.status_code}"

        data = resp.json()
        current = (data.get("current_condition") or [{}])[0]
        today = (data.get("weather") or [{}])[0]

        # 提取英文描述
        desc_en = ""
        if current.get("lang_zh"):
            desc_en = current["lang_zh"][0].get("value", "")
        elif current.get("weatherDesc"):
            desc_en = current["weatherDesc"][0].get("value", "")

        # 转中文
        text_cn = _wttr_desc_to_cn(desc_en)

        # 风向英文转中文
        wind_dir_en = current.get("winddir16Point", "")
        wind_dir_cn = _WIND_DIR_CN.get(wind_dir_en, wind_dir_en)

        # 风速 km/h → 风级（粗略换算）
        wind_kmph = current.get("windspeedKmph", "0")
        try:
            kmph = int(wind_kmph)
            if kmph < 1: wind_scale = "0"
            elif kmph < 6: wind_scale = "1"
            elif kmph < 12: wind_scale = "2"
            elif kmph < 20: wind_scale = "3"
            elif kmph < 29: wind_scale = "4"
            elif kmph < 39: wind_scale = "5"
            elif kmph < 50: wind_scale = "6"
            elif kmph < 62: wind_scale = "7"
            else: wind_scale = "8"
        except (ValueError, TypeError):
            wind_scale = "2"

        # 今天的最高/最低温度
        max_temp = today.get("maxtempC", "")
        min_temp = today.get("mintempC", "")

        weather = {
            "city": HPU_CITY_CN,
            "temp": current.get("temp_C", ""),
            "feels_like": current.get("FeelsLikeC", ""),
            "text": text_cn,
            "wind_dir": wind_dir_cn,
            "wind_scale": wind_scale,
            "humidity": current.get("humidity", ""),
            "update_time": current.get("localObsDateTime", time.strftime("%H:%M")),
            "max_temp": max_temp,
            "min_temp": min_temp,
            "_is_mock": False,
            "_source": "wttr"
        }
        return True, weather, "获取成功（wttr.in）"
    except Exception as e:
        logger.error(f"❌ wttr.in 异常: {e}", exc_info=True)
        return False, {}, str(e)


def get_weather() -> Tuple[bool, Dict[str, Any], str]:
    """获取焦作（河南理工大学）实时天气
    Returns:
        (success, weather_dict, msg)
    优先级：
        1. 和风天气（用户配了 api_host 才走）
        2. wttr.in（免 KEY 兜底）
        3. mock 数据（前两层都失败的极端情况）
    """
    cfg = CONFIG.get("weather", {})
    key = cfg.get("api_key", "")
    api_host = cfg.get("api_host", "").strip()
    location_id = cfg.get("location_id", "101181401")

    # 第一层：和风（用户配了 Host 才走）
    if api_host and key:
        ok, w, msg = _fetch_from_qweather(api_host, key, location_id)
        if ok:
            return True, w, msg
        logger.warning(f"⚠️ 和风失败，回退到 wttr.in: {msg}")
    else:
        logger.info("ℹ️ 未配和风专属 Host，直接用 wttr.in（免 KEY 免费服务）")

    # 第二层：wttr.in 兜底
    ok, w, msg = _fetch_from_wttr()
    if ok:
        return True, w, msg

    # 第三层：mock 兜底
    logger.error(f"❌ wttr.in 也失败 ({msg})，用 mock 数据")
    return True, _mock_weather(), f"wttr.in 失败 ({msg})，用模拟数据"


def weather_to_text(weather: Dict[str, Any]) -> str:
    """天气数据转成给 AI 的简短描述"""
    text = weather.get("text", "")
    temp = weather.get("temp", "")
    wind_dir = weather.get("wind_dir", "")
    wind_scale = weather.get("wind_scale", "")
    humidity = weather.get("humidity", "")
    feels = weather.get("feels_like", "")
    city = weather.get("city", HPU_CITY_CN)
    source = weather.get("_source", "mock")

    parts = [f"{city}天气：{text} {temp}℃"]
    if feels and feels != temp:
        parts.append(f"体感{feels}℃")
    parts.append(f"{wind_dir}{wind_scale}级")
    parts.append(f"湿度{humidity}%")

    # 如果有最高最低温度（wttr.in 提供）
    max_t = weather.get("max_temp")
    min_t = weather.get("min_temp")
    if max_t and min_t:
        parts.append(f"今日{min_t}-{max_t}℃")

    desc = "，".join(parts)
    # 标注数据源（让用户知道是真天气还是兜底）
    if source == "wttr":
        desc += "（数据源: wttr.in）"
    elif source == "qweather":
        desc += "（数据源: 和风天气）"
    return desc
