# -*- coding: utf-8 -*-
"""验证晚安 tags 空 bug 修复"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.content_generator import generate_night_content

print("=== 晚安单条验证（tags 空 bug 修复）===")
items = generate_night_content(count=1)
if items and items[0].text:
    print(f"✅ text: {items[0].text}")
    print(f"✅ tags: {items[0].tags}")
    print(f"✅ image: {'有' if items[0].image_bytes else '无'}")
    if items[0].tags and ("#晚安理工#" in items[0].tags or "#每日话题#" in items[0].tags):
        print("🎉 tags bug 已修复！晚安标签正常带上")
    else:
        print("⚠️ tags 仍然异常，需要再排查")
else:
    print(f"❌ 生成失败: {items[0].error if items else '无返回'}")
