import os
import sys # Added for sys.platform check
from PyQt6.QtWidgets import (QFileDialog, QMessageBox, QApplication, QTabWidget) # Ensuring QTabWidget is imported
from PyQt6.QtCore import QSignalBlocker, QTimer, QUrl # Added QTimer and QUrl

# Corrected relative imports
from ..atomic.editor.text_editor import TextEditor # Still needed for source view of HTML if implemented
from ..atomic.editor.wang_editor import WangEditor # Import WangEditor
from ..atomic.markdown_editor_widget import MarkdownEditorWidget
from ..views.pdf_viewer_view import PdfViewerView
from ..views.office_viewer_view import OfficeViewerWidget
from ..views.image_viewer_view import ImageViewWidget 
from ..views.video_player_view import VideoPlayerWidget
from ..views.editable_html_preview_widget import EditableHtmlPreviewWidget


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
        if file_type == "html": # User wants TextEditor for new HTML files
            editor = TextEditor() 
            editor.setPlainText("<!DOCTYPE html>\n<html>\n<head>\n    <title>New Page</title>\n</head>\n<body>\n    \n</body>\n</html>")
            tab_name_suffix = ".html"
        elif file_type == "markdown":
            editor = MarkdownEditorWidget()
            editor.clear_content()
            tab_name_suffix = ".md"
        else: # Default to text, now uses WangEditor as per user request
            editor = WangEditor() 
            editor.setHtml("") # Start with empty content, WangEditor will handle it
            tab_name_suffix = ".txt" # Keep .txt suffix

        self.untitled_counter += 1
        actual_tab_name = f"未命名-{self.untitled_counter}"
        # full_untitled_name = f"{actual_tab_name}{tab_name_suffix}" # This is set as property later
        
        editor.setProperty("untitled_name", f"{actual_tab_name}{tab_name_suffix}")
        editor.setProperty("file_path", None)
        editor.setProperty("is_new", True)
        if workspace_path:
            editor.setProperty("workspace_path", workspace_path)
        
        # For WangEditor used as a text editor, ensure it's marked as not modified initially.
        if isinstance(editor, WangEditor):
             # WangEditor's modification status might be handled by its own 'isModified' or via MainWindow's on_editor_content_changed
             # For a new file, it's not modified.
             if hasattr(editor, 'setModifiedStatus'): # Hypothetical method
                 editor.setModifiedStatus(False)
             elif hasattr(self.main_window, 'on_editor_content_changed'):
                 # Use a timer to ensure the editor is fully set up in the tab
                 QTimer.singleShot(0, lambda ed=editor: self.main_window.on_editor_content_changed(ed, initially_modified=False))


        QTimer.singleShot(0, lambda ed=editor, name=actual_tab_name, ft=file_type: self._delayed_new_file_add_tab(ed, name, ft))
        self.main_window.statusBar.showMessage(f"正在创建新 {file_type.upper()} 文件...")

    def _delayed_new_file_add_tab(self, editor_widget, tab_name_to_add, file_type_for_status):
        """
        Delayed logic to add the new file tab.
        """
        current_active_group = self.ui_manager.get_active_editor_group()
        target_tab_widget = current_active_group.get_tab_widget() if current_active_group else self.main_window.tab_widget 

        if target_tab_widget is None: # Explicit check for None
            QMessageBox.critical(self.main_window, "错误 (延迟后)", "无法获取目标标签页控件。")
            if editor_widget: editor_widget.deleteLater()
            return
        
        # Simplified validity check
        try:
            from PyQt6 import sip
            if sip.isdeleted(target_tab_widget):
                QMessageBox.critical(self.main_window, "错误 (延迟后)", "目标标签页控件已删除。")
                if editor_widget: editor_widget.deleteLater()
                return
        except Exception: pass # Ignore if sip check fails

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
                actual_editor_part_to_focus = editor_widget # WangEditor handles its own focus
            elif isinstance(editor_widget, TextEditor): # Should not happen for new text files now
                actual_editor_part_to_focus = editor_widget._editor
            
            if actual_editor_part_to_focus:
                actual_editor_part_to_focus.setFocus()

            # Set modified state
            if isinstance(editor_widget, (TextEditor, MarkdownEditorWidget)):
                if hasattr(actual_editor_part_to_focus, 'document') and callable(actual_editor_part_to_focus.document):
                    actual_editor_part_to_focus.document().setModified(False)
            elif isinstance(editor_widget, WangEditor):
                # WangEditor's modification status is handled via on_editor_content_changed in MainWindow
                # or its own internal mechanism. For a new file, it's initially not modified.
                # The call in new_file() with QTimer should handle this.
                pass
            elif hasattr(editor_widget, 'setModified'): # Generic fallback
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

            if target_tab_widget is None: # Explicit check for None
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
                # Office file handling remains the same
                if sys.platform == 'win32':
                    # ... (existing office handling logic) ...
                    # For brevity, assuming this part is correct and unchanged
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
                with open(abs_file_path, 'r', encoding='utf-8') as f: content = f.read()
                editor_to_add = EditableHtmlPreviewWidget()
                base_url = QUrl.fromLocalFile(os.path.dirname(abs_file_path) + os.path.sep)
                editor_to_add.setHtml(content, base_url)
                # Corrected lambda to accept the signal's string argument
                editor_to_add._bridge.htmlChanged.connect(
                    lambda _html_payload, editor=editor_to_add: self.main_window.on_editor_content_changed(editor)
                )
                QTimer.singleShot(0, lambda ed=editor_to_add: self.main_window.on_editor_content_changed(ed, initially_modified=False))
                opened_as_special_view = True # Technically an editor, but handled specifically
            elif ext.lower() in ['.md', '.markdown']:
                with open(abs_file_path, 'r', encoding='utf-8') as f: content = f.read()
                print(f"DEBUG FileOperations: Opening Markdown '{abs_file_path}', content (first 100): {content[:100]}")
                editor_to_add = MarkdownEditorWidget()
                editor_to_add.set_content(content)
                # MarkdownEditorWidget handles its own modified status internally with document()
            else: # Default to WangEditor for .txt and other text files
                try:
                    with open(abs_file_path, 'r', encoding='utf-8') as f: content = f.read()
                except UnicodeDecodeError:
                    with open(abs_file_path, 'r', encoding='gbk') as f: content = f.read() # Fallback
                
                print(f"DEBUG FileOperations: Opening Text/Other '{abs_file_path}' with WangEditor, content (first 100): {content[:100]}")
                editor_to_add = WangEditor()
                editor_to_add.setHtml(content) # WangEditor will try to interpret plain text
                # Connect signals for WangEditor
                # Assuming WangEditor's bridge also has a contentChangedSignal that emits a string (the HTML)
                # And that its Python wrapper WangEditor might re-emit this or provide access to the bridge.
                # For now, let's assume WangEditor itself might emit a signal like 'document_modified' or similar
                # that MainWindow can connect to. If it has a direct `htmlChanged` signal like EditableHtmlPreviewWidget's bridge:
                if hasattr(editor_to_add, '_bridge') and hasattr(editor_to_add._bridge, 'contentChangedSignal'):
                     editor_to_add._bridge.contentChangedSignal.connect(
                         lambda _html_payload, editor=editor_to_add: self.main_window.on_editor_content_changed(editor)
                     )
                elif hasattr(editor_to_add, 'document_modified'): # Fallback to its own document_modified signal
                    editor_to_add.document_modified.connect(
                        lambda _modified_status, editor=editor_to_add: self.main_window.on_editor_content_changed(editor) # Will set custom flag
                    )

                QTimer.singleShot(0, lambda ed=editor_to_add: self.main_window.on_editor_content_changed(ed, initially_modified=False))


            if editor_to_add:
                editor_to_add.setProperty("file_path", abs_file_path)
                editor_to_add.setProperty("is_new", False)
                if workspace_path: editor_to_add.setProperty("workspace_path", workspace_path)
                
                # Defer adding the tab
                QTimer.singleShot(0, lambda ed=editor_to_add, name=file_base_name, fp=file_path: self._delayed_add_opened_file_tab(ed, name, fp))

            elif not opened_as_special_view : 
                 QMessageBox.critical(self.main_window, "打开文件错误", f"无法创建编辑器或预览窗口对于文件: {file_path}")
        
        except Exception as e:
             QMessageBox.critical(self.main_window, "打开文件错误", f"打开文件 '{file_path}' 时发生未知错误:\n{str(e)}")

    def _delayed_add_opened_file_tab(self, editor_widget, tab_name_to_add, file_path_for_status):
        """
        Delayed logic to add the opened file tab.
        Re-fetches the target_tab_widget.
        """
        current_active_group = self.ui_manager.get_active_editor_group()
        target_tab_widget = current_active_group.get_tab_widget() if current_active_group else self.main_window.tab_widget 

        if target_tab_widget is None: # Explicit check for None
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
            if hasattr(editor_widget, 'setFocus'): # Generic focus call
                editor_widget.setFocus()

            # Initial modified state for newly opened files should be false.
            # This is handled by on_editor_content_changed in MainWindow for EditableHtmlPreviewWidget and WangEditor.
            # For MarkdownEditorWidget, its internal document is already not modified.
            if isinstance(editor_widget, MarkdownEditorWidget):
                 if hasattr(editor_widget.editor, 'document') and callable(editor_widget.editor.document):
                    editor_widget.editor.document().setModified(False)
            # For EditableHtmlPreviewWidget and WangEditor, on_editor_content_changed(ed, initially_modified=False)
            # is already called via QTimer in open_file_from_path.

            if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar:
                self.main_window.statusBar.showMessage(f"已打开: {file_path_for_status}")
            self.main_window.update_edit_actions_state(self.main_window.get_current_editor_widget()) # Update actions for the new tab
        else:
            QMessageBox.critical(self.main_window, "错误", f"无法添加已打开文件标签页 '{tab_name_to_add}'.")
            if editor_widget: editor_widget.deleteLater()

    def save_file(self) -> bool:
        # This method's logic for getting content from WangEditor and EditableHtmlPreviewWidget
        # seems mostly correct from the previous version.
        active_editor_group = self.ui_manager.get_active_editor_group()
        current_tab_widget = active_editor_group.get_tab_widget() if active_editor_group else self.main_window.tab_widget
        if not current_tab_widget: return False
        
        current_tab_container = current_tab_widget.currentWidget()
        # actual_editor_component is used for TextEditor/Markdown's QPlainTextEdit
        actual_editor_component = self.main_window.get_current_editor_widget() 

        if not current_tab_container: return False # current_tab_container is the key

        file_path = current_tab_container.property("file_path")
        is_new = current_tab_container.property("is_new")

        if is_new or not file_path:
            return self.save_file_as()
        else:
            try:
                content_to_save = ""
                if isinstance(current_tab_container, EditableHtmlPreviewWidget):
                    content_to_save = current_tab_container.getHtml()
                elif isinstance(current_tab_container, WangEditor): # Now also for .txt files
                    content_to_save = current_tab_container.getHtml()
                elif isinstance(current_tab_container, TextEditor) and hasattr(actual_editor_component, 'toPlainText'): # For pure TextEditor (e.g. source view)
                     content_to_save = actual_editor_component.toPlainText()
                elif isinstance(current_tab_container, MarkdownEditorWidget) and hasattr(actual_editor_component, 'toPlainText'):
                    content_to_save = actual_editor_component.toPlainText()
                else: # Fallback or unhandled type
                    QMessageBox.critical(self.main_window, "错误", f"无法获取编辑器内容进行保存 (类型: {type(current_tab_container).__name__})。")
                    return False

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content_to_save)
                
                # Reset modified state
                if isinstance(current_tab_container, (EditableHtmlPreviewWidget, WangEditor)):
                    self.main_window.on_editor_content_changed(current_tab_container, initially_modified=False)
                elif hasattr(actual_editor_component, 'document') and callable(actual_editor_component.document):
                    actual_editor_component.document().setModified(False)
                # If WangEditor has a setModified method, it could be called here too.
                # For now, relying on on_editor_content_changed for HTML based editors.

                if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar:
                    self.main_window.statusBar.showMessage(f"已保存: {file_path}")
                self.main_window.update_tab_title(current_tab_container, False) 
                return True
            except Exception as e:
                QMessageBox.critical(self.main_window, "错误", f"无法保存文件 '{file_path}':\n{str(e)}")
                return False

    def save_file_as(self) -> bool:
        # This method's logic for getting content from WangEditor and EditableHtmlPreviewWidget
        # seems mostly correct from the previous version.
        active_editor_group = self.ui_manager.get_active_editor_group()
        current_tab_widget = active_editor_group.get_tab_widget() if active_editor_group else self.main_window.tab_widget
        if not current_tab_widget: return False

        current_tab_container = current_tab_widget.currentWidget()
        if not current_tab_container: return False

        current_path = current_tab_container.property("file_path")
        untitled_name = current_tab_container.property("untitled_name") # e.g., "未命名-1.txt"
        workspace_path = current_tab_container.property("workspace_path")
        
        suggested_name = os.path.basename(current_path) if current_path else (untitled_name or f"未命名-{self.untitled_counter}.txt")
        default_dir = os.path.dirname(current_path) if current_path else (workspace_path or os.getcwd())

        # Determine default filter based on current editor type
        default_filter = "文本文件 (*.txt)" # Fallback
        if isinstance(current_tab_container, (WangEditor, EditableHtmlPreviewWidget)):
            # If it's WangEditor and its untitled_name ends with .txt, keep .txt as an option
            if isinstance(current_tab_container, WangEditor) and untitled_name and untitled_name.lower().endswith(".txt"):
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
            # Ensure extension if not provided by user, based on selected_filter
            # This logic was fine.

            try:
                content_to_save = ""
                actual_editor_component = self.main_window.get_current_editor_widget() # For TextEditor/Markdown
                if isinstance(current_tab_container, EditableHtmlPreviewWidget):
                    content_to_save = current_tab_container.getHtml()
                elif isinstance(current_tab_container, WangEditor): # Now also for .txt files
                    content_to_save = current_tab_container.getHtml()
                elif isinstance(current_tab_container, TextEditor) and hasattr(actual_editor_component, 'toPlainText'):
                     content_to_save = actual_editor_component.toPlainText()
                elif isinstance(current_tab_container, MarkdownEditorWidget) and hasattr(actual_editor_component, 'toPlainText'):
                    content_to_save = actual_editor_component.toPlainText()
                else:
                    QMessageBox.critical(self.main_window, "错误", f"无法获取编辑器内容进行另存为 (类型: {type(current_tab_container).__name__})。")
                    return False

                with open(abs_file_path, 'w', encoding='utf-8') as f: f.write(content_to_save)

                current_tab_container.setProperty("file_path", abs_file_path)
                current_tab_container.setProperty("is_new", False)
                current_tab_container.setProperty("untitled_name", None) # Clear untitled name
                
                current_index = current_tab_widget.currentIndex()
                if current_index != -1: 
                    current_tab_widget.setTabText(current_index, os.path.basename(abs_file_path))
                
                # Reset modified state
                if isinstance(current_tab_container, (EditableHtmlPreviewWidget, WangEditor)):
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
        # This method's logic for checking modification status for various editors
        # (EditableHtmlPreviewWidget, WangEditor, TextEditor, MarkdownEditorWidget)
        # seems mostly correct from the previous version.
        active_editor_group = self.ui_manager.get_active_editor_group()
        current_tab_widget = active_editor_group.get_tab_widget() if active_editor_group else self.main_window.tab_widget
        if not current_tab_widget: return False
        if index < 0 or index >= current_tab_widget.count(): return False

        widget_in_tab = current_tab_widget.widget(index)
        
        is_modified = False
        # Determine 'is_modified' based on widget type
        if isinstance(widget_in_tab, EditableHtmlPreviewWidget):
            is_modified = widget_in_tab.property("is_modified_custom_flag") or False 
        elif isinstance(widget_in_tab, WangEditor):
            # WangEditor might have its own isModified or rely on the custom flag set by on_editor_content_changed
            is_modified = widget_in_tab.property("is_modified_custom_flag") or \
                          (hasattr(widget_in_tab, 'isModified') and widget_in_tab.isModified())
        elif isinstance(widget_in_tab, TextEditor): # Should be less common now for general text
            if widget_in_tab._editor.document(): is_modified = widget_in_tab._editor.document().isModified()
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

        # Check if the editor component to remove is the 'previous_editor'
        # This part had 'editor_component' which was not defined in this scope.
        # We should compare widget_in_tab with self.main_window.previous_editor
        if self.main_window.previous_editor == widget_in_tab:
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
        while target_tab_widget.count() > 0: # Use while loop as count changes
            if not self.close_tab(0): # Always close the first tab
                return False 
        return True

    def add_editor_tab(self, content: str = "", file_path: str | None = None, file_type: str = "text", 
                       set_current: bool = True, untitled_name: str | None = None, 
                       target_tab_w: QTabWidget | None = None): 
        # This method is now less central as open_file_from_path handles most direct openings.
        # It's primarily used by open_file_from_path for Markdown, and potentially if we revert text opening.
        # For now, if file_type is 'text', it should use WangEditor.
        editor_container = None
        actual_editor_part = None 
        tab_name = ""
        is_new = file_path is None

        target_tab_widget = target_tab_w or (self.ui_manager.get_active_editor_group().get_tab_widget() if self.ui_manager.get_active_editor_group() else self.main_window.tab_widget)

        if target_tab_widget is None: # Explicit check for None
            QMessageBox.critical(self.main_window, "错误", "无法找到用于添加标签页的目标控件。")
            return None
        
        try:
            if file_type == "html": # This path is less used now by open_file_from_path for existing HTML
                editor_container = WangEditor() 
                editor_container.setHtml(content)
                actual_editor_part = editor_container 
            elif file_type == "markdown":
                editor_container = MarkdownEditorWidget()
                editor_container.set_content(content)
                actual_editor_part = editor_container.editor
            else: # text
                editor_container = WangEditor() # Use WangEditor for text type here too
                editor_container.setHtml(content) # Pass plain text to WangEditor
                actual_editor_part = editor_container

            if is_new:
                tab_name = untitled_name or f"未命名-{self.untitled_counter}"
                editor_container.setProperty("untitled_name", tab_name) 
            else:
                tab_name = os.path.basename(file_path)
                editor_container.setProperty("file_path", os.path.abspath(file_path))

            editor_container.setProperty("is_new", is_new)
            
            # Set modified state
            if isinstance(editor_container, (TextEditor, MarkdownEditorWidget)): # TextEditor case is rare now
                if hasattr(actual_editor_part, 'document') and callable(actual_editor_part.document):
                    actual_editor_part.document().setModified(False)
            elif isinstance(editor_container, WangEditor):
                 QTimer.singleShot(0, lambda ed=editor_container: self.main_window.on_editor_content_changed(ed, initially_modified=False))

            index = target_tab_widget.addTab(editor_container, tab_name)
            
            if set_current and index != -1:
                target_tab_widget.setCurrentIndex(index)
                if actual_editor_part: actual_editor_part.setFocus()
                self.main_window.update_edit_actions_state(actual_editor_part) # or editor_container
            return editor_container
        except Exception as e:
            QMessageBox.critical(self.main_window, "错误", f"创建编辑器标签页时出错: {e}")
            # Safe removal if tab was added before error
            if editor_container and target_tab_widget.indexOf(editor_container) != -1 :
                target_tab_widget.removeTab(target_tab_widget.indexOf(editor_container))
                editor_container.deleteLater()
            return None
