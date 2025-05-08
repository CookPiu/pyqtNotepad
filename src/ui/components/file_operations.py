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
        # self.markdown_editor_widget_instance is not strictly needed if new instances are created per tab
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
        # For TextEditor, HtmlEditor (new), and MarkdownEditorWidget, the actual editor component has a document.
        actual_editor_part = editor
        if isinstance(editor, TextEditor):
            actual_editor_part = editor._editor # _InternalTextEdit
        elif isinstance(editor, HtmlEditor): # New HtmlEditor (QWidget)
            actual_editor_part = editor.source_editor # QPlainTextEdit
        elif isinstance(editor, MarkdownEditorWidget):
            actual_editor_part = editor.editor # QPlainTextEdit
        
        if hasattr(actual_editor_part, 'document') and callable(actual_editor_part.document):
            actual_editor_part.document().setModified(False)
        elif hasattr(editor, 'setModified'): # Fallback for old HtmlEditor if it were still used by mistake
             editor.setModified(False)


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

    # _save_html_editor_content is removed as new HtmlEditor saves synchronously via its source_editor

    def save_file(self) -> bool:
        """保存当前文件"""
        # current_tab_container is the QWidget holding the editor (e.g. HtmlEditor, MarkdownEditorWidget, TextEditor)
        current_tab_container = self.main_window.tab_widget.currentWidget()
        # actual_editor_component is the QPlainTextEdit or _InternalTextEdit
        actual_editor_component = self.main_window.get_current_editor_widget()

        if not actual_editor_component or not current_tab_container: 
            return False

        file_path = current_tab_container.property("file_path")
        is_new = current_tab_container.property("is_new")

        if is_new or not file_path:
            return self.save_file_as()
        else:
            try:
                content_to_save = ""
                if isinstance(current_tab_container, HtmlEditor):
                    content_to_save = actual_editor_component.toPlainText() # Save HTML source
                elif isinstance(current_tab_container, MarkdownEditorWidget):
                    content_to_save = actual_editor_component.toPlainText() # Save Markdown source
                elif isinstance(current_tab_container, TextEditor):
                    content_to_save = actual_editor_component.toPlainText() # Save plain text
                else:
                    # Fallback or unknown editor type in tab
                    if hasattr(actual_editor_component, 'toPlainText'):
                        content_to_save = actual_editor_component.toPlainText()
                    else:
                        raise TypeError(f"无法确定编辑器类型 {type(current_tab_container)} / {type(actual_editor_component)} 以进行保存。")

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
        """将文件另存为"""
        current_tab_container = self.main_window.tab_widget.currentWidget()
        actual_editor_component = self.main_window.get_current_editor_widget()
        
        if not actual_editor_component or not current_tab_container: 
            return False

        current_path = current_tab_container.property("file_path")
        untitled_name = current_tab_container.property("untitled_name")
        
        suggested_name = os.path.basename(current_path) if current_path else (untitled_name or f"未命名-{self.untitled_counter}")
        default_dir = os.path.dirname(current_path) if current_path else ""

        filters = "HTML文件 (*.html);;Markdown文件 (*.md *.markdown);;文本文件 (*.txt);;所有文件 (*)"
        default_filter = "文本文件 (*.txt)"

        if isinstance(current_tab_container, HtmlEditor):
            default_filter = "HTML文件 (*.html)"
        elif isinstance(current_tab_container, MarkdownEditorWidget):
            default_filter = "Markdown文件 (*.md *.markdown)"
        # No need to check current_path for TextEditor, as it defaults to .txt if new

        file_name, selected_filter = QFileDialog.getSaveFileName(
            self.main_window, "另存为", os.path.join(default_dir, suggested_name),
            filters, default_filter
        )

        if file_name:
            abs_file_path = os.path.abspath(file_name)
            # Ensure correct extension based on selected filter if none provided by user
            # This logic might need refinement if user types "myfile.other" but selects "HTML files (*.html)"
            _, current_ext = os.path.splitext(abs_file_path)
            if not current_ext: # Only add extension if user didn't provide one
                if "HTML" in selected_filter: abs_file_path += ".html"
                elif "Markdown" in selected_filter: abs_file_path += ".md"
                elif "文本文件" in selected_filter: abs_file_path += ".txt"
            
            try:
                current_tab_container.setProperty("file_path", abs_file_path)
                current_tab_container.setProperty("is_new", False)
                current_tab_container.setProperty("untitled_name", None)

                current_index = self.main_window.tab_widget.currentIndex()
                if current_index != -1 and self.main_window.tab_widget.widget(current_index) == current_tab_container:
                    self.main_window.tab_widget.setTabText(current_index, os.path.basename(abs_file_path))
                    self.main_window.update_window_title()
                
                content_to_save = ""
                if isinstance(current_tab_container, HtmlEditor):
                    content_to_save = actual_editor_component.toPlainText()
                elif isinstance(current_tab_container, MarkdownEditorWidget):
                    content_to_save = actual_editor_component.toPlainText()
                elif isinstance(current_tab_container, TextEditor):
                     content_to_save = actual_editor_component.toPlainText()
                else: # Fallback
                    if hasattr(actual_editor_component, 'toPlainText'):
                        content_to_save = actual_editor_component.toPlainText()
                    else:
                        raise TypeError("无法确定编辑器类型以获取内容进行另存为。")

                with open(abs_file_path, 'w', encoding='utf-8') as f:
                    f.write(content_to_save)

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
        """关闭标签页"""
        if index < 0 or index >= self.main_window.tab_widget.count(): return False # Return bool
        widget_in_tab = self.main_window.tab_widget.widget(index) # This is the container (e.g., MarkdownEditorWidget)

        # Get the actual editor part for isModified check (e.g., QMarkdownTextEdit)
        # For TextEditor, widget_in_tab is TextEditor, editor_component is _InternalTextEdit.
        # For new HtmlEditor, widget_in_tab is HtmlEditor, editor_component is source_editor (QPlainTextEdit).
        # For MarkdownEditorWidget, widget_in_tab is MarkdownEditorWidget, editor_component is editor (QPlainTextEdit).
        editor_component = None
        if isinstance(widget_in_tab, TextEditor):
            editor_component = widget_in_tab._editor
        elif isinstance(widget_in_tab, HtmlEditor):
            editor_component = widget_in_tab.source_editor
        elif isinstance(widget_in_tab, MarkdownEditorWidget):
            editor_component = widget_in_tab.editor
        else: # Could be a non-editor view
            editor_component = widget_in_tab 

        is_modified = False
        if hasattr(editor_component, 'document') and callable(editor_component.document):
            doc = editor_component.document()
            if doc: is_modified = doc.isModified()
        elif hasattr(widget_in_tab, 'isModified') and callable(widget_in_tab.isModified): # Fallback for containers like old HtmlEditor
            is_modified = widget_in_tab.isModified()


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
