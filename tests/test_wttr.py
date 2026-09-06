# -*- coding: utf-8 -*-
"""探测 wttr.in 服务能否拿到焦作天气
wttr.in 是免费、无需 KEY 的全球天气服务
数据源：WorldWeatherOnline / OpenWeatherMap
"""
import requests
import json
import time


def try_wttr(location: str):
    """测试 wttr.in 服务
    location 可以是中文「焦作」、拼音「jiaozuo」、或坐标
    """
    print(f"\n--- 测 wttr.in / {location} ---")

    # 方法 1：JSON 完整格式
    url = f"https://wttr.in/{location}"
    params = {"format": "j1", "lang": "zh"}
    headers = {"Accept-Language": "zh-CN,zh;q=0.9"}

    try:
        t0 = time.time()
        r = requests.get(url, params=params, headers=headers, timeout=15)
        dt = time.time() - t0
        print(f"  HTTP {r.status_code} 耗时 {dt:.1f}s")

        if r.status_code == 200:
            data = r.json()
            current = data.get("current_condition", [{}])[0]
            nearest = data.get("nearest_area", [{}])[0]

            # 当前实况
            temp_c = current.get("temp_C", "?")
            feels = current.get("FeelsLikeC", "?")
            desc = current.get("lang_zh", [{}])[0].get("value", "?") if current.get("lang_zh") else current.get("weatherDesc", [{}])[0].get("value", "?")
            humidity = current.get("humidity", "?")
            wind_dir = current.get("winddir16Point", "?")
            wind_scale = current.get("windspeedKmph", "?")
            wind_speed_kmph = current.get("windspeedKmph", "?")
            city_name = nearest.get("areaName", [{}])[0].get("value", "?")
            region = nearest.get("region", [{}])[0].get("value", "")
            country = nearest.get("country", [{}])[0].get("value", "")

            print(f"  ✅ 成功！")
            print(f"     城市: {city_name} / {region} / {country}")
            print(f"     实况: {desc} {temp_c}℃（体感 {feels}℃）")
            print(f"     风: {wind_dir} {wind_speed_kmph} km/h")
            print(f"     湿度: {humidity}%")
            print(f"     更新时间: {current.get('localObsDateTime', '?')}")

            # 拿今天的预报（最高最低）
            today_weather = data.get("weather", [{}])[0]
            max_temp = today_weather.get("maxtempC", "?")
            min_temp = today_weather.get("mintempC", "?")
            print(f"     今日: 最高 {max_temp}℃ / 最低 {min_temp}℃")

            return True
        else:
            print(f"  ❌ body: {r.text[:300]}")
    except Exception as e:
        print(f"  ❌ 异常: {e}")

    return False


def main():
    print("=" * 60)
    print("wttr.in 服务探测开始")
    print("=" * 60)

    # 测多个城市名格式，看哪个最好用
    locations = [
        "Jiaozuo",          # 拼音（最稳）
        "焦作",             # 中文
        "Jiaozuo,Henan",    # 拼音+省
        "35.23,113.62",     # 河南理工大学坐标（焦作 35.23N 113.62E）
    ]

    success_count = 0
    for loc in locations:
        if try_wttr(loc):
            success_count += 1

    print()
    print("=" * 60)
    print(f"结果: {success_count}/{len(locations)} 个查询方式可用")
    if success_count > 0:
        print("🎉 wttr.in 可用！建议改 weather.py 加 wttr.in 兜底")
        print("   城市名推荐用坐标 35.23,113.62（河南理工大学焦作校区）")
    else:
        print("⚠️ wttr.in 不可用，仍需用户拿和风专属 Host")
    print("=" * 60)


if __name__ == "__main__":
    main()
