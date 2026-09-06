# -*- coding: utf-8 -*-
"""程序入口
双击运行本文件（开发时）：
    python src/main.py
"""
import sys
import os

# ===== Windows 控制台 UTF-8 支持（解决中文/emoji 乱码）=====
if sys.platform == "win32":
    os.system("chcp 65001 >nul")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 确保能找到 src 包（直接 python src/main.py 时，把项目根加到 sys.path）
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from src.ui.main_window import MainWindow
from src.utils.logger import logger


def main():
    """程序启动函数"""
    logger.info("=" * 60)
    logger.info("🚀 自动早晚安小助手 启动")
    logger.info("=" * 60)

    # ===== 高 DPI 支持（Windows 高分屏不模糊）=====
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # ===== 创建 QApplication =====
    app = QApplication(sys.argv)
    app.setApplicationName("自动早晚安小助手")
    app.setOrganizationName("XiaoQing")

    # ===== 全局字体：微软雅黑（确保中文不乱码）=====
    from PySide6.QtGui import QFont
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    # ===== 创建并显示主窗口 =====
    window = MainWindow()
    window.show()

    logger.info("✅ 程序启动完成，主窗口已显示")
    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"❌ 程序崩溃：{e}", exc_info=True)
        raise
