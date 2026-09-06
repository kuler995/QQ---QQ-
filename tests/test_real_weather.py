# -*- coding: utf-8 -*-
"""测试真天气调用（wttr.in 兜底版）"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.api.weather import get_weather, weather_to_text

print("=" * 60)
print("真天气调用测试（不用 mock）")
print("=" * 60)

ok, weather, msg = get_weather()
print(f"\nsuccess: {ok}")
print(f"msg: {msg}")
print(f"\n天气字典:")
for k, v in weather.items():
    print(f"  {k}: {v}")

print(f"\n给 AI 的天气描述:")
print(f"  {weather_to_text(weather)}")

if not weather.get("_is_mock", True):
    source = weather.get("_source", "?")
    print(f"\n🎉 成功拿到真天气！数据源: {source}")
else:
    print(f"\n⚠️ 还是 mock 数据，需要排查")
