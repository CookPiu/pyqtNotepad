import sys
import os
from PyQt6.QtWidgets import (QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QTextEdit, QListWidget, QListWidgetItem, QToolBar, QMenuBar, QMenu,
                             QStatusBar, QFileDialog, QFontDialog, QColorDialog, QMessageBox,
                             QInputDialog, QSplitter, QTabWidget, QToolButton, QDockWidget, QMenu, QSizePolicy)
from PyQt6.QtGui import QAction, QFont, QColor, QTextCursor, QIcon, QImage, QTextDocument, QPainter
from PyQt6.QtCore import Qt, QSize, QUrl, QRect, QEvent, pyqtSignal, QPointF, QFile, QTextStream, QPoint, QSignalBlocker, QDateTime
from PyQt6.QtWebEngineWidgets import QWebEngineView
import fitz  # PyMuPDF库

# 导入组件和工具
from src.utils.theme_manager import ThemeManager
from src.ui.file_explorer import FileExplorer
from src.ui.editor import TextEditWithLineNumbers
from src.ui.html_editor import HtmlEditor
from src.ui.combined_tools_widget import CombinedToolsWidget
from pathlib import Path
from .note_downloader_widget import NoteDownloaderWidget

# 导入重构后的组件模块
from src.ui.components.ui_initializer import UIInitializer
from src.ui.components.file_operations import FileOperations
from src.ui.components.edit_operations import EditOperations
from src.ui.components.view_operations import ViewOperations
from src.ui.components.ui_manager import UIManager


