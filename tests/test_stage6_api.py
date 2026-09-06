# -*- coding: utf-8 -*-
"""阶段6 单条生成 API 自动化测试
测试 4 个核心生成函数：
1. generate_morning_content(count=1) → 早安 1 条
2. generate_night_content(count=1) → 晚安 1 条
3. generate_single_recommend('book') → 推荐单条（书籍）
4. generate_single_share('science') → 分享单条（科普冷知识）
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.content_generator import generate_morning_content, generate_night_content
from src.core.recommend_generator import generate_single_recommend
from src.core.share_generator import generate_single_share


def fmt(item, label):
    print(f"\n--- {label} ---")
    if item is None:
        print("  ❌ 返回 None")
        return False
    if getattr(item, "error", None):
        print(f"  ❌ error: {item.error}")
        return False
    text = getattr(item, "text", "") or ""
    tags = getattr(item, "tags", []) or []
    img = getattr(item, "image_bytes", None)
    print(f"  字数: {len(text)}")
    print(f"  text[:80]: {text[:80]}")
    print(f"  tags: {tags}")
    print(f"  image_bytes: {'有图' if img else '无图'} ({len(img) // 1024 if img else 0}KB)")
    src = getattr(item, "source_note", "")
    print(f"  source_note: {src}")
    return len(text) > 0 and img is not None


def main():
    print("=" * 60)
    print("阶段 6 自动化测试开始")
    print("=" * 60)

    results = []

    # 1. 早安单条
    t0 = time.time()
    try:
        items = generate_morning_content(count=1)
        item = items[0] if items else None
        ok = fmt(item, "1) generate_morning_content(count=1)")
    except Exception as e:
        ok = False
        print(f"\n--- 1) generate_morning_content 异常 ---\n  ❌ {e}")
    dt = time.time() - t0
    print(f"  耗时: {dt:.1f}s")
    results.append(("早安单条", ok, dt))

    # 2. 晚安单条
    t0 = time.time()
    try:
        items = generate_night_content(count=1)
        item = items[0] if items else None
        ok = fmt(item, "2) generate_night_content(count=1)")
    except Exception as e:
        ok = False
        print(f"\n--- 2) generate_night_content 异常 ---\n  ❌ {e}")
    dt = time.time() - t0
    print(f"  耗时: {dt:.1f}s")
    results.append(("晚安单条", ok, dt))

    # 3. 推荐单条（书籍）
    t0 = time.time()
    try:
        item = generate_single_recommend("book")
        ok = fmt(item, "3) generate_single_recommend('book')")
    except Exception as e:
        ok = False
        print(f"\n--- 3) generate_single_recommend 异常 ---\n  ❌ {e}")
    dt = time.time() - t0
    print(f"  耗时: {dt:.1f}s")
    results.append(("推荐单条", ok, dt))

    # 4. 分享单条（科普冷知识）
    t0 = time.time()
    try:
        item = generate_single_share("science")
        ok = fmt(item, "4) generate_single_share('science')")
    except Exception as e:
        ok = False
        print(f"\n--- 4) generate_single_share 异常 ---\n  ❌ {e}")
    dt = time.time() - t0
    print(f"  耗时: {dt:.1f}s")
    results.append(("分享单条", ok, dt))

    # 汇总
    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)
    all_ok = True
    for name, ok, dt in results:
        flag = "✅" if ok else "❌"
        print(f"  {flag} {name}: {'通过' if ok else '失败'}  ({dt:.1f}s)")
        if not ok:
            all_ok = False

    print()
    if all_ok:
        print("🎉 全部 4 项测试通过！")
    else:
        print("⚠️ 有失败项，请看上面输出排查")
    print("=" * 60)


if __name__ == "__main__":
    main()
