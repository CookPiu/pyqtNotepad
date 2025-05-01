import sys
import os
from PyQt6.QtWidgets import (QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QTextEdit, QListWidget, QListWidgetItem, QToolBar, QMenuBar, QMenu,
                             QStatusBar, QFileDialog, QFontDialog, QColorDialog, QMessageBox,
                              QInputDialog, QSplitter, QTabWidget, QToolButton, QDockWidget, QMenu, QSizePolicy) # Import QTabWidget, QToolButton, QDockWidget, QMenu, QSizePolicy
from PyQt6.QtGui import QAction, QFont, QColor, QTextCursor, QIcon, QImage, QTextDocument, QPainter # Corrected indentation
# Import QUrl for setting browser URL and QWebEngineView for the browser widget
from PyQt6.QtCore import Qt, QSize, QUrl, QRect, QEvent, pyqtSignal, QPointF, QFile, QTextStream, QPoint, QSignalBlocker, QDateTime # Corrected indentation
# Ensure WebEngineWidgets is imported before QApplication instance (usually satisfied by top-level import)
from PyQt6.QtWebEngineWidgets import QWebEngineView # Corrected indentation
import fitz  # PyMuPDF库

# Updated imports for moved components # Corrected indentation
from src.utils.theme_manager import ThemeManager
from src.ui.file_explorer import FileExplorer
from src.utils.pdf_utils import extract_pdf_content, cleanup_temp_images
from src.ui.pdf_viewer import PDFViewer
# from src.ui.timer_widget import TimerWindow # Replaced by CombinedToolsWidget
from src.ui.editor import TextEditWithLineNumbers # Import the editor component
from src.ui.calculator_widget import CalculatorWindow
# from src.ui.calendar_widget import CalendarWindow # Replaced by CombinedToolsWidget
# from src.ui.combined_notes_widget import CombinedNotesWidget # ✅ 组合控件, Replaced by CombinedToolsWidget
from src.ui.combined_tools_widget import CombinedToolsWidget # ★ 新增组合工具控件
# --- Added imports for Note Downloader ---
import sys
from pathlib import Path
from .note_downloader_widget import NoteDownloaderWidget # Use relative import


