# src/ui/main/main_window.py
import sys
import os
from PyQt6.QtWidgets import (QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QTextEdit, QListWidget, QListWidgetItem, QToolBar, QMenuBar, QMenu,
                             QStatusBar, QFileDialog, QFontDialog, QColorDialog, QMessageBox,
                              QInputDialog, QSplitter, QTabWidget, QToolButton, QDockWidget, QMenu, QSizePolicy)
from PyQt6.QtGui import QAction, QFont, QColor, QTextCursor, QIcon, QImage, QTextDocument, QPainter, QKeyEvent, QDragEnterEvent, QDropEvent # Added QDragEnterEvent, QDropEvent
from PyQt6.QtCore import Qt, QSize, QUrl, QRect, QEvent, pyqtSignal, QPointF, QFile, QTextStream, QPoint, QSignalBlocker, QDateTime, QTimer

from ..core.base_widget import BaseWidget
from .ui_initializer import UIInitializer
from ..components.file_operations import FileOperations
from ..components.edit_operations import EditOperations
from ..components.view_operations import ViewOperations
from ..components.ui_manager import UIManager

from ..atomic.editor.html_editor import HtmlEditor
from ..atomic.markdown_editor_widget import MarkdownEditorWidget
from ..atomic.editor.text_editor import TextEditor, _InternalTextEdit


