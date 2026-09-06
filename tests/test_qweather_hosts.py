# -*- coding: utf-8 -*-
"""探测和风天气 API KEY 在哪个公共 Host 下能正常工作
2026 年起官方强制用专属 Host，但部分老 KEY 在公共域名下可能还有效
"""
import requests
import time

API_KEY = "f3967f30ced34e54a417acc145065d67"
# 河南理工大学所在城市焦作的标准 Location ID
LOCATION_ID = "101181401"  # 焦作

# 备选城市 ID（防止 ID 不对）
JIAOZUO_FALLBACK = "焦作"

# 候选 Host 列表（按可能性排序）
HOSTS = [
    "https://devapi.qweather.com",  # 开发版公共域名（2024前主流）
    "https://api.qweather.com",     # 标准版公共域名
]


def try_host(host: str):
    """测试一个 Host：先直接请求，再带 header 请求"""
    print(f"\n--- 测 {host} ---")

    # 方法 1：URL 里带 key
    url1 = f"{host}/v7/weather/now"
    params = {"location": LOCATION_ID, "key": API_KEY, "lang": "zh", "unit": "m"}
    try:
        t0 = time.time()
        r = requests.get(url1, params=params, timeout=10)
        dt = time.time() - t0
        print(f"  [URL key] HTTP {r.status_code} 耗时 {dt:.1f}s")
        if r.status_code == 200:
            data = r.json()
            code = data.get("code")
            print(f"  和风返回 code: {code}")
            if str(code) == "200":
                now = data.get("now", {})
                print(f"  ✅ 成功！{now.get('text')} {now.get('temp')}℃ 风{now.get('windDir')}")
                return True, "url_key"
            else:
                print(f"  ❌ code 异常: {data.get('message', '')}")
        else:
            print(f"  ❌ body: {r.text[:200]}")
    except Exception as e:
        print(f"  ❌ 异常: {e}")

    # 方法 2：header 传 key
    url2 = f"{host}/v7/weather/now"
    headers = {"X-QW-Api-Key": API_KEY}
    params2 = {"location": LOCATION_ID, "lang": "zh", "unit": "m"}
    try:
        t0 = time.time()
        r = requests.get(url2, headers=headers, params=params2, timeout=10)
        dt = time.time() - t0
        print(f"  [Header key] HTTP {r.status_code} 耗时 {dt:.1f}s")
        if r.status_code == 200:
            data = r.json()
            code = data.get("code")
            print(f"  和风返回 code: {code}")
            if str(code) == "200":
                now = data.get("now", {})
                print(f"  ✅ 成功！{now.get('text')} {now.get('temp')}℃ 风{now.get('windDir')}")
                return True, "header_key"
            else:
                print(f"  ❌ code 异常: {data.get('message', '')}")
        else:
            print(f"  ❌ body: {r.text[:200]}")
    except Exception as e:
        print(f"  ❌ 异常: {e}")

    return False, None


# 城市查询 API 测试（如果上面都不行，可能是 location_id 不对）
def try_city_lookup(host: str):
    """用「焦作」关键字查 location id"""
    print(f"\n--- 测城市查询 {host} ---")
    url = f"{host}/v2/city/lookup"
    # 城市查询也支持 key 在 URL 或 header
    for mode in ["url", "header"]:
        if mode == "url":
            params = {"location": JIAOZUO_FALLBACK, "key": API_KEY, "lang": "zh"}
            headers = {}
        else:
            params = {"location": JIAOZUO_FALLBACK, "lang": "zh"}
            headers = {"X-QW-Api-Key": API_KEY}
        try:
            r = requests.get(url, params=params, headers=headers, timeout=10)
            print(f"  [{mode}] HTTP {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                if str(data.get("code")) == "200":
                    cities = data.get("location", [])
                    print(f"  ✅ 找到 {len(cities)} 个城市:")
                    for c in cities:
                        print(f"     {c.get('name')} id={c.get('id')} adm2={c.get('adm2')}")
                    return True
                else:
                    print(f"  ❌ {data.get('message', '')}")
            else:
                print(f"  ❌ body: {r.text[:200]}")
        except Exception as e:
            print(f"  ❌ 异常: {e}")
    return False


def main():
    print("=" * 60)
    print(f"和风天气 KEY 探测开始 (KEY={API_KEY[:8]}...)")
    print("=" * 60)

    found_host = None
    found_mode = None
    for host in HOSTS:
        ok, mode = try_host(host)
        if ok:
            found_host = host
            found_mode = mode
            break

    if not found_host:
        # 都不行，试试城市查询是不是 location_id 错了
        for host in HOSTS:
            try_city_lookup(host)

    print("\n" + "=" * 60)
    if found_host:
        print(f"🎉 推荐 Host: {found_host}")
        print(f"   认证模式: {found_mode}")
        if found_mode == "url_key":
            print("   → weather.py 的 host 判断要改成 devapi.qweather.com + URL 带 key")
        else:
            print("   → weather.py 用 X-QW-Api-Key header")
    else:
        print("⚠️ 两个公共 Host 都不通，需要用户去和风控制台拿专属 Host")
        print("   控制台地址: https://console.qweather.com/setting")
    print("=" * 60)


if __name__ == "__main__":
    main()
