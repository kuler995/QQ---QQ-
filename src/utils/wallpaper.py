# -*- coding: utf-8 -*-
"""壁纸模块：内置淡蓝渐变壁纸 + 影视飓风免费实拍壁纸
模拟苹果天气的毛玻璃质感——用壁纸做底，上层半透明卡片叠加
"""
import os
import sys
from PySide6.QtGui import QPixmap, QPainter, QLinearGradient, QColor, QRadialGradient, Qt
from PySide6.QtCore import QSize


def _get_wallpaper_dir() -> str:
    """获取壁纸目录路径（兼容开发模式和 PyInstaller 打包）"""
    if getattr(sys, "frozen", False):
        # 打包后：资源在 _MEIPASS/assets/wallpapers
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        return os.path.join(base, "assets", "wallpapers")
    else:
        # 开发模式：src/assets/wallpapers
        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "assets", "wallpapers")


# 影视飓风壁纸目录
_WALLPAPER_DIR = _get_wallpaper_dir()


# 内置壁纸列表（key → 中文名）
# 第一组：淡蓝渐变（程序绘制，体积小、加载快）
# 第二组：影视飓风实拍壁纸（src/assets/wallpapers/ 下的本地图片）
WALLPAPERS = {
    # —— 渐变壁纸 ——
    "clear_blue": "☀️ 晴蓝",
    "morning_mist": "🌫️ 晨雾",
    "dusk": "🌅 暮色",
    "sea_blue": "🌊 海蓝",
    "snow": "❄️ 雪白",
    # —— 影视飓风实拍壁纸 ——
    "ysjf_001": "🏔️ 山间云雾",
    "ysjf_002": "⛰️ 雪峰",
    "ysjf_003": "🏔️ 雪山云海",
    "ysjf_004": "🏜️ 戈壁原野",
    "ysjf_005": "🌀 橙韵流体",
    "ysjf_006": "🌀 蓝绿流光",
    "ysjf_007": "🌀 蓝色漩涡",
    "ysjf_008": "🌀 暖色漩涡",
    "ysjf_009": "🐦 海岛飞鸟",
    "ysjf_010": "🦀 红蟹青苔",
    "ysjf_011": "🐦 蜂鸟采花",
    "ysjf_012": "🪲 独角仙",
    "ysjf_013": "🌿 翠绿苔藓",
    "ysjf_014": "🍃 深绿叶脉",
    "ysjf_015": "⚡ 影视飓风·白",
    "ysjf_016": "⚡ 影视飓风·黑",
}


def _is_ysjf(key: str) -> bool:
    """判断是否为影视飓风实拍壁纸"""
    return key.startswith("ysjf_")