class MainWindow(QMainWindow):
    current_editor_changed = pyqtSignal(object) 
    theme_changed = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        # print("▶ MainWindow.__init__ (Refactored)") # Keep for debug if needed

        self.ui_manager = UIManager(self)
        self.markdown_editor_widget = MarkdownEditorWidget(self)
        # Initialize current_workspace_path before FileOperations, as it might use it
        self.current_workspace_path = None 
        self.file_operations = FileOperations(self, self.ui_manager, self.markdown_editor_widget)
        self.edit_operations = EditOperations(self, self.ui_manager)
        self.view_operations = ViewOperations(self, self.ui_manager)

        self.base_font_size_pt = 10.0
        self.current_zoom_factor = 1.0
        self.zoom_step = 0.1
        self.min_zoom_factor = 0.5
        self.max_zoom_factor = 3.0

        self.tab_widget = QTabWidget(self)
        if self.tab_widget is None:
             print("MainWindow: ERROR - QTabWidget creation returned None!")
             self.ui_manager.tab_widget = None
        else:
             self.tab_widget.setDocumentMode(True)
             self.tab_widget.setTabsClosable(True)
             self.tab_widget.setMovable(True)
             self.ui_manager.tab_widget = self.tab_widget
        
        self.ui_initializer = UIInitializer(self, self.ui_manager, self.tab_widget)
        self.previous_editor = None # Store the container widget of the previous tab
        self.setDockOptions(QMainWindow.DockOption.AllowTabbedDocks | QMainWindow.DockOption.AnimatedDocks)
        
        self.create_actions()
        self.ui_initializer.setup_ui() # This creates self.toolbar and self.file_explorer
        
        # Connect signals for FileExplorer after it's created by UIInitializer
        if hasattr(self, 'file_explorer') and self.file_explorer:
            self.file_explorer.root_path_changed.connect(self.on_workspace_changed)
            self.file_explorer.file_double_clicked.connect(self.handle_file_explorer_double_click)
            
            # Manually trigger on_workspace_changed with the initial path from FileExplorer
            # This ensures current_workspace_path is set correctly at startup
            # and also handles showing the FileExplorer if it was hidden and a valid path is set.
            initial_fe_path = self.file_explorer.get_root_path()
            if initial_fe_path and os.path.isdir(initial_fe_path):
                # Call on_workspace_changed to ensure all related states are updated
                # This will set self.current_workspace_path and show file explorer if needed.
                self.on_workspace_changed(initial_fe_path) 
            else:
                print(f"MainWindow: FileExplorer initial path ('{initial_fe_path}') is not a valid directory.")
        else:
            print("MainWindow: ERROR - self.file_explorer not initialized by UIInitializer, cannot set initial workspace from it.")

        self.create_menu_bar()
        self.create_toolbar() 
        
        self.ui_manager.apply_current_theme()

        if self.tab_widget is not None:
             self.tab_widget.tabCloseRequested.connect(self.file_operations.close_tab)
             self.tab_widget.currentChanged.connect(self.on_current_tab_changed)
             self.on_current_tab_changed(self.tab_widget.currentIndex()) # Initial call
             if self.tab_widget.count() == 0:
                 # If a workspace path is set (e.g., to Desktop by default from FileExplorer init,
                 # or by user action later), and no tabs are open, create a new file in that workspace.
                 # The self.current_workspace_path should be set by on_workspace_changed
                 # signal from FileExplorer's initialization.
                 if self.current_workspace_path and os.path.isdir(self.current_workspace_path): 
                    if hasattr(self, 'file_operations'):
                        print(f"MainWindow: Creating initial new file in workspace: {self.current_workspace_path}")
                        self.file_operations.new_file(workspace_path=self.current_workspace_path)
                    else:
                        print("MainWindow: ERROR - file_operations not available for initial file.")
                 else:
                    print(f"MainWindow: No valid current_workspace_path ('{self.current_workspace_path}') at startup or no tabs, not creating initial file.")
                 # If current_workspace_path is None or invalid, do not create an initial file and do not show any dialog.
                 # The user can open a folder or create a new file manually.
        else:
             print("错误：MainWindow 未能创建 tab_widget。")
        
        if QApplication.clipboard() is not None:
            QApplication.clipboard().dataChanged.connect(
                lambda: self.update_edit_actions_state(self.get_current_editor_widget())
            )
        self.update_window_title()
        self.setAcceptDrops(True) # Enable drag and drop for the main window

    # def set_initial_workspace(self, path: str): # Removed as FileExplorer now defaults to Desktop
    #     """Sets the initial workspace path for the application."""
    #     if path and os.path.isdir(path):
    #         if hasattr(self, 'file_explorer') and self.file_explorer:
    #             self.file_explorer.set_root_path(path) 
    #         else: 
    #             self.current_workspace_path = path 
    #             print(f"MainWindow: Initial workspace set to {path} before FileExplorer fully ready.")

    def create_actions(self):
        self.new_action = QAction("新建文本", self, shortcut="Ctrl+N", toolTip="创建新文本文件", triggered=self.new_file_wrapper)
        self.new_html_action = QAction("新建HTML", self, shortcut="Ctrl+Shift+N", toolTip="创建新HTML文件", triggered=self.new_html_file_wrapper)
        self.new_markdown_action = QAction("新建Markdown", self, shortcut="Ctrl+Alt+N", toolTip="创建新Markdown文件", triggered=self.new_markdown_file_wrapper)
        
        self.open_action = QAction("打开文件...", self, shortcut="Ctrl+O", toolTip="打开文件", triggered=self.open_file_dialog_wrapper) # Renamed for clarity
        self.open_folder_action = QAction("打开文件夹...", self, shortcut="Ctrl+K Ctrl+O", toolTip="打开文件夹作为工作区", triggered=self.open_folder_wrapper) # New action
        
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

        self.toggle_theme_action = QAction("切换主题", self, shortcut="Ctrl+T", toolTip="切换主题", triggered=self.toggle_theme_wrapper)
        self.zen_action = QAction("Zen Mode", self, checkable=True, shortcut="F11", triggered=self.toggle_zen_mode_wrapper, toolTip="Zen模式")

        self.zoom_in_action = QAction("放大", self, shortcut="Ctrl++", toolTip="放大", triggered=self.zoom_in)
        self.zoom_out_action = QAction("缩小", self, shortcut="Ctrl+-", toolTip="缩小", triggered=self.zoom_out)
        self.reset_zoom_action = QAction("重置缩放", self, shortcut="Ctrl+0", toolTip="重置缩放", triggered=self.reset_zoom)

        self.toggle_markdown_preview_action = QAction("MD 预览↔源码", self, checkable=True, shortcut="Ctrl+Shift+M", toolTip="切换Markdown预览/源码", triggered=self.toggle_markdown_preview_panel_wrapper, enabled=False)
        self.toggle_html_preview_action = QAction("HTML 预览↔源码", self, checkable=True, shortcut="Ctrl+Shift+H", toolTip="切换HTML预览/源码", triggered=self.toggle_html_preview_panel_wrapper, enabled=False)

        self.about_action = QAction("关于", self, toolTip="关于", triggered=self.show_about_wrapper)

    def create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("文件")
        file_menu.addActions([self.new_action, self.new_html_action, self.new_markdown_action])
        file_menu.addSeparator()
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.open_folder_action) # Add new action to menu
        file_menu.addSeparator()
        file_menu.addActions([self.save_action, self.save_as_action])
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
        edit_menu.addSeparator()
        edit_menu.addActions([self.translate_action, self.translate_selection_action])

        format_menu = menu_bar.addMenu("格式")
        format_menu.addActions([self.font_action, self.color_action])
        format_menu.addSeparator()
        format_menu.addAction(self.insert_image_action) # Keep for now, logic in update_edit_actions_state will disable it
        format_menu.addSeparator()
        format_menu.addAction(self.toggle_theme_action)
        
        view_menu = menu_bar.addMenu("视图")
        view_menu.addAction(self.zen_action)
        view_menu.addSeparator()
        view_menu.addAction(self.toggle_markdown_preview_action)
        view_menu.addAction(self.toggle_html_preview_action)
        view_menu.addSeparator()
        view_menu.addActions([self.zoom_in_action, self.zoom_out_action, self.reset_zoom_action])
        
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
        # self.toolbar.addActions([self.new_action, self.new_html_action, self.new_markdown_action, self.open_action, self.save_action])
        self.toolbar.addAction(self.new_action)
        self.toolbar.addAction(self.new_html_action)
        self.toolbar.addAction(self.new_markdown_action)
        
        # Create a QToolButton for "Open" with a dropdown menu
        open_menu_button = QToolButton(self)
        open_menu_button.setText("打开") # Or use an icon
        open_menu_button.setToolTip("打开文件或文件夹")
        open_menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        
        open_options_menu = QMenu(open_menu_button)
        open_options_menu.addAction(self.open_action) # "打开文件..."
        open_options_menu.addAction(self.open_folder_action) # "打开文件夹..."
        
        open_menu_button.setMenu(open_options_menu)
        open_menu_button.setDefaultAction(self.open_action) # Default click action
        self.toolbar.addWidget(open_menu_button)
        
        self.toolbar.addAction(self.save_action)
        self.toolbar.addSeparator()
        self.toolbar.addActions([self.undo_action, self.redo_action])
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.find_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.translate_action)
        self.toolbar.addSeparator()
        self.toolbar.addActions([self.toggle_markdown_preview_action, self.toggle_html_preview_action])
        
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.toolbar.addWidget(spacer)
        
        menu_btn = QToolButton()
        menu_btn.setText("...")
        menu_btn.setToolTip("更多选项")
        menu_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        more_menu = QMenu(menu_btn)
        
        file_submenu = more_menu.addMenu("文件")
        file_submenu.addActions([self.save_as_action, self.close_tab_action, self.exit_action])
        edit_submenu = more_menu.addMenu("编辑")
        edit_submenu.addActions([self.cut_action, self.copy_action, self.paste_action, self.select_all_action, self.replace_action, self.translate_selection_action])
        format_submenu = more_menu.addMenu("格式")
        format_submenu.addActions([self.font_action, self.color_action, self.insert_image_action])
        view_submenu = more_menu.addMenu("视图")
        view_submenu.addActions([self.toggle_theme_action, self.zen_action, self.zoom_in_action, self.zoom_out_action, self.reset_zoom_action])
        help_submenu = more_menu.addMenu("帮助")
        help_submenu.addAction(self.about_action)
        
        menu_btn.setMenu(more_menu)
        self.toolbar.addWidget(menu_btn)
        self.addAction(self.zen_action)

    def new_file_wrapper(self):
        if not self.current_workspace_path and hasattr(self, 'file_explorer') and self.file_explorer:
            QMessageBox.information(self, "选择工作区", "请首先选择一个工作区来创建新文件。")
            self.file_explorer.browse_for_folder()
            if not self.current_workspace_path: # User cancelled
                return
        self.file_operations.new_file(workspace_path=self.current_workspace_path)

    def new_html_file_wrapper(self):
        if not self.current_workspace_path and hasattr(self, 'file_explorer') and self.file_explorer:
            QMessageBox.information(self, "选择工作区", "请首先选择一个工作区来创建新HTML文件。")
            self.file_explorer.browse_for_folder()
            if not self.current_workspace_path: # User cancelled
                return
        self.file_operations.new_file(file_type="html", workspace_path=self.current_workspace_path)

    def new_markdown_file_wrapper(self):
        if not self.current_workspace_path and hasattr(self, 'file_explorer') and self.file_explorer:
            # Since default is Desktop, this prompt might be less frequent unless Desktop path is invalid
            QMessageBox.information(self, "选择工作区", "当前未指定有效工作区。请选择一个工作区来创建新Markdown文件。")
            self.open_folder_wrapper() # Use the new menu action's logic
            if not self.current_workspace_path: # User cancelled
                return
        self.file_operations.new_file(file_type="markdown", workspace_path=self.current_workspace_path)

    def open_file_dialog_wrapper(self): 
        # Open file dialog should default to current workspace, or home/desktop if no workspace
        default_open_dir = self.current_workspace_path
        if not default_open_dir or not os.path.isdir(default_open_dir):
            from PyQt6.QtCore import QStandardPaths
            default_open_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
            if not default_open_dir or not os.path.isdir(default_open_dir):
                default_open_dir = os.path.expanduser("~")
        self.file_operations.open_file_dialog(initial_dir=default_open_dir)

    def open_folder_wrapper(self):
        """Wrapper to open folder chooser and set as workspace."""
        if hasattr(self, 'file_explorer') and self.file_explorer:
            self.file_explorer.browse_for_folder()
            # self.current_workspace_path will be updated by on_workspace_changed signal

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
    def show_about_wrapper(self): self.view_operations.show_about()
    def open_translation_dialog_wrapper(self): 
        if hasattr(self, 'edit_operations'): self.edit_operations.open_translation_dialog()
    def translate_selection_wrapper(self):
        if hasattr(self, 'edit_operations'): self.edit_operations.translate_selection()

    def toggle_markdown_preview_panel_wrapper(self, checked):
        current_tab_container = self.tab_widget.currentWidget()
        if isinstance(current_tab_container, MarkdownEditorWidget):
            current_tab_container.set_preview_visible(checked)

    def toggle_html_preview_panel_wrapper(self, checked):
        current_tab_container = self.tab_widget.currentWidget()
        if isinstance(current_tab_container, HtmlEditor):
            current_tab_container.set_preview_visible(checked)

    def zoom_in(self): 
        self.current_zoom_factor=min(self.max_zoom_factor,self.current_zoom_factor+self.zoom_step)
        self.ui_manager.apply_current_theme()
        self._apply_content_zoom_to_current_editor()
    def zoom_out(self): 
        self.current_zoom_factor=max(self.min_zoom_factor,self.current_zoom_factor-self.zoom_step)
        self.ui_manager.apply_current_theme()
        self._apply_content_zoom_to_current_editor()
    def reset_zoom(self): 
        self.current_zoom_factor=1.0
        self.ui_manager.apply_current_theme()
        self._apply_content_zoom_to_current_editor()
    
    def _apply_content_zoom_to_current_editor(self):
        # This was for old QWebEngineView HtmlEditor. New one uses QPlainTextEdit.
        # Markdown preview (QWebEngineView) might need its own zoom handling if desired.
        pass

    def keyPressEvent(self, event: QKeyEvent):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() in (Qt.Key.Key_Plus, Qt.Key.Key_Equal): 
                self.zoom_in()
                event.accept()
                return
            if event.key() == Qt.Key.Key_Minus: 
                self.zoom_out()
                event.accept()
                return
            if event.key() == Qt.Key.Key_0: 
                self.reset_zoom()
                event.accept()
                return
        super().keyPressEvent(event)

    def get_current_editor_widget(self) -> QWidget | None:
        if not (self.ui_manager and self.ui_manager.tab_widget): return None
        current_tab_container = self.ui_manager.tab_widget.currentWidget()
        if not current_tab_container: return None

        if isinstance(current_tab_container, TextEditor):
            return current_tab_container._editor 
        if isinstance(current_tab_container, HtmlEditor): 
             return current_tab_container.source_editor 
        if isinstance(current_tab_container, MarkdownEditorWidget): 
             return current_tab_container.editor 
        if isinstance(current_tab_container, _InternalTextEdit): 
             return current_tab_container
        
        return current_tab_container

    def on_current_tab_changed(self, index):
        current_editor_component = self.get_current_editor_widget()
        current_tab_container_widget = self.tab_widget.currentWidget() if self.tab_widget else None

        if self.previous_editor and hasattr(self.previous_editor, 'view_mode_changed'):
            try:
                if isinstance(self.previous_editor, MarkdownEditorWidget):
                    self.previous_editor.view_mode_changed.disconnect(self.toggle_markdown_preview_action.setChecked)
                elif isinstance(self.previous_editor, HtmlEditor):
                     self.previous_editor.view_mode_changed.disconnect(self.toggle_html_preview_action.setChecked)
            except TypeError: pass 

        if isinstance(current_tab_container_widget, MarkdownEditorWidget):
            self.toggle_markdown_preview_action.setEnabled(True)
            current_tab_container_widget.view_mode_changed.connect(self.toggle_markdown_preview_action.setChecked)
            self.toggle_markdown_preview_action.setChecked(current_tab_container_widget.is_preview_mode)
        else:
            self.toggle_markdown_preview_action.setEnabled(False)
            self.toggle_markdown_preview_action.setChecked(False)

        if isinstance(current_tab_container_widget, HtmlEditor):
            self.toggle_html_preview_action.setEnabled(True)
            current_tab_container_widget.view_mode_changed.connect(self.toggle_html_preview_action.setChecked)
            self.toggle_html_preview_action.setChecked(current_tab_container_widget.is_preview_mode)
        else:
            self.toggle_html_preview_action.setEnabled(False)
            self.toggle_html_preview_action.setChecked(False)
        
        self.previous_editor = current_tab_container_widget

        self.update_edit_actions_state(current_editor_component) # Must be after preview actions are updated
        self.update_window_title()
        self.current_editor_changed.emit(current_editor_component)
        if current_tab_container_widget: # Check if it's not None
            self.view_operations.handle_tab_change(current_tab_container_widget)

        if self.ui_manager.is_widget_editor(current_editor_component): 
             current_editor_component.setFocus()

    def _update_copy_cut_state(self, available: bool):
        self.copy_action.setEnabled(available)
        self.cut_action.setEnabled(available)

    def update_edit_actions_state(self, current_widget: QWidget | None):
        all_editor_actions = [
            self.undo_action, self.redo_action, self.cut_action, self.copy_action, 
            self.select_all_action, self.font_action, self.color_action, 
            self.insert_image_action, self.find_action, self.replace_action, 
            self.save_action, self.save_as_action, 
            self.translate_selection_action
        ]
        # Preview toggles are handled separately based on tab container type
        # self.close_tab_action is enabled if there's any tab

        if current_widget is None or not self.ui_manager.is_widget_editor(current_widget):
            for action in all_editor_actions:
                action.setEnabled(False)
            # Keep paste always enabled, close_tab enabled if tabs exist
            self.close_tab_action.setEnabled(self.tab_widget.count() > 0 if self.tab_widget else False)
            # Disable preview toggles if not an editor or no tab
            self.toggle_markdown_preview_action.setEnabled(False)
            self.toggle_html_preview_action.setEnabled(False)
            return
            
        is_editor = True # We know it's an editor from the check above
        is_writable = not current_widget.isReadOnly() if hasattr(current_widget, 'isReadOnly') else True

        # Document-based actions
        if hasattr(current_widget, 'document') and callable(current_widget.document):
            doc = current_widget.document()
            if doc:
                self.undo_action.setEnabled(doc.isUndoAvailable())
                self.redo_action.setEnabled(doc.isRedoAvailable())
                self.save_action.setEnabled(doc.isModified() and is_writable)
            else:
                self.undo_action.setEnabled(False); self.redo_action.setEnabled(False); self.save_action.setEnabled(False)
        else: # No document method (should not happen for known editors)
            self.undo_action.setEnabled(False); self.redo_action.setEnabled(False); self.save_action.setEnabled(False)
            
        has_selection = False
        if hasattr(current_widget, 'textCursor') and callable(current_widget.textCursor):
            cursor = current_widget.textCursor()
            if cursor: has_selection = cursor.hasSelection()
                
        self._update_copy_cut_state(has_selection) # is_editor is true here
        self.translate_selection_action.setEnabled(has_selection)
        self.select_all_action.setEnabled(True) # Always possible for an editor
        self.find_action.setEnabled(True); self.replace_action.setEnabled(True)
        self.save_as_action.setEnabled(is_writable)
        self.close_tab_action.setEnabled(True) 
        self.font_action.setEnabled(True); self.color_action.setEnabled(True)
        
        # insert_image_action is for WYSIWYG HTML, disable for source editors
        self.insert_image_action.setEnabled(False) 

        # Update preview toggle states based on the container widget type
        current_tab_container = self.tab_widget.currentWidget() if self.tab_widget else None
        is_markdown_tab = isinstance(current_tab_container, MarkdownEditorWidget)
        is_html_tab = isinstance(current_tab_container, HtmlEditor)

        self.toggle_markdown_preview_action.setEnabled(is_markdown_tab)
        if is_markdown_tab:
            self.toggle_markdown_preview_action.setChecked(current_tab_container.is_preview_mode)
        
        self.toggle_html_preview_action.setEnabled(is_html_tab)
        if is_html_tab:
            self.toggle_html_preview_action.setChecked(current_tab_container.is_preview_mode)

    def update_window_title(self):
        title_prefix = "Pynote Refactored"
        current_tab_idx = self.tab_widget.currentIndex() if self.tab_widget else -1
        if current_tab_idx != -1:
            tab_text = self.tab_widget.tabText(current_tab_idx)
            if tab_text: # Ensure tab_text is not empty
                base_tab_text = tab_text[:-1].strip() if tab_text.endswith("*") else tab_text
                title_prefix = f"{base_tab_text} - {title_prefix}"
        self.setWindowTitle(title_prefix)

    def update_tab_title(self, modified: bool | None = None):
        if not (self.ui_manager and self.ui_manager.tab_widget): return
        index = self.ui_manager.tab_widget.currentIndex()
        if index == -1: return
        
        current_tab_container = self.ui_manager.tab_widget.widget(index)
        actual_editor_component = self.get_current_editor_widget()

        if modified is None:
            if actual_editor_component and hasattr(actual_editor_component, 'document') and \
               callable(actual_editor_component.document):
                doc = actual_editor_component.document()
                modified = doc.isModified() if doc else False
            else:
                modified = False 

        base_name = self.ui_manager.get_widget_base_name(current_tab_container)
        if not base_name: base_name = f"标签 {index + 1}"
        new_tab_text = f"{base_name}{'*' if modified else ''}"
        self.ui_manager.tab_widget.setTabText(index, new_tab_text)
        self.update_window_title()

    def closeEvent(self, event):
        if self.file_operations.close_all_tabs(): event.accept()
        else: event.ignore()

    # --- Custom Slots for Workspace and File Explorer Interaction ---
    def on_workspace_changed(self, new_path: str):
        """Slot to handle workspace path changes from FileExplorer."""
        self.current_workspace_path = new_path
        if hasattr(self, 'statusBar') and self.statusBar: # Check if statusBar exists
            self.statusBar.showMessage(f"工作区已更改为: {new_path}", 5000)
        
        # Ensure the file explorer panel is visible after a workspace is chosen
        if hasattr(self, 'file_explorer') and self.file_explorer:
            if not self.file_explorer.isVisible():
                self.file_explorer.show() # Directly show the panel
            
            # Synchronize the activity bar button's state
            if hasattr(self, 'toggle_sidebar_button') and self.toggle_sidebar_button:
                if not self.toggle_sidebar_button.isChecked():
                    # Set checked without re-triggering the slot that UIInitializer connects to 'clicked'
                    # QToolButton's setChecked does not emit clicked(), but toggled(bool).
                    # The UIInitializer connects to 'clicked', so this should be fine.
                    # The button's visual state will update.
                    # The actual visibility is handled by file_explorer.show() above.
                    # And when user clicks the button, UIInitializer's slot will handle it.
                    self.toggle_sidebar_button.setChecked(True)
        
        # Update window title or other UI elements if needed
        # self.update_window_title() # Could incorporate workspace path into title

    def handle_file_explorer_double_click(self, file_path: str):
        """Slot to handle file double-click from FileExplorer."""
        if hasattr(self.file_operations, 'open_file_from_path') and callable(getattr(self.file_operations, 'open_file_from_path')):
            self.file_operations.open_file_from_path(file_path)
        elif hasattr(self.file_operations, 'open_file_dialog') and callable(getattr(self.file_operations, 'open_file_dialog')):
            # Fallback: use open_file_dialog, passing the path.
            # This isn't ideal as open_file_dialog itself shows a dialog.
            # The preferred method is open_file_from_path.
            print(f"MainWindow: open_file_from_path not found, attempting fallback with open_file_dialog for {file_path}")
            self.file_operations.open_file_dialog(initial_path=file_path)
        else:
            QMessageBox.warning(self, "打开文件错误", f"无法处理文件打开请求: {file_path}\nFileOperations模块不完整。")
            print(f"MainWindow: ERROR - Cannot open file from explorer: {file_path}. FileOperations methods missing.")

    # --- Drag and Drop Event Handlers ---
    def dragEnterEvent(self, event: QDragEnterEvent): # Corrected type hint
        mime_data = event.mimeData()
        # We are interested in file URLs
        if mime_data.hasUrls():
            # Check if at least one URL is a local file
            for url in mime_data.urls():
                if url.isLocalFile():
                    event.acceptProposedAction() # Accept the drag if it contains local files
                    return
        event.ignore() # Otherwise, ignore the drag

    def dropEvent(self, event: QDropEvent): # Corrected type hint
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            files_to_open = []
            for url in mime_data.urls():
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    if os.path.isfile(file_path): # Ensure it's a file, not a directory
                        files_to_open.append(file_path)
            
            if files_to_open:
                event.acceptProposedAction() # Crucial: accept the drop action
                for f_path in files_to_open:
                    if hasattr(self.file_operations, 'open_file_from_path'):
                        self.file_operations.open_file_from_path(f_path)
                    else:
                        print(f"MainWindow: Cannot open dropped file {f_path}, open_file_from_path is missing.")
                # After handling, ensure the event is marked as accepted and stop further processing by child widgets.
                # For QMainWindow, accepting the event should be enough.
                # If child widgets (like QTextEdit) still process it, they might need their acceptDrops set to False
                # or their own dropEvents overridden to ignore if the parent (MainWindow) handled it.
                return 
        
        # If the drop doesn't contain URLs or no valid files were found, ignore it.
        event.ignore()
