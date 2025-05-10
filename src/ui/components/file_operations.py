import os
import sys # Added for sys.platform check
from PyQt6.QtWidgets import (QFileDialog, QMessageBox, QApplication, QTabWidget) # Ensuring QTabWidget is imported
from PyQt6.QtCore import QSignalBlocker, QTimer, QUrl # Added QTimer and QUrl
import shutil # For cleaning up resource directories

# Corrected relative imports
from ..atomic.editor.text_editor import TextEditor
from ..atomic.editor.wang_editor import WangEditor
from ..atomic.markdown_editor_widget import MarkdownEditorWidget
from ..views.pdf_viewer_view import PdfViewerView
from ..views.office_viewer_view import OfficeViewerWidget
from ..views.image_viewer_view import ImageViewWidget
from ..views.video_player_view import VideoPlayerWidget
# EditableHtmlPreviewWidget is now used inside HtmlViewContainer
# from ..views.editable_html_preview_widget import EditableHtmlPreviewWidget 
from ..composite.html_view_container import HtmlViewContainer, HTML_SKELETON # Import new container
from ..views.editable_html_preview_widget import EditableHtmlPreviewWidget # For type checking


class FileOperations:
    """处理MainWindow的文件操作功能"""

    def __init__(self, main_window, ui_manager, markdown_editor_widget_instance):
        self.main_window = main_window
        self.ui_manager = ui_manager
        self.untitled_counter = 0

    def new_file(self, file_type="text", workspace_path=None):
        """创建新文件"""
        editor_container = None # Renamed from editor to editor_container
        tab_name_suffix = ""
        if file_type == "html":
            editor_container = HtmlViewContainer(parent=self.main_window, 
                                                 initial_content=HTML_SKELETON, 
                                                 is_new_file=True,
                                                 main_window_ref=self.main_window)
            tab_name_suffix = ".html"
        elif file_type == "markdown":
            editor_container = MarkdownEditorWidget() # This remains a direct editor widget
            editor_container.clear_content()
            tab_name_suffix = ".md"
        else: # Default to text, now uses WangEditor as per user request
            editor_container = WangEditor() 
            editor_container.setHtml("") # Start with empty content, WangEditor will handle it
            tab_name_suffix = ".txt" # Keep .txt suffix

        self.untitled_counter += 1
        actual_tab_name = f"未命名-{self.untitled_counter}"
        
        editor_container.setProperty("untitled_name", f"{actual_tab_name}{tab_name_suffix}")
        editor_container.setProperty("file_path", None)
        editor_container.setProperty("is_new", True)
        if workspace_path:
            editor_container.setProperty("workspace_path", workspace_path)
        
        if isinstance(editor_container, WangEditor):
             if hasattr(self.main_window, 'on_editor_content_changed'):
                 QTimer.singleShot(0, lambda ed=editor_container: self.main_window.on_editor_content_changed(ed, initially_modified=False))
        elif isinstance(editor_container, HtmlViewContainer):
            editor_container.set_modified_status_on_current_editor(False)


        QTimer.singleShot(0, lambda ed=editor_container, name=actual_tab_name, ft=file_type: self._delayed_new_file_add_tab(ed, name, ft))
        self.main_window.statusBar.showMessage(f"正在创建新 {file_type.upper()} 文件...")

    def _delayed_new_file_add_tab(self, editor_widget, tab_name_to_add, file_type_for_status):
        current_active_group = self.ui_manager.get_active_editor_group()
        target_tab_widget = current_active_group.get_tab_widget() if current_active_group else self.main_window.tab_widget 

        if target_tab_widget is None: 
            QMessageBox.critical(self.main_window, "错误 (延迟后)", "无法获取目标标签页控件。")
            if editor_widget: editor_widget.deleteLater()
            return
        
        try:
            from PyQt6 import sip
            if sip.isdeleted(target_tab_widget):
                QMessageBox.critical(self.main_window, "错误 (延迟后)", "目标标签页控件已删除。")
                if editor_widget: editor_widget.deleteLater()
                return
        except Exception: pass 

        index = -1
        try:
            index = target_tab_widget.addTab(editor_widget, tab_name_to_add)
        except RuntimeError as e_addtab:
            QMessageBox.critical(self.main_window, "运行时错误", f"添加标签页 '{tab_name_to_add}' 时发生运行时错误: {e_addtab}")
            if editor_widget: editor_widget.deleteLater()
            return
            
        if index != -1:
            target_tab_widget.setCurrentIndex(index)
            
            actual_editor_part_to_focus = editor_widget
            if isinstance(editor_widget, MarkdownEditorWidget):
                actual_editor_part_to_focus = editor_widget.editor
            elif isinstance(editor_widget, WangEditor):
                actual_editor_part_to_focus = editor_widget
            elif isinstance(editor_widget, HtmlViewContainer): 
                actual_editor_part_to_focus = editor_widget 
            
            if actual_editor_part_to_focus:
                actual_editor_part_to_focus.setFocus()

            if isinstance(editor_widget, MarkdownEditorWidget): 
                if hasattr(actual_editor_part_to_focus, 'document') and callable(actual_editor_part_to_focus.document):
                    actual_editor_part_to_focus.document().setModified(False)
            elif isinstance(editor_widget, WangEditor):
                pass
            elif isinstance(editor_widget, HtmlViewContainer):
                pass
            elif hasattr(editor_widget, 'setModified'): 
                 editor_widget.setModified(False)

            self.main_window.statusBar.showMessage(f"已创建新 {file_type_for_status.upper()} 文件: '{tab_name_to_add}'")
            self.main_window.update_edit_actions_state(self.main_window.get_current_editor_widget())
        else:
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
            
            active_editor_group = self.ui_manager.get_active_editor_group()
            target_tab_widget = active_editor_group.get_tab_widget() if active_editor_group else self.main_window.tab_widget

            if target_tab_widget is None: 
                QMessageBox.critical(self.main_window, "错误", "无法找到用于打开文件的目标标签页控件。")
                return

            image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp']
            video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.webm', '.flv', '.wmv']

            editor_to_add = None
            opened_as_special_view = False

            if ext.lower() == '.pdf':
                self.ui_manager.open_pdf_preview(abs_file_path) 
                opened_as_special_view = True
            elif ext.lower() in image_extensions:
                editor_to_add = ImageViewWidget(self.main_window)
                if not editor_to_add.load_image(abs_file_path): editor_to_add = None
                opened_as_special_view = True
            elif ext.lower() in video_extensions:
                editor_to_add = VideoPlayerWidget(self.main_window)
                if not editor_to_add.load_video(abs_file_path): editor_to_add = None
                opened_as_special_view = True
            elif ext.lower() in ['.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt']:
                if sys.platform == 'win32':
                    msg_box = QMessageBox(self.main_window); msg_box.setWindowTitle("选择预览类型")
                    msg_box.setText(f"您希望如何预览 Office 文件 '{file_base_name}'？"); pdf_button = msg_box.addButton("PDF 预览", QMessageBox.ButtonRole.YesRole)
                    html_button = msg_box.addButton("HTML 预览", QMessageBox.ButtonRole.NoRole); cancel_button = msg_box.addButton("取消", QMessageBox.ButtonRole.RejectRole)
                    msg_box.setDefaultButton(pdf_button); msg_box.exec()
                    preview_format = None
                    if msg_box.clickedButton() == pdf_button: preview_format = 'pdf'
                    elif msg_box.clickedButton() == html_button: preview_format = 'html'
                    else: return
                    viewer_widget = OfficeViewerWidget(self.main_window)
                    if viewer_widget.loadFile(abs_file_path, preview_format=preview_format): editor_to_add = viewer_widget
                    else: viewer_widget.deleteLater()
                else: QMessageBox.information(self.main_window, "功能限制", "Office 文件预览功能目前仅在 Windows 系统上通过本地 Office 转换实现。")
                opened_as_special_view = True
            elif ext.lower() == '.html':
                try:
                    with open(abs_file_path, 'r', encoding='utf-8') as f: content = f.read()
                    editor_to_add = HtmlViewContainer(parent=self.main_window,
                                                      file_path=abs_file_path,
                                                      initial_content=content,
                                                      is_new_file=False,
                                                      main_window_ref=self.main_window)
                    opened_as_special_view = True
                except AttributeError as e_attr:
                    if "'connect'" in str(e_attr):
                        import traceback
                        tb_str = traceback.format_exc()
                        QMessageBox.critical(self.main_window, "HTML 打开 AttributeError", f"创建 HtmlViewContainer 时发生 'connect' 相关错误:\n{str(e_attr)}\n\nTraceback:\n{tb_str}")
                        editor_to_add = None # Ensure it's None so it doesn't proceed
                    else:
                        raise # Re-raise other AttributeErrors
                except Exception as e_html: # Catch other potential errors during HtmlViewContainer creation
                    import traceback
                    tb_str = traceback.format_exc()
                    QMessageBox.critical(self.main_window, "HTML 打开错误", f"创建 HtmlViewContainer 时发生错误:\n{str(e_html)}\n\nTraceback:\n{tb_str}")
                    editor_to_add = None
            elif ext.lower() in ['.md', '.markdown']:
                with open(abs_file_path, 'r', encoding='utf-8') as f: content = f.read()
                editor_to_add = MarkdownEditorWidget()
                editor_to_add.set_content(content)
            else: 
                try:
                    with open(abs_file_path, 'r', encoding='utf-8') as f: content = f.read()
                except UnicodeDecodeError:
                    with open(abs_file_path, 'r', encoding='gbk') as f: content = f.read() 
                
                editor_to_add = WangEditor()
                editor_to_add.setHtml(content) 
                if hasattr(editor_to_add, '_bridge') and hasattr(editor_to_add._bridge, 'contentChangedSignal'):
                     editor_to_add._bridge.contentChangedSignal.connect(
                         lambda _html_payload, editor=editor_to_add: self.main_window.on_editor_content_changed(editor)
                     )
                elif hasattr(editor_to_add, 'document_modified'): 
                    editor_to_add.document_modified.connect(
                        lambda _modified_status, editor=editor_to_add: self.main_window.on_editor_content_changed(editor) 
                    )
                QTimer.singleShot(0, lambda ed=editor_to_add: self.main_window.on_editor_content_changed(ed, initially_modified=False))

            if editor_to_add:
                editor_to_add.setProperty("file_path", abs_file_path)
                editor_to_add.setProperty("is_new", False)
                if workspace_path: editor_to_add.setProperty("workspace_path", workspace_path)
                
                QTimer.singleShot(0, lambda ed=editor_to_add, name=file_base_name, fp=file_path: self._delayed_add_opened_file_tab(ed, name, fp))

            elif not opened_as_special_view : 
                 QMessageBox.critical(self.main_window, "打开文件错误", f"无法创建编辑器或预览窗口对于文件: {file_path}")
        
        except Exception as e:
             QMessageBox.critical(self.main_window, "打开文件错误", f"打开文件 '{file_path}' 时发生未知错误:\n{str(e)}")

    def _delayed_add_opened_file_tab(self, editor_widget, tab_name_to_add, file_path_for_status):
        current_active_group = self.ui_manager.get_active_editor_group()
        target_tab_widget = current_active_group.get_tab_widget() if current_active_group else self.main_window.tab_widget 

        if target_tab_widget is None: 
            QMessageBox.critical(self.main_window, "错误 (延迟后)", "无法获取目标标签页控件 (打开文件)。")
            if editor_widget: editor_widget.deleteLater()
            return
        
        try:
            from PyQt6 import sip
            if sip.isdeleted(target_tab_widget):
                QMessageBox.critical(self.main_window, "错误 (延迟后)", "目标标签页控件已删除 (打开文件)。")
                if editor_widget: editor_widget.deleteLater()
                return
        except Exception: pass

        index = -1
        try:
            index = target_tab_widget.addTab(editor_widget, tab_name_to_add)
        except RuntimeError as e_addtab:
            QMessageBox.critical(self.main_window, "运行时错误", f"添加已打开文件标签页 '{tab_name_to_add}' 时发生运行时错误: {e_addtab}")
            if editor_widget: editor_widget.deleteLater()
            return
            
        if index != -1:
            target_tab_widget.setCurrentIndex(index)
            if hasattr(editor_widget, 'setFocus'): 
                editor_widget.setFocus()

            if isinstance(editor_widget, MarkdownEditorWidget):
                 if hasattr(editor_widget.editor, 'document') and callable(editor_widget.editor.document):
                    editor_widget.editor.document().setModified(False)

            if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar:
                self.main_window.statusBar.showMessage(f"已打开: {file_path_for_status}")
            self.main_window.update_edit_actions_state(self.main_window.get_current_editor_widget()) 
        else:
            QMessageBox.critical(self.main_window, "错误", f"无法添加已打开文件标签页 '{tab_name_to_add}'.")
            if editor_widget: editor_widget.deleteLater()

    def save_file(self) -> bool:
        active_editor_group = self.ui_manager.get_active_editor_group()
        current_tab_widget = active_editor_group.get_tab_widget() if active_editor_group else self.main_window.tab_widget
        if not current_tab_widget: return False
        
        current_tab_container = current_tab_widget.currentWidget()
        actual_editor_component = self.main_window.get_current_editor_widget() 

        if not current_tab_container: return False

        file_path = current_tab_container.property("file_path")
        is_new = current_tab_container.property("is_new")

        if is_new or not file_path:
            return self.save_file_as()
        else:
            try:
                content_to_save = ""
                if isinstance(current_tab_container, HtmlViewContainer): 
                    content_to_save = current_tab_container.get_content_for_saving()
                elif isinstance(current_tab_container, WangEditor):
                    content_to_save = current_tab_container.getHtml()
                elif isinstance(current_tab_container, MarkdownEditorWidget) and hasattr(actual_editor_component, 'toPlainText'):
                    content_to_save = actual_editor_component.toPlainText()
                else: 
                    QMessageBox.critical(self.main_window, "错误", f"无法获取编辑器内容进行保存 (类型: {type(current_tab_container).__name__})。")
                    return False

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content_to_save)
                
                if isinstance(current_tab_container, HtmlViewContainer):
                    current_tab_container.set_modified_status_on_current_editor(False)
                    current_tab_container.is_new_file = False 
                    current_tab_container.setProperty("is_new", False)
                elif isinstance(current_tab_container, WangEditor):
                    self.main_window.on_editor_content_changed(current_tab_container, initially_modified=False)
                elif hasattr(actual_editor_component, 'document') and callable(actual_editor_component.document): 
                    actual_editor_component.document().setModified(False)

                if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar:
                    self.main_window.statusBar.showMessage(f"已保存: {file_path}")
                self.main_window.update_tab_title(current_tab_container, False) 
                return True
            except Exception as e:
                QMessageBox.critical(self.main_window, "错误", f"无法保存文件 '{file_path}':\n{str(e)}")
                return False

    def save_file_as(self) -> bool:
        active_editor_group = self.ui_manager.get_active_editor_group()
        current_tab_widget = active_editor_group.get_tab_widget() if active_editor_group else self.main_window.tab_widget
        if not current_tab_widget: return False

        current_tab_container = current_tab_widget.currentWidget()
        if not current_tab_container: return False

        current_path = current_tab_container.property("file_path")
        untitled_name = current_tab_container.property("untitled_name") 
        workspace_path = current_tab_container.property("workspace_path")
        
        suggested_name = os.path.basename(current_path) if current_path else (untitled_name or f"未命名-{self.untitled_counter}.txt")
        default_dir = os.path.dirname(current_path) if current_path else (workspace_path or os.getcwd())

        default_filter = "文本文件 (*.txt)" 
        if isinstance(current_tab_container, HtmlViewContainer): 
            default_filter = "HTML文件 (*.html)"
        elif isinstance(current_tab_container, WangEditor):
            if untitled_name and untitled_name.lower().endswith(".txt"):
                default_filter = "文本文件 (*.txt)"
            else: 
                default_filter = "HTML文件 (*.html)" 
        elif isinstance(current_tab_container, MarkdownEditorWidget):
            default_filter = "Markdown文件 (*.md *.markdown)"
        
        filters = "HTML文件 (*.html);;Markdown文件 (*.md *.markdown);;文本文件 (*.txt);;所有文件 (*)"
        
        file_name, selected_filter = QFileDialog.getSaveFileName(
            self.main_window, "另存为", os.path.join(default_dir, suggested_name), filters, default_filter
        )

        if file_name:
            abs_file_path = os.path.abspath(file_name)
            try:
                content_to_save = ""
                actual_editor_component = self.main_window.get_current_editor_widget() 
                if isinstance(current_tab_container, HtmlViewContainer): 
                    content_to_save = current_tab_container.get_content_for_saving()
                elif isinstance(current_tab_container, WangEditor):
                    content_to_save = current_tab_container.getHtml()
                elif isinstance(current_tab_container, MarkdownEditorWidget) and hasattr(actual_editor_component, 'toPlainText'):
                    content_to_save = actual_editor_component.toPlainText()
                else:
                    QMessageBox.critical(self.main_window, "错误", f"无法获取编辑器内容进行另存为 (类型: {type(current_tab_container).__name__})。")
                    return False

                with open(abs_file_path, 'w', encoding='utf-8') as f: f.write(content_to_save)
                
                if isinstance(current_tab_container, HtmlViewContainer):
                    current_tab_container.set_file_path_and_name(abs_file_path, False)
                else: 
                    current_tab_container.setProperty("file_path", abs_file_path)
                    current_tab_container.setProperty("is_new", False)
                    current_tab_container.setProperty("untitled_name", None) 
                
                current_index = current_tab_widget.currentIndex()
                if current_index != -1: 
                    current_tab_widget.setTabText(current_index, os.path.basename(abs_file_path))
                
                if isinstance(current_tab_container, HtmlViewContainer):
                    current_tab_container.set_modified_status_on_current_editor(False)
                elif isinstance(current_tab_container, WangEditor):
                    self.main_window.on_editor_content_changed(current_tab_container, initially_modified=False)
                elif hasattr(actual_editor_component, 'document') and callable(actual_editor_component.document): 
                    actual_editor_component.document().setModified(False)
                
                self.main_window.update_window_title() 
                if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar:
                    self.main_window.statusBar.showMessage(f"已保存: {abs_file_path}")
                self.main_window.update_tab_title(current_tab_container, False)
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
        
        is_modified = False
        if isinstance(widget_in_tab, HtmlViewContainer): 
            is_modified = widget_in_tab.is_modified()
        elif isinstance(widget_in_tab, WangEditor):
            is_modified = widget_in_tab.property("is_modified_custom_flag") or \
                          (hasattr(widget_in_tab, 'isModified') and widget_in_tab.isModified())
        elif isinstance(widget_in_tab, MarkdownEditorWidget): 
            if widget_in_tab.editor.document(): is_modified = widget_in_tab.editor.document().isModified()
        
        if is_modified:
            current_tab_widget.setCurrentIndex(index)
            tab_name = current_tab_widget.tabText(index)
            ret = QMessageBox.warning(self.main_window, "关闭标签页", f"文档 '{tab_name}' 已被修改。\n是否保存更改？",
                                    QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
            if ret == QMessageBox.StandardButton.Save:
                if not self.save_file(): return False
            elif ret == QMessageBox.StandardButton.Cancel: return False

        if self.main_window.previous_editor == widget_in_tab:
             self.main_window.previous_editor = None
        
        # Cleanup resource directory if this tab was from a PDF to HTML conversion
        # Check if the widget_in_tab (which could be HtmlViewContainer) has 'resource_dir_path'
        resource_dir_path = widget_in_tab.property("resource_dir_path")
        pdf_source_path = widget_in_tab.property("pdf_source_path") # Usually set on the container by UIManager

        if resource_dir_path and os.path.isdir(resource_dir_path):
            try:
                shutil.rmtree(resource_dir_path)
                tab_display_name = widget_in_tab.property('untitled_name') or \
                                   (os.path.basename(pdf_source_path) if pdf_source_path else "Unknown Tab")
                print(f"DEBUG FileOperations: Cleaned up resource dir {resource_dir_path} for tab '{tab_display_name}'")
                if pdf_source_path and pdf_source_path in self.ui_manager.pdf_conversion_resource_dirs:
                    del self.ui_manager.pdf_conversion_resource_dirs[pdf_source_path]
            except Exception as e_shutil:
                print(f"DEBUG FileOperations: Error cleaning up resource dir {resource_dir_path}: {e_shutil}")

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
        while target_tab_widget.count() > 0: 
            if not self.close_tab(0): 
                return False 
        return True

    def add_editor_tab(self, content: str = "", file_path: str | None = None, file_type: str = "text", 
                       set_current: bool = True, untitled_name: str | None = None, 
                       target_tab_w: QTabWidget | None = None): 
        editor_container_to_add = None
        actual_editor_part_to_focus = None 
        tab_name_to_display = ""
        is_new_file_flag = file_path is None

        target_tab_w_resolved = target_tab_w or \
                               (self.ui_manager.get_active_editor_group().get_tab_widget() 
                                if self.ui_manager.get_active_editor_group() else self.main_window.tab_widget)

        if target_tab_w_resolved is None:
            QMessageBox.critical(self.main_window, "错误", "无法找到用于添加标签页的目标控件 (add_editor_tab)。")
            return None
        
        try:
            if file_type == "html":
                editor_container_to_add = HtmlViewContainer(parent=self.main_window, 
                                                            file_path=file_path, 
                                                            initial_content=content, 
                                                            is_new_file=is_new_file_flag,
                                                            main_window_ref=self.main_window)
                actual_editor_part_to_focus = editor_container_to_add 
            elif file_type == "markdown":
                editor_container_to_add = MarkdownEditorWidget()
                editor_container_to_add.set_content(content)
                actual_editor_part_to_focus = editor_container_to_add.editor
            else: # text
                editor_container_to_add = WangEditor()
                editor_container_to_add.setHtml(content)
                actual_editor_part_to_focus = editor_container_to_add

            if is_new_file_flag:
                tab_name_to_display = untitled_name or f"未命名-{self.untitled_counter}"
                editor_container_to_add.setProperty("untitled_name", tab_name_to_display) 
            else:
                tab_name_to_display = os.path.basename(file_path)
                editor_container_to_add.setProperty("file_path", os.path.abspath(file_path))

            editor_container_to_add.setProperty("is_new", is_new_file_flag)
            
            if isinstance(editor_container_to_add, MarkdownEditorWidget):
                if hasattr(actual_editor_part_to_focus, 'document') and callable(actual_editor_part_to_focus.document):
                    actual_editor_part_to_focus.document().setModified(False)
            elif isinstance(editor_container_to_add, WangEditor):
                 QTimer.singleShot(0, lambda ed=editor_container_to_add: self.main_window.on_editor_content_changed(ed, initially_modified=False))
            elif isinstance(editor_container_to_add, HtmlViewContainer):
                editor_container_to_add.set_modified_status_on_current_editor(False)

            index = target_tab_w_resolved.addTab(editor_container_to_add, tab_name_to_display)
            
            if set_current and index != -1:
                target_tab_w_resolved.setCurrentIndex(index)
                if actual_editor_part_to_focus: actual_editor_part_to_focus.setFocus()
                self.main_window.update_edit_actions_state(editor_container_to_add) 
            return editor_container_to_add
        except Exception as e:
            QMessageBox.critical(self.main_window, "错误", f"创建编辑器标签页时出错 (add_editor_tab): {e}")
            if editor_container_to_add and target_tab_w_resolved.indexOf(editor_container_to_add) != -1 :
                target_tab_w_resolved.removeTab(target_tab_w_resolved.indexOf(editor_container_to_add))
                editor_container_to_add.deleteLater()
            return None
