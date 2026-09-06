# -*- coding: utf-8 -*-
"""历史内容查看弹窗（阶段7）
左侧：日期列表（扫描 小青素材/ 下所有 YYYY-MM-DD 文件夹）
右侧：选中日期当天的所有内容（文案 + 图片缩略图）
"""
import os
import re
from datetime import datetime
from typing import List, Dict, Tuple

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QImage, QGuiApplication, QFont
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QScrollArea, QFrame, QGridLayout,
    QMessageBox, QSizePolicy
)

from src.utils import paths
from src.utils.logger import logger


# 文案备份解析正则：---- [HH:MM:SS] 类型 ----
# 字符类里只排除一个 '-'（原 [^----] 会触发 FutureWarning）
_ENTRY_RE = re.compile(
    r"----\s*\[([^\]]+)\]\s*([^-]+?)\s*----\s*\n(.*?)(?=\n----\s*\[|\Z)",
    flags=re.DOTALL
)


class HistoryDialog(QDialog):
    """历史记录浏览对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📜 历史记录 - 小青素材库")
        self.resize(1080, 720)
        self._selected_date = ""
        self._init_ui()
        self._load_dates()

    # ============================================================
    # UI 初始化
    # ============================================================
    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ===== 左侧：日期列表 =====
        left = QFrame(self)
        left.setFixedWidth(220)
        left.setStyleSheet("background-color: #F0F6FC; border-right: 1px solid #D4E6F7;")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(6)

        title = QLabel("📅 崩史日期", left)
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #2C5F8D; padding: 4px;")
        left_layout.addWidget(title)

        self.lst_dates = QListWidget(left)
        self.lst_dates.setStyleSheet("""
            QListWidget { background-color: #FFFFFF; border: 1px solid #D4E6F7; border-radius: 6px; font-size: 14px; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #EAF2FA; }
            QListWidget::item:selected { background-color: #D4E6F7; color: #2C5F8D; font-weight: bold; }
            QListWidget::item:hover { background-color: #EAF2FA; }
        """)
        self.lst_dates.itemClicked.connect(self._on_date_clicked)
        left_layout.addWidget(self.lst_dates)

        # 底部刷新 + 打开根目录按钮
        btn_row = QHBoxLayout()
        btn_refresh = QPushButton("🔄 刷新", left)
        btn_refresh.setProperty("btnType", "normal")
        btn_refresh.clicked.connect(self._load_dates)
        btn_open_root = QPushButton("📂 打开根目录", left)
        btn_open_root.setProperty("btnType", "normal")
        btn_open_root.clicked.connect(self._open_root_folder)
        btn_row.addWidget(btn_refresh)
        btn_row.addWidget(btn_open_root)
        left_layout.addLayout(btn_row)

        layout.addWidget(left)

        # ===== 右侧：内容预览 =====
        right = QFrame(self)
        right.setStyleSheet("background-color: #FFFFFF;")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(10)

        self.lbl_date_title = QLabel("← 请选择左侧的日期", right)
        self.lbl_date_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2C5F8D;")
        right_layout.addWidget(self.lbl_date_title)

        self.lbl_summary = QLabel("", right)
        self.lbl_summary.setStyleSheet("font-size: 13px; color: #748594;")
        right_layout.addWidget(self.lbl_summary)

        # 滚动区放内容
        self.scroll = QScrollArea(right)
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background-color: #FFFFFF; }")
        self.content_widget = QWidget(self.scroll)
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(16)
        self.content_layout.addStretch()
        self.scroll.setWidget(self.content_widget)
        right_layout.addWidget(self.scroll, 1)

        layout.addWidget(right, 1)

    # ============================================================
    # 日期加载
    # ============================================================
    def _load_dates(self):
        """扫描 小青素材/ 下所有日期文件夹，倒序展示"""
        self.lst_dates.clear()
        root = paths.get_materials_root()
        if not os.path.isdir(root):
            item = QListWidgetItem("（还没有历史记录）")
            item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            self.lst_dates.addItem(item)
            return

        # 扫描所有 YYYY-MM-DD 文件夹
        date_dirs = []
        for name in os.listdir(root):
            full = os.path.join(root, name)
            if not os.path.isdir(full):
                continue
            if re.match(r"^\d{4}-\d{2}-\d{2}$", name):
                date_dirs.append(name)

        if not date_dirs:
            item = QListWidgetItem("（还没有历史记录）")
            item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            self.lst_dates.addItem(item)
            return

        # 倒序：最新在上
        date_dirs.sort(reverse=True)
        for d in date_dirs:
            item = QListWidgetItem(f"📅 {d}")
            item.setData(Qt.UserRole, d)
            self.lst_dates.addItem(item)

        # 默认选中第一个（最新）
        self.lst_dates.setCurrentRow(0)
        self._on_date_clicked(self.lst_dates.item(0))

    # ============================================================
    # 日期点击 → 加载当天内容
    # ============================================================
    def _on_date_clicked(self, item: QListWidgetItem):
        if not item:
            return
        date_str = item.data(Qt.UserRole)
        if not date_str:
            return
        self._selected_date = date_str
        self.lbl_date_title.setText(f"📅 {date_str} 的内容")
        self._load_date_content(date_str)

    def _load_date_content(self, date_str: str):
        """加载某天的所有内容"""
        # 清空
        while self.content_layout.count() > 1:
            w = self.content_layout.takeAt(0).widget()
            if w:
                w.deleteLater()

        date_dir = paths.get_date_dir(date_str)
        if not os.path.isdir(date_dir):
            self.lbl_summary.setText("（该日期没有内容）")
            return

        # 1. 解析文案备份
        text_entries = self._parse_text_backups(date_dir)

        # 2. 读取图片列表
        images_dir = paths.get_images_dir(date_str)
        image_files = []
        if os.path.isdir(images_dir):
            for name in sorted(os.listdir(images_dir)):
                if name.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    image_files.append(os.path.join(images_dir, name))

        # 统计
        self.lbl_summary.setText(
            f"文案 {sum(len(v) for v in text_entries.values())} 条 | 图片 {len(image_files)} 张"
        )

        # 3. 按模块分组展示
        # 先按文案模块分组
        MODULE_ORDER = ["morning", "night", "recommend", "share", "weather", ""]
        MODULE_CN = {
            "morning": "🌤️ 早安理工",
            "night": "🌙 晚安理工",
            "recommend": "📚 小青超推荐",
            "share": "💡 小青爱分享",
            "weather": "🌤️🌙 早晚安",
            "": "📌 其他",
        }

        # 先按日期文件夹里的 txt 文件名归类
        rendered_modules = set()

        # 文案按模块展示
        for module_key in MODULE_ORDER:
            entries = text_entries.get(module_key, [])
            if not entries:
                continue
            rendered_modules.add(module_key)
            self._render_module_block(MODULE_CN.get(module_key, module_key), entries)

        # 图片区独立展示（不按模块分，因为文件名含 module）
        if image_files:
            self._render_images_block(image_files)

        if not text_entries and not image_files:
            empty = QLabel("（该日期没有内容）", self.content_widget)
            empty.setStyleSheet("font-size: 14px; color: #748594; padding: 40px;")
            empty.setAlignment(Qt.AlignCenter)
            self.content_layout.insertWidget(self.content_layout.count() - 1, empty)

    # ============================================================
    # 文案备份解析
    # ============================================================
    def _parse_text_backups(self, date_dir: str) -> Dict[str, List[dict]]:
        """扫描日期目录下所有 文案备份*.txt，按模块分类返回
        Returns: {module_key: [{time, type, text, tags}, ...]}
        """
        result: Dict[str, List[dict]] = {}
        try:
            files = [f for f in os.listdir(date_dir) if f.startswith("文案备份") and f.endswith(".txt")]
        except Exception as e:
            logger.warning(f"读取日期目录失败: {e}")
            return result

        for fname in files:
            # 文件名 文案备份_morning.txt → module_key = morning
            module_key = fname.replace("文案备份", "").replace(".txt", "")
            if module_key.startswith("_"):
                module_key = module_key[1:]
            if not module_key:
                module_key = ""
            full_path = os.path.join(date_dir, fname)
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                logger.warning(f"读取文案备份失败 {full_path}: {e}")
                continue

            # 解析每条 entry
            for m in _ENTRY_RE.finditer(content):
                time_str = m.group(1).strip()
                item_type = m.group(2).strip()
                body = m.group(3).strip()
                # 拆出正文 + 标签
                lines = body.split("\n")
                text_lines = []
                tag_lines = []
                for line in lines:
                    if line.strip().startswith("#") and "#" in line:
                        tag_lines.append(line.strip())
                    else:
                        text_lines.append(line)
                text = "\n".join(text_lines).strip()
                tags = " ".join(tag_lines).strip()
                result.setdefault(module_key, []).append({
                    "time": time_str,
                    "type": item_type,
                    "text": text,
                    "tags": tags,
                })

        return result

    # ============================================================
    # 渲染：文案模块块
    # ============================================================
    def _render_module_block(self, title: str, entries: List[dict]):
        """渲染一个模块的文案块"""
        block = QFrame(self.content_widget)
        block.setStyleSheet("""
            QFrame { background-color: #F8FBFE; border: 1px solid #D4E6F7; border-radius: 8px; }
        """)
        block_layout = QVBoxLayout(block)
        block_layout.setContentsMargins(14, 10, 14, 10)
        block_layout.setSpacing(8)

        # 标题
        lbl_title = QLabel(f"{title}（{len(entries)} 条）", block)
        lbl_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #2C5F8D;")
        block_layout.addWidget(lbl_title)

        # 每条文案
        for idx, e in enumerate(entries, 1):
            card = self._build_text_card(idx, e, block)
            block_layout.addWidget(card)

        # 插入到主内容区
        self.content_layout.insertWidget(self.content_layout.count() - 1, block)

    def _build_text_card(self, idx: int, entry: dict, parent: QWidget) -> QFrame:
        """单条文案卡片"""
        card = QFrame(parent)
        card.setStyleSheet("""
            QFrame { background-color: #FFFFFF; border: 1px solid #E0EAF5; border-radius: 6px; }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 8, 10, 8)
        card_layout.setSpacing(4)

        # 头：时间 + 类型
        head = QLabel(f"⏰ {entry['time']}  |  {entry['type']}", card)
        head.setStyleSheet("font-size: 12px; color: #748594;")
        card_layout.addWidget(head)

        # 正文
        body = QLabel(entry["text"], card)
        body.setWordWrap(True)
        body.setTextFormat(Qt.PlainText)
        body.setStyleSheet("font-size: 14px; color: #2C3E50; padding: 4px 0;")
        card_layout.addWidget(body)

        # 标签
        if entry["tags"]:
            tags = QLabel(entry["tags"], card)
            tags.setWordWrap(True)
            tags.setStyleSheet("font-size: 12px; color: #4A90D9; padding: 2px 0;")
            card_layout.addWidget(tags)

        # 复制按钮
        btn_copy = QPushButton("📋 复制这条", card)
        btn_copy.setProperty("btnType", "normal")
        btn_copy.setProperty("btnSize", "small")
        btn_copy.clicked.connect(lambda: self._copy_text(entry))
        card_layout.addWidget(btn_copy, 0, Qt.AlignRight)

        return card

    def _copy_text(self, entry: dict):
        text = entry.get("text", "")
        tags = entry.get("tags", "")
        full = f"{text}\n{tags}".strip() if tags else text
        QGuiApplication.clipboard().setText(full)
        # 短提示
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("✅ 已复制")
        msg.setText("这条文案已复制到剪贴板")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()

    # ============================================================
    # 渲染：图片网格
    # ============================================================
    def _render_images_block(self, image_files: List[str]):
        """图片网格块"""
        block = QFrame(self.content_widget)
        block.setStyleSheet("""
            QFrame { background-color: #F8FBFE; border: 1px solid #D4E6F7; border-radius: 8px; }
        """)
        block_layout = QVBoxLayout(block)
        block_layout.setContentsMargins(14, 10, 14, 10)
        block_layout.setSpacing(10)

        lbl_title = QLabel(f"🖼️ 配图（{len(image_files)} 张）", block)
        lbl_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #2C5F8D;")
        block_layout.addWidget(lbl_title)

        # 网格：每行 3 张
        grid = QGridLayout()
        grid.setSpacing(10)
        cols = 3
        for i, img_path in enumerate(image_files):
            row = i // cols
            col = i % cols
            cell = self._build_image_cell(img_path, block)
            grid.addWidget(cell, row, col)
        block_layout.addLayout(grid)

        self.content_layout.insertWidget(self.content_layout.count() - 1, block)

    def _build_image_cell(self, img_path: str, parent: QWidget) -> QFrame:
        """单个图片缩略图卡片"""
        cell = QFrame(parent)
        cell.setFixedHeight(220)
        cell.setStyleSheet("""
            QFrame { background-color: #FFFFFF; border: 1px solid #E0EAF5; border-radius: 6px; }
        """)
        cell_layout = QVBoxLayout(cell)
        cell_layout.setContentsMargins(6, 6, 6, 6)
        cell_layout.setSpacing(4)

        # 图片
        lbl_img = QLabel(cell)
        lbl_img.setFixedSize(180, 160)
        lbl_img.setAlignment(Qt.AlignCenter)
        lbl_img.setStyleSheet("background-color: #F0F6FC; border-radius: 4px;")
        try:
            img = QImage(img_path)
            if not img.isNull():
                pix = QPixmap.fromImage(img).scaled(
                    180, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                lbl_img.setPixmap(pix)
            else:
                lbl_img.setText("❌ 图片损坏")
        except Exception as e:
            lbl_img.setText(f"❌ {e}")
        cell_layout.addWidget(lbl_img, 0, Qt.AlignCenter)

        # 文件名（截断）
        fname = os.path.basename(img_path)
        if len(fname) > 28:
            fname = fname[:25] + "..."
        lbl_name = QLabel(fname, cell)
        lbl_name.setStyleSheet("font-size: 11px; color: #748594;")
        lbl_name.setAlignment(Qt.AlignCenter)
        cell_layout.addWidget(lbl_name)

        # 操作按钮行
        btn_row = QHBoxLayout()
        btn_open = QPushButton("📂 打开", cell)
        btn_open.setProperty("btnType", "normal")
        btn_open.setProperty("btnSize", "small")
        btn_open.clicked.connect(lambda: self._open_image(img_path))
        btn_copy_path = QPushButton("📋 路径", cell)
        btn_copy_path.setProperty("btnType", "normal")
        btn_copy_path.setProperty("btnSize", "small")
        btn_copy_path.clicked.connect(lambda: self._copy_path(img_path))
        btn_row.addWidget(btn_open)
        btn_row.addWidget(btn_copy_path)
        cell_layout.addLayout(btn_row)

        return cell

    def _open_image(self, img_path: str):
        try:
            if hasattr(os, "startfile"):
                os.startfile(img_path)
            else:
                import subprocess
                subprocess.Popen(["explorer", img_path])
        except Exception as e:
            logger.warning(f"打开图片失败: {e}")

    def _copy_path(self, img_path: str):
        QGuiApplication.clipboard().setText(img_path)
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("✅ 已复制路径")
        msg.setText(f"图片路径已复制：\n{img_path}")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()

    def _open_root_folder(self):
        """打开 小青素材 根目录"""
        root = paths.get_materials_root()
        try:
            if hasattr(os, "startfile"):
                os.startfile(root)
            else:
                import subprocess
                subprocess.Popen(["explorer", root])
        except Exception as e:
            QMessageBox.warning(self, "⚠️ 打开失败", f"无法打开文件夹：{e}")
