import os
import sys # Added for sys.platform check
from PyQt6.QtWidgets import (QFileDialog, QMessageBox, QApplication, QTabWidget) # Ensuring QTabWidget is imported
from PyQt6.QtCore import QSignalBlocker, QTimer # Added QTimer

# Corrected relative imports
from ..atomic.editor.text_editor import TextEditor
# from ..atomic.editor.html_editor import HtmlEditor # Will be replaced by WangEditor
from ..atomic.editor.wang_editor import WangEditor # Import WangEditor
from ..atomic.markdown_editor_widget import MarkdownEditorWidget
from ..views.pdf_viewer_view import PdfViewerView
from ..views.office_viewer_view import OfficeViewerWidget
from ..views.image_viewer_view import ImageViewWidget # Added
from ..views.video_player_view import VideoPlayerWidget # Added


class FileOperations:
    """处理MainWindow的文件操作功能"""

    def __init__(self, main_window, ui_manager, markdown_editor_widget_instance):
        self.main_window = main_window
        self.ui_manager = ui_manager
        self.untitled_counter = 0

    def new_file(self, file_type="text", workspace_path=None):
        """创建新文件"""
        editor = None
        tab_name_suffix = ""
        if file_type == "html":
            editor = WangEditor() # Use WangEditor
            tab_name_suffix = ".html"
        elif file_type == "markdown":
            editor = MarkdownEditorWidget()
            editor.clear_content()
            tab_name_suffix = ".md"
        else: # Default to text
            editor = TextEditor()
            tab_name_suffix = ".txt"

        self.untitled_counter += 1
        actual_tab_name = f"未命名-{self.untitled_counter}"
        full_untitled_name = f"{actual_tab_name}{tab_name_suffix}"
        
        editor.setProperty("untitled_name", full_untitled_name)
        editor.setProperty("file_path", None)
        editor.setProperty("is_new", True)
        if workspace_path:
            editor.setProperty("workspace_path", workspace_path)

        # Initial logging, but the core logic is deferred
        print(f"DEBUG: FileOperations.new_file (type: {file_type}) - Initial call. Editor created: {editor}")
        # The following lines for initial check of target_tab_widget are for debugging and can be removed later
        active_editor_group = self.ui_manager.get_active_editor_group()
        initial_target_tab_widget = active_editor_group.get_tab_widget() if active_editor_group else self.main_window.tab_widget
        print(f"DEBUG: FileOperations.new_file - Initial target_tab_widget: {initial_target_tab_widget} (type: {type(initial_target_tab_widget)})")
        if initial_target_tab_widget is not None:
            is_deleted_initial = False
            try:
                from PyQt6 import sip
                is_deleted_initial = sip.isdeleted(initial_target_tab_widget)
            except Exception: pass # Ignore error if sip is not available or fails
            print(f"DEBUG: FileOperations.new_file - Initial bool(target_tab_widget): {bool(initial_target_tab_widget)}, sip.isdeleted: {is_deleted_initial}")
        
        print(f"DEBUG: FileOperations.new_file - Scheduling _delayed_new_file_add_tab for '{actual_tab_name}'")
        # Pass editor, actual_tab_name, and file_type for status message
        QTimer.singleShot(0, lambda ed=editor, name=actual_tab_name, ft=file_type: self._delayed_new_file_add_tab(ed, name, ft))
        
        self.main_window.statusBar.showMessage(f"正在创建新 {file_type.upper()} 文件...")

    def _delayed_new_file_add_tab(self, editor_widget, tab_name_to_add, file_type_for_status):
        """
        Delayed logic to add the new file tab.
        Re-fetches the target_tab_widget in case its state has 'normalized'.
        """
        print(f"DEBUG: FileOperations._delayed_new_file_add_tab - Called for tab: '{tab_name_to_add}'")

        current_active_group = self.ui_manager.get_active_editor_group()
        if current_active_group:
            target_tab_widget = current_active_group.get_tab_widget()
            print(f"DEBUG: FileOperations._delayed_new_file_add_tab - Re-fetched target_tab_widget from group: {target_tab_widget} (type: {type(target_tab_widget)})")
        else: 
            target_tab_widget = self.main_window.tab_widget 
            print(f"WARNING DEBUG: FileOperations._delayed_new_file_add_tab - No active group, re-fetched target_tab_widget from main_window: {target_tab_widget} (type: {type(target_tab_widget)})")

        if target_tab_widget is not None:
            is_target_deleted_sip_delayed = False
            try:
                from PyQt6 import sip
                is_target_deleted_sip_delayed = sip.isdeleted(target_tab_widget)
            except Exception as e_sip_delayed:
                print(f"WARNING DEBUG: FileOperations._delayed_new_file_add_tab - Error checking sip.isdeleted: {e_sip_delayed}")
            
            print(f"DEBUG: FileOperations._delayed_new_file_add_tab - target_tab_widget Python object: {target_tab_widget}")
            print(f"DEBUG: FileOperations._delayed_new_file_add_tab - bool(target_tab_widget) is {bool(target_tab_widget)}") 
            print(f"DEBUG: FileOperations._delayed_new_file_add_tab - sip.isdeleted(target_tab_widget) is {is_target_deleted_sip_delayed}")
            
            # --- Aggressive fix: Proceed if Python object exists and C++ object is not deleted ---
            if target_tab_widget is not None and not is_target_deleted_sip_delayed:
                 print(f"DEBUG: FileOperations._delayed_new_file_add_tab - target_tab_widget seems usable (Python obj exists, C++ not deleted), proceeding to addTab. Current tab count: {target_tab_widget.count()}")
            elif not target_tab_widget: # Original check, now as a fallback log
                 print(f"WARNING DEBUG: FileOperations._delayed_new_file_add_tab - bool(target_tab_widget) is False, but attempting addTab anyway as C++ object might be valid.")
            # If target_tab_widget is None (Python object), the next 'if not target_tab_widget' will catch it.

        else: # target_tab_widget is Python None
            print("CRITICAL DEBUG: FileOperations._delayed_new_file_add_tab - target_tab_widget is Python None after re-fetch.")
            QMessageBox.critical(self.main_window, "错误 (延迟后)", "无法获取目标标签页控件 (Python object is None)。")
            if editor_widget: editor_widget.deleteLater()
            return

        # Final check based on Python object existence and sip.isdeleted status
        # We proceed if the Python object exists AND sip.isdeleted is False.
        # The bool(target_tab_widget) is logged but not used to abort if sip.isdeleted is False.
        
        can_proceed = False
        if target_tab_widget is not None:
            try:
                from PyQt6 import sip
                if not sip.isdeleted(target_tab_widget):
                    can_proceed = True
            except Exception: # If sip check fails, rely on bool() as a fallback, though it's problematic
                if target_tab_widget: # Fallback to bool() if sip fails
                    can_proceed = True
        
        if not can_proceed:
            QMessageBox.critical(self.main_window, "错误 (延迟后)", "目标标签页控件无效或已删除，无法添加新文件。")
            print(f"CRITICAL DEBUG: FileOperations._delayed_new_file_add_tab - Cannot proceed. target_tab_widget: {target_tab_widget}. Aborting.")
            if editor_widget: editor_widget.deleteLater()
            return

        # At this point, target_tab_widget is considered usable enough to attempt addTab
        print(f"DEBUG: FileOperations._delayed_new_file_add_tab - Proceeding to call addTab. Current tab count: {target_tab_widget.count()}")
        index = -1
        try:
            index = target_tab_widget.addTab(editor_widget, tab_name_to_add)
        except RuntimeError as e_addtab:
            print(f"CRITICAL ERROR: FileOperations._delayed_new_file_add_tab - RuntimeError during addTab: {e_addtab}")
            QMessageBox.critical(self.main_window, "运行时错误", f"添加标签页 '{tab_name_to_add}' 时发生运行时错误。")
            if editor_widget: editor_widget.deleteLater()
            return
            
        print(f"DEBUG: FileOperations._delayed_new_file_add_tab - addTab called. Returned index: {index}. New tab count: {target_tab_widget.count()}")
        
        if index != -1:
            target_tab_widget.setCurrentIndex(index)
            
            actual_editor_part_to_focus = editor_widget
            if isinstance(editor_widget, MarkdownEditorWidget):
                actual_editor_part_to_focus = editor_widget.editor
            elif isinstance(editor_widget, WangEditor): # Use WangEditor
                actual_editor_part_to_focus = editor_widget # WangEditor handles its own focus
            elif isinstance(editor_widget, TextEditor):
                actual_editor_part_to_focus = editor_widget._editor
            
            if actual_editor_part_to_focus:
                actual_editor_part_to_focus.setFocus()

            if hasattr(actual_editor_part_to_focus, 'document') and callable(actual_editor_part_to_focus.document):
                actual_editor_part_to_focus.document().setModified(False)
            elif hasattr(editor_widget, 'setModified'): 
                 editor_widget.setModified(False)

            self.main_window.statusBar.showMessage(f"已创建新 {file_type_for_status.upper()} 文件: '{tab_name_to_add}'")
            self.main_window.update_edit_actions_state(self.main_window.get_current_editor_widget())
        else:
            print(f"ERROR: FileOperations._delayed_new_file_add_tab - addTab failed to add '{tab_name_to_add}'. Index was -1.")
            QMessageBox.critical(self.main_window, "错误", f"无法添加新标签页 '{tab_name_to_add}'.")
            if editor_widget: editor_widget.deleteLater()

    def open_file_dialog(self, initial_dir=None, initial_path=None):
        if initial_path and os.path.exists(initial_path):
            self.open_file_from_path(initial_path)
            return

        start_dir = initial_dir or os.getcwd()
        file_name, _ = QFileDialog.getOpenFileName(
            self.main_window, "打开文件", start_dir,
            "Office 文件 (*.docx *.xlsx *.pptx);;HTML文件 (*.html);;Markdown文件 (*.md *.markdown);;文本文件 (*.txt);;PDF文件 (*.pdf);;所有文件 (*)"
        )
        if file_name:
            self.open_file_from_path(file_name)

    def open_file_from_path(self, file_path: str, workspace_path: str | None = None):
        abs_file_path = os.path.abspath(file_path)
        if self.ui_manager.is_file_open(abs_file_path): 
            self.ui_manager.focus_tab_by_filepath(abs_file_path) 
            if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar:
                self.main_window.statusBar.showMessage(f"切换到已打开文件: {file_path}")
            return

        try:
            _, ext = os.path.splitext(file_path)
            file_base_name = os.path.basename(file_path)
            
            # TODO: Apply QTimer delay logic similar to new_file if issues persist for opening files
            active_editor_group = self.ui_manager.get_active_editor_group()
            target_tab_widget = active_editor_group.get_tab_widget() if active_editor_group else self.main_window.tab_widget

            if not target_tab_widget: # This check might also be problematic
                QMessageBox.critical(self.main_window, "错误", "无法找到用于打开文件的目标标签页控件。")
                return

            # Define known file type extensions
            image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp']
            video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.webm', '.flv', '.wmv']

            if ext.lower() == '.pdf':
                self.ui_manager.open_pdf_preview(abs_file_path) 
                return
            
            elif ext.lower() in image_extensions:
                try:
                    image_viewer = ImageViewWidget(self.main_window) # Pass parent
                    if image_viewer.load_image(abs_file_path):
                        index = target_tab_widget.addTab(image_viewer, file_base_name)
                        target_tab_widget.setCurrentIndex(index)
                        image_viewer.setFocus() # Or appropriate focus handling
                        if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar:
                            self.main_window.statusBar.showMessage(f"已打开图片: {file_path}")
                    else:
                        image_viewer.deleteLater() # Cleanup if loading failed
                except Exception as e:
                    QMessageBox.critical(self.main_window, "图片预览错误", f"预览图片文件 '{file_path}' 时发生意外错误:\n{str(e)}")
                return

            elif ext.lower() in video_extensions:
                try:
                    video_player = VideoPlayerWidget(self.main_window) # Pass parent
                    if video_player.load_video(abs_file_path):
                        index = target_tab_widget.addTab(video_player, file_base_name)
                        target_tab_widget.setCurrentIndex(index)
                        video_player.setFocus() # Or appropriate focus handling
                        if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar:
                            self.main_window.statusBar.showMessage(f"已打开视频: {file_path}")
                    else:
                        video_player.deleteLater() # Cleanup if loading failed
                except Exception as e:
                    QMessageBox.critical(self.main_window, "视频播放错误", f"播放视频文件 '{file_path}' 时发生意外错误:\n{str(e)}")
                return
            
            elif ext.lower() in ['.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt']:
                if sys.platform == 'win32':
                    msg_box = QMessageBox(self.main_window)
                    msg_box.setWindowTitle("选择预览类型")
                    msg_box.setText(f"您希望如何预览 Office 文件 '{file_base_name}'？")
                    pdf_button = msg_box.addButton("PDF 预览", QMessageBox.ButtonRole.YesRole)
                    html_button = msg_box.addButton("HTML 预览", QMessageBox.ButtonRole.NoRole)
                    cancel_button = msg_box.addButton("取消", QMessageBox.ButtonRole.RejectRole)
                    msg_box.setDefaultButton(pdf_button)
                    msg_box.exec()

                    preview_format = None
                    if msg_box.clickedButton() == pdf_button: preview_format = 'pdf'
                    elif msg_box.clickedButton() == html_button: preview_format = 'html'
                    else: return

                    try:
                        viewer_widget = OfficeViewerWidget(self.main_window)
                        if viewer_widget.loadFile(abs_file_path, preview_format=preview_format):
                            tab_title_suffix = "(PDF预览)" if preview_format == 'pdf' else "(HTML预览)"
                            tab_name = os.path.basename(abs_file_path) + f" {tab_title_suffix}"
                            
                            index = target_tab_widget.addTab(viewer_widget, tab_name)
                            target_tab_widget.setCurrentIndex(index)
                            viewer_widget.setProperty("original_office_file_path", abs_file_path)
                            viewer_widget.setFocus()
                            if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar:
                                self.main_window.statusBar.showMessage(f"已打开 Office 文件 {tab_title_suffix}: {file_path}")
                        else:
                            viewer_widget.deleteLater()
                    except Exception as e:
                        QMessageBox.critical(self.main_window, "Office 预览错误", f"预览 Office 文件 '{file_path}' 时发生意外错误:\n{str(e)}")
                else:
                    QMessageBox.information(self.main_window, "功能限制", "Office 文件预览功能目前仅在 Windows 系统上通过本地 Office 转换实现。")
                return

            elif ext.lower() == '.html':
                try:
                    with open(abs_file_path, 'r', encoding='utf-8') as f: content = f.read()
                    self.add_editor_tab(content=content, file_path=abs_file_path, file_type='html', set_current=True, target_tab_w=target_tab_widget)
                except Exception as e:
                    QMessageBox.critical(self.main_window, "错误", f"无法打开HTML文件 '{file_path}':\n{str(e)}")
                return
            
            elif ext.lower() in ['.md', '.markdown']:
                try:
                    with open(abs_file_path, 'r', encoding='utf-8') as f: content = f.read()
                    self.add_editor_tab(content=content, file_path=abs_file_path, file_type='markdown', set_current=True, target_tab_w=target_tab_widget)
                except Exception as e:
                    QMessageBox.critical(self.main_window, "错误", f"无法打开Markdown文件 '{file_path}':\n{str(e)}")
                return
            
            else: # Assume text file
                try:
                    with open(abs_file_path, 'r', encoding='utf-8') as f: content = f.read()
                except UnicodeDecodeError:
                    try:
                        with open(abs_file_path, 'r', encoding='gbk') as f: content = f.read()
                    except Exception as e_gbk:
                        QMessageBox.critical(self.main_window, "错误", f"无法以 UTF-8 或 GBK 打开文件 '{file_path}':\n{e_gbk}")
                        return
                except Exception as e_utf8:
                    QMessageBox.critical(self.main_window, "错误", f"无法打开文本文件 '{file_path}':\n{e_utf8}")
                    return
                
                editor_tab_container = self.add_editor_tab(content=content, file_path=abs_file_path, file_type='text', set_current=True, target_tab_w=target_tab_widget)
                if editor_tab_container and workspace_path:
                    editor_tab_container.setProperty("workspace_path", workspace_path)

            if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar:
                self.main_window.statusBar.showMessage(f"已打开: {file_path}")

        except Exception as e:
             QMessageBox.critical(self.main_window, "打开文件错误", f"打开文件 '{file_path}' 时发生未知错误:\n{str(e)}")

    def save_file(self) -> bool:
        active_editor_group = self.ui_manager.get_active_editor_group()
        current_tab_widget = active_editor_group.get_tab_widget() if active_editor_group else self.main_window.tab_widget
        if not current_tab_widget: return False
        
        current_tab_container = current_tab_widget.currentWidget()
        actual_editor_component = self.main_window.get_current_editor_widget() 

        if not actual_editor_component or not current_tab_container: return False

        file_path = current_tab_container.property("file_path")
        is_new = current_tab_container.property("is_new")

        if is_new or not file_path:
            return self.save_file_as()
        else:
            try:
                content_to_save = actual_editor_component.toPlainText()
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content_to_save)
                if hasattr(actual_editor_component, 'document'):
                    actual_editor_component.document().setModified(False)
                
                if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar:
                    self.main_window.statusBar.showMessage(f"已保存: {file_path}")
                self.main_window.update_tab_title(False) 
                return True
            except Exception as e:
                QMessageBox.critical(self.main_window, "错误", f"无法保存文件 '{file_path}':\n{str(e)}")
                return False

    def save_file_as(self) -> bool:
        active_editor_group = self.ui_manager.get_active_editor_group()
        current_tab_widget = active_editor_group.get_tab_widget() if active_editor_group else self.main_window.tab_widget
        if not current_tab_widget: return False

        current_tab_container = current_tab_widget.currentWidget()
        actual_editor_component = self.main_window.get_current_editor_widget()
        
        if not actual_editor_component or not current_tab_container: return False

        current_path = current_tab_container.property("file_path")
        untitled_name = current_tab_container.property("untitled_name")
        workspace_path = current_tab_container.property("workspace_path")
        
        suggested_name = os.path.basename(current_path) if current_path else (untitled_name or f"未命名-{self.untitled_counter}")
        default_dir = os.path.dirname(current_path) if current_path else (workspace_path or os.getcwd())

        filters = "HTML文件 (*.html);;Markdown文件 (*.md *.markdown);;文本文件 (*.txt);;所有文件 (*)"
        default_filter = "文本文件 (*.txt)"
        if isinstance(current_tab_container, WangEditor): default_filter = "HTML文件 (*.html)" # Use WangEditor
        elif isinstance(current_tab_container, MarkdownEditorWidget): default_filter = "Markdown文件 (*.md *.markdown)"

        file_name, selected_filter = QFileDialog.getSaveFileName(
            self.main_window, "另存为", os.path.join(default_dir, suggested_name), filters, default_filter
        )

        if file_name:
            abs_file_path = os.path.abspath(file_name)
            _, current_ext = os.path.splitext(abs_file_path)
            if not current_ext:
                if "HTML" in selected_filter: abs_file_path += ".html"
                elif "Markdown" in selected_filter: abs_file_path += ".md"
                elif "文本文件" in selected_filter: abs_file_path += ".txt"
            
            try:
                current_tab_container.setProperty("file_path", abs_file_path)
                current_tab_container.setProperty("is_new", False)
                current_tab_container.setProperty("untitled_name", None)
                
                current_index = current_tab_widget.currentIndex()
                if current_index != -1: 
                    current_tab_widget.setTabText(current_index, os.path.basename(abs_file_path))
                self.main_window.update_window_title() 
                
                content_to_save = actual_editor_component.toPlainText()
                with open(abs_file_path, 'w', encoding='utf-8') as f: f.write(content_to_save)
                if hasattr(actual_editor_component, 'document'):
                    actual_editor_component.document().setModified(False)
                
                if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar:
                    self.main_window.statusBar.showMessage(f"已保存: {abs_file_path}")
                self.main_window.update_tab_title(False)
                return True
            except Exception as e:
                QMessageBox.critical(self.main_window, "错误", f"无法另存为文件 '{abs_file_path}':\n{str(e)}")
        return False

    def close_tab(self, index): 
        active_editor_group = self.ui_manager.get_active_editor_group()
        current_tab_widget = active_editor_group.get_tab_widget() if active_editor_group else self.main_window.tab_widget
        if not current_tab_widget: return False
        if index < 0 or index >= current_tab_widget.count(): return False

        widget_in_tab = current_tab_widget.widget(index)
        
        editor_component = None 
        if isinstance(widget_in_tab, TextEditor): editor_component = widget_in_tab._editor
        elif isinstance(widget_in_tab, WangEditor): editor_component = widget_in_tab # Use WangEditor, editor_component is the widget itself
        elif isinstance(widget_in_tab, MarkdownEditorWidget): editor_component = widget_in_tab.editor
        else: editor_component = widget_in_tab 

        is_modified = False
        if hasattr(editor_component, 'document') and callable(editor_component.document):
            doc = editor_component.document()
            if doc: is_modified = doc.isModified()
        elif hasattr(widget_in_tab, 'isModified') and callable(widget_in_tab.isModified):
            is_modified = widget_in_tab.isModified()

        if is_modified:
            current_tab_widget.setCurrentIndex(index)
            tab_name = current_tab_widget.tabText(index)
            ret = QMessageBox.warning(self.main_window, "关闭标签页", f"文档 '{tab_name}' 已被修改。\n是否保存更改？",
                                    QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
            if ret == QMessageBox.StandardButton.Save:
                if not self.save_file(): return False
            elif ret == QMessageBox.StandardButton.Cancel: return False

        if self.main_window.previous_editor == editor_component:
             self.main_window.previous_editor = None

        current_tab_widget.removeTab(index)
        if hasattr(widget_in_tab, 'cleanup'): widget_in_tab.cleanup()
        widget_in_tab.deleteLater()

        if current_tab_widget.count() == 0:
            current_workspace = self.main_window.current_workspace_path
            self.new_file(workspace_path=current_workspace) 

        new_current_editor_widget = self.main_window.get_current_editor_widget()
        self.main_window.update_edit_actions_state(new_current_editor_widget)
        return True

    def close_all_tabs(self) -> bool:
        target_tab_widget = self.main_window.tab_widget 
        if not target_tab_widget: return True 

        for i in range(target_tab_widget.count() - 1, -1, -1):
            if not self.close_tab(i): 
                return False 
        return True

    def add_editor_tab(self, content: str = "", file_path: str | None = None, file_type: str = "text", 
                       set_current: bool = True, untitled_name: str | None = None, 
                       target_tab_w: QTabWidget | None = None): 
        editor_container = None
        actual_editor_part = None 
        tab_name = ""
        is_new = file_path is None

        print(f"DEBUG: FileOperations.add_editor_tab - Called with file_type: '{file_type}', file_path: '{file_path}', title_hint: '{untitled_name}'")
        if target_tab_w is None:
            print("DEBUG: FileOperations.add_editor_tab - target_tab_w is None, determining from UIManager.")
            active_editor_group = self.ui_manager.get_active_editor_group()
            if active_editor_group:
                print(f"DEBUG: FileOperations.add_editor_tab - Active editor group found: {active_editor_group}")
                target_tab_widget = active_editor_group.get_tab_widget()
                print(f"DEBUG: FileOperations.add_editor_tab - Target tab widget from group: {target_tab_widget} (type: {type(target_tab_widget)})")
            else:
                print("DEBUG: FileOperations.add_editor_tab - No active editor group, falling back to main_window.tab_widget.")
                target_tab_widget = self.main_window.tab_widget
                print(f"DEBUG: FileOperations.add_editor_tab - Target tab widget from main_window: {target_tab_widget} (type: {type(target_tab_widget)})")
        else:
            target_tab_widget = target_tab_w
            print(f"DEBUG: FileOperations.add_editor_tab - Using provided target_tab_w: {target_tab_widget} (type: {type(target_tab_widget)})")

        if not target_tab_widget:
            QMessageBox.critical(self.main_window, "错误", "无法找到用于添加标签页的目标控件。")
            print("CRITICAL DEBUG: FileOperations.add_editor_tab - target_tab_widget is None or False, cannot add tab.")
            return None
        
        try:
            from PyQt6 import sip
            is_target_deleted = sip.isdeleted(target_tab_widget)
            print(f"DEBUG: FileOperations.add_editor_tab - sip.isdeleted(target_tab_widget: {id(target_tab_widget)}) is {is_target_deleted}")
            if is_target_deleted:
                 QMessageBox.critical(self.main_window, "错误", "目标标签页控件的C++对象已删除，无法添加新标签。")
                 print(f"CRITICAL DEBUG: FileOperations.add_editor_tab - target_tab_widget (id: {id(target_tab_widget)}) C++ object is deleted.")
                 return None
        except Exception as e_sip_check:
            print(f"WARNING DEBUG: FileOperations.add_editor_tab - Error checking sip.isdeleted for target_tab_widget: {e_sip_check}")

        try:
            if file_type == "html":
                editor_container = WangEditor() # Use WangEditor
                editor_container.setHtml(content)
                actual_editor_part = editor_container # WangEditor itself or its web_view for focus
            elif file_type == "markdown":
                editor_container = MarkdownEditorWidget()
                editor_container.set_content(content)
                actual_editor_part = editor_container.editor
            else: 
                editor_container = TextEditor()
                with QSignalBlocker(editor_container.document()): editor_container.setPlainText(content)
                actual_editor_part = editor_container._editor

            if is_new:
                tab_name = untitled_name or f"未命名-{self.untitled_counter}"
                editor_container.setProperty("untitled_name", tab_name) 
            else:
                tab_name = os.path.basename(file_path)
                editor_container.setProperty("file_path", os.path.abspath(file_path))

            editor_container.setProperty("is_new", is_new)
            
            if hasattr(actual_editor_part, 'document') and callable(actual_editor_part.document):
                actual_editor_part.document().setModified(False)
            elif hasattr(editor_container, 'setModified') and callable(editor_container.setModified):
                 editor_container.setModified(False)

            print(f"DEBUG: FileOperations.add_editor_tab - About to call target_tab_widget.addTab() with widget: {editor_container}, title: '{tab_name}'")
            initial_tab_count = target_tab_widget.count()
            index = target_tab_widget.addTab(editor_container, tab_name)
            new_tab_count = target_tab_widget.count()
            print(f"DEBUG: FileOperations.add_editor_tab - addTab called. Returned index: {index}. Tab count changed from {initial_tab_count} to {new_tab_count}.")
            
            if index == -1 or new_tab_count == initial_tab_count:
                 print(f"WARNING DEBUG: FileOperations.add_editor_tab - addTab might have failed silently. Index: {index}, Count change: {initial_tab_count} -> {new_tab_count}")

            if set_current:
                target_tab_widget.setCurrentIndex(index)
                if actual_editor_part: actual_editor_part.setFocus()

            if set_current:
                 self.main_window.update_edit_actions_state(actual_editor_part)
            return editor_container
        except Exception as e:
            QMessageBox.critical(self.main_window, "错误", f"创建编辑器标签页时出错: {e}")
            if editor_container and 'index' in locals() and index < target_tab_widget.count() and target_tab_widget.widget(index) == editor_container:
                target_tab_widget.removeTab(index)
                editor_container.deleteLater()
            return None
