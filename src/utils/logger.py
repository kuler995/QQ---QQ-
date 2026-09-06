# -*- coding: utf-8 -*-
"""日志初始化模块
- 按天分日志文件，存 logs/YYYY-MM-DD.log
- 同时输出到控制台
- 统一格式：时间 - 级别 - 模块 - 消息
"""
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler


def get_log_dir() -> str:
    """获取日志目录路径
    - 开发时：项目根目录下的 logs/
    - 打包后：exe 同级目录的 logs/
    """
    import sys
    if getattr(sys, "frozen", False):
        # PyInstaller 打包后：exe 同级目录
        base = os.path.dirname(sys.executable)
    else:
        # 开发模式：src/utils/logger.py → 往上两级到项目根
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    log_dir = os.path.join(base, "logs")
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def init_logger(name: str = "auto_greeting") -> logging.Logger:
    """初始化并返回全局 Logger

    Args:
        name: Logger 名称

    Returns:
        配置好的 logging.Logger 实例
    """
    logger = logging.getLogger(name)

    # 避免重复添加 handler（模块多次 import 时）
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # ===== 日志格式 =====
    fmt = logging.Formatter(
        "%(asctime)s - %(levelname)-7s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # ===== 1. 文件 Handler：按天轮转，单个最大 10MB，保留 30 天 =====
    log_dir = get_log_dir()
    log_file = os.path.join(log_dir, f"{datetime.now().strftime('%Y-%m-%d')}.log")
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=30,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    # ===== 2. 控制台 Handler：只看 INFO 及以上 =====
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)
    logger.addHandler(console_handler)

    logger.info(f"✅ 日志系统初始化完成，日志文件：{log_file}")
    return logger


# 全局默认实例，其他模块直接 import logger 即可用
logger = init_logger()
