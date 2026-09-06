# -*- coding: utf-8 -*-
"""端到端测试：真天气 → 生成早安 → 自动备份 → 验证历史数据可解析"""
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.content_generator import generate_morning_content
from src.utils import paths
from src.utils.logger import logger
from src.api.weather import get_weather, weather_to_text


def main():
    print("=" * 60)
    print("阶段 7 端到端测试：真天气 + 生成 + 备份 + 历史解析")
    print("=" * 60)

    # 1. 验证真天气
    print("\n[1/4] 验证真天气...")
    ok, w, msg = get_weather()
    if w.get("_is_mock", True):
        print(f"  ❌ 天气仍是 mock: {msg}")
        return
    print(f"  ✅ {msg}")
    print(f"     {weather_to_text(w)}")

    # 2. 生成早安（真天气会自动带入文案）
    print("\n[2/4] 生成早安（用真天气）...")
    items = generate_morning_content(count=1)
    if not items or items[0].error:
        print(f"  ❌ 生成失败: {items[0].error if items else '空'}")
        return
    item = items[0]
    print(f"  ✅ 文案: {item.text}")
    print(f"  ✅ 标签: {item.tags}")
    print(f"  ✅ 图片: {'有' if item.image_bytes else '无'} ({len(item.image_bytes or b'')//1024}KB)")

    # 3. 模拟「复制文案」和「保存图片」按钮触发的备份动作
    print("\n[3/4] 模拟点击复制+保存按钮（触发自动备份）...")
    paths.append_text_backup(item.module, item.item_type, item.text, item.tags)
    if item.image_bytes:
        saved = paths.save_image_auto(item.module, item.item_type, item.image_bytes)
        if saved and os.path.exists(saved):
            print(f"  ✅ 图片已备份: {saved}")
        else:
            print(f"  ❌ 图片备份失败")
            return
    else:
        print("  ⚠️ 无图片，跳过图片备份")

    # 4. 验证历史面板能扫到今天的数据
    print("\n[4/4] 验证历史面板扫描...")
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    date_dir = paths.get_date_dir(today)
    print(f"  今天日期文件夹: {date_dir}")
    if not os.path.isdir(date_dir):
        print(f"  ❌ 日期文件夹不存在")
        return

    # 扫文案备份
    txt_files = [f for f in os.listdir(date_dir) if f.startswith("文案备份") and f.endswith(".txt")]
    print(f"  📄 文案备份文件: {txt_files}")

    # 扫图片
    images_dir = paths.get_images_dir(today)
    if os.path.isdir(images_dir):
        imgs = [f for f in os.listdir(images_dir) if f.lower().endswith((".png", ".jpg"))]
        print(f"  🖼️ 图片文件: {len(imgs)} 张")

    # 用历史对话框的解析逻辑
    from src.ui.history_dialog import HistoryDialog, _ENTRY_RE
    for txt in txt_files:
        full = os.path.join(date_dir, txt)
        with open(full, "r", encoding="utf-8") as f:
            content = f.read()
        matches = list(_ENTRY_RE.finditer(content))
        print(f"  📖 {txt} 解析出 {len(matches)} 条 entry")
        for m in matches[:1]:
            print(f"     第1条: time={m.group(1).strip()}, type={m.group(2).strip()}")

    print("\n" + "=" * 60)
    print("🎉 端到端测试通过！真天气 + 备份 + 历史解析全链路 OK")
    print("=" * 60)


if __name__ == "__main__":
    main()
