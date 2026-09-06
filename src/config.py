# -*- coding: utf-8 -*-
"""配置管理模块
- 读写 config.json（不存在则从 config.example.json 复制）
- 提供全局 CONFIG 单例
- 保存时加异常处理，确保配置文件损坏时不崩溃
"""
import json
import os
import shutil
import sys
from typing import Any, Dict

from src.utils.logger import logger


def get_app_dir() -> str:
    """获取程序运行目录
    - 开发时：项目根目录（src/config.py → 往上一级）
    - 打包后：exe 所在目录
    """
    if getattr(sys, "frozen", False):
        # PyInstaller 打包后，sys.executable 是 exe 路径
        return os.path.dirname(sys.executable)
    else:
        # 开发模式：src/ 的上一级 = 项目根
        return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def get_config_paths() -> Dict[str, str]:
    """返回配置文件路径和模板路径"""
    app_dir = get_app_dir()
    # config.json 放在 app_dir（exe 同级，方便用户找到）
    config_path = os.path.join(app_dir, "config.json")
    # config.example.json：开发时在项目根，打包后在 _internal 目录
    if getattr(sys, "frozen", False):
        # PyInstaller 打包后，模板在 _internal 目录
        example_path = os.path.join(getattr(sys, "_MEIPASS", app_dir), "config.example.json")
    else:
        example_path = os.path.join(app_dir, "config.example.json")
    return {
        "config": config_path,
        "example": example_path
    }


def load_config() -> Dict[str, Any]:
    """读取配置文件
    - 不存在 config.json → 从 example 复制一份
    - example 也不存在 → 用内置默认值（极端兜底）
    - 文件损坏 → 弹日志错误，返回默认值

    Returns:
        配置字典（结构与 config.example.json 一致）
    """
    paths = get_config_paths()

    # 1. config.json 不存在，尝试从 example 复制
    if not os.path.exists(paths["config"]):
        logger.warning(f"config.json 不存在，尝试从模板复制：{paths['config']}")
        if os.path.exists(paths["example"]):
            try:
                shutil.copy2(paths["example"], paths["config"])
                logger.info(f"✅ 已从模板创建 config.json：{paths['config']}")
            except Exception as e:
                logger.error(f"❌ 复制配置模板失败：{e}，使用内置默认值")
                return _default_config()
        else:
            logger.warning(f"模板文件也不存在：{paths['example']}，使用内置默认值")
            return _default_config()

    # 2. 读取并解析
    try:
        with open(paths["config"], "r", encoding="utf-8") as f:
            cfg = json.load(f)
        logger.info(f"✅ 配置加载成功，共 {len(cfg)} 个大项")
        # 校验必填字段，缺失的用默认补
        return _merge_default(cfg)
    except json.JSONDecodeError as e:
        logger.error(f"❌ config.json 格式损坏：{e}，使用默认值")
        return _default_config()
    except Exception as e:
        logger.error(f"❌ 读取配置失败：{e}，使用默认值")
        return _default_config()


def save_config(cfg: Dict[str, Any]) -> bool:
    """保存配置到 config.json

    Args:
        cfg: 完整配置字典

    Returns:
        True=保存成功，False=失败
    """
    paths = get_config_paths()
    try:
        # 先备份一份（加 .bak 后缀），防止写一半断电损坏
        if os.path.exists(paths["config"]):
            shutil.copy2(paths["config"], paths["config"] + ".bak")

        with open(paths["config"], "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)

        # 成功就删掉 .bak
        bak = paths["config"] + ".bak"
        if os.path.exists(bak):
            os.remove(bak)

        logger.info(f"✅ 配置保存成功：{paths['config']}")
        return True
    except Exception as e:
        logger.error(f"❌ 保存配置失败：{e}")
        return False


# ============ 内部：默认值与合并 ============

def _default_config() -> Dict[str, Any]:
    """内置兜底默认值（极端情况使用）"""
    return {
        "agnes_ai": {
            "api_key": "",
            "base_url": "https://apihub.agnes-ai.cn/v1",
            "image_model": "agnes-image-2.1-flash",
            "text_model": "agnes-2.0-flash"
        },
        "weather": {
            "api_key": "",
            "api_host": "",
            "city": "焦作",
            "location_id": "101181101"
        },
        "storage": {
            "base_path": "",
            "image_quality": 85
        },
        "tags": {
            "required": ["#早安理工#", "#晚安理工#", "#小青超推荐#", "#每日话题#"],
            "morning_extra": [],
            "night_extra": [],
            "recommend_extra": ["#小青爱分享#"],
            "share_extra": ["#小青爱分享#"]
        },
        "generation": {
            "candidates_per_item": 3,
            "recommend_daily_min": 1,
            "recommend_daily_max": 2,
            "share_daily_min": 1,
            "share_daily_max": 2
        },
        "wallpaper": "clear_blue"  # 壁纸风格：clear_blue / morning_mist / dusk / sea_blue / snow
    }


def _merge_default(user_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """把用户配置与默认值合并，缺失的字段用默认补，防止 KeyError"""
    default = _default_config()
    merged = {}

    for key in default:
        if key not in user_cfg:
            merged[key] = default[key]
        elif isinstance(default[key], dict) and isinstance(user_cfg[key], dict):
            # 深合并：子字典也逐一补默认
            merged[key] = {**default[key], **user_cfg[key]}
        else:
            merged[key] = user_cfg[key]
    return merged


# 全局单例：启动时加载一次，其他模块直接 `from src.config import CONFIG` 用
CONFIG: Dict[str, Any] = load_config()