class MainWindow(QMainWindow):
    current_editor_changed = pyqtSignal(QTextEdit)  # 保持QTextEdit以获得更广泛的兼容性

    def __init__(self):
        print("▶ MainWindow.__init__")
        super().__init__()
        
        # 初始化主题管理器
        self.theme_manager = ThemeManager()
        
        # 初始化状态变量
        self.untitled_counter = 0
        self.previous_editor = None
        self.sidebar_original_width = 250  # 默认宽度，类似VS Code
        self.tool_docks = {}  # 存储工具dock窗口的引用
        self._pre_zen_sizes = None  # 用于保存Zen模式前的分割器大小
        self._saved_sidebar_width = self.sidebar_original_width  # 用于切换侧边栏
        
        # 允许Dock自动分页和动画
        self.setDockOptions(
            QMainWindow.DockOption.AllowTabbedDocks
            | QMainWindow.DockOption.AnimatedDocks
        )
        
        # 初始化组件模块
        self.file_explorer = FileExplorer()
        self.file_explorer.file_double_clicked.connect(self.open_file_from_path)
        
        # 初始化操作模块
        self.ui_initializer = UIInitializer(self)
        self.file_operations = FileOperations(self)
        self.edit_operations = EditOperations(self)
        self.view_operations = ViewOperations(self)
        self.ui_manager = UIManager(self)
        
        # 先创建操作，确保在setup_ui之前创建所有必要的操作对象
        self.create_actions()
        
        # 初始化UI
        self.ui_initializer.setup_ui()
        self.create_menu_bar()
        self.create_toolbar()
        
        # 应用当前主题
        self.apply_current_theme()
        
        # 如果标签页为空，创建新文件
        if self.tab_widget.count() == 0:
            self.new_file()
    
    # --- 委托给组件模块的方法 ---
    
    # 文件操作
    def new_file(self):
        self.file_operations.new_file()
    
    def open_file_dialog(self):
        self.file_operations.open_file_dialog()
    
    def open_file_from_path(self, file_path):
        self.file_operations.open_file_from_path(file_path)
    
    def save_file(self):
        return self.file_operations.save_file()
    
    def save_file_as(self):
        return self.file_operations.save_file_as()
    
    def close_tab(self, index):
        self.file_operations.close_tab(index)
    
    # 编辑操作
    def undo_action_handler(self):
        self.edit_operations.undo_action_handler()
    
    def redo_action_handler(self):
        self.edit_operations.redo_action_handler()
    
    def cut_action_handler(self):
        self.edit_operations.cut_action_handler()
    
    def copy_action_handler(self):
        self.edit_operations.copy_action_handler()
    
    def paste_action_handler(self):
        self.edit_operations.paste_action_handler()
    
    def select_all_action_handler(self):
        self.edit_operations.select_all_action_handler()
    
    def change_font(self):
        self.edit_operations.change_font()
    
    def change_color(self):
        self.edit_operations.change_color()
    
    def insert_image(self):
        self.edit_operations.insert_image()
    
    def find_text(self):
        self.edit_operations.find_text()
    
    def replace_text(self):
        self.edit_operations.replace_text()
    
    # 视图操作
    def toggle_theme(self):
        self.view_operations.toggle_theme()
    
    def toggle_zen_mode(self, checked):
        self.view_operations.toggle_zen_mode(checked)
    
    def toggle_sidebar(self, show=None):
        self.view_operations.toggle_sidebar(show)
    
    def _collapse_global_browser(self):
        self.view_operations._collapse_global_browser()
    
    def _restore_global_browser(self):
        self.view_operations._restore_global_browser()
    
    def show_about(self):
        self.view_operations.show_about()
    
    # UI管理
    def apply_current_theme(self):
        self.ui_manager.apply_current_theme()
    
    def open_note_downloader_tab(self):
        self.ui_manager.open_note_downloader_tab()
    
    def open_pdf_preview(self, pdf_path):
        self.ui_manager.open_pdf_preview(pdf_path)
    
    def sidebar_item_clicked(self, item):
        self.ui_manager.sidebar_item_clicked(item)
    
    def convert_pdf_to_html(self, pdf_path):
        self.ui_manager.convert_pdf_to_html(pdf_path)
    
    # --- 保留在MainWindow中的核心方法 ---
    
    def create_actions(self):
        # 添加工具提示到所有操作
        self.new_action = QAction("新建文本", self, shortcut="Ctrl+N", toolTip="创建新文本文件 (Ctrl+N)", triggered=self.new_file)
        self.new_html_action = QAction("新建HTML", self, shortcut="Ctrl+Shift+N", toolTip="创建新HTML文件 (Ctrl+Shift+N)", triggered=lambda: self.file_operations.new_file("html"))
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
        file_menu.addActions([self.new_action, self.new_html_action, self.open_action, self.save_action, self.save_as_action])
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
        edit_menu.addActions([self.find_action, self.replace_action])

        format_menu = menu_bar.addMenu("格式")
        format_menu.addActions([self.font_action, self.color_action])
        format_menu.addSeparator()
        format_menu.addAction(self.insert_image_action)
        format_menu.addSeparator()
        format_menu.addAction(self.toggle_theme_action)

        view_menu = menu_bar.addMenu("视图")
        view_menu.addAction(self.zen_action)

        help_menu = menu_bar.addMenu("帮助")
        help_menu.addAction(self.about_action)

        # 默认隐藏菜单栏
        menu_bar.setVisible(False)
    
    def create_toolbar(self):
        # 保留高频操作
        self.toolbar.setMovable(False)          # 防止拖动成多行
        self.toolbar.setIconSize(QSize(20, 20)) # 设置图标大小

        # --- 主要操作按钮 ---
        self.toolbar.addActions([self.new_action, self.new_html_action, self.open_action, self.save_action])
        self.toolbar.addSeparator()
        self.toolbar.addActions([self.undo_action, self.redo_action])
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.find_action)

        # --- 添加空白区域将菜单按钮推到右侧 ---
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.toolbar.addWidget(spacer)

        # --- 菜单下拉按钮 ---
        menu_btn = QToolButton()
        menu_btn.setText("...") # 备用文本
        menu_btn.setToolTip("更多选项")

        menu_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup) # 点击时立即显示菜单
        more_menu = QMenu(menu_btn)

        # 添加之前在菜单栏中的操作
        file_submenu = more_menu.addMenu("文件") # 文件操作分组
        file_submenu.addActions([self.save_as_action, self.close_tab_action])
        file_submenu.addSeparator()
        file_submenu.addAction(self.exit_action)

        edit_submenu = more_menu.addMenu("编辑") # 编辑操作分组
        edit_submenu.addActions([self.cut_action, self.copy_action,
                                 self.paste_action, self.select_all_action])
        edit_submenu.addSeparator()
        edit_submenu.addAction(self.replace_action)

        format_submenu = more_menu.addMenu("格式") # 格式操作分组
        format_submenu.addActions([self.font_action, self.color_action,
                                   self.insert_image_action])

        view_submenu = more_menu.addMenu("视图") # 视图操作分组
        view_submenu.addAction(self.toggle_theme_action)
        view_submenu.addSeparator()
        view_submenu.addAction(self.zen_action)

        help_submenu = more_menu.addMenu("帮助") # 帮助操作分组
        help_submenu.addAction(self.about_action)

        menu_btn.setMenu(more_menu)
        self.toolbar.addWidget(menu_btn)

        # 添加Zen模式全局快捷键
        self.addAction(self.zen_action)
    
    def get_current_editor(self):
        # 确保返回正确的类型或None
        widget = self.tab_widget.currentWidget()
        # 明确检查是否为TextEditWithLineNumbers或HtmlEditor类型
        if isinstance(widget, (TextEditWithLineNumbers, HtmlEditor)):
            return widget
        return None
    
    def on_current_tab_changed(self, index):
        editor = self.get_current_editor()
        self.update_edit_actions_state(editor)
        self.update_window_title()
        # 确保信号发出正确的类型或None
        self.current_editor_changed.emit(editor if editor else None)

        # 根据标签类型折叠/展开全局浏览器
        w = self.tab_widget.widget(index)
        if isinstance(w, NoteDownloaderWidget):
            self._collapse_global_browser()
        else:
            # 仅当浏览器实际折叠时恢复
            if len(self.editor_browser_splitter.sizes()) == 2 and self.editor_browser_splitter.sizes()[1] == 0:
                self._restore_global_browser()
    
    def _update_copy_cut_state(self, available: bool):
        # 辅助函数保持不变
        self.copy_action.setEnabled(available)
        self.cut_action.setEnabled(available)
    
    def update_edit_actions_state(self, editor):
        # 确保操作正确启用/禁用
        has_editor = isinstance(editor, (TextEditWithLineNumbers, HtmlEditor))
        # 安全获取剪贴板数据
        try:
            can_paste = QApplication.clipboard().text() != "" if has_editor else False
        except Exception:
            can_paste = False # 处理剪贴板访问可能失败的情况

        # 安全断开先前的信号连接
        if self.previous_editor:
            try: self.previous_editor.document().undoAvailable.disconnect(self.undo_action.setEnabled)
            except TypeError: pass
            try: self.previous_editor.document().redoAvailable.disconnect(self.redo_action.setEnabled)
            except TypeError: pass
            
            # 处理不同编辑器类型的copyAvailable信号
            if hasattr(self.previous_editor, 'copyAvailable') and callable(self.previous_editor.copyAvailable):
                # HtmlEditor类型
                try: self.previous_editor.copyAvailable().disconnect(self._update_copy_cut_state)
                except TypeError: pass
            else:
                # TextEditWithLineNumbers类型
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

        # 安全连接当前编辑器的信号
        if has_editor:
            try: editor.document().undoAvailable.connect(self.undo_action.setEnabled)
            except TypeError: pass
            try: editor.document().redoAvailable.connect(self.redo_action.setEnabled)
            except TypeError: pass
            
            # 处理不同编辑器类型的copyAvailable信号
            if hasattr(editor, 'copyAvailable') and callable(editor.copyAvailable):
                # HtmlEditor类型
                try: editor.copyAvailable().connect(self._update_copy_cut_state)
                except TypeError: pass
            else:
                # TextEditWithLineNumbers类型
                try: editor.copyAvailable.connect(self._update_copy_cut_state)
                except TypeError: pass
                
            try: editor.document().modificationChanged.connect(self.update_tab_title)
            except TypeError: pass
            self.previous_editor = editor
        else:
            self.previous_editor = None
    
    def update_window_title(self):
        editor = self.get_current_editor()
        title_prefix = "多功能记事本"
        if editor and (index := self.tab_widget.currentIndex()) != -1:
            tab_text = self.tab_widget.tabText(index)
            if tab_text: # 检查tab_text是否非空
                # 仅当存在时才去除末尾的'*'
                base_tab_text = tab_text[:-1].strip() if tab_text.endswith("*") else tab_text
                title_prefix = f"{base_tab_text} - {title_prefix}"
        self.setWindowTitle(title_prefix)
    
    def update_tab_title(self, modified: bool):
        index = self.tab_widget.currentIndex()
        if index == -1: return
        editor = self.tab_widget.widget(index)
        if not isinstance(editor, TextEditWithLineNumbers): return

        file_path = editor.property("file_path")
        # 如果file_path为None，则使用untitled_name，否则使用基本名称
        tab_name_base = os.path.basename(file_path) if file_path else (editor.property("untitled_name") or f"未命名-{self.untitled_counter}")

        new_tab_text = f"{tab_name_base}{'*' if modified else ''}"
        self.tab_widget.setTabText(index, new_tab_text)
        self.update_window_title() # 同时更新窗口标题


# 应用程序入口点
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
