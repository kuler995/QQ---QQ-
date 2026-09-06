# -*- coding: utf-8 -*-
"""图片水印模块
按 docs/03_UI设计规范.md：右下角半透明白字水印，不挡画面主体
"""
import io
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

from src.utils.logger import logger


def add_watermark(image_bytes: bytes, watermark_text: str) -> bytes:
    """给图片加右下角半透明白字水印
    Args:
        image_bytes: 原图片字节
        watermark_text: 水印文字（如「早安理工 · 2026-08-29」）
    Returns:
        加水印后的图片字节（PNG 格式）
    """
    if not image_bytes or not watermark_text:
        return image_bytes

    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        width, height = img.size

        # 创建透明水印图层
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # 字号根据图片宽度自适应（图片越大字越大，但限制范围）
        font_size = max(16, min(36, width // 35))

        font = _load_font(font_size)

        # 测量文字大小
        try:
            text_bbox = draw.textbbox((0, 0), watermark_text, font=font)
            text_w = text_bbox[2] - text_bbox[0]
            text_h = text_bbox[3] - text_bbox[1]
        except Exception:
            text_w = len(watermark_text) * font_size * 0.6
            text_h = font_size

        # 右下角位置，留边距
        margin = max(12, width // 50)
        x = width - text_w - margin
        y = height - text_h - margin

        # === 优化点：给水印加一个淡蓝圆角背景条 ===
        # 目的：保证水印在明亮/浅色背景下也清晰可读，同时不遮挡画面主体
        # 背景：淡蓝色半透明 + 小圆角，紧贴文字（padding 小）
        bg_pad_x = max(6, font_size // 5)
        bg_pad_y = max(4, font_size // 8)
        bg_x = x - bg_pad_x
        bg_y = y - bg_pad_y
        bg_w = text_w + bg_pad_x * 2
        bg_h = text_h + bg_pad_y * 2
        bg_radius = min(bg_w, bg_h) // 4

        # 画圆角背景（淡蓝 #4A90D9, Alpha=60 → 23% 透明）
        draw.rounded_rectangle(
            [bg_x, bg_y, bg_x + bg_w, bg_y + bg_h],
            radius=bg_radius,
            fill=(74, 144, 217, 60)
        )

        # 半透明白色字 + 深色描边（保证任何背景下可见）
        # 先画描边（深色半透明）
        shadow_offset = max(1, font_size // 16)
        for dx, dy in [(-shadow_offset, 0), (shadow_offset, 0),
                       (0, -shadow_offset), (0, shadow_offset)]:
            draw.text((x + dx, y + dy), watermark_text,
                      fill=(0, 0, 0, 140), font=font)
        # 再画主文字（白色半透明）
        draw.text((x, y), watermark_text, fill=(255, 255, 255, 220), font=font)

        # 合并图层
        result = Image.alpha_composite(img, overlay).convert("RGB")

        # 输出
        out = io.BytesIO()
        result.save(out, format="PNG", quality=95)
        out_bytes = out.getvalue()
        logger.info(f"✅ 水印已添加: {watermark_text} (图片 {width}x{height})")
        return out_bytes
    except Exception as e:
        logger.error(f"❌ 水印添加失败: {e}", exc_info=True)
        return image_bytes


def _load_font(size: int):
    """加载中文字体（微软雅黑）"""
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",      # 微软雅黑
        "C:/Windows/Fonts/simhei.ttf",     # 黑体
        "C:/Windows/Fonts/simsun.ttc",     # 宋体
    ]
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    # 找不到中文字体，用默认
    return ImageFont.load_default()


def make_watermark_text(prefix: str, date_str: str = "") -> str:
    """生成水印文字
    Args:
        prefix: 前缀，如「早安理工」「小青超推荐」
        date_str: 日期，如「2026-08-29」，为空则取今天
    Returns:
        水印文字，如「早安理工 · 2026-08-29」
    """
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    return f"{prefix} · {date_str}"