def _load_ysjf(key: str, size: QSize) -> QPixmap:
    """加载影视飓风实拍壁纸，按比例缩放铺满窗口（裁剪居中）"""
    fp = os.path.join(_WALLPAPER_DIR, key + ".jpg")
    if not os.path.exists(fp):
        # 壁纸文件丢失，回退到晴蓝渐变
        return _draw_clear_blue(size)
    pix = QPixmap(fp)
    if pix.isNull():
        return _draw_clear_blue(size)
    # 按比例裁剪缩放到目标尺寸（cover 模式，避免变形）
    scaled = pix.scaled(size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    x = (scaled.width() - size.width()) // 2
    y = (scaled.height() - size.height()) // 2
    return scaled.copy(x, y, size.width(), size.height())


def get_wallpaper(key: str, size: QSize) -> QPixmap:
    """根据 key 生成对应壁纸
    Args:
        key: 壁纸 key（WALLPAPERS 的 key），未知则用 clear_blue
        size: 壁纸尺寸（通常是窗口大小）
    Returns:
        QPixmap 壁纸
    """
    if key not in WALLPAPERS:
        key = "clear_blue"

    # 影视飓风实拍壁纸
    if _is_ysjf(key):
        return _load_ysjf(key, size)

    # 内置渐变壁纸
    if key == "clear_blue":
        return _draw_clear_blue(size)
    elif key == "morning_mist":
        return _draw_morning_mist(size)
    elif key == "dusk":
        return _draw_dusk(size)
    elif key == "sea_blue":
        return _draw_sea_blue(size)
    elif key == "snow":
        return _draw_snow(size)

    return _draw_clear_blue(size)


def _draw_clear_blue(size: QSize) -> QPixmap:
    """☀️ 晴蓝：晴天的淡蓝天空，苹果天气晴日风格"""
    pix = QPixmap(size)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    # 从上到下：天蓝 → 淡蓝 → 近白
    grad = QLinearGradient(0, 0, 0, size.height())
    grad.setColorAt(0.0, QColor("#A8D8F0"))
    grad.setColorAt(0.4, QColor("#C5E4F5"))
    grad.setColorAt(0.8, QColor("#E0F0FA"))
    grad.setColorAt(1.0, QColor("#F0F7FC"))
    p.fillRect(pix.rect(), grad)
    # 右上角柔光
    glow = QRadialGradient(size.width() * 0.85, size.height() * 0.1, size.width() * 0.5)
    glow.setColorAt(0.0, QColor(255, 255, 255, 120))
    glow.setColorAt(1.0, QColor(255, 255, 255, 0))
    p.fillRect(pix.rect(), glow)
    p.end()
    return pix


def _draw_morning_mist(size: QSize) -> QPixmap:
    """🌫️ 晨雾：薄雾晨光，苹果天气多云清晨风格"""
    pix = QPixmap(size)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    grad = QLinearGradient(0, 0, size.width(), size.height())
    grad.setColorAt(0.0, QColor("#D4E6F1"))
    grad.setColorAt(0.5, QColor("#E8F1F8"))
    grad.setColorAt(1.0, QColor("#F5F0E8"))
    p.fillRect(pix.rect(), grad)
    # 左侧暖光
    glow = QRadialGradient(size.width() * 0.15, size.height() * 0.6, size.width() * 0.4)
    glow.setColorAt(0.0, QColor(255, 240, 220, 150))
    glow.setColorAt(1.0, QColor(255, 240, 220, 0))
    p.fillRect(pix.rect(), glow)
    p.end()
    return pix


def _draw_dusk(size: QSize) -> QPixmap:
    """🌅 暮色：傍晚暖橙蓝渐变，苹果天气黄昏风格"""
    pix = QPixmap(size)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    grad = QLinearGradient(0, 0, 0, size.height())
    grad.setColorAt(0.0, QColor("#A8C8E8"))
    grad.setColorAt(0.4, QColor("#D4B8D8"))
    grad.setColorAt(0.7, QColor("#F0C8B0"))
    grad.setColorAt(1.0, QColor("#F5E0D0"))
    p.fillRect(pix.rect(), grad)
    p.end()
    return pix


def _draw_sea_blue(size: QSize) -> QPixmap:
    """🌊 海蓝：深海蓝渐变，沉稳大气"""
    pix = QPixmap(size)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    grad = QLinearGradient(0, 0, 0, size.height())
    grad.setColorAt(0.0, QColor("#8FB8D8"))
    grad.setColorAt(0.5, QColor("#B0D0E8"))
    grad.setColorAt(1.0, QColor("#D8E8F2"))
    p.fillRect(pix.rect(), grad)
    p.end()
    return pix


def _draw_snow(size: QSize) -> QPixmap:
    """❄️ 雪白：纯白到极淡蓝，干净极简"""
    pix = QPixmap(size)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    grad = QLinearGradient(0, 0, 0, size.height())
    grad.setColorAt(0.0, QColor("#F0F5FA"))
    grad.setColorAt(0.5, QColor("#F5F8FC"))
    grad.setColorAt(1.0, QColor("#FAFBFD"))
    p.fillRect(pix.rect(), grad)
    p.end()
    return pix


def wallpaper_keys() -> list:
    """返回所有壁纸 key 列表"""
    return list(WALLPAPERS.keys())


def wallpaper_cn(key: str) -> str:
    """key → 中文名"""
    return WALLPAPERS.get(key, "☀️ 晴蓝")


# ============================================================
# 壁纸亮度分析 + 动态主题色（根据壁纸明暗自动切换文字/面板颜色）
# ============================================================

# 渐变壁纸的预设亮度（0~255，越大越亮），避免每次都渲染分析
_GRADIENT_BRIGHTNESS = {
    "clear_blue": 225,    # ☀️ 晴蓝：很亮
    "morning_mist": 230,  # 🌫️ 晨雾：很亮
    "dusk": 215,          # 🌅 暮色：中亮
    "sea_blue": 210,      # 🌊 海蓝：中亮
    "snow": 245,          # ❄️ 雪白：极亮
}


def get_wallpaper_brightness(key: str, size: QSize = None) -> int:
    """分析壁纸的平均亮度（0~255）
    - 渐变壁纸：用预设值
    - 实拍壁纸：缩放后采样计算平均亮度
    Returns:
        0~255 的亮度值
    """
    if key in _GRADIENT_BRIGHTNESS:
        return _GRADIENT_BRIGHTNESS[key]

    if not _is_ysjf(key):
        return 220  # 未知壁纸默认偏亮

    # 实拍壁纸：加载后采样计算
    fp = os.path.join(_WALLPAPER_DIR, key + ".jpg")
    if not os.path.exists(fp):
        return 220
    pix = QPixmap(fp)
    if pix.isNull():
        return 220
    # 缩放到小尺寸加速计算
    small = pix.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    img = small.toImage()
    if img.isNull():
        return 220

    total_r, total_g, total_b, count = 0, 0, 0, 0
    for y in range(img.height()):
        for x in range(img.width()):
            c = img.pixelColor(x, y)
            total_r += c.red()
            total_g += c.green()
            total_b += c.blue()
            count += 1
    if count == 0:
        return 220
    avg_r = total_r // count
    avg_g = total_g // count
    avg_b = total_b // count
    # 人眼感知亮度公式
    brightness = int(0.299 * avg_r + 0.587 * avg_g + 0.114 * avg_b)
    return brightness


def is_dark_wallpaper(key: str, size: QSize = None) -> bool:
    """判断壁纸是否偏暗（亮度 < 140 视为暗色）"""
    return get_wallpaper_brightness(key, size) < 140


def get_theme_colors(key: str, size: QSize = None) -> dict:
    """返回统一的浅色主题色方案（保留模块淡蓝风格）
    设计原则：面板始终为白色半透明 + 深色文字，保证任何壁纸上文字都清晰
    面板不透明度适中，既能衬托文字，又能透出壁纸
    Returns:
        dict 包含 text_color, secondary_color, panel_bg, border_color 等
    """
    return {
        "text_color": "#2C3E50",          # 主文字：深蓝灰
        "secondary_color": "#5D6D7E",     # 次要文字：中灰
        "module_title_color": "#2C5F8D",  # 模块标题：深蓝
        "panel_bg": "rgba(255, 255, 255, 185)",      # 面板：白色半透明（偏高，保证文字清晰）
        "card_bg": "rgba(255, 255, 255, 200)",       # 卡片：白色半透明
        "bar_bg": "rgba(255, 255, 255, 190)",        # 顶/底栏：白色半透明
        "border_color": "rgba(255, 255, 255, 220)",  # 边框：半透明白
        "status_ready": "#27AE60",          # 就绪状态：绿
        "status_loading": "#E67E22",        # 加载状态：橙
        "empty_color": "rgba(169, 197, 232, 220)",  # 空状态提示
    }