class MainWindow(QMainWindow): # Corrected indentation for the following block
    current_editor_changed = pyqtSignal(QTextEdit) # Keep QTextEdit for broader compatibility, or change to TextEditWithLineNumbers if specific methods are needed

    def __init__(self):
        print("▶ MainWindow.__init__") # ★ 添加打印
        super().__init__()
        # Initialize ThemeManager using the correct import path
        self.theme_manager = ThemeManager()
        self.untitled_counter = 0
        self.previous_editor = None
        self.sidebar_original_width = 250 # Default width like VS Code suggestion
        self.tool_docks = {} # Dictionary to store references to tool dock widgets
        self._pre_zen_sizes = None # For saving splitter sizes before Zen mode
        self._saved_sidebar_width = self.sidebar_original_width # For toggle sidebar
        # 允许 Dock 自动分页 + 动画
        self.setDockOptions(
            QMainWindow.DockOption.AllowTabbedDocks
            | QMainWindow.DockOption.AnimatedDocks
        )
        self.initUI()
        self.apply_current_theme()
        # Check if tab widget is empty before creating a new file
        if self.tab_widget.count() == 0: # Corrected indentation
            self.new_file()

    def initUI(self):
        self.setWindowTitle("多功能记事本")
        self.setGeometry(100, 100, 1000, 700)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # --- Top Toolbar ---
        self.toolbar = QToolBar("主工具栏")
        self.toolbar.setIconSize(QSize(20, 20))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonFollowStyle) # Show text on hover
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)

        # --- ActivityBar (Left Toolbar) ---
        self.activity_bar = QToolBar("ActivityBar", self)
        self.activity_bar.setOrientation(Qt.Orientation.Vertical)
        self.activity_bar.setIconSize(QSize(20, 20))
        self.activity_bar.setFixedWidth(48)            # VS Code 默认 48
        self.activity_bar.setMovable(False)
        # Styling will be handled by QSS primarily
        # Add placeholder text/actions (remove icon loading)
        files_action = self.activity_bar.addAction("Files", lambda: self.toggle_sidebar()) # Text instead of icon
        files_action.setToolTip("文件资源管理器 (切换侧边栏)")
        self.activity_bar.addSeparator()
        # Add other placeholder actions
        # search_action = self.activity_bar.addAction(QIcon(":/icons/search.svg"), "", self.search_action.trigger)
        # search_action.setToolTip("搜索")
        # --- Add Note Downloader action ---
        act_download = self.activity_bar.addAction("DL")   # DL = Download 缩写
        act_download.setToolTip("笔记下载器")
        act_download.triggered.connect(lambda: (self.toggle_sidebar(False), self.open_note_downloader_tab())) # Show sidebar and open tab
        self.activity_bar.addSeparator() # Optional separator
        # ------------------------------------
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self.activity_bar) # Add to the left

        # --- Initialize Browser View early ---
        self.browser = QWebEngineView(self)
        self.browser.setUrl(QUrl("about:blank")) # Default URL

        # --- Tab Widget for Editors ---
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)

        # --- Vertical Splitter for original sidebar content (List + Explorer) ---
        self.sidebar_content_splitter = QSplitter(Qt.Orientation.Vertical)
        self.sidebar_content_splitter.setHandleWidth(1)

        # --- Sidebar Function List ---
        self.function_list = QListWidget() # Renamed from self.sidebar
        sidebar_items = [
            {"name": "计时器",   "icon": "clock"},
            {"name": "便签与待办","icon": "note"},   # 新条目
            {"name": "计算器",   "icon": "calculator"},
            {"name": "日历",     "icon": "calendar"},
            {"name": "笔记下载", "icon": "download"},     # ★ 新增
        ]
        for item in sidebar_items:
            list_item = QListWidgetItem(item["name"])
            list_item.setToolTip(f"{item['name']}功能（占位符）")
            # You might want to associate icons properly here if available
            self.function_list.addItem(list_item)
        self.function_list.itemClicked.connect(self.sidebar_item_clicked)

        # --- File Explorer (using imported class) ---
        self.file_explorer = FileExplorer()
        self.file_explorer.file_double_clicked.connect(self.open_file_from_path)

        # --- Add Widgets to the VERTICAL Sidebar Content Splitter ---
        self.sidebar_content_splitter.addWidget(self.function_list)
        self.sidebar_content_splitter.addWidget(self.file_explorer)
        self.sidebar_content_splitter.setSizes([200, 400]) # Adjust initial sizes if needed

        # ---------- SideBar Container----------
        # This QWidget will hold the sidebar_content_splitter
        self.sidebar = QWidget() # This is the main sidebar widget to hide/show
        self.sidebar.setObjectName("SideBarContainer") # For potential styling
        side_layout = QVBoxLayout(self.sidebar)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(0)
        side_layout.addWidget(self.sidebar_content_splitter) # Put the vertical splitter inside

        # --- Editor/Browser Splitter (Vertical) ---
        self.editor_browser_splitter = QSplitter(Qt.Orientation.Vertical)
        self.editor_browser_splitter.setHandleWidth(1) # Keep handle thin
        self.editor_browser_splitter.addWidget(self.tab_widget) # Editor tabs on top
        self.editor_browser_splitter.addWidget(self.browser)    # Browser view below
        self.editor_browser_splitter.setSizes([500, 200]) # Initial height: 500px for editor, 200px for browser

        # --- Main Horizontal Splitter (VS Code Layout) ---
        self.v_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.v_splitter.setHandleWidth(1) # Thin splitter handle
        # Note: ActivityBar is a QToolBar, added via addToolBar, not in this splitter

        # Add Sidebar Container and Editor/Browser Area to the horizontal splitter
        self.v_splitter.addWidget(self.sidebar)                 # Index 0
        self.v_splitter.addWidget(self.editor_browser_splitter) # Index 1

        # Set stretch factors: editor area (index 1) expands, sidebar (index 0) does not initially
        self.v_splitter.setStretchFactor(0, 0)
        self.v_splitter.setStretchFactor(1, 1)
        self.v_splitter.setSizes([self.sidebar_original_width, 800]) # Initial sizes

        # Set the main horizontal splitter as the central widget's layout item
        main_layout.addWidget(self.v_splitter)

        # --- Create Actions, Menus (for Zen mode), Toolbar ---
        self.create_actions()       # Define actions (including zen_action)
        self.create_menu_bar()    # Keep menu bar logic for now, will be hidden by Zen/QSS
        self.create_toolbar()     # Setup the top toolbar

        # --- Status Bar ---
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("就绪")

        # --- Make F11 Global Shortcut Work ---
        self.addAction(self.zen_action) # Add Zen mode action to window

        # --- Connect Signals ---
        self.tab_widget.currentChanged.connect(self.on_current_tab_changed)

        # --- Set Initial State ---
        self.update_edit_actions_state(self.get_current_editor())
        print("▶ initUI 完成") # ★ 添加打印

    def create_actions(self):
        # Add tooltips to all actions
        # Remove icon loading attempts to ensure text buttons appear
        self.new_action = QAction("新建", self, shortcut="Ctrl+N", toolTip="创建新文件 (Ctrl+N)", triggered=self.new_file)
        self.open_action = QAction("打开...", self, shortcut="Ctrl+O", toolTip="打开现有文件 (Ctrl+O)", triggered=self.open_file_dialog)
        self.save_action = QAction("保存", self, shortcut="Ctrl+S", toolTip="保存当前文件 (Ctrl+S)", triggered=self.save_file, enabled=False)
        self.save_as_action = QAction("另存为...", self, shortcut="Ctrl+Shift+S", toolTip="将当前文件另存为... (Ctrl+Shift+S)", triggered=self.save_file_as, enabled=False)
        self.close_tab_action = QAction("关闭标签页", self, shortcut="Ctrl+W", toolTip="关闭当前标签页 (Ctrl+W)", triggered=lambda: self.close_tab(self.tab_widget.currentIndex()), enabled=False)
        self.exit_action = QAction("退出", self, shortcut="Ctrl+Q", toolTip="退出应用程序 (Ctrl+Q)", triggered=self.close)

        self.undo_action = QAction("撤销", self, shortcut="Ctrl+Z", toolTip="撤销上一步操作 (Ctrl+Z)", triggered=self.undo_action_handler, enabled=False)
        self.redo_action = QAction("重做", self, shortcut="Ctrl+Y", toolTip="重做上一步操作 (Ctrl+Y)", triggered=self.redo_action_handler, enabled=False)
        self.cut_action = QAction("剪切", self, shortcut="Ctrl+X", toolTip="剪切选中内容 (Ctrl+X)", triggered=self.cut_action_handler, enabled=False)
        self.copy_action = QAction("复制", self, shortcut="Ctrl+C", toolTip="复制选中内容 (Ctrl+C)", triggered=self.copy_action_handler, enabled=False)
        self.paste_action = QAction("粘贴", self, shortcut="Ctrl+V", toolTip="粘贴剪贴板内容 (Ctrl+V)", triggered=self.paste_action_handler, enabled=False)
        self.select_all_action = QAction("全选", self, shortcut="Ctrl+A", toolTip="全选文档内容 (Ctrl+A)", triggered=self.select_all_action_handler, enabled=False)

        self.font_action = QAction("字体...", self, toolTip="更改字体设置", triggered=self.change_font, enabled=False)
        self.color_action = QAction("颜色...", self, toolTip="更改文本颜色", triggered=self.change_color, enabled=False)
        self.insert_image_action = QAction("插入图片...", self, toolTip="在光标处插入图片", triggered=self.insert_image, enabled=False)
        self.find_action = QAction("查找", self, shortcut="Ctrl+F", toolTip="在当前文件中查找文本 (Ctrl+F)", triggered=self.find_text, enabled=False)
        self.replace_action = QAction("替换", self, shortcut="Ctrl+H", toolTip="在当前文件中查找并替换文本 (Ctrl+H)", triggered=self.replace_text, enabled=False)

        self.toggle_theme_action = QAction("切换主题", self, shortcut="Ctrl+T", toolTip="切换亮色/暗色主题 (Ctrl+T)", triggered=self.toggle_theme)
        self.about_action = QAction("关于", self, toolTip="显示关于信息", triggered=self.show_about)

        # --- Zen Mode Action ---
        self.zen_action = QAction("Zen Mode", self, checkable=True,
                                  shortcut="F11", triggered=self.toggle_zen_mode,
                                  toolTip="进入/退出 Zen 模式 (F11)")

    def create_menu_bar(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("文件")
        file_menu.addActions([self.new_action, self.open_action, self.save_action, self.save_as_action])
        file_menu.addSeparator()
        file_menu.addAction(self.close_tab_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        edit_menu = menu_bar.addMenu("编辑")
        edit_menu.addActions([self.undo_action, self.redo_action])
        edit_menu.addSeparator()
        edit_menu.addActions([self.cut_action, self.copy_action, self.paste_action])
        edit_menu.addSeparator()
        edit_menu.addAction(self.select_all_action)
        edit_menu.addSeparator()
        edit_menu.addActions([self.find_action, self.replace_action]) # Added find/replace

        format_menu = menu_bar.addMenu("格式")
        format_menu.addActions([self.font_action, self.color_action])
        format_menu.addSeparator()
        format_menu.addAction(self.insert_image_action)
        format_menu.addSeparator()
        format_menu.addAction(self.toggle_theme_action)

        # --- Add Zen Mode to View Menu (Optional) ---
        view_menu = menu_bar.addMenu("视图")
        view_menu.addAction(self.zen_action)

        help_menu = menu_bar.addMenu("帮助")
        help_menu.addAction(self.about_action)

        # Hide the menu bar by default if using the toolbar button approach
        # menu_bar.setVisible(False) # Or control visibility in Zen Mode / QSS

    def create_toolbar(self):
        # Keep only high-frequency actions
        self.toolbar.setMovable(False)          # Prevent dragging into multiple rows
        self.toolbar.setIconSize(QSize(20, 20)) # Set desired icon size

        # --- Main Action Buttons ---
        self.toolbar.addActions([self.new_action, self.open_action, self.save_action])
        self.toolbar.addSeparator()
        self.toolbar.addActions([self.undo_action, self.redo_action])
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.find_action)

        # --- Spacer to push menu button to the right ---
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.toolbar.addWidget(spacer)

        # --- Menu Dropdown Button ---
        menu_btn = QToolButton()
        # Use fallback text directly
        menu_btn.setText("...") # Fallback text
        menu_btn.setToolTip("更多选项")

        menu_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup) # Show menu immediately on click
        more_menu = QMenu(menu_btn)

        # Add actions previously in the menu bar
        file_submenu = more_menu.addMenu("文件") # Group file actions
        file_submenu.addActions([self.save_as_action, self.close_tab_action])
        file_submenu.addSeparator()
        file_submenu.addAction(self.exit_action)

        edit_submenu = more_menu.addMenu("编辑") # Group edit actions
        edit_submenu.addActions([self.cut_action, self.copy_action,
                                 self.paste_action, self.select_all_action])
        edit_submenu.addSeparator()
        edit_submenu.addAction(self.replace_action) # Add replace back here

        format_submenu = more_menu.addMenu("格式") # Group format actions
        format_submenu.addActions([self.font_action, self.color_action,
                                   self.insert_image_action])

        view_submenu = more_menu.addMenu("视图") # Group view actions
        view_submenu.addAction(self.toggle_theme_action)
        view_submenu.addSeparator()
        view_submenu.addAction(self.zen_action) # Add Zen mode toggle here too

        help_submenu = more_menu.addMenu("帮助") # Group help actions
        help_submenu.addAction(self.about_action)

        menu_btn.setMenu(more_menu)
        self.toolbar.addWidget(menu_btn)

        # --- Hide the original Menu Bar ---
        # Keep menuBar object for Zen mode toggle, but hide it visually
        self.menuBar().setVisible(False)

    def get_current_editor(self) -> TextEditWithLineNumbers | None:
        # Ensure we return the correct type or None
        widget = self.tab_widget.currentWidget()
        return widget if isinstance(widget, TextEditWithLineNumbers) else None

    def on_current_tab_changed(self, index):
         # This function remains mostly the same
         editor = self.get_current_editor()
         self.update_edit_actions_state(editor)
         self.update_window_title() # Corrected indentation
         # Ensure signal emits the correct type or None
         self.current_editor_changed.emit(editor if editor else None)

         # --- Collapse/Expand global browser based on tab type ---
         w = self.tab_widget.widget(index)
         if isinstance(w, NoteDownloaderWidget):
             self._collapse_global_browser()
         else:
             # Only restore if the browser is actually collapsed
             if len(self.editor_browser_splitter.sizes()) == 2 and self.editor_browser_splitter.sizes()[1] == 0:
                self._restore_global_browser()

    def _update_copy_cut_state(self, available: bool):
        # This helper function remains the same
        self.copy_action.setEnabled(available)
        self.cut_action.setEnabled(available)

    def update_edit_actions_state(self, editor: TextEditWithLineNumbers | None):
        # This function remains largely the same, ensures actions are enabled/disabled correctly
        has_editor = isinstance(editor, TextEditWithLineNumbers)
        # Attempt to get clipboard data safely
        try:
            can_paste = QApplication.clipboard().text() != "" if has_editor else False
        except Exception:
            can_paste = False # Handle cases where clipboard access might fail

        # Disconnect previous signals safely
        if self.previous_editor:
            try: self.previous_editor.document().undoAvailable.disconnect(self.undo_action.setEnabled)
            except TypeError: pass
            try: self.previous_editor.document().redoAvailable.disconnect(self.redo_action.setEnabled)
            except TypeError: pass
            try: self.previous_editor.copyAvailable.disconnect(self._update_copy_cut_state)
            except TypeError: pass
            try: self.previous_editor.document().modificationChanged.disconnect(self.update_tab_title)
            except TypeError: pass

        is_undoable = has_editor and editor.document().isUndoAvailable()
        is_redoable = has_editor and editor.document().isRedoAvailable()
        has_selection = has_editor and editor.textCursor().hasSelection()

        self.undo_action.setEnabled(is_undoable)
        self.redo_action.setEnabled(is_redoable)
        self.cut_action.setEnabled(has_selection)
        self.copy_action.setEnabled(has_selection)
        self.paste_action.setEnabled(has_editor and can_paste)
        self.select_all_action.setEnabled(has_editor)
        self.font_action.setEnabled(has_editor)
        self.color_action.setEnabled(has_editor)
        self.insert_image_action.setEnabled(has_editor)
        self.save_action.setEnabled(has_editor)
        self.save_as_action.setEnabled(has_editor)
        self.close_tab_action.setEnabled(has_editor)
        self.find_action.setEnabled(has_editor)
        self.replace_action.setEnabled(has_editor)

        # Connect signals for the current editor safely
        if has_editor:
            try: editor.document().undoAvailable.connect(self.undo_action.setEnabled)
            except TypeError: pass
            try: editor.document().redoAvailable.connect(self.redo_action.setEnabled)
            except TypeError: pass
            try: editor.copyAvailable.connect(self._update_copy_cut_state)
            except TypeError: pass
            try: editor.document().modificationChanged.connect(self.update_tab_title)
            except TypeError: pass
            self.previous_editor = editor
        else:
            self.previous_editor = None

    def update_window_title(self):
        # This function remains mostly the same
        editor = self.get_current_editor()
        title_prefix = "多功能记事本"
        if editor and (index := self.tab_widget.currentIndex()) != -1:
            tab_text = self.tab_widget.tabText(index)
            if tab_text: # Check if tab_text is not empty
                # Strip '*' only if it exists at the end
                base_tab_text = tab_text[:-1].strip() if tab_text.endswith("*") else tab_text
                title_prefix = f"{base_tab_text} - {title_prefix}"
        self.setWindowTitle(title_prefix)

    def update_tab_title(self, modified: bool):
         # This function remains mostly the same
         index = self.tab_widget.currentIndex()
         if index == -1: return
         editor = self.tab_widget.widget(index)
         if not isinstance(editor, TextEditWithLineNumbers): return

         file_path = editor.property("file_path")
         # Use untitled_name if file_path is None, otherwise use base name
         tab_name_base = os.path.basename(file_path) if file_path else (editor.property("untitled_name") or f"未命名-{self.untitled_counter}")

         new_tab_text = f"{tab_name_base}{'*' if modified else ''}"
         self.tab_widget.setTabText(index, new_tab_text)
         self.update_window_title() # Update window title as well

    # --- Action Handlers ---
    def undo_action_handler(self):
        if editor := self.get_current_editor(): editor.undo()
    def redo_action_handler(self):
        if editor := self.get_current_editor(): editor.redo()
    def cut_action_handler(self):
        if editor := self.get_current_editor(): editor.cut()
    def copy_action_handler(self):
        if editor := self.get_current_editor(): editor.copy()
    def paste_action_handler(self):
        if editor := self.get_current_editor(): editor.paste()
    def select_all_action_handler(self):
        if editor := self.get_current_editor(): editor.selectAll()

    # --- Sidebar Click Handler (Corrected Logic Again) ---
    def sidebar_item_clicked(self, item):
        item_text = item.text()
        is_combined_tool = item_text in ("计时器", "便签与待办", "日历")
        combined_dock_key = "CombinedTools"
        # 确定要查找或存储的 dock 的 key
        dock_key = combined_dock_key if is_combined_tool else item_text

        dock = self.tool_docks.get(dock_key) # 尝试获取已存在的 dock

        if dock is None: # 如果 dock 不存在，则创建
            widget_instance = None
            dock_title = item_text # 默认标题

            # 根据 item_text 创建对应的 widget 实例
            if is_combined_tool:
                widget_instance = CombinedToolsWidget(self)
                dock_title = "工具箱"
            elif item_text == "计算器":
                widget_instance = CalculatorWindow(self)
            elif item_text == "笔记下载":
                self.open_note_downloader_tab()
                return # 笔记下载不创建 dock
            # Add other non-combined tools here if needed

            # 如果成功创建了 widget 实例，则创建 Dock 并进行处理
            if widget_instance:
                # ★ 使用临时变量 new_dock 存储新创建的 dock ★
                new_dock = QDockWidget(dock_title, self)
                new_dock.setWidget(widget_instance)
                new_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.BottomDockWidgetArea)
                self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, new_dock)

                # --- Attempt to Tabify ---
                tabified = False
                # 尝试将新 dock 与该区域已存在的 dock 合并为 Tab
                for existing in self.findChildren(QDockWidget):
                    # 确保 existing 不是 new_dock 本身，并且在同一个区域
                    if existing is not new_dock and self.dockWidgetArea(existing) == self.dockWidgetArea(new_dock):
                        self.tabifyDockWidget(existing, new_dock)
                        tabified = True
                        break

                # ★ 将新创建的 dock 存储到 self.tool_docks 中，并赋值给 dock 变量 ★
                self.tool_docks[dock_key] = new_dock
                dock = new_dock # ★ 关键：确保后续操作使用的是新创建的 dock

                # 移除显式隐藏逻辑，让 raise_() 处理显示

            # 如果没有创建 widget 实例，且不是合并工具（即真正的占位符）
            elif not is_combined_tool:
                QMessageBox.information(self, "功能占位符", f"'{item_text}' 功能尚未实现。")
                return # Exit if no widget created

        # --- dock 存在（无论是找到的还是新创建的）---
        if dock: # 检查 dock 是否有效
            dock.show() # ★ 添加显式显示 ★
            dock.raise_() # 提升到顶层并显示

            # 如果是合并工具，切换内部 Tab
            if is_combined_tool and isinstance(dock.widget(), CombinedToolsWidget):
                tab_map = {"日历": 0, "便签与待办": 1, "计时器": 2}
                target_index = tab_map.get(item_text)
                if target_index is not None:
                    dock.widget().tabs.setCurrentIndex(target_index)

            # 更新状态栏消息
            if is_combined_tool:
                self.statusBar.showMessage(f"已切换到工具箱中的 '{item_text}'")
            else:
                self.statusBar.showMessage(f"已打开 {item_text} 功能")
        # else: # Debugging check
        #     print(f"ERROR: Dock is still None for item '{item_text}' after creation attempt!")


    # --- File Operations ---
    def new_file(self):
        # Use the imported TextEditWithLineNumbers (now based on QPlainTextEdit)
        editor = TextEditWithLineNumbers()
        # Set font size for QPlainTextEdit
        font = editor.font()
        font.setPointSize(12)
        editor.setFont(font)
        self.untitled_counter += 1
        tab_name = f"未命名-{self.untitled_counter}"
        editor.setProperty("untitled_name", tab_name)
        # No need to manually connect signals handled within TextEditWithLineNumbers
        index = self.tab_widget.addTab(editor, tab_name)
        self.tab_widget.setCurrentIndex(index)
        # Set properties directly on the editor instance
        editor.setProperty("file_path", None)
        editor.setProperty("is_new", True)
        editor.setProperty("is_pdf_converted", False)
        editor.setProperty("pdf_temp_dir", None)
        editor.document().setModified(False) # Ensure new file starts unmodified
        self.statusBar.showMessage("新建文件")
        # Update actions state for the new editor
        self.update_edit_actions_state(editor)

    def open_file_dialog(self):
         # This function remains mostly the same
         file_name, _ = QFileDialog.getOpenFileName(self, "打开文件", "", "HTML文件 (*.html);;文本文件 (*.txt);;PDF文件 (*.pdf);;所有文件 (*)")
         if file_name:
             self.open_file_from_path(file_name)

    def open_file_from_path(self, file_path):
        # This function remains mostly the same
        abs_file_path = os.path.abspath(file_path)
        # Check if file is already open
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if isinstance(widget, TextEditWithLineNumbers) and widget.property("file_path") == abs_file_path:
                self.tab_widget.setCurrentIndex(i)
                self.statusBar.showMessage(f"切换到已打开文件: {file_path}")
                return

        # Use the imported TextEditWithLineNumbers
        editor = TextEditWithLineNumbers()
        editor.setFontPointSize(12)
        try:
            _, ext = os.path.splitext(file_path)
            file_base_name = os.path.basename(file_path)

            if ext.lower() == '.pdf':
                 self.open_pdf_preview(abs_file_path)
                 # PDF preview is modal or handles its own lifecycle, don't add an editor tab here
                 return
            elif ext.lower() == '.html':
                # Use QSignalBlocker to prevent premature modification signals
                with open(abs_file_path, 'r', encoding='utf-8') as f: content = f.read()
                with QSignalBlocker(editor.document()): editor.setHtml(content)
            else: # Handle text files
                try:
                    with open(abs_file_path, 'r', encoding='utf-8') as f: content = f.read()
                except UnicodeDecodeError: # Fallback encoding
                    with open(abs_file_path, 'r', encoding='gbk') as f: content = f.read()
                # Use QSignalBlocker here as well
                with QSignalBlocker(editor.document()): editor.setPlainText(content)

            # Add the new editor as a tab
            index = self.tab_widget.addTab(editor, file_base_name)
            self.tab_widget.setCurrentIndex(index)
            editor.setProperty("file_path", abs_file_path)
            editor.setProperty("is_new", False)
            editor.setProperty("is_pdf_converted", False) # Reset PDF flag
            editor.setProperty("pdf_temp_dir", None)    # Reset temp dir
            editor.document().setModified(False) # Mark as unmodified initially
            self.statusBar.showMessage(f"已打开: {file_path}")
            self.update_edit_actions_state(editor) # Update actions for the new tab

        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开文件 '{file_path}':\n{str(e)}")
            # Clean up the tab if editor creation failed mid-way
            # Check if 'index' exists and if the widget at that index is the problematic editor
            if 'index' in locals() and index < self.tab_widget.count() and self.tab_widget.widget(index) == editor:
                 self.tab_widget.removeTab(index)
                 editor.deleteLater()

    def save_file(self) -> bool:
        # This function remains mostly the same
        editor = self.get_current_editor()
        if not editor: return False

        if editor.property("is_new") or not editor.property("file_path"):
            return self.save_file_as()
        else:
            file_path = editor.property("file_path")
            try:
                _, ext = os.path.splitext(file_path)
                # Check if saving as HTML or Plain Text based on extension
                content_to_save = editor.toHtml() if ext.lower() == '.html' else editor.toPlainText()
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content_to_save)
                editor.document().setModified(False)
                self.statusBar.showMessage(f"已保存: {file_path}")
                self.update_tab_title(False) # Update tab title immediately
                return True
            except Exception as e:
                 QMessageBox.critical(self, "错误", f"无法保存文件 '{file_path}':\n{str(e)}")
                 return False

    def save_file_as(self) -> bool:
        # This function remains mostly the same
        editor = self.get_current_editor()
        if not editor: return False

        current_path = editor.property("file_path")
        untitled_name = editor.property("untitled_name")
        # Suggest filename based on current path or untitled name
        suggested_name = os.path.basename(current_path) if current_path else (untitled_name or f"未命名-{self.untitled_counter}")

        default_dir = os.path.dirname(current_path) if current_path else ""

        # Determine default filter based on content or existing extension
        default_filter = "HTML文件 (*.html)"
        is_plain = editor.toPlainText() == editor.toHtml() # Basic check if content is likely plain text
        if current_path and os.path.splitext(current_path)[1].lower() != '.html':
             default_filter = "文本文件 (*.txt)"
        elif is_plain and not current_path: # New file that looks like plain text
             default_filter = "文本文件 (*.txt)"

        file_name, selected_filter = QFileDialog.getSaveFileName(
            self, "另存为", os.path.join(default_dir, suggested_name),
            "HTML文件 (*.html);;文本文件 (*.txt);;所有文件 (*)", default_filter
        )

        if file_name:
            abs_file_path = os.path.abspath(file_name)
            # Ensure extension based on filter if none provided
            _, current_ext = os.path.splitext(abs_file_path)
            if not current_ext:
                 abs_file_path += ".html" if "HTML" in selected_filter else ".txt"

            _, save_ext = os.path.splitext(abs_file_path)
            try:
                # Save as HTML or Plain Text based on final extension
                content_to_save = editor.toHtml() if save_ext.lower() == '.html' else editor.toPlainText()
                with open(abs_file_path, 'w', encoding='utf-8') as f:
                    f.write(content_to_save)

                # Update editor properties
                editor.setProperty("file_path", abs_file_path)
                editor.setProperty("is_new", False)
                editor.setProperty("untitled_name", None) # Clear untitled name
                editor.document().setModified(False)

                # Update tab text for the current editor
                current_index = self.tab_widget.currentIndex()
                if current_index != -1 and self.tab_widget.widget(current_index) == editor:
                     # Update tab text immediately after save as
                     self.tab_widget.setTabText(current_index, os.path.basename(abs_file_path))
                     # Explicitly call update_tab_title to ensure '*' is removed and window title updates
                     self.update_tab_title(False)

                self.statusBar.showMessage(f"已保存: {abs_file_path}")
                return True
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法保存文件 '{abs_file_path}':\n{str(e)}")
        return False

    def close_tab(self, index):
        # This function remains mostly the same, ensure cleanup happens correctly
        if index < 0 or index >= self.tab_widget.count(): return
        widget = self.tab_widget.widget(index)

        # Handle non-editor widgets (like potential future PDF viewer tabs directly)
        if not isinstance(widget, TextEditWithLineNumbers):
            self.tab_widget.removeTab(index)
            widget.deleteLater() # Ensure non-editor widgets are cleaned up
            return

        editor = widget # Now we know it's an editor
        if editor.document().isModified():
            self.tab_widget.setCurrentIndex(index) # Ensure the tab being closed is active for the dialog
            tab_name = self.tab_widget.tabText(index)
            ret = QMessageBox.warning(self, "关闭标签页", f"文档 '{tab_name}' 已被修改。\n是否保存更改？",
                                    QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
            if ret == QMessageBox.StandardButton.Save:
                if not self.save_file(): return # Don't close if save fails
            elif ret == QMessageBox.StandardButton.Cancel: return # Don't close if cancelled

        # Cleanup PDF temp files if this tab was a converted PDF
        temp_dir = editor.property("pdf_temp_dir")
        if temp_dir:
            cleanup_temp_images(temp_dir) # Use imported function

        # Safely disconnect signals before removing
        if self.previous_editor == editor: self.previous_editor = None
        try: editor.document().undoAvailable.disconnect()
        except TypeError: pass
        try: editor.document().redoAvailable.disconnect()
        except TypeError: pass
        try: editor.copyAvailable.disconnect()
        except TypeError: pass
        try: editor.document().modificationChanged.disconnect()
        except TypeError: pass

        self.tab_widget.removeTab(index)
        editor.deleteLater() # Schedule deletion

        # If the last tab was closed, create a new one
        if self.tab_widget.count() == 0:
            self.new_file()
        else:
             # Update actions state based on the potentially new current tab
             current_editor = self.get_current_editor()
             if current_editor:
                 self.update_edit_actions_state(current_editor)
             else: # No editor left after close? Should not happen if new_file is called
                 self.update_edit_actions_state(None)

    # --- New Sidebar Toggle Method ---
    def toggle_sidebar(self, force_hide=None):
        """Toggles the visibility of the sidebar using splitter sizes.
           None=toggle, True=hide, False=show"""
        sizes = self.v_splitter.sizes() # [sidebar_width, editor_width]
        # Activity bar width (48) is not part of the splitter sizes

        if force_hide is None:
            force_hide = sizes[0] > 0 # Considered visible if width > 0

        if force_hide:
            # Hide sidebar
            if sizes[0] > 0: # Store width only if it was visible
                 self._saved_sidebar_width = sizes[0]
            # Set sidebar width to 0, give its space to the editor
            self.v_splitter.setSizes([0, sizes[1] + self._saved_sidebar_width])
        else:
            # Show sidebar
            # Restore saved width or default, ensure minimum width
            w = max(getattr(self, "_saved_sidebar_width", self.sidebar_original_width), 150)
            # Calculate new editor width, ensuring it's not negative
            new_editor_width = max(150, sizes[1] - w)
            self.v_splitter.setSizes([w, new_editor_width])

    # --- New Zen Mode Toggle Method ---
    def toggle_zen_mode(self, zen: bool):
        """Enters or exits Zen mode."""
        # Widgets to hide/show
        widgets_to_hide = [self.activity_bar, self.sidebar, self.toolbar, self.statusBar(), self.menuBar()]

        if zen:
            # --- Enter Zen Mode ---
            # Save current splitter sizes BEFORE hiding widgets
            self._pre_zen_sizes = self.v_splitter.sizes()

            # Hide UI elements
            for w in widgets_to_hide:
                w.setVisible(False)

            # Make editor take full space (set sidebar width to 0 in splitter)
            # Note: v_splitter only contains [sidebar, editor_browser_splitter]
            self.v_splitter.setSizes([0, 1]) # Give all space to editor area (index 1)

            # Optional: Go Fullscreen
            # self.showFullScreen()

        else:
            # --- Exit Zen Mode ---
            # Restore splitter sizes if available, otherwise use defaults
            if self._pre_zen_sizes:
                 # Ensure restored sizes are valid (e.g., handle case where sidebar was hidden before Zen)
                 if self._pre_zen_sizes[0] == 0 and self.sidebar.isVisible(): # If sidebar was hidden but should be visible now
                      restore_sidebar_width = getattr(self, "_saved_sidebar_width", self.sidebar_original_width)
                      restore_editor_width = max(150, self._pre_zen_sizes[1] - restore_sidebar_width)
                      self.v_splitter.setSizes([restore_sidebar_width, restore_editor_width])
                 else:
                      self.v_splitter.setSizes(self._pre_zen_sizes)
            else:
                 # Fallback default sizes
                 self.v_splitter.setSizes([self.sidebar_original_width, 800])

            # Show UI elements
            for w in widgets_to_hide:
                 # Special case: Don't show menuBar if it was originally hidden by toolbar logic
                 if w == self.menuBar() and not w.isVisible():
                      continue # Keep it hidden if it should be
                 w.setVisible(True)

            # Optional: Exit Fullscreen
            # self.showNormal()

        # Ensure the action's checked state reflects the mode
        self.zen_action.setChecked(zen)

    # --- Helper methods for managing global browser visibility ---
    def _collapse_global_browser(self):
        """隐藏全局 browser，让上部编辑区占满整个垂直空间"""
        self.browser.setVisible(False)
        sizes = self.editor_browser_splitter.sizes()
        if len(sizes) == 2 and sizes[1] > 0: # Only collapse if browser has size
            total = sum(sizes)
            self.editor_browser_splitter.setSizes([total, 0])

    def _restore_global_browser(self):
        """恢复浏览器视图（非笔记下载标签被选中时调用）"""
        self.browser.setVisible(True)
        # Restore a reasonable ratio, ensuring total size isn't drastically changed
        # Get current sizes first to maintain total height if possible
        current_sizes = self.editor_browser_splitter.sizes()
        if len(current_sizes) == 2:
            total = sum(current_sizes)
            # Restore to a fixed ratio like 500/200 or calculate based on total
            restore_top = max(100, total - 200) # Ensure top has at least 100px
            restore_bottom = total - restore_top
            # Check if browser was actually collapsed before restoring fixed sizes
            if current_sizes[1] == 0:
                 self.editor_browser_splitter.setSizes([restore_top, restore_bottom])
            # If browser wasn't collapsed (e.g., user dragged), keep current sizes? Or force restore?
            # For simplicity, let's force restore the ratio if it's not already collapsed.
            # You might want different logic here based on desired behavior.
            # Let's assume we only need to restore *if* it was collapsed.
            # If current_sizes[1] > 0, do nothing, user might have resized manually.

    def maybe_save_all(self) -> bool:
         # This function remains mostly the same
         original_index = self.tab_widget.currentIndex()
         modified_tabs = [i for i in range(self.tab_widget.count())
                          if isinstance(w := self.tab_widget.widget(i), TextEditWithLineNumbers) and w.document().isModified()]

         if not modified_tabs: return True # No modified tabs, safe to exit

         for i in reversed(modified_tabs): # Iterate backwards for stable indices when saving
              self.tab_widget.setCurrentIndex(i) # Activate the tab
              tab_name = self.tab_widget.tabText(i)
              ret = QMessageBox.warning(self, "退出确认", f"文档 '{tab_name}' 已被修改。\n是否保存更改？",
                                        QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
              if ret == QMessageBox.StandardButton.Save:
                  if not self.save_file(): # Attempt to save
                      # Restore original index if save fails and user cancels exit
                      if original_index < self.tab_widget.count(): self.tab_widget.setCurrentIndex(original_index)
                      return False # Exit cancelled due to save failure
              elif ret == QMessageBox.StandardButton.Cancel:
                  # Restore original index if user cancels exit
                  if original_index < self.tab_widget.count(): self.tab_widget.setCurrentIndex(original_index)
                  return False # Exit cancelled by user

         # If we reach here, all saves/discards were successful or user chose discard
         # Restore a valid index if possible after potential tab closures during save
         # Need to re-check tab count as it might have changed
         current_tab_count = self.tab_widget.count()
         if current_tab_count > 0:
             # Ensure the original index is still valid within the new count
             new_index = max(0, min(original_index, current_tab_count - 1)) if original_index < current_tab_count else 0
             self.tab_widget.setCurrentIndex(new_index)
         return True # Exit approved

    # --- PDF Handling ---
    def open_pdf_preview(self, pdf_path):
        # Use the imported PDFViewer
        try:
            pdf_viewer = PDFViewer(pdf_path, self) # Use imported class
            pdf_viewer.convert_to_html_signal.connect(self.convert_pdf_to_html)
            pdf_viewer.exec() # Show as modal dialog
        except Exception as e:
             QMessageBox.critical(self, "错误", f"无法打开PDF预览: {str(e)}")

    def convert_pdf_to_html(self, pdf_path):
        # Use imported pdf_utils functions
        try:
            # Pass self (main window) as parent for potential dialogs in extract_pdf_content
            html_content, temp_dir = extract_pdf_content(pdf_path, self)
            if html_content:
                # Use imported TextEditWithLineNumbers
                editor = TextEditWithLineNumbers()
                editor.setFontPointSize(12)
                with QSignalBlocker(editor.document()): editor.setHtml(html_content)

                tab_name = f"{os.path.basename(pdf_path)} (HTML)"
                index = self.tab_widget.addTab(editor, tab_name)
                self.tab_widget.setCurrentIndex(index)

                # Set properties for the new editor tab
                editor.setProperty("file_path", None) # Converted content isn't saved yet
                editor.setProperty("is_new", True)     # Treat as a new file until saved
                editor.setProperty("is_pdf_converted", True)
                editor.setProperty("pdf_temp_dir", temp_dir) # Store temp dir for cleanup
                editor.document().setModified(False) # Start as unmodified

                self.statusBar.showMessage(f"已从PDF转换为HTML: {pdf_path}")
                self.update_edit_actions_state(editor) # Update actions
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法转换PDF文件: {str(e)}")

    # --- Formatting ---
    def change_font(self):
        # This function remains mostly the same
        if editor := self.get_current_editor():
            font, ok = QFontDialog.getFont(editor.currentFont(), self, "选择字体")
            if ok:
                editor.setCurrentFont(font)
                editor.document().setModified(True) # Mark as modified

    def change_color(self):
        # This function remains mostly the same
        if editor := self.get_current_editor():
            color = QColorDialog.getColor(editor.textColor(), self, "选择颜色")
            if color.isValid():
                editor.setTextColor(color)
                editor.document().setModified(True) # Mark as modified

    def insert_image(self):
         # This function remains mostly the same
         if editor := self.get_current_editor():
             file_name, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif)")
             if file_name:
                 try:
                     image = QImage(file_name)
                     if image.isNull():
                         QMessageBox.warning(self, "插入图片", "无法加载图片！")
                         return

                     # Basic scaling logic (can be improved)
                     max_width = editor.viewport().width() - 40 # Leave some margin
                     if image.width() > max_width:
                         image = image.scaledToWidth(max_width, Qt.TransformationMode.SmoothTransformation)

                     # Add image resource to document
                     image_url = QUrl.fromLocalFile(file_name)
                     document = editor.document()
                     # Use a unique name for the resource in case the same file is inserted multiple times
                     resource_name = f"{image_url.toString()}_{QDateTime.currentMSecsSinceEpoch()}"
                     document.addResource(QTextDocument.ResourceType.ImageResource, QUrl(resource_name), image)

                     # Insert image at cursor position using the unique resource name
                     editor.textCursor().insertImage(resource_name)
                     self.statusBar.showMessage(f"已插入图片: {os.path.basename(file_name)}")
                     editor.document().setModified(True) # Mark as modified
                 except Exception as e:
                      QMessageBox.critical(self, "插入图片错误", f"插入图片时出错: {str(e)}")
         else:
             QMessageBox.warning(self, "插入图片", "没有活动的编辑窗口！")

    # --- Find and Replace ---
    def find_text(self):
        if editor := self.get_current_editor():
            text, ok = QInputDialog.getText(self, "查找", "输入要查找的文本:", text=getattr(self, '_last_find_text', '')) # Remember last search
            if ok and text:
                 self._last_find_text = text # Store last search term
                 # Start search from current cursor or top if not found initially
                 if not editor.find(text):
                     cursor = editor.textCursor()
                     cursor.movePosition(QTextCursor.MoveOperation.Start)
                     editor.setTextCursor(cursor)
                     if not editor.find(text):
                         QMessageBox.information(self, "查找", f"未找到 '{text}'")
                     else:
                          # Scroll to ensure the found text is visible (optional)
                          editor.ensureCursorVisible()
                 else:
                      editor.ensureCursorVisible()

    def replace_text(self):
        if editor := self.get_current_editor():
            find_text, ok1 = QInputDialog.getText(self, "查找", "输入要查找的文本:", text=getattr(self, '_last_find_text', ''))
            if ok1 and find_text:
                self._last_find_text = find_text # Store search term
                replace_text, ok2 = QInputDialog.getText(self, "替换", "输入要替换的文本:", text=getattr(self, '_last_replace_text', ''))
                if ok2:
                    self._last_replace_text = replace_text # Store replace term
                    # Offer Replace All or Replace Next (Example: Replace All)
                    reply = QMessageBox.question(self, '替换', f"查找 '{find_text}' 并替换为 '{replace_text}'？\n选择 'Yes' 替换所有, 'No' 查找下一个。",
                                               QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)

                    if reply == QMessageBox.StandardButton.Cancel: return

                    if reply == QMessageBox.StandardButton.Yes: # Replace All
                        cursor = editor.textCursor()
                        cursor.movePosition(QTextCursor.MoveOperation.Start)
                        editor.setTextCursor(cursor)
                        count = 0
                        # Use QSignalBlocker for performance during bulk replace
                        # Use document's begin/end macro for better undo grouping
                        editor.document().beginMacro("Replace All")
                        while editor.find(find_text):
                             cursor = editor.textCursor()
                             # Check if the found text is exactly what we search for before replacing
                             if cursor.selectedText() == find_text:
                                  cursor.insertText(replace_text)
                                  count += 1
                             else: # If find highlights something different, stop to avoid issues
                                  break
                        editor.document().endMacro()

                        if count > 0:
                             # No need to set modified=True, endMacro handles it
                             self.statusBar.showMessage(f"已替换 {count} 处匹配项")
                        else:
                             self.statusBar.showMessage("未找到匹配项")
                    elif reply == QMessageBox.StandardButton.No: # Find Next (similar to find_text logic)
                         if not editor.find(find_text):
                             cursor = editor.textCursor()
                             cursor.movePosition(QTextCursor.MoveOperation.Start)
                             editor.setTextCursor(cursor)
                             if not editor.find(find_text):
                                 QMessageBox.information(self, "查找", f"未找到 '{find_text}'")
                             else: editor.ensureCursorVisible()
                         else: editor.ensureCursorVisible()

                    # Update actions state after potential modification
                    self.update_edit_actions_state(editor)

    # --- Help and Theme ---
    def show_about(self):
        # Consider moving this to a separate dialog class (e.g., src/ui/dialogs/about_dialog.py)
        QMessageBox.about(self, "关于多功能记事本",
                          "多功能记事本 v1.4 (持续改进中)\n\n一个基于PyQt6的记事本应用，支持多文件编辑、HTML、PDF预览/转换、图片插入、主题切换等。")

    def apply_current_theme(self):
        """调用 ThemeManager 并刷新所有子组件的调色板 / QSS。"""
        try:
            app = QApplication.instance()
            if not app: return # Safety check

            # 1. Apply base QSS from ThemeManager
            self.theme_manager.apply_theme(app)

            # 2. Determine if dark theme is active (Corrected logic)
            is_dark = self.theme_manager.get_current_theme() == ThemeManager.DARK_THEME # ★ 修正：使用 get_current_theme() 比较

            # 3. Refresh editor colors explicitly
            for i in range(self.tab_widget.count()):
                 widget = self.tab_widget.widget(i)
                 if isinstance(widget, TextEditWithLineNumbers):
                     widget.update_highlight_colors(is_dark) # Call the new method in editor
                     # No need for separate viewport updates if update_highlight_colors handles it

            # 4. Refresh File Explorer theme if exists
            if hasattr(self, 'file_explorer') and self.file_explorer:
                 self.file_explorer.update_theme(self.theme_manager.get_current_theme()) # Assuming FileExplorer has this method

            # 5. Apply global scrollbar styles dynamically - This might be better handled entirely in QSS
            # Combine base style with scrollbar style to avoid overriding everything
            base_stylesheet = app.styleSheet() # Get the currently applied base style
            # Scrollbar styles are now primarily defined in the main QSS file
            # Append scrollbar style to existing stylesheet
            # app.setStyleSheet(base_stylesheet + "\n" + scrollbar_style) # Let QSS handle this

            # Update status bar message
            theme_name = "深色" if is_dark else "浅色"
            self.statusBar.showMessage(f"已切换至 {theme_name} 主题", 3000)

            # Update Activity Bar Style based on theme (Corrected indentation)
            activity_bg = "#333333" if is_dark else "#F3F3F3" # Example light theme color
            activity_hover = "#444444" if is_dark else "#E0E0E0"
            activity_pressed = "#555555" if is_dark else "#D0D0D0" # Added pressed color
            # Create stylesheet string separately to avoid f-string indentation issues
            activity_bar_style = f"""
                QToolBar {{ background: {activity_bg}; border: 0; }}
                QToolButton {{
                    width: 48px;
                    padding: 10px 0; /* Adjust padding */
                    color: {'#FFFFFF' if is_dark else '#000000'}; /* Text color */
                    border: none; /* Ensure no border */
                }}
                QToolButton:hover {{ background: {activity_hover}; }}
                QToolButton:pressed {{ background: {activity_pressed}; }} /* Added pressed style */
            """
            self.activity_bar.setStyleSheet(activity_bar_style.strip()) # Apply the created string

        except Exception as e:
            print(f"应用主题时出错: {str(e)}")
            # Consider showing a user-friendly error message
            # QMessageBox.warning(self, "主题错误", f"应用主题时出错:\n{str(e)}")
        print("▶ 主题应用完成") # ★ 添加打印

    def toggle_theme(self):
        # This function remains the same, relies on ThemeManager
        self.theme_manager.toggle_theme()
        self.apply_current_theme()

    # --- Application Closing ---
    def closeEvent(self, event):
        # This function remains mostly the same
        if self.maybe_save_all(): # Check if user wants to save changes
            # Cleanup temporary PDF directories before closing
            for i in range(self.tab_widget.count()):
                widget = self.tab_widget.widget(i)
                if isinstance(widget, TextEditWithLineNumbers):
                    if temp_dir := widget.property("pdf_temp_dir"):
                        cleanup_temp_images(temp_dir) # Use imported function
            event.accept() # Allow closing
        else:
            event.ignore() # Prevent closing

    # --- Note Downloader Tab Method ---
    def open_note_downloader_tab(self):
        # Check if tab already exists
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == "笔记下载":
                self.tab_widget.setCurrentIndex(i)
                return

        # Calculate project root relative to this file's location
        # main_window.py is in src/ui/, so go up three levels to project root
        project_root = Path(__file__).resolve().parent.parent.parent / "note_downloader"

        # Check if the directory exists
        if not project_root.is_dir():
            QMessageBox.critical(self, "错误", f"Note Downloader 目录未找到:\n{project_root}")
            self.statusBar.showMessage("错误：Note Downloader 目录未找到")
            return # Corrected indentation

        widget = NoteDownloaderWidget(str(project_root), self) # Corrected indentation
        index = self.tab_widget.addTab(widget, "笔记下载")      # Corrected indentation
        self.tab_widget.setCurrentWidget(widget)             # Corrected indentation
        self.statusBar.showMessage("已打开笔记下载器")           # Corrected indentation
        self._collapse_global_browser()   # Immediately collapse global browser (Corrected indentation)


# Notes for further refactoring (optional):
# - Consider moving Action/Menu/Toolbar creation into separate methods or classes.
# - File operations (new, open, save, save_as) could potentially move to a dedicated service class (e.g., FileService).
# - Error handling could be centralized or improved.
# - Signal connections could be managed more systematically.
# QDateTime import moved near other QtCore imports
