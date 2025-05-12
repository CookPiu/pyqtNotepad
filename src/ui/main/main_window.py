# src/ui/main/main_window.py
import sys
import os
from PyQt6.QtWidgets import (QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QTextEdit, QListWidget, QListWidgetItem, QToolBar, QMenuBar, QMenu,
                             QStatusBar, QFileDialog, QFontDialog, QColorDialog, QMessageBox,
                              QInputDialog, QSplitter, QTabWidget, QToolButton, QDockWidget, QMenu, QSizePolicy)
from PyQt6.QtGui import QAction, QFont, QColor, QTextCursor, QIcon, QImage, QTextDocument, QPainter, QKeyEvent, QDragEnterEvent, QDropEvent # Added QDragEnterEvent, QDropEvent
from PyQt6.QtCore import Qt, QSize, QUrl, QRect, QEvent, pyqtSignal, QPointF, QFile, QTextStream, QPoint, QSignalBlocker, QDateTime, QTimer, QStandardPaths
from PyQt6.QtWebEngineWidgets import QWebEngineView # Added
from PyQt6.QtWebEngineCore import QWebEnginePage # Added

from ..core.base_widget import BaseWidget
from .ui_initializer import UIInitializer
from ..components.file_operations import FileOperations
from ..components.edit_operations import EditOperations
from ..components.view_operations import ViewOperations
from ..components.ui_manager import UIManager
from ..docks.optimized_ai_chat_dock import OptimizedAIChatDock  # 导入优化的AI聊天组件
from ...services.network_service import NetworkService # Added for fetching URL source
# PDF转换服务现在直接在open_pdf_conversion_dialog方法中导入

# from ..atomic.editor.html_editor import HtmlEditor # No longer primary HTML editor
from ..atomic.editor.wang_editor import WangEditor # Import WangEditor
from ..atomic.markdown_editor_widget import MarkdownEditorWidget
from ..atomic.editor.text_editor import TextEditor, _InternalTextEdit
# EditableHtmlPreviewWidget is now inside HtmlViewContainer, but still needed for isinstance checks
from ..views.editable_html_preview_widget import EditableHtmlPreviewWidget 
from ..composite.html_view_container import HtmlViewContainer # Added
# PaginatedViewWidget is no longer used.
# from ..composite.paginated_view_widget import PaginatedViewWidget
# from ..composite.editor_group_widget import EditorGroupWidget # Used by RootEditorAreaWidget
from ..core.dockable_tab_widget import DockableTabWidget # Used by RootEditorAreaWidget
from ..composite.root_editor_area_widget import RootEditorAreaWidget # Added


