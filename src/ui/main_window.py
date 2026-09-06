# -*- coding: utf-8 -*-
"""主窗口
阶段1：实现基础布局（标题栏 + 顶栏按钮 + 中间滚动区 + 底栏），淡蓝色主题
后续阶段：逐步接入各模块功能
"""
import os
from datetime import datetime

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QIcon, QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QScrollArea, QFrame, QSizePolicy, QApplication, QMenu
)

from src.config import get_app_dir
from src.ui.settings_dialog import SettingsDialog
from src.ui.widgets.module_panel import ModulePanel
from src.ui.widgets.generate_worker import GenerateWorker
from src.utils.logger import logger


class MainWindow(QMainWindow):
    """自动早晚安小助手 - 主窗口"""

    WINDOW_WIDTH = 1080
    WINDOW_HEIGHT = 760
    MIN_WIDTH = 960
    MIN_HEIGHT = 640

    def __init__(self):
        super().__init__()
        logger.info("🏠 主窗口初始化开始...")
        self._base_qss = ""  # 先初始化，避免 _apply_wallpaper 报错
        self._init_window()
        self._load_style()
        self._build_ui()
        self._apply_wallpaper()  # UI 构建完成后再应用壁纸+主题色
        logger.info("✅ 主窗口初始化完成")

    # ============================================================
    # 初始化
    # ============================================================

    def _init_window(self):
        """窗口基本属性"""
        self.setWindowTitle("自动早晚安小助手")
        self.resize(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)
        self.setMinimumSize(self.MIN_WIDTH, self.MIN_HEIGHT)

        # 中心 Widget（承载所有布局）
        central = QWidget(self)
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        # 壁纸背景层（毛玻璃效果的底层）
        from src.utils.wallpaper import get_wallpaper
        from src.config import CONFIG
        wp_key = CONFIG.get("wallpaper", "clear_blue")
        self._wallpaper_key = wp_key
        self.lbl_wallpaper = QLabel(central)
        self.lbl_wallpaper.setObjectName("wallpaperBg")
        self.lbl_wallpaper.setScaledContents(True)
        self.lbl_wallpaper.setGeometry(0, 0, self.width(), self.height())
        self.lbl_wallpaper.lower()  # 放最底层
        # 壁纸清晰显示（不模糊），配合上层半透明白色面板保证文字可读性
        # 注意：_apply_wallpaper 在 __init__ 末尾调用（需等 _load_style 设置 _base_qss）

        self._root_layout = QVBoxLayout(central)
        self._root_layout.setContentsMargins(10, 10, 10, 10)
        self._root_layout.setSpacing(8)

    def _apply_wallpaper(self, key: str = ""):
        """应用壁纸（毛玻璃底层）+ 动态主题色（根据壁纸亮度切换文字颜色）"""
        from src.utils.wallpaper import get_wallpaper, get_theme_colors
        if not key:
            key = self._wallpaper_key
        self._wallpaper_key = key
        size = QSize(max(self.width(), 800), max(self.height(), 600))
        pix = get_wallpaper(key, size)
        self.lbl_wallpaper.setPixmap(pix)
        self.lbl_wallpaper.setGeometry(0, 0, self.width(), self.height())
        # 根据壁纸亮度动态调整文字/面板颜色
        self._apply_theme_colors(get_theme_colors(key, size))

    def _apply_theme_colors(self, colors: dict):
        """根据主题色字典动态生成 QSS 并应用到窗口
        核心思路：在基础 QSS 后追加覆盖规则，只改文字/面板颜色，不影响按钮
        """
        base_qss = getattr(self, "_base_qss", "")
        if not base_qss:
            return
        tc = colors["text_color"]
        sc = colors["secondary_color"]
        mtc = colors["module_title_color"]
        panel_bg = colors["panel_bg"]
        card_bg = colors["card_bg"]
        bar_bg = colors["bar_bg"]
        border = colors["border_color"]

        # 追加覆盖规则：只改全局文字、面板/卡片/栏背景
        extra_qss = f"""
        QWidget, QLabel {{
            color: {tc};
        }}
        QLabel#moduleTitle {{
            color: {mtc};
        }}
        QLabel#statusText, QLabel#helperText {{
            color: {sc};
        }}
        QFrame#modulePanel {{
            background-color: {panel_bg};
            border: 1px solid {border};
        }}
        QFrame#cardPanel {{
            background-color: {card_bg};
            border: 1px solid {border};
        }}
        QFrame#topBar, QFrame#bottomBar {{
            background-color: {bar_bg};
            border: 1px solid {border};
        }}
        """
        self.setStyleSheet(base_qss + extra_qss)
        # 同步更新模块面板和卡片的内联样式（它们用 setStyleSheet 覆盖了 QSS）
        self._refresh_child_styles(colors)

    def resizeEvent(self, event):
        """窗口缩放时同步壁纸尺寸"""
        super().resizeEvent(event)
        if hasattr(self, "lbl_wallpaper"):
            self.lbl_wallpaper.setGeometry(0, 0, self.width(), self.height())

    def _load_style(self):
        """加载淡蓝色 QSS 主题"""
        import sys
        # 开发模式路径
        qss_path = os.path.join(
            get_app_dir(), "src", "ui", "styles", "theme_light_blue.qss"
        )
        # PyInstaller 打包后：样式在 _internal/ui/styles
        if not os.path.exists(qss_path):
            internal = getattr(sys, "_MEIPASS", get_app_dir())
            qss_path = os.path.join(internal, "ui", "styles", "theme_light_blue.qss")
        # 兜底：exe 同级 ui/styles
        if not os.path.exists(qss_path):
            qss_path = os.path.join(get_app_dir(), "ui", "styles", "theme_light_blue.qss")

        if os.path.exists(qss_path):
            try:
                with open(qss_path, "r", encoding="utf-8") as f:
                    self._base_qss = f.read()  # 保存原始 QSS 作为动态替换模板
                    self.setStyleSheet(self._base_qss)
                logger.info(f"🎨 主题加载成功：{qss_path}")
            except Exception as e:
                logger.error(f"❌ 主题加载失败：{e}，使用默认样式")
                self._base_qss = ""
        else:
            logger.warning(f"⚠️ 主题文件不存在：{qss_path}，使用默认样式")
            self._base_qss = ""

    def _refresh_child_styles(self, colors: dict):
        """更新模块面板、卡片等用 setStyleSheet 覆盖的子控件样式"""
        tc = colors["text_color"]
        sc = colors["secondary_color"]
        mtc = colors["module_title_color"]
        panel_bg = colors["panel_bg"]
        card_bg = colors["card_bg"]
        border = colors["border_color"]
        empty = colors["empty_color"]
        ready = colors["status_ready"]
        loading = colors["status_loading"]

        # 遍历所有模块面板
        for panel in self.findChildren(ModulePanel):
            panel.setStyleSheet(f"""
            #modulePanel {{
                background-color: {panel_bg};
                border: 1px solid {border};
                border-radius: 16px;
            }}
            """)
            # 标题、副标题、状态文字
            if hasattr(panel, "lbl_title"):
                panel.lbl_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {mtc};")
            if hasattr(panel, "lbl_subtitle"):
                panel.lbl_subtitle.setStyleSheet(f"font-size: 12px; color: {sc};")
            if hasattr(panel, "lbl_status"):
                # 保持当前状态颜色
                cur = panel.lbl_status.styleSheet()
                if "#27AE60" in cur or "#2ECC71" in cur:
                    panel.lbl_status.setStyleSheet(f"font-size: 12px; color: {ready};")
                elif "#E67E22" in cur or "#F39C12" in cur:
                    panel.lbl_status.setStyleSheet(f"font-size: 12px; color: {loading};")
                else:
                    panel.lbl_status.setStyleSheet(f"font-size: 12px; color: {sc};")
            # 空状态提示
            if hasattr(panel, "lbl_empty"):
                panel.lbl_empty.setStyleSheet(f"color: {empty}; padding: 18px; font-size: 13px;")

        # 遍历所有内容卡片
        from src.ui.widgets.content_card import ContentCard
        for card in self.findChildren(ContentCard):
            card.setStyleSheet(f"""
            #contentCard {{
                background-color: {card_bg};
                border: 1px solid {border};
                border-radius: 14px;
                padding: 6px;
            }}
            #contentCard:hover {{
                border-color: rgba(74, 144, 217, 200);
            }}
            """)
            # 卡片内文案、标签
            if hasattr(card, "lbl_text"):
                cur = card.lbl_text.styleSheet()
                if "#E74C3C" in cur:
                    card.lbl_text.setStyleSheet("font-size: 13px; color: #E74C3C; padding: 4px;")
                else:
                    card.lbl_text.setStyleSheet(f"font-size: 14px; color: {tc}; padding: 4px;")
            if hasattr(card, "lbl_tags"):
                card.lbl_tags.setStyleSheet(f"font-size: 12px; color: {mtc}; padding: 2px;")

    # ============================================================
    # UI 构建（4 层，参考 docs/03_UI设计规范.md 的主窗口布局图）
    # ============================================================

    def _build_ui(self):
        """按 UI 规范构建 4 层布局"""
        self._build_header_bar()     # 1. 标题栏
        self._build_top_action_bar() # 2. 顶栏按钮区
        self._build_content_area()   # 3. 中间滚动区（三个模块面板）
        self._build_bottom_bar()     # 4. 底栏（状态 + 打包按钮）

    # ----- 1. 标题栏（高 56px）-----
    def _build_header_bar(self):
        bar = QFrame(self)
        bar.setObjectName("headerBar")
        bar.setFixedHeight(56)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(8)

        # 左侧：窗口标题
        title = QLabel("🏠 自动早晚安小助手", bar)
        title.setObjectName("windowTitle")
        layout.addWidget(title)

        layout.addStretch(1)

        # 右侧：壁纸 / 设置 / 历史 / 关闭
        self.btn_wallpaper = self._make_btn("🖼️ 壁纸", "normal", bar)
        self.btn_wallpaper.clicked.connect(self._show_wallpaper_menu)
        self.btn_settings = self._make_btn("⚙️ 设置", "normal", bar)
        self.btn_history = self._make_btn("📜 历史", "normal", bar)
        self.btn_close = self._make_btn("❌ 关闭", "danger", bar)
        self.btn_close.clicked.connect(self.close)

        layout.addWidget(self.btn_wallpaper)
        layout.addWidget(self.btn_settings)
        layout.addWidget(self.btn_history)
        layout.addWidget(self.btn_close)

        self._root_layout.addWidget(bar)

    def _show_wallpaper_menu(self):
        """快速切换壁纸：点按钮弹菜单，选一个立即生效"""
        from src.utils.wallpaper import WALLPAPERS, _is_ysjf
        from src.config import CONFIG

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(255,255,255,235);
                border: 1px solid #D4E6F7;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 7px 24px;
                border-radius: 6px;
                color: #2C3E50;
            }
            QMenu::item:selected {
                background-color: #4A90D9;
                color: white;
            }
            QMenu::separator {
                height: 1px;
                background: #D4E6F7;
                margin: 4px 8px;
            }
        """)

        current = getattr(self, "_wallpaper_key", "clear_blue")

        # 第一组：渐变壁纸
        for key, cn in WALLPAPERS.items():
            if _is_ysjf(key):
                continue
            mark = "✓ " if key == current else "   "
            action = menu.addAction(f"{mark}{cn}")
            action.triggered.connect(lambda checked, k=key: self._switch_wallpaper(k))

        # 分隔符 + 第二组标题
        menu.addSeparator()
        title = menu.addAction("📷 影视飓风实拍壁纸")
        title.setEnabled(False)

        # 第二组：影视飓风实拍壁纸
        for key, cn in WALLPAPERS.items():
            if not _is_ysjf(key):
                continue
            mark = "✓ " if key == current else "   "
            action = menu.addAction(f"{mark}{cn}")
            action.triggered.connect(lambda checked, k=key: self._switch_wallpaper(k))

        menu.exec(self.btn_wallpaper.mapToGlobal(self.btn_wallpaper.rect().bottomLeft()))

    def _switch_wallpaper(self, key: str):
        """切换壁纸并保存到配置"""
        self._apply_wallpaper(key)
        from src.config import CONFIG, save_config
        CONFIG["wallpaper"] = key
        save_config()
        self.lbl_status.setText(f"🖼️ 壁纸已切换")
        self.statusTimer = self.statusTimer if hasattr(self, "statusTimer") else None

    # ----- 2. 顶栏按钮区（高 56px，苹果风紧凑）-----
    def _build_top_action_bar(self):
        bar = QFrame(self)
        bar.setObjectName("topBar")
        bar.setFixedHeight(56)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        self.btn_gen_all = self._make_btn("🎯 一键生成全部", "primary", bar)
        self.btn_gen_all.setMinimumWidth(160)
        self.btn_gen_weather = self._make_btn("🌤️ 生成天气", "secondary", bar)
        self.btn_gen_recommend = self._make_btn("📚 生成推荐", "secondary", bar)
        self.btn_gen_share = self._make_btn("💡 生成分享", "secondary", bar)

        layout.addWidget(self.btn_gen_all)
        layout.addWidget(self.btn_gen_weather)
        layout.addWidget(self.btn_gen_recommend)
        layout.addWidget(self.btn_gen_share)
        layout.addStretch(1)

        # 按钮功能：顶栏全接真逻辑
        self.btn_gen_all.clicked.connect(lambda: self._start_generate("all"))
        self.btn_gen_weather.clicked.connect(lambda: self._start_generate("weather"))
        self.btn_gen_recommend.clicked.connect(lambda: self._start_generate("recommend"))
        self.btn_gen_share.clicked.connect(lambda: self._start_generate("share"))
        self.btn_settings.clicked.connect(self._open_settings)   # 阶段2：真逻辑
        self.btn_history.clicked.connect(self._open_history)   # 阶段7：真逻辑

        self._root_layout.addWidget(bar)

    # ----- 3. 中间滚动区（三大模块面板，可滚动）-----
    def _build_content_area(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # 滚动区内部容器
        container = QWidget(scroll)
        container.setObjectName("contentContainer")
        scroll_layout = QVBoxLayout(container)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(10)

        # 三个模块面板（用真 ModulePanel 组件）
        self.panel_weather = ModulePanel(
            "morning", "🌤️ 早晚安理工", "每天必须发的早安+晚安问候语和天气配图", container
        )
        self.panel_recommend = ModulePanel(
            "recommend", "📚 小青超推荐（书 · 影 · 纪）", "每日书籍、电影、纪录片推荐（阶段4上线）", container
        )
        self.panel_share = ModulePanel(
            "share", "💡 小青爱分享", "冷知识、生活小妙招、学习技巧、健康、校史、节气等混搭分享", container
        )

        # 接入生成信号：面板的 module_key（morning）要映射成合成模块 weather
        self.panel_weather.request_generate.connect(
            lambda module_key: self._start_generate("weather")
        )
        self.panel_weather.request_refresh_all.connect(
            lambda module_key: self._start_generate("weather")
        )
        self.panel_recommend.request_generate.connect(self._start_generate)
        self.panel_recommend.request_refresh_all.connect(self._start_generate)
        self.panel_share.request_generate.connect(self._start_generate)
        self.panel_share.request_refresh_all.connect(self._start_generate)
        # 三张面板的单条「换一条」信号 → 走单条刷新流程
        self.panel_weather.request_refresh_single.connect(self._on_refresh_single)
        self.panel_recommend.request_refresh_single.connect(self._on_refresh_single)
        self.panel_share.request_refresh_single.connect(self._on_refresh_single)

        scroll_layout.addWidget(self.panel_weather)
        scroll_layout.addWidget(self.panel_recommend)
        scroll_layout.addWidget(self.panel_share)
        scroll_layout.addStretch(1)  # 底部撑开

        scroll.setWidget(container)
        self._root_layout.addWidget(scroll, stretch=1)  # 占满剩余空间

    def _build_module_panel(self, title: str, subtitle: str) -> QFrame:
        """[已废弃] 阶段1占位模块面板，阶段3起改用 ModulePanel 组件"""
        # 保留方法签名防止外部调用报错，实际不再使用
        panel = QFrame()
        return panel

    # ----- 4. 底栏（高 44px，苹果风紧凑）-----
    def _build_bottom_bar(self):
        bar = QFrame(self)
        bar.setObjectName("bottomBar")
        bar.setFixedHeight(44)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(10)

        # 左侧：状态文字
        self.lbl_status = QLabel("📊 状态：就绪 ✅", bar)
        self.lbl_status.setObjectName("statusText")
        layout.addWidget(self.lbl_status)

        # 分割
        sep = QLabel("|", bar)
        sep.setObjectName("statusText")
        layout.addWidget(sep)

        # 中间：日期
        today = datetime.now().strftime("%Y-%m-%d %A")
        weekday_map = {"Monday": "周一", "Tuesday": "周二", "Wednesday": "周三",
                       "Thursday": "周四", "Friday": "周五", "Saturday": "周六", "Sunday": "周日"}
        for en, cn in weekday_map.items():
            today = today.replace(en, cn)
        self.lbl_date = QLabel(f"📅 今天 {today}", bar)
        self.lbl_date.setObjectName("dateText")
        layout.addWidget(self.lbl_date)

        layout.addStretch(1)

        # 右侧：两个打包按钮
        self.btn_pack_selected = self._make_btn("📦 打包精选内容", "secondary", bar)
        self.btn_pack_all = self._make_btn("🗂️ 打包全部草稿", "normal", bar)
        self.btn_pack_selected.clicked.connect(self._on_pack_selected)
        self.btn_pack_all.clicked.connect(self._on_pack_all_drafts)
        layout.addWidget(self.btn_pack_selected)
        layout.addWidget(self.btn_pack_all)

        self._root_layout.addWidget(bar)

    # ============================================================
    # 工具方法
    # ============================================================

    def _make_btn(self, text: str, btn_type: str, parent=None, small: bool = False) -> QPushButton:
        """统一创建按钮（自动设置属性名供 QSS 识别）

        Args:
            text: 按钮文字
            btn_type: primary / secondary / normal / danger
            parent: 父对象
            small: 是否小尺寸按钮

        Returns:
            QPushButton
        """
        btn = QPushButton(text, parent)
        btn.setProperty("btnType", btn_type)
        if small:
            btn.setProperty("btnSize", "small")
        btn.setCursor(Qt.PointingHandCursor)
        # 按钮高度统一（阶段9再精修图标和间距）
        btn.setMinimumHeight(32 if not small else 26)
        return btn

    def _show_notice(self, title: str, msg: str):
        """阶段1占位：功能提示弹窗（后续阶段换成真逻辑）"""
        QMessageBox.information(self, title, msg)

    def _open_settings(self):
        """阶段2：打开设置弹窗"""
        try:
            dlg = SettingsDialog(self)
            result = dlg.exec()
            if result == QMessageBox.Accepted:
                # 用户保存了，刷新底栏状态显示新配置
                self.lbl_status.setText("📊 状态：设置已更新 ✅")
                logger.info("📊 主窗口状态已更新（用户保存了新设置）")
                # 阶段9：壁纸切换立即生效
                from src.config import CONFIG
                wp_key = CONFIG.get("wallpaper", "clear_blue")
                if wp_key != getattr(self, "_wallpaper_key", ""):
                    self._apply_wallpaper(wp_key)
                    logger.info(f"🖼️ 壁纸已切换为: {wp_key}")
        except Exception as e:
            logger.error(f"❌ 打开设置弹窗失败：{e}", exc_info=True)
            QMessageBox.critical(self, "❌ 错误", f"打开设置失败：{e}")

    # ============================================================
    # 阶段3：内容生成逻辑
    # ============================================================

    def _start_generate(self, module: str):
        """启动后台生成线程
        Args:
            module: morning / night / recommend / share / all
        """
        # 防止重复点击
        if hasattr(self, '_worker') and self._worker and self._worker.isRunning():
            QMessageBox.information(self, "⏳ 请稍等", "正在生成中，请等当前任务完成")
            return

        # 根据 module 选择对应的面板置 loading
        self._loading_panels = []
        if module in ("morning", "night", "weather"):
            self.panel_weather.set_loading(True, "生成中...")
            self._loading_panels.append(self.panel_weather)
        elif module == "recommend":
            self.panel_recommend.set_loading(True, "生成中...")
            self._loading_panels.append(self.panel_recommend)
        elif module == "share":
            self.panel_share.set_loading(True, "生成中...")
            self._loading_panels.append(self.panel_share)
        elif module == "all":
            self.panel_weather.set_loading(True, "生成中...")
            self.panel_recommend.set_loading(True, "生成中...")
            self.panel_share.set_loading(True, "生成中...")
            self._loading_panels.extend([self.panel_weather, self.panel_recommend, self.panel_share])
        else:
            self._show_notice("⚠️ 暂未开放", f"{module} 模块开发中")
            return

        self.lbl_status.setText(f"📊 状态：正在生成{module}...")
        self.btn_gen_all.setEnabled(False)
        self.btn_gen_weather.setEnabled(False)
        self.btn_gen_recommend.setEnabled(False)
        self.btn_gen_share.setEnabled(False)

        # 创建并启动线程
        self._worker = GenerateWorker(module, self)
        self._worker.progress.connect(self._on_generate_progress)
        self._worker.finished_items.connect(
            lambda items: self._on_generate_done(items, module)
        )
        self._worker.error.connect(self._on_generate_error)
        self._worker.start()

    def _on_generate_progress(self, msg: str):
        """生成进度回调：把进度文字写到当前所有正在加载的面板"""
        self.lbl_status.setText(f"📊 状态：{msg}")
        for panel in getattr(self, '_loading_panels', [self.panel_weather]):
            panel.lbl_status.setText(msg)

    def _on_generate_done(self, items: list, module: str):
        """生成完成回调：按 item.module 分发到对应面板"""
        # 分组
        by_panel = {
            self.panel_weather: [],
            self.panel_recommend: [],
            self.panel_share: [],
        }
        for it in items:
            if it.module in ("morning", "night"):
                by_panel[self.panel_weather].append(it)
            elif it.module == "recommend":
                by_panel[self.panel_recommend].append(it)
            elif it.module == "share":
                by_panel[self.panel_share].append(it)
        for panel, its in by_panel.items():
            if its:
                panel.show_items(its)
            panel.set_loading(False)

        self.lbl_status.setText(f"📊 状态：生成完成，共 {len(items)} 条 ✅")
        self.btn_gen_all.setEnabled(True)
        self.btn_gen_weather.setEnabled(True)
        self.btn_gen_recommend.setEnabled(True)
        self.btn_gen_share.setEnabled(True)
        logger.info(f"🎯 {module} 生成完成，UI 已更新（{len(items)} 条）")

    def _on_generate_error(self, err: str):
        """生成失败回调"""
        for panel in getattr(self, '_loading_panels', [self.panel_weather]):
            panel.set_loading(False)
        self.lbl_status.setText("📊 状态：生成失败 ❌")
        self.btn_gen_all.setEnabled(True)
        self.btn_gen_weather.setEnabled(True)
        self.btn_gen_recommend.setEnabled(True)
        self.btn_gen_share.setEnabled(True)
        QMessageBox.critical(self, "❌ 生成失败", str(err))
        logger.error(f"❌ 生成失败: {err}")

    # ============================================================
    # 单条「换一条」流程
    # ============================================================
    def _build_single_func(self, item):
        """根据 item 的 module / item_type 构造单条生成 callable"""
        module = item.module
        itype = str(item.item_type or "")
        from src.core.content_generator import (
            generate_morning_content, generate_night_content,
        )
        from src.core.recommend_generator import generate_single_recommend
        from src.core.share_generator import generate_single_share

        if module == "morning":
            return lambda: (generate_morning_content(count=1) or [None])[0]
        if module == "night":
            return lambda: (generate_night_content(count=1) or [None])[0]
        if module == "recommend":
            # 传原 item_type（中文：书籍/电影/纪录片）
            return lambda: generate_single_recommend(itype)
        if module == "share":
            # 中文 item_type 映射回英文 key（科普冷知识→science 等）
            from src.core.share_generator import _TYPE_CN as SHARE_TYPES
            key = ""
            for k, cn in SHARE_TYPES.items():
                if cn == itype:
                    key = k; break
            return lambda: generate_single_share(key) if key else generate_single_share("science")
        # 兜底
        return None

    def _on_refresh_single(self, old_item, card):
        """单条刷新入口：起一个小 worker，只调用单条生成函数"""
        func = self._build_single_func(old_item)
        if func is None:
            card.update_item(old_item.__class__(
                module=old_item.module, item_type=old_item.item_type,
                error="换一条失败：未知模块类型"
            ))
            return
        w = GenerateWorker(single_func=func)

        def _apply(items):
            self._apply_single_refresh(items, card, old_item)

        def _err(e):
            self._apply_single_refresh(
                [old_item.__class__(
                    module=old_item.module, item_type=old_item.item_type,
                    error=f"换一条失败: {e}"
                )], card, old_item
            )

        w.finished_items.connect(_apply)
        w.error.connect(_err)
        w.start()

    def _apply_single_refresh(self, items, card, old_item):
        """worker 完成后把新 item 应用到卡片上，状态栏给 3 秒提示"""
        if items:
            new_item = items[0]
            card.update_item(new_item)
            self.lbl_status.setText(f"🔄 换一条成功（{old_item.item_type}） ✅")
        else:
            from src.core.content_generator import ContentItem
            card.update_item(ContentItem(
                module=old_item.module, item_type=old_item.item_type,
                error="换一条失败：无结果返回，再试一次吧"
            ))
            self.lbl_status.setText("🔄 换一条失败：无结果，可再点一次 ❌")
        # 3 秒后状态栏恢复静态
        QTimer.singleShot(3000, lambda: self.lbl_status.setText(
            "📊 状态：就绪 ✅  |  今天 " + datetime.now().strftime("%Y-%m-%d %A")
        ))

    # ============================================================
    # 历史记录
    # ============================================================
    def _open_history(self):
        """阶段7：打开历史记录浏览对话框"""
        from src.ui.history_dialog import HistoryDialog
        try:
            dlg = HistoryDialog(self)
            dlg.exec()
        except Exception as e:
            logger.exception("打开历史记录面板失败")
            QMessageBox.critical(self, "❌ 打开失败", f"无法打开历史记录：{e}")

    # ============================================================
    # 阶段8：两个打包按钮
    # ============================================================
    def _collect_saved_items(self) -> list:
        """收集 4 个面板里所有 item.saved=True 的 ContentItem"""
        saved = []
        for panel in (self.panel_weather, self.panel_recommend, self.panel_share):
            for card in panel._cards:
                if getattr(card.item, "saved", False):
                    saved.append(card.item)
        return saved

    def _on_pack_selected(self):
        """打包精选内容（用户点过「保存图片」的）"""
        saved_items = self._collect_saved_items()
        if not saved_items:
            QMessageBox.information(
                self, "⚠️ 没有精选内容",
                "今天还没有保存任何精选内容。\n\n请先在卡片上点「💾 保存图片」，\n我会把这些保存过的内容打成 zip。"
            )
            return

        # 询问是否继续
        ret = QMessageBox.question(
            self, "📦 打包精选内容",
            f"今天共保存了 {len(saved_items)} 条精选内容。\n确定打包成 zip 吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )
        if ret != QMessageBox.Yes:
            return

        self.lbl_status.setText(f"📊 状态：正在打包 {len(saved_items)} 条精选内容...")
        self.btn_pack_selected.setEnabled(False)
        self.btn_pack_selected.setText("⏳ 打包中...")
        QApplication.processEvents()

        try:
            from src.utils.packer import pack_selected
            ok, result = pack_selected(saved_items)
            if ok:
                size_kb = os.path.getsize(result) / 1024
                self.lbl_status.setText(f"📊 状态：精选内容打包完成 ✅ ({len(saved_items)} 条, {size_kb:.0f} KB)")
                self._show_pack_result(result, "精选内容打包成功")
                logger.info(f"📦 精选内容打包完成: {result}")
            else:
                self.lbl_status.setText(f"📊 状态：打包失败 ❌")
                QMessageBox.critical(self, "❌ 打包失败", result)
        except Exception as e:
            logger.exception("精选打包异常")
            QMessageBox.critical(self, "❌ 打包失败", f"打包异常：{e}")
        finally:
            self.btn_pack_selected.setEnabled(True)
            self.btn_pack_selected.setText("📦 打包精选内容")

    def _on_pack_all_drafts(self):
        """打包全部草稿（今天日期文件夹下所有内容）"""
        from src.utils import paths
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        date_dir = paths.get_date_dir(today)

        # 先统计
        if not os.path.isdir(date_dir):
            QMessageBox.information(
                self, "⚠️ 没有内容",
                f"今天 ({today}) 还没有生成任何内容。\n请先点「一键生成全部」。"
            )
            return

        file_count = 0
        for root, dirs, files in os.walk(date_dir):
            for f in files:
                if not f.endswith(".zip"):
                    file_count += 1

        if file_count == 0:
            QMessageBox.information(
                self, "⚠️ 没有内容",
                f"今天 ({today}) 的文件夹是空的，请先点「一键生成全部」。"
            )
            return

        ret = QMessageBox.question(
            self, "🗂️ 打包全部草稿",
            f"今天 ({today}) 共有 {file_count} 个文件（包括所有文案备份和图片）。\n确定全部打包成 zip 吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )
        if ret != QMessageBox.Yes:
            return

        self.lbl_status.setText(f"📊 状态：正在打包全部草稿 ({file_count} 个文件)...")
        self.btn_pack_all.setEnabled(False)
        self.btn_pack_all.setText("⏳ 打包中...")
        QApplication.processEvents()

        try:
            from src.utils.packer import pack_all_drafts
            ok, result = pack_all_drafts()
            if ok:
                size_kb = os.path.getsize(result) / 1024
                self.lbl_status.setText(f"📊 状态：全部草稿打包完成 ✅ ({file_count} 个文件, {size_kb:.0f} KB)")
                self._show_pack_result(result, "全部草稿打包成功")
                logger.info(f"📦 全部草稿打包完成: {result}")
            else:
                self.lbl_status.setText(f"📊 状态：打包失败 ❌")
                QMessageBox.critical(self, "❌ 打包失败", result)
        except Exception as e:
            logger.exception("全部草稿打包异常")
            QMessageBox.critical(self, "❌ 打包失败", f"打包异常：{e}")
        finally:
            self.btn_pack_all.setEnabled(True)
            self.btn_pack_all.setText("🗂️ 打包全部草稿")

    def _show_pack_result(self, zip_path: str, title: str):
        """打包完成后的提示框，带「打开文件夹」按钮"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle(f"✅ {title}")
        msg.setText(f"📦 zip 已保存到：")
        msg.setInformativeText(zip_path)
        msg.setStandardButtons(QMessageBox.Ok)
        btn_open = msg.addButton("📂 打开所在文件夹", QMessageBox.AcceptRole)
        msg.exec()
        if msg.clickedButton() == btn_open:
            try:
                folder = os.path.dirname(zip_path)
                if hasattr(os, "startfile"):
                    os.startfile(folder)
                else:
                    import subprocess
                    subprocess.Popen(["explorer", folder])
            except Exception as e:
                logger.warning(f"打开文件夹失败: {e}")

    # ============================================================
    # 事件
    # ============================================================

    def closeEvent(self, event):
        """关闭窗口前记录日志"""
        logger.info("👋 用户关闭主窗口")
        super().closeEvent(event)
