# -*- coding: utf-8 -*-
"""Agnes AI 接口封装
基于 docs/05_API接口文档.md 和实测验证结果：
- 文案：.cn 端点 + agnes-2.0-flash，OpenAI 兼容格式
- 画图：.com 端点 + agnes-image-2.1-flash，不传 return_base64，返回 URL 后下载
"""
import json
import time
import requests
from typing import List, Optional, Tuple

from src.config import CONFIG
from src.utils.logger import logger


class AgnesAIClient:
    """Agnes AI 客户端"""

    def __init__(self):
        cfg = CONFIG.get("agnes_ai", {})
        self.api_key = cfg.get("api_key", "")
        # 文案用 .cn（国内稳定），画图用 .com（.cn 画图超时）
        self.text_base_url = cfg.get("base_url", "https://apihub.agnes-ai.cn/v1").rstrip("/")
        self.image_base_url = cfg.get("image_base_url", "https://apihub.agnes-ai.com/v1").rstrip("/")
        self.text_model = cfg.get("text_model", "agnes-2.0-flash")
        self.image_model = cfg.get("image_model", "agnes-image-2.1-flash")