class MainWindow(QMainWindow):
    current_editor_changed = pyqtSignal(object) 
    theme_changed = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        # print("▶ MainWindow.__init__ (Refactored)") # Keep for debug if needed

        self.ui_manager = UIManager(self)
        
        self.current_workspace_path = None 
        
        self.tab_widget: DockableTabWidget | None = None 
        self.root_editor_area: RootEditorAreaWidget | None = None

        self.file_operations = FileOperations(self, self.ui_manager, None) 
        self.edit_operations = EditOperations(self, self.ui_manager)
        self.view_operations = ViewOperations(self, self.ui_manager)
        self.network_service = NetworkService(self) # Instantiate NetworkService

        self.base_font_size_pt = 10.0
        self.current_zoom_factor = 1.0
        self.zoom_step = 0.1
        self.min_zoom_factor = 0.5
        self.max_zoom_factor = 3.0
        
        self.ui_initializer = UIInitializer(self, self.ui_manager)
        self.previous_editor = None 
        self.setDockOptions(QMainWindow.DockOption.AllowTabbedDocks | QMainWindow.DockOption.AnimatedDocks)
        
        self.create_actions() # Actions must be created before UI setup if UI uses them
        self.ui_initializer.setup_ui() 
        
        # Connect NetworkService signals
        self.network_service.html_fetched.connect(self._handle_html_fetched)
        self.network_service.fetch_error.connect(self._handle_fetch_error)
        
        if hasattr(self, 'file_explorer') and self.file_explorer:
            self.file_explorer.root_path_changed.connect(self.on_workspace_changed)
            self.file_explorer.file_double_clicked.connect(self.handle_file_explorer_double_click)
            
            initial_fe_path = self.file_explorer.get_root_path()
            if initial_fe_path and os.path.isdir(initial_fe_path):
                self.on_workspace_changed(initial_fe_path) 
            else:
                print(f"MainWindow: FileExplorer initial path ('{initial_fe_path}') is not a valid directory.")
        else:
            print("MainWindow: ERROR - self.file_explorer not initialized by UIInitializer, cannot set initial workspace from it.")

        self.create_menu_bar()
        self.create_toolbar() 
        
        # 创建并添加AI聊天侧边栏
        self.ai_chat_dock = OptimizedAIChatDock(self)
        self.ai_chat_dock.setObjectName("AIChatDock")
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.ai_chat_dock)
        # 初始隐藏AI聊天侧边栏
        self.ai_chat_dock.hide()
        
        self.ui_manager.apply_current_theme()

        if self.tab_widget is not None:
             self.tab_widget.tabCloseRequested.connect(self.file_operations.close_tab)
             self.tab_widget.currentChanged.connect(self.on_current_tab_changed)
             self.on_current_tab_changed(self.tab_widget.currentIndex()) 
             if self.tab_widget.count() == 0:
                 if self.current_workspace_path and os.path.isdir(self.current_workspace_path): 
                    if hasattr(self, 'file_operations'):
                        self.file_operations.new_file(workspace_path=self.current_workspace_path)
        else:
             print("错误：MainWindow 未能创建 tab_widget。")
        
        if QApplication.clipboard() is not None:
            QApplication.clipboard().dataChanged.connect(
                lambda: self.update_edit_actions_state(self.get_current_editor_widget())
            )
        self.update_window_title()
        self.setAcceptDrops(True)

    def create_actions(self):
        self.new_action = QAction("新建文本", self, shortcut="Ctrl+N", toolTip="创建新文本文件", triggered=self.new_file_wrapper)
        self.new_html_action = QAction("新建HTML", self, shortcut="Ctrl+Shift+N", toolTip="创建新HTML文件", triggered=self.new_html_file_wrapper)
        self.new_markdown_action = QAction("新建Markdown", self, shortcut="Ctrl+Alt+N", toolTip="创建新Markdown文件", triggered=self.new_markdown_file_wrapper)
        
        self.open_action = QAction("打开文件...", self, shortcut="Ctrl+O", toolTip="打开文件", triggered=self.open_file_dialog_wrapper)
        self.open_folder_action = QAction("打开文件夹...", self, shortcut="Ctrl+K Ctrl+O", toolTip="打开文件夹作为工作区", triggered=self.open_folder_wrapper)
        
        self.save_action = QAction("保存", self, shortcut="Ctrl+S", toolTip="保存文件", triggered=self.save_file_wrapper, enabled=False)
        self.save_as_action = QAction("另存为...", self, shortcut="Ctrl+Shift+S", toolTip="另存为", triggered=self.save_file_as_wrapper, enabled=False)
        self.close_tab_action = QAction("关闭标签页", self, shortcut="Ctrl+W", toolTip="关闭标签页", triggered=self.close_current_tab_wrapper, enabled=False)
        self.exit_action = QAction("退出", self, shortcut="Ctrl+Q", toolTip="退出", triggered=self.close)

        self.undo_action = QAction("撤销", self, shortcut="Ctrl+Z", toolTip="撤销", triggered=self.undo_action_wrapper, enabled=False)
        self.redo_action = QAction("重做", self, shortcut="Ctrl+Y", toolTip="重做", triggered=self.redo_action_wrapper, enabled=False)
        self.cut_action = QAction("剪切", self, shortcut="Ctrl+X", toolTip="剪切", triggered=self.cut_action_wrapper, enabled=False)
        self.copy_action = QAction("复制", self, shortcut="Ctrl+C", toolTip="复制", triggered=self.copy_action_wrapper, enabled=False)
        self.paste_action = QAction("粘贴", self, shortcut="Ctrl+V", toolTip="粘贴", triggered=self.paste_action_wrapper, enabled=True)
        self.select_all_action = QAction("全选", self, shortcut="Ctrl+A", toolTip="全选", triggered=self.select_all_action_wrapper, enabled=False)

        self.font_action = QAction("字体...", self, toolTip="字体", triggered=self.change_font_wrapper, enabled=False)
        self.color_action = QAction("颜色...", self, toolTip="颜色", triggered=self.change_color_wrapper, enabled=False)
        self.insert_image_action = QAction("插入图片...", self, toolTip="插入图片", triggered=self.insert_image_wrapper, enabled=False)
        self.find_action = QAction("查找", self, shortcut="Ctrl+F", toolTip="查找", triggered=self.find_text_wrapper, enabled=False)
        self.replace_action = QAction("替换", self, shortcut="Ctrl+H", toolTip="替换", triggered=self.replace_text_wrapper, enabled=False)
        
        self.translate_action = QAction("翻译...", self, shortcut="Ctrl+Shift+T", toolTip="翻译", triggered=self.open_translation_dialog_wrapper, enabled=True)
        self.translate_selection_action = QAction("翻译选中内容", self, toolTip="翻译选中内容", triggered=self.translate_selection_wrapper, enabled=False)
        
        # New actions for context menu
        self.calculate_selection_action = QAction("计算选中内容", self, toolTip="计算选中的数学表达式", triggered=self.calculate_selection_wrapper, enabled=False)
        self.copy_to_ai_action = QAction("将选中内容复制到 AI 助手", self, toolTip="将选中文本发送到AI助手输入框", triggered=self.copy_to_ai_wrapper, enabled=False)

        # PDF转HTML功能
        self.pdf_to_html_action = QAction("PDF转HTML...", self, toolTip="将PDF转换为HTML", triggered=self.open_pdf_conversion_dialog)

        # Export action
        self.export_action = QAction("导出...", self, shortcut="Ctrl+E", toolTip="导出当前文件为不同格式", triggered=self.export_file_wrapper, enabled=False)

        # Fetch URL source action
        self.fetch_url_source_action = QAction("打开并抓取源码(Web视图)", self, toolTip="抓取选中URL的源码并在新标签页显示", triggered=self.fetch_url_source_wrapper, enabled=False)

        self.toggle_theme_action = QAction("切换主题", self, shortcut="Ctrl+T", toolTip="切换主题", triggered=self.toggle_theme_wrapper)
        self.zen_action = QAction("Zen Mode", self, checkable=True, shortcut="F11", triggered=self.toggle_zen_mode_wrapper, toolTip="Zen模式")

        self.zoom_in_action = QAction("放大", self, shortcut="Ctrl++", toolTip="放大", triggered=self.zoom_in)
        self.zoom_out_action = QAction("缩小", self, shortcut="Ctrl+-", toolTip="缩小", triggered=self.zoom_out)
        self.reset_zoom_action = QAction("重置缩放", self, shortcut="Ctrl+0", toolTip="重置缩放", triggered=self.reset_zoom)

        self.toggle_markdown_preview_action = QAction("MD 预览↔源码", self, checkable=True, shortcut="Ctrl+Shift+M", toolTip="切换Markdown预览/源码", triggered=self.toggle_markdown_preview_panel_wrapper, enabled=False)
        
        # New action for HTML source/preview toggle using HtmlViewContainer
        self.toggle_html_view_action = QAction("切换HTML视图", self, shortcut="Ctrl+Shift+H", toolTip="切换HTML源码/预览视图", triggered=self.handle_toggle_html_view, enabled=False)
        
        # Action for toggling visual edit mode - REMOVED as preview is now always editable (though changes may not save via QWebChannel)
        # self.toggle_html_visual_edit_action = QAction("HTML可视化编辑", self, checkable=True, toolTip="切换HTML可视化编辑模式", triggered=self.handle_toggle_html_visual_edit, enabled=False)

        # Old HTML actions (to be reviewed/removed or repurposed if WangEditor still needs its own toggle)
        # self.toggle_html_preview_action = QAction("HTML 预览↔源码 (Wang)", self, checkable=True, toolTip="切换HTML预览/源码 (WangEditor:源码/富文本)", triggered=self.toggle_html_preview_panel_wrapper, enabled=False) # For WangEditor
        # self.view_html_source_action = QAction("查看HTML源码 (Old)", self, toolTip="查看当前预览HTML的源码 (Old)", triggered=self.view_html_source_wrapper, enabled=False) 

        # 创建AI聊天菜单项
        self.toggle_ai_chat_action = QAction("AI对话助手", self, checkable=True, triggered=self.toggle_ai_chat_dock)
        self.set_ai_api_key_action = QAction("设置AI API密钥", self, triggered=self.set_ai_api_key_wrapper)
        self.clear_ai_conversation_action = QAction("清空AI对话", self, triggered=self.clear_ai_conversation_wrapper)

        self.about_action = QAction("关于", self, toolTip="关于", triggered=self.show_about_wrapper)

    def set_ai_api_key_wrapper(self):
        if hasattr(self, 'ai_chat_dock') and self.ai_chat_dock:
            self.ai_chat_dock.set_api_key()

    def clear_ai_conversation_wrapper(self):
        if hasattr(self, 'ai_chat_dock') and self.ai_chat_dock:
            self.ai_chat_dock.clear_conversation()

    def create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("文件")
        file_menu.addActions([self.new_action, self.new_html_action, self.new_markdown_action, self.open_action, self.open_folder_action, self.save_action, self.save_as_action, self.export_action, self.close_tab_action, self.exit_action])
        
        edit_menu = menu_bar.addMenu("编辑")
        # Add new actions to edit menu if desired, or they can remain context-menu only
        edit_menu.addActions([self.undo_action, self.redo_action, self.cut_action, self.copy_action, self.paste_action, self.select_all_action, self.find_action, self.replace_action, self.translate_action, self.translate_selection_action, self.calculate_selection_action, self.copy_to_ai_action, self.fetch_url_source_action])

        format_menu = menu_bar.addMenu("格式")
        format_menu.addActions([self.font_action, self.color_action, self.insert_image_action, self.toggle_theme_action, self.pdf_to_html_action])
        
        view_menu = menu_bar.addMenu("视图")
        # Add new HTML actions, remove/comment out old ones
        view_menu.addActions([self.zen_action, self.toggle_markdown_preview_action, 
                              self.toggle_html_view_action, # Visual edit action (self.toggle_html_visual_edit_action) removed
                              # self.toggle_html_preview_action, self.toggle_html_edit_mode_action, self.view_html_source_action, # Old HTML actions
                              self.zoom_in_action, self.zoom_out_action, self.reset_zoom_action])
        
        ai_assistant_menu = menu_bar.addMenu("AI助手")
        ai_assistant_menu.addAction(self.toggle_ai_chat_action)
        ai_assistant_menu.addAction(self.set_ai_api_key_action)
        ai_assistant_menu.addAction(self.clear_ai_conversation_action)
        
        help_menu = menu_bar.addMenu("帮助")
        help_menu.addAction(self.about_action)
        menu_bar.setVisible(False)

    def create_toolbar(self):
        if not hasattr(self, 'toolbar') or self.toolbar is None:
             self.toolbar = self.addToolBar("MainToolBar")
        else:
             self.toolbar.clear()

        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(20, 20))
        
        # ===== 文件类别 =====
        file_btn = QToolButton(self)
        file_btn.setText("文件")
        file_btn.setToolTip("文件操作")
        file_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        file_menu = QMenu(file_btn)
        file_menu.addAction(self.new_action)
        file_menu.addAction(self.new_html_action)
        file_menu.addAction(self.new_markdown_action)
        file_menu.addSeparator()
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.open_folder_action)
        file_menu.addSeparator()
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_as_action)
        file_menu.addAction(self.export_action) # Add export to toolbar file menu
        file_menu.addSeparator()
        file_menu.addAction(self.close_tab_action)
        file_menu.addAction(self.exit_action)
        file_btn.setMenu(file_menu)
        self.toolbar.addWidget(file_btn)
        
        # ===== 编辑类别 =====
        edit_btn = QToolButton(self)
        edit_btn.setText("编辑")
        edit_btn.setToolTip("编辑操作")
        edit_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        edit_menu = QMenu(edit_btn)
        edit_menu.addAction(self.undo_action)
        edit_menu.addAction(self.redo_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.cut_action)
        edit_menu.addAction(self.copy_action)
        edit_menu.addAction(self.paste_action)
        edit_menu.addAction(self.select_all_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.find_action)
        edit_menu.addAction(self.replace_action)
        edit_btn.setMenu(edit_menu)
        self.toolbar.addWidget(edit_btn)
        
        # ===== 格式类别 =====
        format_btn = QToolButton(self)
        format_btn.setText("格式")
        format_btn.setToolTip("格式操作")
        format_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        format_menu = QMenu(format_btn)
        format_menu.addAction(self.font_action)
        format_menu.addAction(self.color_action)
        format_menu.addAction(self.insert_image_action)
        format_menu.addSeparator()
        format_menu.addAction(self.pdf_to_html_action)
        format_btn.setMenu(format_menu)
        self.toolbar.addWidget(format_btn)
        
        # ===== 翻译类别 =====
        translate_btn = QToolButton(self)
        translate_btn.setText("翻译")
        translate_btn.setToolTip("翻译功能")
        translate_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        translate_menu = QMenu(translate_btn)
        translate_menu.addAction(self.translate_action)
        translate_menu.addAction(self.translate_selection_action)
        translate_btn.setMenu(translate_menu)
        self.toolbar.addWidget(translate_btn)
        
        # ===== 视图类别 =====
        view_btn = QToolButton(self)
        view_btn.setText("视图")
        view_btn.setToolTip("视图操作")
        view_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        view_menu = QMenu(view_btn)
        view_menu.addAction(self.toggle_markdown_preview_action)
        view_menu.addAction(self.toggle_html_view_action)
        view_menu.addSeparator()
        view_menu.addAction(self.zoom_in_action)
        view_menu.addAction(self.zoom_out_action)
        view_menu.addAction(self.reset_zoom_action)
        view_menu.addSeparator()
        view_menu.addAction(self.toggle_theme_action)
        view_menu.addAction(self.zen_action)
        view_btn.setMenu(view_menu)
        self.toolbar.addWidget(view_btn)
        
        # ===== 帮助类别 =====
        help_btn = QToolButton(self)
        help_btn.setText("帮助")
        help_btn.setToolTip("帮助选项")
        help_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        help_menu = QMenu(help_btn)
        help_menu.addAction(self.toggle_ai_chat_action)
        help_menu.addAction(self.about_action)
        help_btn.setMenu(help_menu)
        self.toolbar.addWidget(help_btn)
        
        # 添加弹性空间
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.toolbar.addWidget(spacer)
        
        # 添加常用操作的快捷按钮
        self.toolbar.addAction(self.new_action)
        self.toolbar.addAction(self.open_action)
        self.toolbar.addAction(self.save_action)
        
        # 添加翻译工具和AI对话工具按钮
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.translate_action)
        self.toolbar.addAction(self.toggle_ai_chat_action)
        
        self.addAction(self.zen_action)

    def new_file_wrapper(self):
        if not self.current_workspace_path and hasattr(self, 'file_explorer') and self.file_explorer:
            QMessageBox.information(self, "选择工作区", "请首先选择一个工作区来创建新文件。")
            self.file_explorer.browse_for_folder(); return
        self.file_operations.new_file(workspace_path=self.current_workspace_path)

    def new_html_file_wrapper(self):
        if not self.current_workspace_path and hasattr(self, 'file_explorer') and self.file_explorer:
            QMessageBox.information(self, "选择工作区", "请首先选择一个工作区来创建新HTML文件。"); self.file_explorer.browse_for_folder(); return
        self.file_operations.new_file(file_type="html", workspace_path=self.current_workspace_path)

    def new_markdown_file_wrapper(self):
        if not self.current_workspace_path and hasattr(self, 'file_explorer') and self.file_explorer:
            QMessageBox.information(self, "选择工作区", "当前未指定有效工作区。请选择一个工作区来创建新Markdown文件。"); self.open_folder_wrapper(); return
        self.file_operations.new_file(file_type="markdown", workspace_path=self.current_workspace_path)

    def open_file_dialog_wrapper(self): 
        default_open_dir = self.current_workspace_path or QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation) or os.path.expanduser("~")
        filters = ";;".join([
            "所有支持的文件 (*.txt *.md *.markdown *.html *.pdf *.docx *.xlsx *.pptx *.png *.jpg *.jpeg *.gif *.bmp *.webp *.mp4 *.avi *.mkv *.mov *.webm)",
            "图片文件 (*.png *.jpg *.jpeg *.gif *.bmp *.webp)", "视频文件 (*.mp4 *.avi *.mkv *.mov *.webm)",
            "Office 文件 (*.docx *.xlsx *.pptx)", "HTML 文件 (*.html)", "Markdown 文件 (*.md *.markdown)",
            "文本文件 (*.txt)", "PDF 文件 (*.pdf)", "所有文件 (*)"
        ])
        file_name, _ = QFileDialog.getOpenFileName(self, "打开文件", default_open_dir, filters)
        if file_name: self.file_operations.open_file_from_path(file_name)

    def open_folder_wrapper(self):
        if hasattr(self, 'file_explorer') and self.file_explorer: self.file_explorer.browse_for_folder()

    def save_file_wrapper(self): self.file_operations.save_file()
    def save_file_as_wrapper(self): self.file_operations.save_file_as()
    def close_current_tab_wrapper(self):
        if self.ui_manager.tab_widget: self.file_operations.close_tab(self.ui_manager.tab_widget.currentIndex())
    
    def undo_action_wrapper(self): self.edit_operations.undo_action_handler()
    def redo_action_wrapper(self): self.edit_operations.redo_action_handler()
    def cut_action_wrapper(self): self.edit_operations.cut_action_handler()
    def copy_action_wrapper(self): self.edit_operations.copy_action_handler()
    def paste_action_wrapper(self): self.edit_operations.paste()
    def select_all_action_wrapper(self): self.edit_operations.select_all_action_handler()
    def change_font_wrapper(self): self.edit_operations.change_font()
    def change_color_wrapper(self): self.edit_operations.change_color()
    def insert_image_wrapper(self): self.edit_operations.insert_image()
    def find_text_wrapper(self): self.edit_operations.find_text()
    def replace_text_wrapper(self): self.edit_operations.replace_text()
    def toggle_theme_wrapper(self): self.view_operations.toggle_theme()
    def toggle_zen_mode_wrapper(self, checked): self.view_operations.toggle_zen_mode(checked)
    
    def toggle_ai_chat_dock(self, checked=None):
        """切换AI聊天侧边栏的显示状态"""
        if checked is None:
            checked = not self.ai_chat_dock.isVisible()
        self.ai_chat_dock.setVisible(checked)
        self.toggle_ai_chat_action.setChecked(checked)
    def show_about_wrapper(self):
        self.ui_manager.show_about_dialog()
    
    def open_pdf_conversion_dialog(self):
        """打开PDF转HTML转换对话框，使用现有的PDF转换服务"""
        from ...services.pdf_conversion_service import PDFConversionService
        
        # 选择PDF文件
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择PDF文件", "", "PDF文件 (*.pdf)"
        )
        
        if not file_path:
            return
        
        # 选择输出目录
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择输出目录", "", QFileDialog.Option.ShowDirsOnly
        )
        
        if not dir_path:
            return
        
        # 设置输出HTML文件路径
        html_filename = os.path.basename(file_path).replace(".pdf", ".html")
        output_html_path = os.path.join(dir_path, html_filename)
        
        # 确认是否使用管理员权限
        use_admin = QMessageBox.question(
            self,
            "PDF转HTML",
            "是否使用管理员权限执行转换？\n(可能需要UAC确认)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        ) == QMessageBox.StandardButton.Yes
        
        # 显示进度对话框
        progress_dialog = QMessageBox(self)
        progress_dialog.setWindowTitle("PDF转HTML")
        progress_dialog.setText("正在转换PDF文件，请稍候...")
        progress_dialog.setStandardButtons(QMessageBox.StandardButton.NoButton)
        progress_dialog.show()
        QApplication.processEvents()
        
        try:
            # 执行转换
            service = PDFConversionService()
            result = service.convert_pdf_to_html(file_path, output_html_path, use_admin)
            
            # 关闭进度对话框
            progress_dialog.close()
            
            # 显示成功消息
            result_msg = QMessageBox.information(
                self, 
                "转换成功", 
                f"PDF已成功转换为HTML:\n{result}\n\n是否打开输出目录?", 
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if result_msg == QMessageBox.StandardButton.Yes:
                # 打开输出目录
                os.startfile(os.path.dirname(result))
                
        except Exception as e:
            # 关闭进度对话框
            progress_dialog.close()
            
            # 显示错误消息
            QMessageBox.critical(self, "转换失败", f"PDF转换失败:\n{str(e)}")
    def open_translation_dialog_wrapper(self): 
        if hasattr(self, 'edit_operations'): self.edit_operations.open_translation_dialog()
    def translate_selection_wrapper(self):
        if hasattr(self, 'edit_operations'): self.edit_operations.translate_selection()

    def calculate_selection_wrapper(self):
        if hasattr(self.edit_operations, 'calculate_selection_from_current_editor'):
            self.edit_operations.calculate_selection_from_current_editor()

    def copy_to_ai_wrapper(self):
        text = ""
        editor_widget = self.get_current_editor_widget()

        if editor_widget:
            if isinstance(editor_widget, QWebEngineView): # For EditableHtmlPreviewWidget and WangEditor's web_view
                text = editor_widget.selectedText()
            elif hasattr(editor_widget, 'textCursor'): # For QPlainTextEdit, _InternalTextEdit
                cursor = editor_widget.textCursor()
                if cursor.hasSelection():
                    text = cursor.selectedText()
        
        if text.strip():
            self.toggle_ai_chat_dock(True) 
            if hasattr(self.ai_chat_dock, 'chat_widget') and hasattr(self.ai_chat_dock.chat_widget, 'input_text'):
                self.ai_chat_dock.chat_widget.input_text.setPlainText(text)
                self.ai_chat_dock.chat_widget.input_text.setFocus()
            else:
                QMessageBox.warning(self, "错误", "AI助手组件不可用或输入框未找到。")
        else:
            if hasattr(self, 'statusBar') and self.statusBar: 
                self.statusBar.showMessage("请先选择文本后再复制到AI助手", 3000)
                
    def export_file_wrapper(self):
        if hasattr(self.file_operations, 'export_file'):
            self.file_operations.export_file()
        else:
            QMessageBox.warning(self, "错误", "导出功能尚未实现。")

    def fetch_url_source_wrapper(self):
        selected_text = ""
        editor_widget = self.get_current_editor_widget()
        if editor_widget:
            if isinstance(editor_widget, QWebEngineView):
                selected_text = editor_widget.selectedText().strip()
            elif hasattr(editor_widget, 'textCursor'):
                cursor = editor_widget.textCursor()
                if cursor.hasSelection():
                    selected_text = cursor.selectedText().strip()
        
        if selected_text:
            q_url = QUrl(selected_text)
            if q_url.isValid() and q_url.scheme() and q_url.host():
                if hasattr(self, 'statusBar') and self.statusBar:
                    self.statusBar.showMessage(f"正在抓取: {selected_text} ...", 0) 
                self.network_service.fetch_html(selected_text)
            else:
                if hasattr(self, 'statusBar') and self.statusBar:
                    self.statusBar.showMessage("选中的文本不是一个有效的URL。", 3000)
        else:
            if hasattr(self, 'statusBar') and self.statusBar:
                self.statusBar.showMessage("请先选择一个URL。", 3000)

    def _handle_html_fetched(self, url: str, html_content: str):
        if hasattr(self, 'statusBar') and self.statusBar:
            self.statusBar.showMessage(f"成功抓取: {url}", 5000)
        
        # Create a meaningful title for the new tab
        parsed_url = QUrl(url)
        tab_title = parsed_url.host() or os.path.basename(parsed_url.path()) or "抓取的源码"
        if not tab_title: tab_title = "抓取的源码"


        if hasattr(self.file_operations, 'open_html_content_in_new_tab'):
            self.file_operations.open_html_content_in_new_tab(html_content, tab_title, base_url_for_resources=url)
        else:
            QMessageBox.warning(self, "错误", "无法在新标签页中打开抓取的源码。")

    def _handle_fetch_error(self, url: str, error_message: str):
        if hasattr(self, 'statusBar') and self.statusBar:
            self.statusBar.showMessage(f"抓取失败: {url} - {error_message}", 5000)
        QMessageBox.warning(self, "抓取源码失败", f"无法抓取以下URL的源码：\n{url}\n\n错误详情：\n{error_message}")


    def toggle_markdown_preview_panel_wrapper(self, checked):
        current_tab_container = self.tab_widget.currentWidget()
        if isinstance(current_tab_container, MarkdownEditorWidget):
            current_tab_container.set_preview_visible(checked)

    # New handler for HtmlViewContainer's view toggle
    def handle_toggle_html_view(self):
        current_tab_container = self.tab_widget.currentWidget()
        if isinstance(current_tab_container, HtmlViewContainer):
            current_tab_container.switch_view()
            # Update actions based on the new active internal editor
            self.update_edit_actions_state(current_tab_container.get_current_actual_editor())
            # Update visual edit toggle state - this action is now removed
            # is_preview_mode = current_tab_container._current_mode == "preview"
            # self.toggle_html_visual_edit_action.setEnabled(is_preview_mode) 
            # if is_preview_mode:
            #     self.toggle_html_visual_edit_action.setChecked(current_tab_container.preview_widget.isEditingEnabled())
            # else:
            #     self.toggle_html_visual_edit_action.setChecked(False)
        # else:
            # This action should be disabled if not an HtmlViewContainer, handled by on_current_tab_changed

    # New handler for HtmlViewContainer's visual edit toggle - REMOVED
    # def handle_toggle_html_visual_edit(self):
    #     # This logic is no longer needed as the button is removed and preview is default-editable.
    #     pass

    # Old WangEditor toggle - keep if WangEditor is still used for other HTML-like content
    # def toggle_html_preview_panel_wrapper(self, checked=None): 
    #     current_tab_container = self.tab_widget.currentWidget()
    #     if isinstance(current_tab_container, WangEditor):
    #         new_mode = 1 - current_tab_container._current_editor_mode 
    #         current_tab_container.set_edit_mode(new_mode)
    
    # Old EditableHtmlPreviewWidget direct toggle - now handled by HtmlViewContainer
    # def toggle_editable_html_edit_mode_wrapper(self, checked=None):
    #     current_tab_container = self.tab_widget.currentWidget()
    #     if isinstance(current_tab_container, EditableHtmlPreviewWidget): # This would now be HtmlViewContainer
    #         current_tab_container.toggleEditing()
    #         self.toggle_html_edit_mode_action.setChecked(current_tab_container.isEditingEnabled())

    # Old _on_html_editor_mode_changed for WangEditor
    # def _on_html_editor_mode_changed(self, mode): 
    #     current_tab_container = self.tab_widget.currentWidget()
    #     if isinstance(current_tab_container, WangEditor):
    #         is_source_mode = (mode == 0)
    #         # self.toggle_html_preview_action.setChecked(is_source_mode) # Old action
    #     # DO NOT call self.update_edit_actions_state here to prevent recursion.

    # Old view_html_source_wrapper - replaced by same-tab toggle
    # def view_html_source_wrapper(self):
    #     current_tab_container = self.tab_widget.currentWidget()
    #     # This would need to check for HtmlViewContainer and get its preview_widget
    #     if isinstance(current_tab_container, HtmlViewContainer) and current_tab_container._current_mode == "preview":
    #         preview_widget_internal = current_tab_container.preview_widget
    #         def open_source_in_new_tab(html_content_from_preview: str):
    #             if self.tab_widget is None: return
    #
    #             current_index_of_preview = self.tab_widget.indexOf(current_tab_container)
    #             if current_index_of_preview == -1: return # Should not happen
    #
    #             original_tab_name = self.tab_widget.tabText(current_index_of_preview)
    #             # Remove existing asterisk if present before adding (源码)
    #             if original_tab_name.endswith("*"):
    #                 original_tab_name = original_tab_name[:-1].strip()
    #             source_view_tab_name = f"{original_tab_name} (源码)"
    #             
    #             source_editor_container = TextEditor() # This is the QWidget container
    #             source_editor_container.setPlainText(html_content_from_preview)
    #             source_editor_container._editor.setReadOnly(True) # Access internal QPlainTextEdit
    #             
    #             source_editor_container.setProperty("is_source_view", True) 
    #             # Set file_path if the original preview had one, so it's associated
    #             original_file_path = current_tab_container.property("file_path")
    #             if original_file_path:
    #                 source_editor_container.setProperty("file_path", original_file_path + " [源码]") # Mark as source view
    #             else: # For untitled previews
    #                 source_editor_container.setProperty("untitled_name", source_view_tab_name)
    #             source_editor_container.setProperty("is_new", True) # Treat as a new, non-savable tab for simplicity
    #
    #             active_editor_group = self.ui_manager.get_active_editor_group()
    #             target_tab_widget = active_editor_group.get_tab_widget() if active_editor_group else self.tab_widget
    #             
    #             if target_tab_widget:
    #                 index = target_tab_widget.addTab(source_editor_container, source_view_tab_name)
    #                 target_tab_widget.setCurrentIndex(index)
    #                 source_editor_container.setFocus() # Focus the TextEditor container
    #                 
    #                 # Mark the new source view tab as not modified
    #                 # The TextEditor's document is modified if setPlainText is called.
    #                 if hasattr(source_editor_container._editor.document(), 'setModified'):
    #                     source_editor_container._editor.document().setModified(False)
    #                 self.update_tab_title(source_editor_container, False)
    #
    #
    #         # Use the callback version of getHtml to ensure up-to-date content
    #         current_tab_container.getHtml(open_source_in_new_tab)

    def zoom_in(self): self.current_zoom_factor=min(self.max_zoom_factor,self.current_zoom_factor+self.zoom_step); self.ui_manager.apply_current_theme(); self._apply_content_zoom_to_current_editor()
    def zoom_out(self): self.current_zoom_factor=max(self.min_zoom_factor,self.current_zoom_factor-self.zoom_step); self.ui_manager.apply_current_theme(); self._apply_content_zoom_to_current_editor()
    def reset_zoom(self): self.current_zoom_factor=1.0; self.ui_manager.apply_current_theme(); self._apply_content_zoom_to_current_editor()
    def _apply_content_zoom_to_current_editor(self):
        # This method might need to be implemented if zoom affects content size in editors
        pass

    def keyPressEvent(self, event: QKeyEvent):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() in (Qt.Key.Key_Plus, Qt.Key.Key_Equal): self.zoom_in(); event.accept(); return
            if event.key() == Qt.Key.Key_Minus: self.zoom_out(); event.accept(); return
            if event.key() == Qt.Key.Key_0: self.reset_zoom(); event.accept(); return
        super().keyPressEvent(event)

    def get_current_editor_widget(self) -> QWidget | None:
        if not (self.ui_manager and self.ui_manager.tab_widget): return None
        current_tab_container = self.ui_manager.tab_widget.currentWidget()
        if not current_tab_container: return None

        if isinstance(current_tab_container, HtmlViewContainer): # New case
            return current_tab_container.get_current_actual_editor()
        if isinstance(current_tab_container, TextEditor): # Should be rare now as standalone
            return current_tab_container._editor
        if isinstance(current_tab_container, WangEditor):
             return current_tab_container.source_code_editor if current_tab_container._current_editor_mode == 0 else current_tab_container.web_view
        if isinstance(current_tab_container, MarkdownEditorWidget): 
            return current_tab_container.editor
        # EditableHtmlPreviewWidget is now inside HtmlViewContainer
        # if isinstance(current_tab_container, EditableHtmlPreviewWidget): return current_tab_container 
        if isinstance(current_tab_container, _InternalTextEdit): # Should be rare
            return current_tab_container
        
        module_path = current_tab_container.__class__.__module__ if current_tab_container else ""
        if 'image_viewer_view' in module_path or \
           'video_player_view' in module_path or \
           'pdf_viewer_view' in module_path or \
           'office_viewer_view' in module_path:
            return current_tab_container
        return current_tab_container

    def on_editor_content_changed(self, editor_widget_container, initially_modified: bool | None = None):
        if not editor_widget_container: return
        is_modified = True
        if initially_modified is not None: is_modified = initially_modified
        
        editor_widget_container.setProperty("is_modified_custom_flag", is_modified)
        self.update_tab_title(editor_widget_container, modified=is_modified)
        
        if self.tab_widget and self.tab_widget.currentWidget() == editor_widget_container:
            self.save_action.setEnabled(is_modified)

    def on_current_tab_changed(self, index):
        current_editor_component = self.get_current_editor_widget()
        current_tab_container_widget = self.tab_widget.currentWidget() if self.tab_widget else None

        # Disconnect signals from previous editor (if it was HtmlViewContainer, it handles internal signals)
        if self.previous_editor:
            if isinstance(self.previous_editor, MarkdownEditorWidget) and hasattr(self.previous_editor, 'view_mode_changed'):
                try: self.previous_editor.view_mode_changed.disconnect(self.toggle_markdown_preview_action.setChecked)
                except TypeError: pass # Already disconnected or never connected
            # Add similar disconnects for WangEditor if its specific toggle is kept
            # For HtmlViewContainer, its internal signals are managed by itself.
            # If MainWindow connected to HtmlViewContainer.internalModificationChanged, disconnect here.
            if isinstance(self.previous_editor, HtmlViewContainer):
                try: self.previous_editor.internalModificationChanged.disconnect(self.handle_html_container_modification)
                except TypeError: pass


        is_markdown_tab = isinstance(current_tab_container_widget, MarkdownEditorWidget)
        is_html_view_container_tab = isinstance(current_tab_container_widget, HtmlViewContainer)
        is_wang_editor_tab = isinstance(current_tab_container_widget, WangEditor) # 保留WangEditor检查

        # 检查当前标签页是否有修改，更新保存按钮状态
        if current_tab_container_widget:
            is_modified = False
            # 检查是否有isModified方法
            if hasattr(current_tab_container_widget, 'is_modified') and callable(current_tab_container_widget.is_modified):
                is_modified = current_tab_container_widget.is_modified()
            elif hasattr(current_tab_container_widget, 'isModified') and callable(current_tab_container_widget.isModified):
                is_modified = current_tab_container_widget.isModified()
            # 检查是否有document方法，并检查document是否被修改
            elif hasattr(current_tab_container_widget, 'document') and callable(current_tab_container_widget.document):
                doc = current_tab_container_widget.document()
                if doc and hasattr(doc, 'isModified') and callable(doc.isModified):
                    is_modified = doc.isModified()
            
            # 更新保存按钮状态
            self.save_action.setEnabled(is_modified)

        self.toggle_markdown_preview_action.setEnabled(is_markdown_tab)
        if is_markdown_tab:
            # Ensure signal is connected only once or use a robust connection method
            try: current_tab_container_widget.view_mode_changed.disconnect(self.toggle_markdown_preview_action.setChecked)
            except TypeError: pass
            current_tab_container_widget.view_mode_changed.connect(self.toggle_markdown_preview_action.setChecked)
            self.toggle_markdown_preview_action.setChecked(current_tab_container_widget.is_preview_mode)
        
        self.toggle_html_view_action.setEnabled(is_html_view_container_tab)
        # self.toggle_html_visual_edit_action.setEnabled(False) # Visual edit action removed

        if is_html_view_container_tab:
            # Connect to the container's modification signal if needed for overall tab state
            try: current_tab_container_widget.internalModificationChanged.disconnect(self.handle_html_container_modification)
            except TypeError: pass
            current_tab_container_widget.internalModificationChanged.connect(self.handle_html_container_modification)
            
            # Visual edit action is removed, so no need to update its state here
            
            # Initial modified state for the container (delegates to current internal editor)
            self.on_editor_content_changed(current_tab_container_widget, 
                                           initially_modified=current_tab_container_widget.is_modified())
        
        self.previous_editor = current_tab_container_widget # Store the container or other editor
        self.update_edit_actions_state(current_editor_component) # Pass the actual internal editor or container
        self.update_window_title()
        self.current_editor_changed.emit(current_editor_component)
        if current_tab_container_widget:
            self.view_operations.handle_tab_change(current_tab_container_widget)

        if current_editor_component and hasattr(current_editor_component, 'setFocus') and \
           self.ui_manager.is_widget_editor(current_editor_component): 
             current_editor_component.setFocus()
        elif current_tab_container_widget and hasattr(current_tab_container_widget, 'setFocus'):
            module_path = current_tab_container_widget.__class__.__module__
            if 'image_viewer_view' in module_path or 'video_player_view' in module_path:
                 current_tab_container_widget.setFocus()

    def _update_copy_cut_state(self, available: bool):
        self.copy_action.setEnabled(available)
        self.cut_action.setEnabled(available)

    def update_edit_actions_state(self, current_widget: QWidget | None):
        all_editor_actions = [
            self.undo_action, self.redo_action, self.cut_action, self.copy_action,
            self.select_all_action, self.font_action, self.color_action,
            self.insert_image_action, self.find_action, self.replace_action,
            self.translate_selection_action, self.calculate_selection_action, self.copy_to_ai_action, self.fetch_url_source_action # Add new actions
        ]
        
        current_tab_container = self.tab_widget.currentWidget() if self.tab_widget else None
        is_known_editor = self.ui_manager.is_widget_editor(current_widget) # True for TextEdit, Wang's source_code_editor
        
        is_image_view = False; is_video_view = False
        is_html_view_container = isinstance(current_tab_container, HtmlViewContainer)
        is_image_view = False; is_video_view = False

        if current_tab_container and not is_html_view_container: # Check other types if not HtmlViewContainer
            module_path = current_tab_container.__class__.__module__
            if 'image_viewer_view' in module_path: is_image_view = True
            elif 'video_player_view' in module_path: is_video_view = True
        
        is_markdown_tab = isinstance(current_tab_container, MarkdownEditorWidget)
        is_wang_editor_tab = isinstance(current_tab_container, WangEditor) # 保留WangEditor检查

        # 初始化所有编辑操作为禁用状态
        for action in all_editor_actions: action.setEnabled(False)
        self.save_action.setEnabled(False)
        self.save_as_action.setEnabled(False)
        self.export_action.setEnabled(False) # Initialize export action
        self.paste_action.setEnabled(False)
        self.close_tab_action.setEnabled(self.tab_widget.count() > 0 if self.tab_widget else False)
        
        if not current_tab_container:
            return # No tab open, all relevant actions remain disabled

        # Actions that are enabled if any tab is open
        self.save_as_action.setEnabled(True)
        self.export_action.setEnabled(True) # Enable export if a tab is open

        has_selection = False
        is_writable = True # Assume writable unless determined otherwise
        doc = None

        if isinstance(current_widget, QWebEngineView): # Handles EditableHtmlPreviewWidget and WangEditor's web_view
            has_selection = current_widget.hasSelection()
            # QWebEngineView doesn't have a direct document() or isReadOnly() like QTextEdit.
            # Undo/redo/cut/copy/paste are handled by QWebEnginePage actions, their enabled state is managed by the page.
            # We can try to reflect this, but it's often simpler to just enable them and let the page handle it.
            self.undo_action.setEnabled(current_widget.page().action(QWebEnginePage.WebAction.Undo).isEnabled())
            self.redo_action.setEnabled(current_widget.page().action(QWebEnginePage.WebAction.Redo).isEnabled())
            self.cut_action.setEnabled(current_widget.page().action(QWebEnginePage.WebAction.Cut).isEnabled() and has_selection)
            self.copy_action.setEnabled(current_widget.page().action(QWebEnginePage.WebAction.Copy).isEnabled() and has_selection)
            self.paste_action.setEnabled(current_widget.page().action(QWebEnginePage.WebAction.Paste).isEnabled())
            self.select_all_action.setEnabled(current_widget.page().action(QWebEnginePage.WebAction.SelectAll).isEnabled())
            # Font, color, insert image might need JS interaction for web views
            self.font_action.setEnabled(False) 
            self.color_action.setEnabled(False)
            self.insert_image_action.setEnabled(False) # WangEditor handles its own image insertion
            self.find_action.setEnabled(True) # Web view has find
            self.replace_action.setEnabled(False) # Replace is more complex in web views

            # Save action for web views (e.g. HtmlViewContainer in preview, WangEditor in rich text)
            if isinstance(current_tab_container, HtmlViewContainer):
                self.save_action.setEnabled(current_tab_container.is_modified())
            elif isinstance(current_tab_container, WangEditor):
                 self.save_action.setEnabled(current_tab_container.isModified())


        elif hasattr(current_widget, 'document'): # Handles _InternalTextEdit, Markdown's editor, WangEditor's source_code_editor
            doc = current_widget.document()
            if doc:
                self.undo_action.setEnabled(doc.isUndoAvailable())
                self.redo_action.setEnabled(doc.isRedoAvailable())
                self.save_action.setEnabled(doc.isModified())
            
            if hasattr(current_widget, 'textCursor'):
                has_selection = current_widget.textCursor().hasSelection()
            
            if hasattr(current_widget, 'isReadOnly'):
                is_writable = not current_widget.isReadOnly()

            self.cut_action.setEnabled(has_selection and is_writable)
            self.copy_action.setEnabled(has_selection)
            self.select_all_action.setEnabled(True) # Always possible for text editors
            self.find_action.setEnabled(True)
            self.replace_action.setEnabled(is_writable)
            self.font_action.setEnabled(is_writable)
            self.color_action.setEnabled(is_writable)
            # Enable insert image only for _InternalTextEdit (which is QTextEdit based)
            self.insert_image_action.setEnabled(isinstance(current_widget, _InternalTextEdit) and is_writable)
            
            clipboard = QApplication.clipboard()
            can_paste_text = clipboard.mimeData().hasText() and hasattr(current_widget, 'canPaste') and current_widget.canPaste()
            self.paste_action.setEnabled(can_paste_text and is_writable)


        # Update selection-dependent actions
        self.translate_selection_action.setEnabled(has_selection)
        self.calculate_selection_action.setEnabled(has_selection)
        self.copy_to_ai_action.setEnabled(has_selection)
        
        # Enable fetch_url_source_action if selection is a valid URL
        is_valid_url_selected = False
        if has_selection and current_widget:
            selected_text_for_url_check = ""
            if isinstance(current_widget, QWebEngineView):
                selected_text_for_url_check = current_widget.selectedText().strip()
            elif hasattr(current_widget, 'textCursor'):
                selected_text_for_url_check = current_widget.textCursor().selectedText().strip()
            
            if selected_text_for_url_check:
                q_url_check = QUrl(selected_text_for_url_check)
                if q_url_check.isValid() and q_url_check.scheme() and q_url_check.host():
                    is_valid_url_selected = True
        self.fetch_url_source_action.setEnabled(is_valid_url_selected)


        # View toggles
        self.toggle_markdown_preview_action.setEnabled(is_markdown_tab)
        if is_markdown_tab:
            self.toggle_markdown_preview_action.setChecked(current_tab_container.is_preview_mode)
        
        self.toggle_html_view_action.setEnabled(is_html_view_container) # Corrected variable name
        # If WangEditor has its own toggle, handle it here (assuming it's not the primary HTML editor now)
        # self.toggle_html_preview_action.setEnabled(is_wang_editor_tab) 
        # if is_wang_editor_tab: 
        #     is_source_mode_wang = (current_tab_container._current_editor_mode == 0)
        #     self.toggle_html_preview_action.setChecked(is_source_mode_wang)
        
        # Ensure HTML specific toggles are disabled if not an HTML container
        if not is_html_view_container: # Corrected variable name
            self.toggle_html_view_action.setEnabled(False)
    
    def handle_html_container_modification(self, modified: bool):
        """Slot to connect to HtmlViewContainer.internalModificationChanged."""
        current_tab_container = self.tab_widget.currentWidget()
        if isinstance(current_tab_container, HtmlViewContainer):
            self.update_tab_title(current_tab_container, modified)
            if self.tab_widget.currentWidget() == current_tab_container:
                self.save_action.setEnabled(modified)


    def update_window_title(self):
        title_prefix = "Pynote Refactored"
        current_tab_idx = self.tab_widget.currentIndex() if self.tab_widget else -1
        if current_tab_idx != -1:
            tab_text = self.tab_widget.tabText(current_tab_idx)
            if tab_text: 
                base_tab_text = tab_text[:-1].strip() if tab_text.endswith("*") else tab_text
                title_prefix = f"{base_tab_text} - {title_prefix}"
        self.setWindowTitle(title_prefix)

    def update_tab_title(self, tab_container_widget, modified: bool | None = None):
        if not (self.ui_manager and self.ui_manager.tab_widget and tab_container_widget): return
        
        index = self.ui_manager.tab_widget.indexOf(tab_container_widget)
        if index == -1: return

        is_modified_flag = False
        if isinstance(tab_container_widget, HtmlViewContainer): # Check HtmlViewContainer first
            is_modified_flag = tab_container_widget.is_modified()
        elif isinstance(tab_container_widget, EditableHtmlPreviewWidget): # Should not be top-level now
            is_modified_flag = tab_container_widget.property("is_modified_custom_flag") or False
        elif isinstance(tab_container_widget, WangEditor):
            is_modified_flag = tab_container_widget.isModified() if hasattr(tab_container_widget, 'isModified') else False
        elif isinstance(tab_container_widget, MarkdownEditorWidget): # Check for MarkdownEditorWidget directly
            actual_editor_component = tab_container_widget.editor
            if actual_editor_component and hasattr(actual_editor_component, 'document') and \
               callable(actual_editor_component.document):
                doc = actual_editor_component.document()
                is_modified_flag = doc.isModified() if doc else False
        elif isinstance(tab_container_widget, TextEditor): # Standalone TextEditor (rare)
             actual_editor_component = tab_container_widget._editor
             if actual_editor_component and hasattr(actual_editor_component, 'document') and \
               callable(actual_editor_component.document):
                doc = actual_editor_component.document()
                is_modified_flag = doc.isModified() if doc else False
        
        if modified is not None: # Override if 'modified' is explicitly passed
            is_modified_flag = modified

        base_name = self.ui_manager.get_widget_base_name(tab_container_widget)
        if not base_name: base_name = f"标签 {index + 1}"
        
        new_tab_text = f"{base_name}{'*' if is_modified_flag else ''}"
        self.ui_manager.tab_widget.setTabText(index, new_tab_text)
        if self.ui_manager.tab_widget.currentWidget() == tab_container_widget:
            self.update_window_title()

    def closeEvent(self, event):
        if self.file_operations.close_all_tabs(): event.accept()
        else: event.ignore()

    def on_workspace_changed(self, new_path: str):
        self.current_workspace_path = new_path
        if hasattr(self, 'statusBar') and self.statusBar:
            self.statusBar.showMessage(f"工作区已更改为: {new_path}", 5000)
        if hasattr(self, 'file_explorer') and self.file_explorer:
            if not self.file_explorer.isVisible(): self.file_explorer.show()
            if hasattr(self, 'toggle_sidebar_button') and self.toggle_sidebar_button:
                if not self.toggle_sidebar_button.isChecked(): self.toggle_sidebar_button.setChecked(True)

    def handle_file_explorer_double_click(self, file_path: str):
        if hasattr(self.file_operations, 'open_file_from_path'):
            self.file_operations.open_file_from_path(file_path)
        else: QMessageBox.warning(self, "打开文件错误", f"无法处理文件打开请求: {file_path}\nFileOperations模块不完整。")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() and any(url.isLocalFile() for url in event.mimeData().urls()):
            event.acceptProposedAction()
        else: event.ignore()

    def dropEvent(self, event: QDropEvent):
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            files_to_open = [url.toLocalFile() for url in mime_data.urls() if url.isLocalFile() and os.path.isfile(url.toLocalFile())]
            if files_to_open:
                event.acceptProposedAction()
                for f_path in files_to_open:
                    if hasattr(self.file_operations, 'open_file_from_path'): self.file_operations.open_file_from_path(f_path)
                return 
        
        if not mime_data.hasFormat("application/x-qtabwidget-tabbar-tab"):
            if mime_data.hasUrls(): # Re-check for file drops not accepted by the first block (e.g. if it was a mix)
                files_to_open = [url.toLocalFile() for url in mime_data.urls() if url.isLocalFile() and os.path.isfile(url.toLocalFile())]
                if files_to_open:
                    event.acceptProposedAction()
                    for f_path in files_to_open: self.file_operations.open_file_from_path(f_path)
                    return
            event.ignore()
        else:
            super().dropEvent(event)
