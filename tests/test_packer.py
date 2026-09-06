# -*- coding: utf-8 -*-
"""测试阶段8 两个打包函数"""
import sys
import os
import zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.packer import pack_selected, pack_all_drafts
from src.core.content_generator import ContentItem


def test_pack_all_drafts():
    """测试打包全部草稿（先测这个，因为今天文件夹里已经有内容）"""
    print("=" * 60)
    print("[1] 测试 pack_all_drafts() 打包当天所有内容")
    print("=" * 60)

    ok, result = pack_all_drafts()
    if not ok:
        print(f"❌ 失败: {result}")
        return False

    print(f"✅ 成功: {result}")
    print(f"   文件大小: {os.path.getsize(result)/1024:.1f} KB")

    # 验证 zip 内容
    with zipfile.ZipFile(result, "r") as zf:
        names = zf.namelist()
        print(f"   zip 内文件数: {len(names)}")
        for n in names[:10]:
            print(f"     - {n}")
        if len(names) > 10:
            print(f"     ... 还有 {len(names)-10} 个")

    return True


def test_pack_selected_empty():
    """测试空精选列表（应该返回失败提示）"""
    print("\n" + "=" * 60)
    print("[2] 测试 pack_selected([]) 空列表应该报错")
    print("=" * 60)

    ok, result = pack_selected([])
    if ok:
        print(f"❌ 应该失败但成功了: {result}")
        return False
    print(f"✅ 正确返回失败: {result}")
    return True


def test_pack_selected_with_items():
    """测试带真实 item 的精选打包"""
    print("\n" + "=" * 60)
    print("[3] 测试 pack_selected(2 个 fake item) 带图片")
    print("=" * 60)

    # 制造 2 个 fake item，带图片字节
    fake_png = b'\x89PNG\r\n\x1a\n' + b'\x00' * 200  # 最简 PNG header
    items = [
        ContentItem(
            text="晴暖22℃，小青祝你早安 🌤️",
            tags=["#早安理工#", "#每日话题#"],
            module="morning",
            item_type="早安",
            image_bytes=fake_png,
            source_note="小红书咖啡早餐风 AI 生成",
            saved=True
        ),
        ContentItem(
            text="《被讨厌的勇气》——同学们好，我是小青！今天想给大家推荐一本超治愈的书...",
            tags=["#小青超推荐#", "#每日话题#"],
            module="recommend",
            item_type="书籍",
            image_bytes=fake_png,
            source_note="小青超推荐·书香治愈风 AI 生成",
            saved=True
        ),
    ]

    ok, result = pack_selected(items)
    if not ok:
        print(f"❌ 失败: {result}")
        return False

    print(f"✅ 成功: {result}")
    print(f"   文件大小: {os.path.getsize(result)/1024:.1f} KB")

    # 验证 zip 内容
    with zipfile.ZipFile(result, "r") as zf:
        names = zf.namelist()
        print(f"   zip 内文件数: {len(names)}")
        for n in names:
            print(f"     - {n}")

        # 读文案汇总
        if "文案汇总.txt" in names:
            content = zf.read("文案汇总.txt").decode("utf-8")
            print(f"\n   📄 文案汇总.txt 内容（前 400 字）:")
            print("   " + "-" * 50)
            for line in content[:400].split("\n"):
                print(f"   {line}")
            print("   " + "-" * 50)

    return True


def main():
    print("=" * 60)
    print("阶段 8 打包功能测试开始")
    print("=" * 60)

    r1 = test_pack_all_drafts()
    r2 = test_pack_selected_empty()
    r3 = test_pack_selected_with_items()

    print("\n" + "=" * 60)
    print("汇总")
    print("=" * 60)
    print(f"  {'✅' if r1 else '❌'} 全部草稿打包")
    print(f"  {'✅' if r2 else '❌'} 空精选列表报错")
    print(f"  {'✅' if r3 else '❌'} 带图片精选打包")
    if r1 and r2 and r3:
        print("\n🎉 阶段 8 打包功能全部测试通过！")
    else:
        print("\n⚠️ 有失败项，请看上面输出")


if __name__ == "__main__":
    main()
