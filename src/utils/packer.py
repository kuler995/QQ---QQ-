# -*- coding: utf-8 -*-
"""打包工具：把当天生成的内容打成 zip

两种模式：
1. 精选内容：从主窗口 4 个面板的 ContentCard 里收集 item.saved=True 的，
   重新组织成「文案.txt + images/」结构打 zip
2. 全部草稿：直接打包当天日期文件夹下的所有文件（保持原结构）
"""
import os
import zipfile
import shutil
from datetime import datetime
from typing import List, Tuple

from src.utils import paths
from src.utils.logger import logger
from src.core.content_generator import ContentItem


# 模块中文名映射
_MODULE_CN = {
    "morning": "早安理工",
    "night": "晚安理工",
    "recommend": "小青超推荐",
    "share": "小青爱分享",
    "weather": "早晚安",
}


def pack_selected(items: List[ContentItem]) -> Tuple[bool, str]:
    """打包精选内容
    Args:
        items: 用户点过「保存图片」的 ContentItem 列表（item.saved=True 的）
    Returns:
        (success, zip_path or msg)
    """
    if not items:
        return False, "今天还没有保存任何精选内容，请先在卡片上点「💾 保存图片」"

    today = datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%H%M%S")
    zip_name = f"精选内容_{today}_{time_str}.zip"
    zip_path = os.path.join(paths.get_date_dir(today), zip_name)

    # 确保目录存在
    os.makedirs(paths.get_date_dir(today), exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # 1. 汇总文案到一个 txt 文件
            text_lines = []
            text_lines.append(f"# 自动早晚安小助手 - 精选内容")
            text_lines.append(f"# 日期：{today}")
            text_lines.append(f"# 打包时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            text_lines.append(f"# 共 {len(items)} 条精选内容")
            text_lines.append("=" * 60)
            text_lines.append("")

            # 2. 把每条 item 的文案+图片写进 zip
            for idx, item in enumerate(items, 1):
                module_cn = _MODULE_CN.get(item.module, item.module or "其他")
                type_str = item.item_type or ""
                text_lines.append(f"【{idx}】{module_cn} - {type_str}")
                text_lines.append("-" * 40)
                if item.text:
                    text_lines.append(item.text)
                if item.tags:
                    text_lines.append(" ".join(item.tags))
                if item.source_note:
                    text_lines.append(f"📷 配图：{item.source_note}")
                text_lines.append("")

                # 把图片加进 zip
                if item.image_bytes:
                    # 优先用 item 自己的图（内存里现成的）
                    img_name = f"images/{idx:02d}_{item.module or 'item'}_{type_str or 'X'}.png"
                    # 安全化文件名
                    img_name = _sanitize_zip_path(img_name)
                    zf.writestr(img_name, item.image_bytes)
                elif item.saved and hasattr(item, "saved_path") and item.saved_path:
                    # 如果有保存路径，从磁盘读
                    if os.path.exists(item.saved_path):
                        arc_name = f"images/{idx:02d}_{os.path.basename(item.saved_path)}"
                        zf.write(item.saved_path, arc_name)

            # 3. 把汇总文案写到 zip
            all_text = "\n".join(text_lines)
            zf.writestr("文案汇总.txt", all_text.encode("utf-8"))

        size_kb = os.path.getsize(zip_path) / 1024
        logger.info(f"📦 精选内容打包完成: {zip_path} ({size_kb:.1f} KB, {len(items)} 条)")
        return True, zip_path

    except Exception as e:
        logger.exception("精选打包失败")
        return False, f"打包失败：{e}"


def pack_all_drafts() -> Tuple[bool, str]:
    """打包当天日期文件夹下所有内容（保持原结构）
    Returns:
        (success, zip_path or msg)
    """
    today = datetime.now().strftime("%Y-%m-%d")
    date_dir = paths.get_date_dir(today)

    if not os.path.isdir(date_dir):
        return False, f"今天 ({today}) 还没有生成任何内容"

    # 统计要打包的文件
    file_count = 0
    total_size = 0
    for root, dirs, files in os.walk(date_dir):
        for f in files:
            if f.endswith(".zip"):  # 跳过之前打的包
                continue
            file_count += 1
            try:
                total_size += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass

    if file_count == 0:
        return False, f"今天 ({today}) 还没有生成任何内容"

    time_str = datetime.now().strftime("%H%M%S")
    zip_name = f"全部草稿_{today}_{time_str}.zip"
    # 放到上一级（小青素材/）避免打包时把 zip 自己打进去
    zip_path = os.path.join(paths.get_materials_root(), zip_name)

    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # 遍历日期目录下所有文件
            for root, dirs, files in os.walk(date_dir):
                for fname in files:
                    if fname.endswith(".zip"):
                        continue
                    full = os.path.join(root, fname)
                    # 压缩包内路径：保留 日期文件夹/原相对路径
                    arcname = os.path.relpath(full, paths.get_materials_root())
                    zf.write(full, arcname)

        size_kb = os.path.getsize(zip_path) / 1024
        logger.info(f"📦 全部草稿打包完成: {zip_path} ({size_kb:.1f} KB, {file_count} 个文件)")
        return True, zip_path

    except Exception as e:
        logger.exception("全部草稿打包失败")
        return False, f"打包失败：{e}"


def _sanitize_zip_path(name: str) -> str:
    """安全化 zip 内的文件路径，避免特殊字符"""
    # 替换 Windows 不允许的字符
    for c in '\\/:*?"<>|':
        name = name.replace(c, "_")
    return name
