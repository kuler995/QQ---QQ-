# -*- coding: utf-8 -*-
"""内容卡片组件
展示一条内容：图片预览 + 文案 + 标签 + 复制/保存/换一条按钮
"""
import os
from PySide6.QtCore import Qt, Signal, QTimer, QPoint
from PySide6.QtGui import QPixmap, QImage, QGuiApplication, QCursor
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QMessageBox, QFileDialog, QToolTip
)

from src.core.content_generator import ContentItem
from src.utils import paths
from src.utils.logger import logger


class ContentCard(QFrame):
    """单条内容卡片：展示+按钮交互+单条刷新"""

    # 信号：用户点「换一条」→ 传出 (当前item, 卡片self)
    request_refresh = Signal(object, object)  # (ContentItem, ContentCard)

    def __init__(self, item: ContentItem, parent=None):
        super().__init__(parent)
        self.item = item
        self.setObjectName("contentCard")
        self._init_ui()
        self._apply_style()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # 图片预览区
        self.lbl_image = QLabel(self)
        self.lbl_image.setAlignment(Qt.AlignCenter)
        self.lbl_image.setMinimumHeight(150)
        self.lbl_image.setStyleSheet("background-color: rgba(240, 246, 252, 200); border-radius: 10px;")
        # 显示优先级：已有图→正常显示；有错误→显示错误占位；无图无错→显示「生成中」
        if self.item.image_bytes:
            self.lbl_image.setText("")
            self._show_image(self.item.image_bytes)
        elif self.item.error:
            self.lbl_image.setText("❌ 图片未生成")
            self.lbl_image.setStyleSheet(
                "background-color: #FDEDEC; border-radius: 6px; color: #E74C3C;"
            )
        else:
            self.lbl_image.setText("🖼️ 图片生成中...")
        layout.addWidget(self.lbl_image)

        # 文案区（显示优先级：错误 > 正常文案 > 生成中）
        self.lbl_text = QLabel(self)
        self.lbl_text.setWordWrap(True)
        self.lbl_text.setTextFormat(Qt.PlainText)
        if self.item.error:
            self.lbl_text.setText(f"❌ {self.item.error}")
            self.lbl_text.setStyleSheet("font-size: 13px; color: #E74C3C; padding: 4px;")
        elif self.item.text:
            self.lbl_text.setText(self.item.text)
            self.lbl_text.setStyleSheet("font-size: 14px; color: #2C3E50; padding: 4px;")
        else:
            self.lbl_text.setText("文案生成中...")
            self.lbl_text.setStyleSheet("font-size: 14px; color: #2C3E50; padding: 4px;")
        layout.addWidget(self.lbl_text)

        # 标签区
        if self.item.tags:
            self.lbl_tags = QLabel(self)
            self.lbl_tags.setWordWrap(True)
            self.lbl_tags.setTextFormat(Qt.PlainText)
            self.lbl_tags.setText(" ".join(self.item.tags))
            self.lbl_tags.setStyleSheet("font-size: 12px; color: #4A90D9; padding: 2px;")
            layout.addWidget(self.lbl_tags)

        # 按钮区（有 error 时，复制/保存按钮禁用，只留「换一条」可用）
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self.btn_copy = self._make_btn("📋 复制文案", "normal")
        self.btn_copy.clicked.connect(self._on_copy)
        self.btn_copy.setEnabled(not self.item.error and bool(self.item.text))
        btn_row.addWidget(self.btn_copy)

        self.btn_save = self._make_btn("💾 保存图片", "normal")
        self.btn_save.clicked.connect(self._on_save)
        self.btn_save.setEnabled(not self.item.error and bool(self.item.image_bytes))
        btn_row.addWidget(self.btn_save)

        self.btn_refresh = self._make_btn("🔄 换一条", "normal")
        self.btn_refresh.clicked.connect(self._on_refresh)
        btn_row.addWidget(self.btn_refresh)

        layout.addLayout(btn_row)

    def _show_image(self, img_bytes: bytes):
        """显示图片"""
        try:
            img = QImage()
            img.loadFromData(img_bytes)
            if not img.isNull():
                pix = QPixmap.fromImage(img)
                # 缩放适应预览区
                scaled = pix.scaled(240, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.lbl_image.setPixmap(scaled)
                self.lbl_image.setStyleSheet("background-color: transparent;")
        except Exception as e:
            self.lbl_image.setText(f"图片显示失败: {e}")

    def update_item(self, new_item: ContentItem):
        """[外部调用] 刷新成新 item（换一条成功后使用），不重建整个面板"""
        self.item = new_item
        # ===== 图片区 =====
        if new_item.image_bytes:
            self.lbl_image.setText("")
            self._show_image(new_item.image_bytes)
        elif new_item.error:
            self.lbl_image.setText("❌ 图片未生成")
            self.lbl_image.setStyleSheet(
                "background-color: rgba(253, 237, 236, 220); border-radius: 10px; color: #E74C3C;"
            )
        else:
            self.lbl_image.setText("🖼️ 图片生成中...")
            self.lbl_image.setStyleSheet("background-color: rgba(240, 246, 252, 200); border-radius: 10px;")

        # ===== 文案区 =====
        if new_item.error:
            self.lbl_text.setText(f"❌ {new_item.error}")
            self.lbl_text.setStyleSheet("font-size: 13px; color: #E74C3C; padding: 4px;")
        elif new_item.text:
            self.lbl_text.setText(new_item.text)
            self.lbl_text.setStyleSheet("font-size: 14px; color: #2C3E50; padding: 4px;")
        else:
            self.lbl_text.setText("文案生成中...")

        # ===== 标签区 =====
        if hasattr(self, "lbl_tags"):
            self.lbl_tags.deleteLater()
            del self.lbl_tags
        if new_item.tags:
            self.lbl_tags = QLabel(self)
            self.lbl_tags.setWordWrap(True)
            self.lbl_tags.setTextFormat(Qt.PlainText)
            self.lbl_tags.setText(" ".join(new_item.tags))
            self.lbl_tags.setStyleSheet("font-size: 12px; color: #4A90D9; padding: 2px;")
            # 标签区在文案后、按钮前插入
            layout = self.layout()
            btn_row_idx = layout.indexOf(self.btn_refresh.parentWidget() if hasattr(self, 'btn_row') else None)
            layout.insertWidget(layout.count() - 1, self.lbl_tags)

        # ===== 按钮 =====
        self.btn_copy.setEnabled(not new_item.error and bool(new_item.text))
        self.btn_save.setEnabled(not new_item.error and bool(new_item.image_bytes))
        self.btn_copy.setText("📋 复制文案")
        self.btn_save.setText("💾 保存图片")
        self.btn_refresh.setText("🔄 换一条")
        self.btn_refresh.setEnabled(True)

    def _reset_btn_later(self, btn: QPushButton, original_text: str, ms: int = 1800):
        """按钮临时显示状态文字，一段时间后恢复原文"""
        QTimer.singleShot(ms, lambda: btn.setText(original_text))

    def _on_copy(self):
        """复制文案：取全局剪贴板，按钮短时显示成功，状态栏弹短提示"""
        text = self.item.full_text
        if not text:
            QMessageBox.warning(self, "⚠️ 无内容", "这条没有文案，无法复制")
            return
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(text)
        # 按钮闪一下
        self.btn_copy.setText("✅ 已复制")
        self._reset_btn_later(self.btn_copy, "📋 复制文案")
        # 不挡屏幕的 1 秒 toast（在按钮上方闪）
        tip_pos = self.btn_copy.mapToGlobal(QPoint(self.btn_copy.width() // 2, -8))
        QToolTip.showText(tip_pos, "✅ 文案已复制，可直接粘贴", self.btn_copy)
        # 自动备份
        paths.append_text_backup(
            self.item.module, self.item.item_type,
            self.item.text, self.item.tags
        )
        logger.info(f"📋 文案已复制: {self.item.text[:30]}...")

    def _on_save(self):
        """保存图片：直接存日期文件夹，按钮闪成功，弹带「打开文件夹」的提示（用户主动开）"""
        if not self.item.image_bytes:
            QMessageBox.warning(self, "⚠️ 无图片", "这条没有图片，无法保存")
            return
        saved_path = paths.save_image_auto(
            self.item.module, self.item.item_type, self.item.image_bytes
        )
        if not saved_path:
            QMessageBox.critical(self, "❌ 保存失败", "保存图片时发生未知错误")
            return
        self.item.saved = True
        self.btn_save.setText("✅ 已保存")
        self._reset_btn_later(self.btn_save, "💾 保存图片")
        paths.append_text_backup(
            self.item.module, self.item.item_type,
            self.item.text, self.item.tags
        )
        logger.info(f"💾 图片已保存: {saved_path}")
        # 给用户看位置 + 可打开文件夹（保留）
        parent = self.window()
        msg = QMessageBox(parent)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("💾 保存成功")
        msg.setText("图片已保存到当天日期文件夹：")
        msg.setInformativeText(saved_path)
        msg.setStandardButtons(QMessageBox.Ok)
        btn_open = msg.addButton("📂 打开文件夹", QMessageBox.AcceptRole)
        msg.exec()
        if msg.clickedButton() == btn_open:
            try:
                import subprocess
                folder = os.path.dirname(saved_path)
                if hasattr(os, "startfile"):
                    os.startfile(folder)
                else:
                    subprocess.Popen(["explorer", folder])
            except Exception as e:
                logger.warning(f"打开文件夹失败: {e}")

    def _on_refresh(self):
        """换一条：禁用按钮，发信号让主窗口生成 1 条再回传 update_item"""
        self.btn_refresh.setEnabled(False)
        self.btn_refresh.setText("⏳ 换中...")
        self.lbl_image.setText("🖼️ 重新生成中...")
        self.lbl_image.setStyleSheet(
            "background-color: #F0F6FC; border-radius: 6px; color: #748594;"
        )
        self.lbl_text.setText("文案重新生成中...")
        self.lbl_text.setStyleSheet("font-size: 14px; color: #748594; padding: 4px;")
        # 发信号：(当前item, 当前卡片)
        self.request_refresh.emit(self.item, self)

    def _make_btn(self, text: str, btn_type: str) -> QPushButton:
        btn = QPushButton(text, self)
        btn.setProperty("btnType", btn_type)
        btn.setProperty("btnSize", "small")
        btn.setCursor(Qt.PointingHandCursor)
        return btn

    def _apply_style(self):
        self.setStyleSheet("""
        #contentCard {
            background-color: rgba(255, 255, 255, 150);
            border: 1px solid rgba(255, 255, 255, 160);
            border-radius: 14px;
            padding: 6px;
        }
        #contentCard:hover {
            border-color: rgba(74, 144, 217, 200);
        }
        """)
