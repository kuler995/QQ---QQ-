# -*- coding: utf-8 -*-
"""模块面板组件
展示一个模块（早晚安/推荐/分享）：标题 + 全部重来按钮 + 卡片列表 + 加载状态
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea
)
from PySide6.QtGui import QFont

from src.core.content_generator import ContentItem
from src.ui.widgets.content_card import ContentCard
from src.utils.logger import logger


class ModulePanel(QFrame):
    """一个模块的完整面板"""

    # 信号
    request_generate = Signal(str)   # 用户点「生成」时，带 module 名
    request_refresh_all = Signal(str)  # 全部重来，带 module 名
    request_refresh_single = Signal(object, object)  # (item, card) 单条换一条向上转发

    def __init__(self, module_key: str, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self.module_key = module_key  # morning/night/recommend/share
        self.setObjectName("modulePanel")
        self._cards = []  # 当前展示的 ContentCard 列表
        self._loading = False

        # 苹果风：柔和阴影增强层级感
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        from PySide6.QtGui import QColor
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(74, 144, 217, 40))  # 淡蓝阴影，柔和不刺眼
        self.setGraphicsEffect(shadow)

        self._init_ui(title, subtitle)
        self._apply_style()

    def _init_ui(self, title: str, subtitle: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # 标题行
        head = QHBoxLayout()
        head.setSpacing(8)

        self.lbl_title = QLabel(title, self)
        self.lbl_title.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #2C5F8D;"
        )
        head.addWidget(self.lbl_title)

        if subtitle:
            self.lbl_subtitle = QLabel(subtitle, self)
            self.lbl_subtitle.setStyleSheet("font-size: 12px; color: #7F8C8D;")
            head.addWidget(self.lbl_subtitle)

        head.addStretch(1)

        # 状态标签
        self.lbl_status = QLabel("等待生成", self)
        self.lbl_status.setStyleSheet("font-size: 12px; color: #7F8C8D;")
        head.addWidget(self.lbl_status)

        self.btn_generate = self._make_btn("⚡ 生成", "primary")
        self.btn_generate.clicked.connect(lambda: self.request_generate.emit(self.module_key))
        head.addWidget(self.btn_generate)

        self.btn_refresh_all = self._make_btn("🔄 全部重来", "normal")
        self.btn_refresh_all.clicked.connect(lambda: self.request_refresh_all.emit(self.module_key))
        head.addWidget(self.btn_refresh_all)

        layout.addLayout(head)

        # 卡片容器（垂直排列）
        self.cards_layout = QVBoxLayout()
        self.cards_layout.setSpacing(6)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)

        # 空状态提示
        self.lbl_empty = QLabel("📭 还没有内容，点「⚡ 生成」开始", self)
        self.lbl_empty.setAlignment(Qt.AlignCenter)
        self.lbl_empty.setStyleSheet("color: #A9C5E8; padding: 18px; font-size: 13px;")
        self.cards_layout.addWidget(self.lbl_empty)

        layout.addLayout(self.cards_layout)
        layout.addStretch(1)

    def set_loading(self, loading: bool, msg: str = "生成中..."):
        """设置加载状态"""
        self._loading = loading
        if loading:
            self.btn_generate.setEnabled(False)
            self.btn_generate.setText("⏳ 生成中")
            self.lbl_status.setText(msg)
            self.lbl_status.setStyleSheet("color: #E67E22; font-size: 12px;")
        else:
            self.btn_generate.setEnabled(True)
            self.btn_generate.setText("⚡ 生成")
            self.lbl_status.setText("就绪 ✅")
            self.lbl_status.setStyleSheet("color: #27AE60; font-size: 12px;")

    def show_items(self, items: list):
        """展示生成好的内容列表
        Args:
            items: ContentItem 列表
        """
        # 清空旧卡片
        self._clear_cards()
        self.lbl_empty.setVisible(False)

        for item in items:
            card = ContentCard(item, self)
            card.request_refresh.connect(self._on_card_refresh)
            self._cards.append(card)
            self.cards_layout.addWidget(card)

        if not items:
            self.lbl_empty.setVisible(True)

        self.set_loading(False)

    def _on_card_refresh(self, item, card):
        """某张卡片点「换一条」：向上转发给主窗口，让主窗口生成新 item 后回传 card.update_item"""
        logger.info(f"🔄 单条换一条请求：module={item.module}, type={item.item_type}")
        self.request_refresh_single.emit(item, card)

    def _clear_cards(self):
        """清空卡片"""
        for card in self._cards:
            card.deleteLater()
        self._cards = []

    def _make_btn(self, text: str, btn_type: str) -> QPushButton:
        btn = QPushButton(text, self)
        btn.setProperty("btnType", btn_type)
        btn.setProperty("btnSize", "small")
        btn.setCursor(Qt.PointingHandCursor)
        return btn

    def _apply_style(self):
        self.setStyleSheet("""
        #modulePanel {
            background-color: rgba(255, 255, 255, 130);
            border: 1px solid rgba(255, 255, 255, 180);
            border-radius: 16px;
        }
        """)
