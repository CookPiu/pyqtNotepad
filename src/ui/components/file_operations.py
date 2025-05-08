import os
from PyQt6.QtWidgets import (QFileDialog, QMessageBox, QApplication)
from PyQt6.QtCore import QSignalBlocker

# Corrected relative imports
from ..atomic.editor.text_editor import TextEditor
from ..atomic.editor.html_editor import HtmlEditor
from ..atomic.markdown_editor_widget import MarkdownEditorWidget # Import MarkdownEditorWidget
# Assuming pdf_utils is still in src/utils
from ...utils.pdf_utils import cleanup_temp_images
# Import PdfViewerView for type checking or instantiation if needed elsewhere
from ..views.pdf_viewer_view import PdfViewerView


class FileOperations:
    """处理MainWindow的文件操作功能"""

    def __init__(self, main_window, ui_manager, markdown_editor_widget_instance): # Accept ui_manager and markdown_editor_widget_instance
        self.main_window = main_window
        self.ui_manager = ui_manager # Store ui_manager
        self.markdown_editor_widget_instance = markdown_editor_widget_instance # Store instance
        self.untitled_counter = 0 # Initialize counter here

    def new_file(self, file_type="text"):
        """创建新文件

        Args:
            file_type: 文件类型，可以是"text", "html", 或 "markdown"
        """
        editor = None
        tab_name_suffix = ""
        # 根据文件类型选择编辑器组件
        if file_type == "html":
            editor = HtmlEditor()
            tab_name_suffix = ".html"
        elif file_type == "markdown":
            # For Markdown, we might want to reuse the instance or create new ones.
            # For simplicity in new_file, let's assume creating a new instance or clearing the existing one.
            # If a single shared instance is used, its content needs to be cleared.
            # self.markdown_editor_widget_instance.clear_content() # If reusing single instance
            # editor = self.markdown_editor_widget_instance 
            editor = MarkdownEditorWidget() # Create a new instance for each new MD tab
            editor.clear_content() # Ensure it's empty
            tab_name_suffix = ".md"
        else: # Default to text
            editor = TextEditor()
            tab_name_suffix = ".txt"


        self.untitled_counter += 1
        # Ensure tab_name includes the suffix for clarity, though it might be trimmed by some logic later
        tab_name = f"未命名-{self.untitled_counter}{tab_name_suffix}"
        editor.setProperty("untitled_name", tab_name) # Store the full untitled name with suffix
        
        # Add tab and set properties
        actual_tab_name = f"未命名-{self.untitled_counter}" # Tab text might not need suffix initially if it's dynamic
        index = self.main_window.tab_widget.addTab(editor, actual_tab_name)
        self.main_window.tab_widget.setCurrentIndex(index)
        
        # Set focus - for MarkdownEditorWidget, focus its internal editor
        if isinstance(editor, MarkdownEditorWidget):
            editor.editor.setFocus()
        else:
            editor.setFocus()

        editor.setProperty("file_path", None)
        editor.setProperty("is_new", True)
        editor.setProperty("is_pdf_converted", False) # Assuming not relevant for MD initially
        editor.setProperty("pdf_temp_dir", None) # Assuming not relevant for MD initially

        # Reset modified state
        if isinstance(editor, TextEditor) and hasattr(editor, "document"):
            editor.document().setModified(False)
        elif isinstance(editor, HtmlEditor):
            editor.setModified(False)
        elif isinstance(editor, MarkdownEditorWidget):
            editor.editor.document().setModified(False) # QMarkdownTextEdit has a document
            # Or if QMarkdownTextEdit manages its own modified state, use its API
            # editor.setModified(False) # Hypothetical if it had such a method

        self.main_window.statusBar.showMessage(f"新建 {file_type.upper()} 文件")
        self.main_window.update_edit_actions_state(self.main_window.get_current_editor_widget())


    def open_file_dialog(self):
        """打开文件对话框"""
        file_name, _ = QFileDialog.getOpenFileName(
            self.main_window, "打开文件", "", 
            "HTML文件 (*.html);;Markdown文件 (*.md *.markdown);;文本文件 (*.txt);;PDF文件 (*.pdf);;所有文件 (*)"
        )
        if file_name:
            self.open_file_from_path(file_name)

    def open_file_from_path(self, file_path):
        """从路径打开文件"""
        abs_file_path = os.path.abspath(file_path)
        # Check if file is already open using UIManager
        if self.main_window.ui_manager.is_file_open(abs_file_path):
             self.main_window.ui_manager.focus_tab_by_filepath(abs_file_path)
             if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar:
                  self.main_window.statusBar.showMessage(f"切换到已打开文件: {file_path}")
             return

        # Determine file type and add tab using add_editor_tab
        try:
            _, ext = os.path.splitext(file_path)
            file_base_name = os.path.basename(file_path)

            if ext.lower() == '.pdf':
                self.main_window.ui_manager.open_pdf_preview(abs_file_path)
                return

            elif ext.lower() == '.html':
                try:
                    with open(abs_file_path, 'r', encoding='utf-8') as f: content = f.read()
                    self.add_editor_tab(content=content, file_path=abs_file_path, file_type='html', set_current=True)
                except Exception as e:
                    QMessageBox.critical(self.main_window, "错误", f"无法打开HTML文件 '{file_path}':\n{str(e)}")
                    return
            
            elif ext.lower() in ['.md', '.markdown']:
                try:
                    with open(abs_file_path, 'r', encoding='utf-8') as f: content = f.read()
                    self.add_editor_tab(content=content, file_path=abs_file_path, file_type='markdown', set_current=True)
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
                # Add text editor tab
                self.add_editor_tab(content=content, file_path=abs_file_path, file_type='text', set_current=True)

            if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar:
                  self.main_window.statusBar.showMessage(f"已打开: {file_path}")

        except Exception as e:
             QMessageBox.critical(self.main_window, "打开文件错误", f"打开文件 '{file_path}' 时发生未知错误:\n{str(e)}")

    def _save_html_editor_content(self, editor: HtmlEditor, file_path: str):
        """异步保存HTML编辑器内容"""
        def save_callback(html: str):
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(html)
                # 在回调中更新状态
                editor.setModified(False)
                if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar:
                    self.main_window.statusBar.showMessage(f"已保存: {file_path}")
                # 确保标签标题也更新（如果标签仍然存在）
                if self.ui_manager.is_widget_still_in_tabs(editor):
                    self.main_window.update_tab_title(False)
                print(f"异步保存成功: {file_path}") # Debugging
            except Exception as e:
                QMessageBox.critical(self.main_window, "错误",
                                   f"无法异步保存文件 '{file_path}':\n{str(e)}")

        # 调用异步 toHtml 并传递回调
        editor.toHtml(save_callback)
        # 注意：此函数立即返回，保存操作在后台进行

    def save_file(self) -> bool:
        """保存当前文件 (处理异步HTML保存)"""
        editor = self.main_window.get_current_editor_widget() # Use the widget getter
        if not editor: return False

        file_path = editor.property("file_path")
        is_new = editor.property("is_new")

        if is_new or not file_path:
            return self.save_file_as()
        else:
            try:
                if isinstance(editor, HtmlEditor):
                    self._save_html_editor_content(editor, file_path)
                    return True
                # Check if the actual editor widget (e.g., QMarkdownTextEdit from MarkdownEditorWidget) has a document
                elif isinstance(editor, MarkdownEditorWidget): # Handle MarkdownEditorWidget
                    content_to_save = editor.get_content() # Use its get_content method
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content_to_save)
                    editor.editor.document().setModified(False) # Access document of internal editor
                    if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar:
                        self.main_window.statusBar.showMessage(f"已保存: {file_path}")
                    self.main_window.update_tab_title(False)
                    return True
                elif hasattr(editor, 'document'): # Handle TextEditor
                    _, ext = os.path.splitext(file_path)
                    # For TextEditor, toPlainText() is usually sufficient unless it's meant to save as HTML
                    content_to_save = editor.toPlainText()
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content_to_save)
                    editor.document().setModified(False)
                    if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar:
                        self.main_window.statusBar.showMessage(f"已保存: {file_path}")
                    self.main_window.update_tab_title(False)
                    return True
                else:
                    raise TypeError(f"无法确定编辑器类型 {type(editor)} 以进行保存。")
            except Exception as e:
                QMessageBox.critical(self.main_window, "错误", f"无法保存文件 '{file_path}':\n{str(e)}")
                return False

    def save_file_as(self) -> bool:
        """将文件另存为 (处理异步HTML保存和同步Markdown/Text保存)"""
        current_tab_widget = self.main_window.tab_widget.currentWidget() # Get the widget in the tab (e.g. MarkdownEditorWidget)
        editor_to_save_from = self.main_window.get_current_editor_widget() # Get the actual editor (e.g. QMarkdownTextEdit)
        
        if not editor_to_save_from or not current_tab_widget: return False

        current_path = current_tab_widget.property("file_path")
        untitled_name = current_tab_widget.property("untitled_name")
        
        suggested_name = os.path.basename(current_path) if current_path else (untitled_name or f"未命名-{self.untitled_counter}")
        default_dir = os.path.dirname(current_path) if current_path else ""

        filters = "HTML文件 (*.html);;Markdown文件 (*.md *.markdown);;文本文件 (*.txt);;所有文件 (*)"
        default_filter = "文本文件 (*.txt)" # Default

        if isinstance(current_tab_widget, HtmlEditor):
            default_filter = "HTML文件 (*.html)"
        elif isinstance(current_tab_widget, MarkdownEditorWidget):
            default_filter = "Markdown文件 (*.md *.markdown)"
        elif current_path: # For TextEditor with existing path
            _, ext = os.path.splitext(current_path)
            if ext.lower() == '.html': default_filter = "HTML文件 (*.html)"
            elif ext.lower() in ['.md', '.markdown']: default_filter = "Markdown文件 (*.md *.markdown)"
        
        file_name, selected_filter = QFileDialog.getSaveFileName(
            self.main_window, "另存为", os.path.join(default_dir, suggested_name),
            filters, default_filter
        )

        if file_name:
            abs_file_path = os.path.abspath(file_name)
            _, current_ext = os.path.splitext(abs_file_path)

            # Ensure correct extension based on selected filter if none provided
            if not current_ext:
                if "HTML" in selected_filter: abs_file_path += ".html"
                elif "Markdown" in selected_filter: abs_file_path += ".md"
                elif "文本文件" in selected_filter: abs_file_path += ".txt"
                # else, no extension added if "所有文件" and no specific type hint

            try:
                current_tab_widget.setProperty("file_path", abs_file_path)
                current_tab_widget.setProperty("is_new", False)
                current_tab_widget.setProperty("untitled_name", None)

                current_index = self.main_window.tab_widget.currentIndex()
                if current_index != -1 and self.main_window.tab_widget.widget(current_index) == current_tab_widget:
                    self.main_window.tab_widget.setTabText(current_index, os.path.basename(abs_file_path))
                    self.main_window.update_window_title()
                
                content_to_save = ""
                is_html_editor_save = isinstance(current_tab_widget, HtmlEditor)
                is_markdown_editor_save = isinstance(current_tab_widget, MarkdownEditorWidget)

                if is_html_editor_save:
                    self._save_html_editor_content(current_tab_widget, abs_file_path) # Async
                    return True 
                elif is_markdown_editor_save:
                    content_to_save = current_tab_widget.get_content()
                elif hasattr(editor_to_save_from, 'toPlainText'): # TextEditor
                    content_to_save = editor_to_save_from.toPlainText()
                else:
                    raise TypeError("无法确定编辑器类型以获取内容进行另存为。")

                # Synchronous save for Markdown and Text
                with open(abs_file_path, 'w', encoding='utf-8') as f:
                    f.write(content_to_save)

                if hasattr(editor_to_save_from, 'document'): # QMarkdownTextEdit and _InternalTextEdit have document
                    editor_to_save_from.document().setModified(False)
                
                if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar:
                    self.main_window.statusBar.showMessage(f"已保存: {abs_file_path}")
                self.main_window.update_tab_title(False)
                return True

            except Exception as e:
                QMessageBox.critical(self.main_window, "错误", f"无法另存为文件 '{abs_file_path}':\n{str(e)}")
        return False

    def close_tab(self, index):
        """关闭标签页"""
        if index < 0 or index >= self.main_window.tab_widget.count(): return False # Return bool
        widget_in_tab = self.main_window.tab_widget.widget(index) # This is the container (e.g., MarkdownEditorWidget)

        # Get the actual editor part for isModified check (e.g., QMarkdownTextEdit)
        # For TextEditor/HtmlEditor, widget_in_tab is the editor.
        # For MarkdownEditorWidget, widget_in_tab.editor is the QMarkdownTextEdit.
        editor_component = widget_in_tab
        if isinstance(widget_in_tab, MarkdownEditorWidget):
            editor_component = widget_in_tab.editor
        
        # Check if the component that holds the content (like QMarkdownTextEdit or HtmlEditor) is modified
        is_modified = False
        if hasattr(editor_component, 'document') and callable(editor_component.document):
            is_modified = editor_component.document().isModified()
        elif hasattr(editor_component, 'isModified') and callable(editor_component.isModified): # For HtmlEditor
            is_modified = editor_component.isModified()


        if is_modified:
            self.main_window.tab_widget.setCurrentIndex(index) # Focus the tab before showing dialog
            tab_name = self.main_window.tab_widget.tabText(index)
            ret = QMessageBox.warning(self.main_window, "关闭标签页", f"文档 '{tab_name}' 已被修改。\n是否保存更改？",
                                    QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
            if ret == QMessageBox.StandardButton.Save:
                if not self.save_file(): # save_file now operates on current tab's editor
                    return False # Save failed or was cancelled
            elif ret == QMessageBox.StandardButton.Cancel:
                return False

        temp_dir = widget_in_tab.property("pdf_temp_dir") # Check property on the container widget
        if temp_dir:
            try:
                cleanup_temp_images(temp_dir)
            except Exception as e:
                print(f"清理 PDF 临时文件时出错: {e}")

        if self.main_window.previous_editor == editor_component: # Compare with the actual editor component
             self.main_window.previous_editor = None

        self.main_window.tab_widget.removeTab(index)
        if hasattr(widget_in_tab, 'cleanup'): widget_in_tab.cleanup()
        widget_in_tab.deleteLater()

        if self.main_window.tab_widget.count() == 0:
            self.new_file() # Creates a default new file

        new_current_editor_widget = self.main_window.get_current_editor_widget()
        self.main_window.update_edit_actions_state(new_current_editor_widget)
        return True

    def close_all_tabs(self) -> bool:
        """Attempts to close all tabs, returns True if successful, False otherwise."""
        tab_widget = self.main_window.tab_widget
        # Iterate backwards as closing tabs changes indices
        for i in range(tab_widget.count() - 1, -1, -1):
            if not self.close_tab(i): # If closing any tab fails (e.g., user cancels save)
                return False # Abort closing process
        return True # All tabs closed successfully

    def add_editor_tab(self, content: str = "", file_path: str | None = None, file_type: str = "text", set_current: bool = True, untitled_name: str | None = None):
         """Helper function to create and add an editor tab."""
         editor_container = None # This will be the widget added to the tab (e.g. MarkdownEditorWidget)
         actual_editor_part = None # This is the part with document/content (e.g. QMarkdownTextEdit)
         tab_name = ""
         is_new = file_path is None

         try:
             if file_type == "html":
                 editor_container = HtmlEditor()
                 editor_container.setHtml(content)
                 actual_editor_part = editor_container
             elif file_type == "markdown":
                 editor_container = MarkdownEditorWidget() # Create new instance for the tab
                 editor_container.set_content(content) # Use set_content
                 actual_editor_part = editor_container.editor # QMarkdownTextEdit
             else: # Default to text
                 editor_container = TextEditor()
                 with QSignalBlocker(editor_container.document()): editor_container.setPlainText(content)
                 actual_editor_part = editor_container._editor # _InternalTextEdit

             if is_new:
                 # untitled_name was already generated with suffix in new_file
                 tab_name = untitled_name or f"未命名-{self.main_window.untitled_counter}"
                 # Store the base name without suffix for tab display if needed, or full name
                 editor_container.setProperty("untitled_name", tab_name) 
             else:
                 tab_name = os.path.basename(file_path)
                 editor_container.setProperty("file_path", os.path.abspath(file_path))

             editor_container.setProperty("is_new", is_new)
             editor_container.setProperty("is_pdf_converted", False)
             editor_container.setProperty("pdf_temp_dir", None)

             if hasattr(actual_editor_part, 'document') and callable(actual_editor_part.document):
                 actual_editor_part.document().setModified(False)
             elif hasattr(actual_editor_part, 'setModified') and callable(actual_editor_part.setModified): # For HtmlEditor
                 actual_editor_part.setModified(False)


             index = self.main_window.tab_widget.addTab(editor_container, tab_name)
             if set_current:
                 self.main_window.tab_widget.setCurrentIndex(index)
                 # Focus the actual editor part
                 if actual_editor_part: actual_editor_part.setFocus()


             if set_current:
                  self.main_window.update_edit_actions_state(actual_editor_part)

             return editor_container

         except Exception as e:
              QMessageBox.critical(self.main_window, "错误", f"创建编辑器标签页时出错: {e}")
              if editor_container and 'index' in locals() and index < self.main_window.tab_widget.count() and self.main_window.tab_widget.widget(index) == editor_container:
                   self.main_window.tab_widget.removeTab(index)
                   editor_container.deleteLater()
              return None
