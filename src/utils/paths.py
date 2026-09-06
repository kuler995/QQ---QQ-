# -*- coding: utf-8 -*-
"""路径管理工具
统一管理素材根目录、按日期的子目录、备份文件名等
"""
import os
from datetime import datetime

from src.config import get_app_dir, CONFIG
from src.utils.logger import logger


def get_materials_root() -> str:
    """获取「小青素材」根目录路径
    优先使用配置中的路径；否则用软件目录下的「小青素材」文件夹
    """
    cfg_storage = CONFIG.get("storage", {})
    custom = (cfg_storage.get("materials_dir") or "").strip()
    if custom:
        root = custom
    else:
        root = os.path.join(get_app_dir(), "小青素材")
    return root


def get_today_dir() -> str:
    """获取「小青素材/YYYY-MM-DD/」当天日期目录，不存在则创建"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    path = os.path.join(get_materials_root(), date_str)
    _ensure(path)
    return path


def get_date_dir(date_str: str = None) -> str:
    """获取「小青素材/指定日期/」目录，不存在则创建"""
    if not date_str:
        return get_today_dir()
    path = os.path.join(get_materials_root(), date_str)
    _ensure(path)
    return path


def get_text_backup_path(module_key: str = "", date_str: str = None) -> str:
    """获取文案备份文件路径（.txt，UTF-8，追加写入）"""
    folder = get_date_dir(date_str)
    module_part = f"_{module_key}" if module_key else ""
    return os.path.join(folder, f"文案备份{module_part}.txt")


def get_images_dir(date_str: str = None) -> str:
    """获取图片子目录（单独存放图片，方便找）"""
    folder = get_date_dir(date_str)
    img_dir = os.path.join(folder, "images")
    _ensure(img_dir)
    return img_dir


def unique_image_filename(prefix: str, date_str: str = None) -> str:
    """生成唯一图片文件名（日期+模块+序号.png）"""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    img_dir = get_images_dir(date_str)
    i = 1
    while True:
        name = f"{date_str}_{prefix}_{i:02d}.png"
        full = os.path.join(img_dir, name)
        if not os.path.exists(full):
            return full
        i += 1


def save_image_auto(module_key: str, item_type: str, image_bytes: bytes,
                    date_str: str = None) -> str:
    """把图片自动保存到当天日期目录的 images/ 里
    Returns: 保存好的绝对路径
    """
    if not image_bytes:
        return ""
    prefix = f"{module_key}_{item_type}"
    path = unique_image_filename(prefix, date_str)
    with open(path, "wb") as f:
        f.write(image_bytes)
    logger.info(f"💾 图片已保存（自动）: {path} ({len(image_bytes)} bytes)")
    return path


def append_text_backup(module_key: str, item_type: str, text: str, tags: list,
                       date_str: str = None) -> str:
    """把一条文案追加写入当天的文案备份文件
    Returns: 写入的文件路径
    """
    if not text:
        return ""
    path = get_text_backup_path(module_key, date_str)
    timestamp = datetime.now().strftime("%H:%M:%S")
    tag_line = " ".join(tags) if tags else ""
    entry = (
        f"---- [{timestamp}] {item_type} ----\n"
        f"{text}\n"
        f"{tag_line}\n\n"
    )
    with open(path, "a", encoding="utf-8") as f:
        f.write(entry)
    logger.info(f"📝 文案已备份（追加写入）: {path}")
    return path


def _ensure(path: str):
    """确保目录存在"""
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)
        logger.info(f"📁 创建目录: {path}")
