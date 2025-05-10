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

# from ..atomic.editor.html_editor import HtmlEditor # No longer primary HTML editor
from ..atomic.editor.wang_editor import WangEditor # Import WangEditor
from ..atomic.markdown_editor_widget import MarkdownEditorWidget
from ..atomic.editor.text_editor import TextEditor, _InternalTextEdit
from ..views.editable_html_preview_widget import EditableHtmlPreviewWidget # Added
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

        self.base_font_size_pt = 10.0
        self.current_zoom_factor = 1.0
        self.zoom_step = 0.1
        self.min_zoom_factor = 0.5
        self.max_zoom_factor = 3.0
        
        self.ui_initializer = UIInitializer(self, self.ui_manager)
        self.previous_editor = None 
        self.setDockOptions(QMainWindow.DockOption.AllowTabbedDocks | QMainWindow.DockOption.AnimatedDocks)
        
        self.create_actions()
        self.ui_initializer.setup_ui() 
        
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

        self.toggle_theme_action = QAction("切换主题", self, shortcut="Ctrl+T", toolTip="切换主题", triggered=self.toggle_theme_wrapper)
        self.zen_action = QAction("Zen Mode", self, checkable=True, shortcut="F11", triggered=self.toggle_zen_mode_wrapper, toolTip="Zen模式")

        self.zoom_in_action = QAction("放大", self, shortcut="Ctrl++", toolTip="放大", triggered=self.zoom_in)
        self.zoom_out_action = QAction("缩小", self, shortcut="Ctrl+-", toolTip="缩小", triggered=self.zoom_out)
        self.reset_zoom_action = QAction("重置缩放", self, shortcut="Ctrl+0", toolTip="重置缩放", triggered=self.reset_zoom)

        self.toggle_markdown_preview_action = QAction("MD 预览↔源码", self, checkable=True, shortcut="Ctrl+Shift+M", toolTip="切换Markdown预览/源码", triggered=self.toggle_markdown_preview_panel_wrapper, enabled=False)
        self.toggle_html_preview_action = QAction("HTML 预览↔源码", self, checkable=True, shortcut="Ctrl+Shift+H", toolTip="切换HTML预览/源码 (WangEditor:源码/富文本)", triggered=self.toggle_html_preview_panel_wrapper, enabled=False) # For WangEditor
        self.toggle_html_edit_mode_action = QAction("HTML 可视化编辑", self, checkable=True, toolTip="切换HTML可视化编辑模式 (预览窗口)", triggered=self.toggle_editable_html_edit_mode_wrapper, enabled=False) # For EditableHtmlPreviewWidget
        self.view_html_source_action = QAction("查看HTML源码", self, toolTip="查看当前预览HTML的源码", triggered=self.view_html_source_wrapper, enabled=False) # New action

        self.about_action = QAction("关于", self, toolTip="关于", triggered=self.show_about_wrapper)

    def create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("文件")
        file_menu.addActions([self.new_action, self.new_html_action, self.new_markdown_action, self.open_action, self.open_folder_action, self.save_action, self.save_as_action, self.close_tab_action, self.exit_action])
        
        edit_menu = menu_bar.addMenu("编辑")
        edit_menu.addActions([self.undo_action, self.redo_action, self.cut_action, self.copy_action, self.paste_action, self.select_all_action, self.find_action, self.replace_action, self.translate_action, self.translate_selection_action])

        format_menu = menu_bar.addMenu("格式")
        format_menu.addActions([self.font_action, self.color_action, self.insert_image_action, self.toggle_theme_action])
        
        view_menu = menu_bar.addMenu("视图")
        view_menu.addActions([self.zen_action, self.toggle_markdown_preview_action, self.toggle_html_preview_action, self.toggle_html_edit_mode_action, self.view_html_source_action, self.zoom_in_action, self.zoom_out_action, self.reset_zoom_action])
        
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
        self.toolbar.addAction(self.new_action)
        self.toolbar.addAction(self.new_html_action)
        self.toolbar.addAction(self.new_markdown_action)
        
        open_menu_button = QToolButton(self)
        open_menu_button.setText("打开")
        open_menu_button.setToolTip("打开文件或文件夹")
        open_menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        open_options_menu = QMenu(open_menu_button)
        open_options_menu.addAction(self.open_action)
        open_options_menu.addAction(self.open_folder_action)
        open_menu_button.setMenu(open_options_menu)
        open_menu_button.setDefaultAction(self.open_action)
        self.toolbar.addWidget(open_menu_button)
        
        self.toolbar.addAction(self.save_action)
        self.toolbar.addSeparator()
        self.toolbar.addActions([self.undo_action, self.redo_action, self.find_action, self.translate_action])
        self.toolbar.addSeparator()
        self.toolbar.addActions([self.toggle_markdown_preview_action, self.toggle_html_preview_action, self.toggle_html_edit_mode_action, self.view_html_source_action])
        
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.toolbar.addWidget(spacer)
        
        menu_btn = QToolButton()
        menu_btn.setText("...")
        menu_btn.setToolTip("更多选项")
        menu_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        more_menu = QMenu(menu_btn)
        file_submenu = more_menu.addMenu("文件"); file_submenu.addActions([self.save_as_action, self.close_tab_action, self.exit_action])
        edit_submenu = more_menu.addMenu("编辑"); edit_submenu.addActions([self.cut_action, self.copy_action, self.paste_action, self.select_all_action, self.replace_action, self.translate_selection_action])
        format_submenu = more_menu.addMenu("格式"); format_submenu.addActions([self.font_action, self.color_action, self.insert_image_action])
        view_submenu = more_menu.addMenu("视图"); view_submenu.addActions([self.toggle_theme_action, self.zen_action, self.zoom_in_action, self.zoom_out_action, self.reset_zoom_action])
        help_submenu = more_menu.addMenu("帮助"); help_submenu.addAction(self.about_action)
        menu_btn.setMenu(more_menu)
        self.toolbar.addWidget(menu_btn)
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
    def show_about_wrapper(self): self.view_operations.show_about()
    def open_translation_dialog_wrapper(self): 
        if hasattr(self, 'edit_operations'): self.edit_operations.open_translation_dialog()
    def translate_selection_wrapper(self):
        if hasattr(self, 'edit_operations'): self.edit_operations.translate_selection()

    def toggle_markdown_preview_panel_wrapper(self, checked):
        current_tab_container = self.tab_widget.currentWidget()
        if isinstance(current_tab_container, MarkdownEditorWidget):
            current_tab_container.set_preview_visible(checked)

    def toggle_html_preview_panel_wrapper(self, checked=None): # For WangEditor (Source <-> Rich)
        current_tab_container = self.tab_widget.currentWidget()
        if isinstance(current_tab_container, WangEditor):
            new_mode = 1 - current_tab_container._current_editor_mode 
            current_tab_container.set_edit_mode(new_mode)
    
    def toggle_editable_html_edit_mode_wrapper(self, checked=None): # For EditableHtmlPreviewWidget
        current_tab_container = self.tab_widget.currentWidget()
        if isinstance(current_tab_container, EditableHtmlPreviewWidget):
            current_tab_container.toggleEditing()
            self.toggle_html_edit_mode_action.setChecked(current_tab_container.isEditingEnabled())

    def _on_html_editor_mode_changed(self, mode): # For WangEditor
        current_tab_container = self.tab_widget.currentWidget()
        if isinstance(current_tab_container, WangEditor):
            is_source_mode = (mode == 0)
            self.toggle_html_preview_action.setChecked(is_source_mode)
        # DO NOT call self.update_edit_actions_state here to prevent recursion.

    def view_html_source_wrapper(self):
        current_tab_container = self.tab_widget.currentWidget()
        if isinstance(current_tab_container, EditableHtmlPreviewWidget):
            
            def open_source_in_new_tab(html_content_from_preview: str):
                if self.tab_widget is None: return # Should not happen if current_tab_container is valid

                current_index_of_preview = self.tab_widget.indexOf(current_tab_container)
                if current_index_of_preview == -1: return # Should not happen

                original_tab_name = self.tab_widget.tabText(current_index_of_preview)
                # Remove existing asterisk if present before adding (源码)
                if original_tab_name.endswith("*"):
                    original_tab_name = original_tab_name[:-1].strip()
                source_view_tab_name = f"{original_tab_name} (源码)"
                
                source_editor_container = TextEditor() # This is the QWidget container
                source_editor_container.setPlainText(html_content_from_preview)
                source_editor_container._editor.setReadOnly(True) # Access internal QPlainTextEdit
                
                source_editor_container.setProperty("is_source_view", True) 
                # Set file_path if the original preview had one, so it's associated
                original_file_path = current_tab_container.property("file_path")
                if original_file_path:
                    source_editor_container.setProperty("file_path", original_file_path + " [源码]") # Mark as source view
                else: # For untitled previews
                    source_editor_container.setProperty("untitled_name", source_view_tab_name)
                source_editor_container.setProperty("is_new", True) # Treat as a new, non-savable tab for simplicity

                active_editor_group = self.ui_manager.get_active_editor_group()
                target_tab_widget = active_editor_group.get_tab_widget() if active_editor_group else self.tab_widget
                
                if target_tab_widget:
                    index = target_tab_widget.addTab(source_editor_container, source_view_tab_name)
                    target_tab_widget.setCurrentIndex(index)
                    source_editor_container.setFocus() # Focus the TextEditor container
                    
                    # Mark the new source view tab as not modified
                    # The TextEditor's document is modified if setPlainText is called.
                    if hasattr(source_editor_container._editor.document(), 'setModified'):
                        source_editor_container._editor.document().setModified(False)
                    self.update_tab_title(source_editor_container, False)


            # Use the callback version of getHtml to ensure up-to-date content
            current_tab_container.getHtml(open_source_in_new_tab)

    def zoom_in(self): self.current_zoom_factor=min(self.max_zoom_factor,self.current_zoom_factor+self.zoom_step); self.ui_manager.apply_current_theme(); self._apply_content_zoom_to_current_editor()
    def zoom_out(self): self.current_zoom_factor=max(self.min_zoom_factor,self.current_zoom_factor-self.zoom_step); self.ui_manager.apply_current_theme(); self._apply_content_zoom_to_current_editor()
    def reset_zoom(self): self.current_zoom_factor=1.0; self.ui_manager.apply_current_theme(); self._apply_content_zoom_to_current_editor()
    def _apply_content_zoom_to_current_editor(self): pass

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

        if isinstance(current_tab_container, TextEditor): return current_tab_container._editor
        if isinstance(current_tab_container, WangEditor):
             return current_tab_container.source_code_editor if current_tab_container._current_editor_mode == 0 else current_tab_container.web_view
        if isinstance(current_tab_container, MarkdownEditorWidget): return current_tab_container.editor
        if isinstance(current_tab_container, EditableHtmlPreviewWidget): return current_tab_container
        if isinstance(current_tab_container, _InternalTextEdit): return current_tab_container
        
        module_path = current_tab_container.__class__.__module__
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

        # Disconnect signals from previous editor
        if self.previous_editor:
            if isinstance(self.previous_editor, MarkdownEditorWidget) and hasattr(self.previous_editor, 'view_mode_changed'):
                try: self.previous_editor.view_mode_changed.disconnect(self.toggle_markdown_preview_action.setChecked)
                except TypeError: pass
            elif isinstance(self.previous_editor, WangEditor) and hasattr(self.previous_editor, 'view_mode_changed'):
                try: self.previous_editor.view_mode_changed.disconnect(self._on_html_editor_mode_changed)
                except TypeError: pass
            elif isinstance(self.previous_editor, EditableHtmlPreviewWidget) and hasattr(self.previous_editor, '_bridge'):
                try: self.previous_editor._bridge.htmlChanged.disconnect() # Disconnect all slots from this signal
                except TypeError: pass
        
        # Configure actions and connect signals for current editor
        is_markdown_tab = isinstance(current_tab_container_widget, MarkdownEditorWidget)
        is_wang_editor_tab = isinstance(current_tab_container_widget, WangEditor)
        is_editable_html_tab = isinstance(current_tab_container_widget, EditableHtmlPreviewWidget)

        self.toggle_markdown_preview_action.setEnabled(is_markdown_tab)
        if is_markdown_tab:
            current_tab_container_widget.view_mode_changed.connect(self.toggle_markdown_preview_action.setChecked)
            self.toggle_markdown_preview_action.setChecked(current_tab_container_widget.is_preview_mode)
        
        self.toggle_html_preview_action.setEnabled(is_wang_editor_tab) # This is for WangEditor (source/rich)
        if is_wang_editor_tab:
            current_tab_container_widget.view_mode_changed.connect(self._on_html_editor_mode_changed)
            self._on_html_editor_mode_changed(current_tab_container_widget._current_editor_mode) # Update checked state

        self.toggle_html_edit_mode_action.setEnabled(is_editable_html_tab) 
        self.view_html_source_action.setEnabled(is_editable_html_tab) # Enable/disable view source action

        if is_editable_html_tab:
            current_tab_container_widget._bridge.htmlChanged.connect(
                lambda html_content, editor=current_tab_container_widget: self.on_editor_content_changed(editor)
            )
            self.on_editor_content_changed(current_tab_container_widget, initially_modified=False) 
            self.toggle_html_edit_mode_action.setChecked(current_tab_container_widget.isEditingEnabled())
        
        self.previous_editor = current_tab_container_widget
        self.update_edit_actions_state(current_editor_component)
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
            self.save_action, self.save_as_action, 
            self.translate_selection_action
        ]
        
        current_tab_container = self.tab_widget.currentWidget() if self.tab_widget else None
        is_known_editor = self.ui_manager.is_widget_editor(current_widget) # True for TextEdit, Wang's source_code_editor
        
        is_image_view = False; is_video_view = False
        is_editable_html_preview = isinstance(current_tab_container, EditableHtmlPreviewWidget)

        if current_tab_container and not is_editable_html_preview:
            module_path = current_tab_container.__class__.__module__
            if 'image_viewer_view' in module_path: is_image_view = True
            elif 'video_player_view' in module_path: is_video_view = True
        
        is_markdown_tab = isinstance(current_tab_container, MarkdownEditorWidget)
        is_wang_editor_tab = isinstance(current_tab_container, WangEditor)

        # Default all to false, then enable selectively
        for action in all_editor_actions: action.setEnabled(False)
        self.paste_action.setEnabled(False)
        self.close_tab_action.setEnabled(self.tab_widget.count() > 0 if self.tab_widget else False)
        
        # Specific for EditableHtmlPreviewWidget
        if is_editable_html_preview:
            is_modified = current_tab_container.property("is_modified_custom_flag") or False
            self.save_action.setEnabled(is_modified)
            self.save_as_action.setEnabled(True)
            self.toggle_html_edit_mode_action.setEnabled(True) 
            self.toggle_html_edit_mode_action.setChecked(current_tab_container.isEditingEnabled())
            self.view_html_source_action.setEnabled(True)
            # Disable WangEditor's specific toggle and Markdown's toggle
            self.toggle_html_preview_action.setEnabled(False) 
            self.toggle_markdown_preview_action.setEnabled(False)
            return 

        # For other known editors (TextEditor, Markdown's editor, WangEditor's source_code_editor)
        if is_known_editor:
            is_writable = not current_widget.isReadOnly() if hasattr(current_widget, 'isReadOnly') else True
            doc = current_widget.document() if hasattr(current_widget, 'document') else None
            if doc:
                self.undo_action.setEnabled(doc.isUndoAvailable())
                self.redo_action.setEnabled(doc.isRedoAvailable())
                self.save_action.setEnabled(doc.isModified() and is_writable)
            
            has_selection = current_widget.textCursor().hasSelection() if hasattr(current_widget, 'textCursor') else False
            self._update_copy_cut_state(has_selection and is_writable) # Cut only if writable
            self.copy_action.setEnabled(has_selection) # Copy always if selection
            self.translate_selection_action.setEnabled(has_selection)
            self.select_all_action.setEnabled(True)
            self.find_action.setEnabled(True); self.replace_action.setEnabled(True)
            self.save_as_action.setEnabled(is_writable)
            self.font_action.setEnabled(True); self.color_action.setEnabled(True)
            # insert_image_action is usually for rich text, disable for plain/code. WangEditor handles its own.
            self.insert_image_action.setEnabled(isinstance(current_widget, QTextEdit) and not isinstance(current_widget, _InternalTextEdit))


        # Paste action
        clipboard = QApplication.clipboard()
        can_paste = bool(clipboard.text())
        if is_known_editor and hasattr(current_widget, 'canPaste') and callable(current_widget.canPaste):
            can_paste = can_paste and current_widget.canPaste()
        self.paste_action.setEnabled(can_paste and is_known_editor)

        # View toggles
        self.toggle_markdown_preview_action.setEnabled(is_markdown_tab)
        if is_markdown_tab: self.toggle_markdown_preview_action.setChecked(current_tab_container.is_preview_mode)
        
        self.toggle_html_preview_action.setEnabled(is_wang_editor_tab) # For WangEditor (source/rich)
        if is_wang_editor_tab: 
            # Directly set the checked state here instead of calling _on_html_editor_mode_changed
            is_source_mode_wang = (current_tab_container._current_editor_mode == 0)
            self.toggle_html_preview_action.setChecked(is_source_mode_wang)

        # Disable EditableHTML's toggles if not that tab type
        if not is_editable_html_preview:
            self.toggle_html_edit_mode_action.setEnabled(False)
            self.view_html_source_action.setEnabled(False)
        else: 
             self.toggle_html_edit_mode_action.setEnabled(True)
             self.toggle_html_edit_mode_action.setChecked(current_tab_container.isEditingEnabled())
             self.view_html_source_action.setEnabled(True)


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
        if isinstance(tab_container_widget, EditableHtmlPreviewWidget):
            is_modified_flag = tab_container_widget.property("is_modified_custom_flag") or False
        elif isinstance(tab_container_widget, WangEditor):
            is_modified_flag = tab_container_widget.isModified() if hasattr(tab_container_widget, 'isModified') else False
        else: 
            actual_editor_component = None
            if isinstance(tab_container_widget, TextEditor): actual_editor_component = tab_container_widget._editor
            elif isinstance(tab_container_widget, MarkdownEditorWidget): actual_editor_component = tab_container_widget.editor
            
            if actual_editor_component and hasattr(actual_editor_component, 'document') and \
               callable(actual_editor_component.document):
                doc = actual_editor_component.document()
                is_modified_flag = doc.isModified() if doc else False
        
        if modified is not None: is_modified_flag = modified

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
