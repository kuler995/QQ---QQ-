# -*- coding: utf-8 -*-
"""设置弹窗
按 docs/03_UI设计规范.md 的设置页规范实现：
- Agnes AI 设置区：API KEY + 画图模型下拉
- 和风天气设置区：API KEY + 城市下拉
- 存储设置区：素材路径 + 浏览按钮 + 图片质量滑块
- 标签设置区：必须标签（逗号分隔）
- 底部：💾 保存 / 取消
- 保存校验：两个 KEY 必填，留空弹警告
"""
import os
from typing import Optional

from PySide6.QtCore import Qt, QDir
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QSlider, QFileDialog, QGroupBox, QMessageBox,
    QFrame, QSizePolicy
)

from src.config import CONFIG, save_config, get_app_dir
from src.utils.logger import logger


class SettingsDialog(QDialog):
    """设置弹窗（模态）

    用法：
        dlg = SettingsDialog(parent)
        if dlg.exec() == QDialog.Accepted:
            # 用户点了保存，配置已写入 config.json
    """

    # 和风天气常用城市列表（location_id → 城市名）
    CITY_OPTIONS = [
        ("101181101", "焦作（河南理工大学）"),
        ("101180101", "郑州"),
        ("101180201", "开封"),
        ("101180301", "洛阳"),
        ("101180401", "平顶山"),
        ("101180701", "新乡"),
        ("101180801", "许昌"),
        ("101180901", "漯河"),
    ]

    # 画图模型可选项（Agnes AI 官方支持）
    IMAGE_MODELS = [
        "agnes-image-2.1-flash",
        "agnes-image-2.0",
        "agnes-image-1.5",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ 软件设置")
        self.setModal(True)
        self.resize(560, 640)
        self.setMinimumWidth(520)

        # 复制一份当前配置作为编辑副本（取消时不影响原配置）
        from copy import deepcopy
        self._cfg = deepcopy(CONFIG)

        self._init_ui()
        self._load_values()
        logger.info("⚙️ 设置弹窗已打开")

    # ============================================================
    # UI 构建
    # ============================================================

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # ===== 标题 =====
        title = QLabel("⚙️ 软件设置", self)
        title.setObjectName("moduleTitle")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #4A90D9;")
        layout.addWidget(title)

        hint = QLabel("修改后点「💾 保存」生效。所有配置保存在 config.json。", self)
        hint.setObjectName("helperText")
        layout.addWidget(hint)

        # ===== 1. Agnes AI 区 =====
        self.agnes_group, agnes_widgets = self._build_group("🤖 Agnes AI（文案 + 配图生成）", [
            ("API KEY", "line", "agnes_api_key"),
            ("画图模型", "combo_image_model", "agnes_image_model"),
            ("文案模型", "line", "agnes_text_model"),
            ("接口地址", "line", "agnes_base_url"),
        ])
        layout.addWidget(self.agnes_group)

        # ===== 2. 和风天气区 =====
        self.weather_group, weather_widgets = self._build_group("🌤️ 和风天气（天气查询）", [
            ("API KEY", "line", "weather_api_key"),
            ("城市", "combo_city", "weather_city"),
        ])
        layout.addWidget(self.weather_group)

        # ===== 3. 存储设置区 =====
        self.storage_group, storage_widgets = self._build_storage_group()
        layout.addWidget(self.storage_group)

        # ===== 4. 标签设置区 =====
        self.tags_group, tags_widgets = self._build_group("🏷️ 标签设置", [
            ("必须标签（逗号分隔）", "line", "tags_required"),
        ])
        layout.addWidget(self.tags_group)

        # 把所有输入控件存到 self._inputs 字典（key 是上面定义的字段名）
        self._inputs = {**agnes_widgets, **weather_widgets, **tags_widgets}

        # ===== 底部按钮 =====
        layout.addStretch(1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch(1)

        self.btn_save = self._make_btn("💾 保存", "primary")
        self.btn_save.setMinimumWidth(120)
        self.btn_save.clicked.connect(self._on_save)

        self.btn_cancel = self._make_btn("取消", "normal")
        self.btn_cancel.setMinimumWidth(100)
        self.btn_cancel.clicked.connect(self.reject)

        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_save)
        layout.addLayout(btn_row)

    def _build_group(self, title: str, fields) -> tuple:
        """构建一个分组区
        Args:
            title: 分组标题
            fields: [(显示标签, 控件类型, 字段名), ...]
                控件类型：line=输入框 / combo_image_model / combo_city
        Returns:
            (QGroupBox, {字段名: 控件对象})
        """
        group = QGroupBox(title, self)
        group.setStyleSheet(self._group_style())
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignRight)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        widgets = {}
        for label_text, widget_type, field_name in fields:
            if widget_type == "line":
                w = QLineEdit(group)
                w.setMinimumHeight(32)
                # API KEY 字段用密码模式显示，防止偷窥
                if "api_key" in field_name:
                    w.setEchoMode(QLineEdit.PasswordEchoOnEdit)
                    w.setPlaceholderText("sk-xxxx（输入后变成密文显示）")
                form.addRow(label_text, w)
            elif widget_type == "combo_image_model":
                w = QComboBox(group)
                w.addItems(self.IMAGE_MODELS)
                w.setMinimumHeight(32)
                form.addRow(label_text, w)
            elif widget_type == "combo_city":
                w = QComboBox(group)
                for loc_id, name in self.CITY_OPTIONS:
                    w.addItem(name, loc_id)  # data 存 location_id
                w.setMinimumHeight(32)
                form.addRow(label_text, w)
            else:
                w = QLineEdit(group)
                form.addRow(label_text, w)
            widgets[field_name] = w

        return group, widgets

    def _build_storage_group(self) -> tuple:
        """构建存储设置区（带浏览按钮 + 滑块）"""
        group = QGroupBox("📁 存储设置", self)
        group.setStyleSheet(self._group_style())
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        # 素材路径
        path_label = QLabel("素材存储路径：", group)
        layout.addWidget(path_label)

        path_row = QHBoxLayout()
        self.input_storage_path = QLineEdit(group)
        self.input_storage_path.setPlaceholderText("留空 = 软件目录/小青素材")
        self.input_storage_path.setMinimumHeight(32)
        path_row.addWidget(self.input_storage_path, stretch=1)

        self.btn_browse = self._make_btn("📁 浏览...", "normal", small=True)
        self.btn_browse.clicked.connect(self._on_browse)
        path_row.addWidget(self.btn_browse)

        layout.addLayout(path_row)

        # 图片质量
        quality_row = QHBoxLayout()
        quality_label = QLabel("图片保存质量：", group)
        quality_row.addWidget(quality_label)

        self.slider_quality = QSlider(Qt.Horizontal, group)
        self.slider_quality.setRange(50, 100)
        self.slider_quality.setValue(85)
        self.slider_quality.setTickInterval(5)
        self.slider_quality.setTickPosition(QSlider.TicksBelow)

        self.lbl_quality_value = QLabel("85%", group)
        self.lbl_quality_value.setMinimumWidth(40)
        self.slider_quality.valueChanged.connect(
            lambda v: self.lbl_quality_value.setText(f"{v}%")
        )

        quality_row.addWidget(self.slider_quality, stretch=1)
        quality_row.addWidget(self.lbl_quality_value)
        layout.addLayout(quality_row)

        # 提示
        hint = QLabel("💡 质量 85% 平衡清晰度与文件大小，建议保持", group)
        hint.setObjectName("helperText")
        layout.addWidget(hint)

        # ===== 壁纸风格（毛玻璃主题）=====
        from src.utils.wallpaper import WALLPAPERS
        wp_label = QLabel("🖼️ 界面壁纸风格：", group)
        layout.addWidget(wp_label)

        self.combo_wallpaper = QComboBox(group)
        self.combo_wallpaper.setMinimumHeight(32)
        for key, cn in WALLPAPERS.items():
            self.combo_wallpaper.addItem(cn, key)
        layout.addWidget(self.combo_wallpaper)

        wp_hint = QLabel("💡 切换后立即生效，毛玻璃半透明卡片叠加壁纸", group)
        wp_hint.setObjectName("helperText")
        layout.addWidget(wp_hint)

        return group, {}

    def _group_style(self) -> str:
        """分组框样式"""
        return """
        QGroupBox {
            font-size: 14px;
            font-weight: bold;
            color: #4A90D9;
            border: 1px solid #D4E6F7;
            border-radius: 8px;
            margin-top: 14px;
            padding: 10px;
            background-color: #FFFFFF;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
            background-color: #EBF4FB;
        }
        """

    # ============================================================
    # 数据加载
    # ============================================================

    def _load_values(self):
        """把当前 CONFIG 的值填到各控件"""
        # Agnes AI
        self._inputs["agnes_api_key"].setText(self._cfg.get("agnes_ai", {}).get("api_key", ""))
        self._inputs["agnes_base_url"].setText(self._cfg.get("agnes_ai", {}).get("base_url", ""))
        text_model = self._cfg.get("agnes_ai", {}).get("text_model", "agnes-text-latest")
        self._inputs["agnes_text_model"].setText(text_model)
        image_model = self._cfg.get("agnes_ai", {}).get("image_model", "agnes-image-2.1-flash")
        idx = self._inputs["agnes_image_model"].findText(image_model)
        if idx >= 0:
            self._inputs["agnes_image_model"].setCurrentIndex(idx)

        # 和风天气
        self._inputs["weather_api_key"].setText(self._cfg.get("weather", {}).get("api_key", ""))
        location_id = self._cfg.get("weather", {}).get("location_id", "101181101")
        idx = self._inputs["weather_city"].findData(location_id)
        if idx >= 0:
            self._inputs["weather_city"].setCurrentIndex(idx)

        # 存储设置
        base_path = self._cfg.get("storage", {}).get("base_path", "")
        self.input_storage_path.setText(base_path)
        quality = self._cfg.get("storage", {}).get("image_quality", 85)
        self.slider_quality.setValue(int(quality))

        # 壁纸
        wp_key = self._cfg.get("wallpaper", "clear_blue")
        idx = self.combo_wallpaper.findData(wp_key)
        if idx >= 0:
            self.combo_wallpaper.setCurrentIndex(idx)

        # 标签
        required_tags = self._cfg.get("tags", {}).get("required", [])
        self._inputs["tags_required"].setText(", ".join(required_tags))

    # ============================================================
    # 事件
    # ============================================================

    def _on_browse(self):
        """点击浏览按钮，打开文件夹选择对话框"""
        cur_path = self.input_storage_path.text().strip()
        if not cur_path:
            cur_path = os.path.join(get_app_dir(), "小青素材")

        new_path = QFileDialog.getExistingDirectory(
            self, "选择素材存储文件夹", cur_path, QFileDialog.ShowDirsOnly
        )
        if new_path:
            self.input_storage_path.setText(new_path)
            logger.info(f"📁 用户选择了路径：{new_path}")

    def _on_save(self):
        """保存按钮：校验 + 写入配置 + 关闭弹窗"""
        # 1. 收集所有值
        agnes_key = self._inputs["agnes_api_key"].text().strip()
        weather_key = self._inputs["weather_api_key"].text().strip()

        # 2. 校验必填项
        if not agnes_key:
            QMessageBox.warning(
                self, "⚠️ 信息不全",
                "Agnes AI 的 API KEY 不能为空！\n文案和配图功能都用它，请填写后保存。"
            )
            self._inputs["agnes_api_key"].setFocus()
            return

        if not weather_key:
            QMessageBox.warning(
                self, "⚠️ 信息不全",
                "和风天气的 API KEY 不能为空！\n天气查询要用，请填写后保存。"
            )
            self._inputs["weather_api_key"].setFocus()
            return

        # 3. 校验路径可写
        storage_path = self.input_storage_path.text().strip()
        if storage_path:
            try:
                os.makedirs(storage_path, exist_ok=True)
                test_file = os.path.join(storage_path, ".write_test")
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)
            except Exception as e:
                QMessageBox.warning(
                    self, "⚠️ 路径不可用",
                    f"无法写入文件夹：{storage_path}\n错误：{e}\n请选别的位置。"
                )
                return

        # 4. 校验标签
        tags_raw = self._inputs["tags_required"].text().strip()
        required_tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
        if len(required_tags) < 1:
            QMessageBox.warning(
                self, "⚠️ 标签缺失",
                "至少要有一个必须标签（如 #早安理工#）"
            )
            return

        # 5. 组装新配置
        self._cfg["agnes_ai"]["api_key"] = agnes_key
        self._cfg["agnes_ai"]["base_url"] = self._inputs["agnes_base_url"].text().strip()
        self._cfg["agnes_ai"]["text_model"] = self._inputs["agnes_text_model"].text().strip()
        self._cfg["agnes_ai"]["image_model"] = self._inputs["agnes_image_model"].currentText()

        self._cfg["weather"]["api_key"] = weather_key
        self._cfg["weather"]["location_id"] = self._inputs["weather_city"].currentData()
        self._cfg["weather"]["city"] = self._inputs["weather_city"].currentText().split("（")[0]

        self._cfg["storage"]["base_path"] = storage_path
        self._cfg["storage"]["image_quality"] = self.slider_quality.value()

        # 壁纸
        self._cfg["wallpaper"] = self.combo_wallpaper.currentData()

        self._cfg["tags"]["required"] = required_tags

        # 6. 保存
        if save_config(self._cfg):
            # 同步更新全局 CONFIG（其他模块运行时用的就是这个）
            CONFIG.clear()
            CONFIG.update(self._cfg)
            logger.info("✅ 设置已保存并同步到全局 CONFIG")
            QMessageBox.information(
                self, "✅ 保存成功",
                "设置已保存，立即生效！\n（API KEY 变更后，下次生成内容会用新 KEY）"
            )
            self.accept()
        else:
            QMessageBox.critical(
                self, "❌ 保存失败",
                "配置写入失败，请检查文件权限或日志。"
            )

    # ============================================================
    # 工具
    # ============================================================

    def _make_btn(self, text: str, btn_type: str, parent=None, small: bool = False) -> QPushButton:
        """统一创建按钮"""
        btn = QPushButton(text, parent or self)
        btn.setProperty("btnType", btn_type)
        if small:
            btn.setProperty("btnSize", "small")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setMinimumHeight(32 if not small else 28)
        return btn
