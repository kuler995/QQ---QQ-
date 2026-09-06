# -*- coding: utf-8 -*-
"""生成内容的工作线程
QThread 子线程调用 Agnes AI，避免主界面卡死
"""
from PySide6.QtCore import QThread, Signal

from src.core.content_generator import (
    generate_morning_content, generate_night_content, ContentItem
)
from src.utils.logger import logger


class GenerateWorker(QThread):
    """后台生成内容的工作线程

    两种使用方式：
      1. 按模块生成：GenerateWorker(module="weather"/"recommend"/...) → 走 run() 分支
      2. 单条换一条：GenerateWorker(single_func=callable) → 直接调用 callable()，
         期望返回一个 ContentItem 或 [ContentItem,...]

    信号：
        progress(str): 进度提示
        finished_items(list): 完成后返回 ContentItem 列表
        error(str): 生成失败时的错误信息
    """
    progress = Signal(str)
    finished_items = Signal(list)
    error = Signal(str)

    def __init__(self, module: str = "", parent=None, single_func=None):
        super().__init__(parent)
        self.module = module  # morning / night / weather / recommend / share / all
        self.single_func = single_func  # Callable[[], ContentItem | List[ContentItem] | None]

    def run(self):
        """线程主函数"""
        # 模式 A：单条换一条（优先）
        if self.single_func is not None:
            try:
                self.progress.emit("🔄 重新生成中...")
                res = self.single_func()
                if res is None:
                    self.finished_items.emit([])
                elif isinstance(res, ContentItem):
                    self.finished_items.emit([res])
                elif isinstance(res, list):
                    self.finished_items.emit(res)
                else:
                    self.finished_items.emit([])
                logger.info(f"✅ single_func 完成，返回 {len(self.finished_items) if False else (1 if isinstance(res, ContentItem) else (len(res) if isinstance(res, list) else 0))} 条")
                return
            except Exception as e:
                logger.exception("single_func 异常")
                self.error.emit(str(e))
                return

        # 模式 B：按 module 分支生成（原逻辑）
        try:
            if self.module == "morning":
                self.progress.emit("🌤️ 查天气 + 写早安文案...")
                items = generate_morning_content()
            elif self.module == "night":
                self.progress.emit("🌙 查天气 + 写晚安文案...")
                items = generate_night_content()
            elif self.module == "weather":
                # 合成模块：早晚安面板的「生成/全部重来」调用这里，保证早安+晚安都有
                self.progress.emit("🌤️ 查天气 + 写早安文案...")
                morning = generate_morning_content()
                self.progress.emit("🌙 写晚安文案 + 画配图...")
                night = generate_night_content()
                items = morning + night
            elif self.module == "recommend":
                self.progress.emit("📚 生成小青超推荐（书/影/纪）...")
                from src.core.recommend_generator import generate_recommend
                items = generate_recommend()
            elif self.module == "share":
                self.progress.emit("💡 生成小青爱分享（冷知识/生活妙招/学习技巧/健康/校史/节气）...")
                from src.core.share_generator import generate_share
                items = generate_share()
            else:
                # 全部生成：早安 + 晚安 + 推荐 + 分享（四大模块）
                self.progress.emit("🎯 生成全部内容...")
                self.progress.emit("🌤️ 生成早安...")
                morning = generate_morning_content()
                self.progress.emit("🌙 生成晚安...")
                night = generate_night_content()
                self.progress.emit("📚 生成推荐...")
                from src.core.recommend_generator import generate_recommend
                recs = generate_recommend()
                self.progress.emit("💡 生成分享...")
                from src.core.share_generator import generate_share
                shares = generate_share()
                items = morning + night + recs + shares

            if items:
                self.finished_items.emit(items)
                logger.info(f"✅ {self.module} 生成完成，共 {len(items)} 条")
            else:
                self.error.emit("生成失败：没有产出内容，请检查 API KEY")
        except Exception as e:
            logger.error(f"❌ 生成线程崩溃: {e}", exc_info=True)
            self.error.emit(str(e))
