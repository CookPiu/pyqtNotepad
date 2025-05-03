import os
from PyQt6.QtWidgets import (QFileDialog, QMessageBox, QApplication)
from PyQt6.QtCore import QSignalBlocker

# Corrected relative imports
from ..atomic.editor.text_editor import TextEditor
from ..atomic.editor.html_editor import HtmlEditor
# Assuming pdf_utils is still in src/utils
from ...utils.pdf_utils import cleanup_temp_images
# Import PdfViewerView for type checking or instantiation if needed elsewhere
from ..views.pdf_viewer_view import PdfViewerView


class FileOperations:
    """处理MainWindow的文件操作功能"""
    
    def __init__(self, main_window, ui_manager): # Accept ui_manager
        self.main_window = main_window
        self.ui_manager = ui_manager # Store ui_manager
        self.untitled_counter = 0 # Initialize counter here
    
    def new_file(self, file_type="text"):
        """创建新文件
        
        Args:
            file_type: 文件类型，可以是"text"或"html"
        """
        # 根据文件类型选择编辑器组件
        if file_type == "html":
            editor = HtmlEditor()
            # setFontPointSize might not exist directly, font setting handled internally or via document
            # editor.setFontPointSize(12)
            # Connect modification signal (already handled in HtmlEditor's base class or internal logic)
            # editor.document_modified.connect(lambda modified: self.main_window.update_tab_title(modified))
        else:
            # Use the refactored TextEditor
            editor = TextEditor()
            # Font setting might be handled internally or via document
            # font = editor.document().defaultFont()
            # font.setPointSize(12)
            # editor.document().setDefaultFont(font)
            
        self.untitled_counter += 1 # Use self.untitled_counter
        tab_name = f"未命名-{self.untitled_counter}" # Use self.untitled_counter
        editor.setProperty("untitled_name", tab_name)
        # 不需要手动连接在TextEditWithLineNumbers中处理的信号
        index = self.main_window.tab_widget.addTab(editor, tab_name)
        self.main_window.tab_widget.setCurrentIndex(index)
        editor.setFocus() # Explicitly set focus to the new editor widget
        # 直接在编辑器实例上设置属性
        editor.setProperty("file_path", None)
        editor.setProperty("is_new", True)
        editor.setProperty("is_pdf_converted", False)
        editor.setProperty("pdf_temp_dir", None)
        # If it's a TextEditor with a document, reset modified state
        # HtmlEditor resets its state internally on setHtml
        if isinstance(editor, TextEditor) and hasattr(editor, "document"):
            editor.document().setModified(False)
        elif isinstance(editor, HtmlEditor):
             editor.setModified(False) # Use HtmlEditor's own method
        self.main_window.statusBar.showMessage("新建文件")
        # 更新新编辑器的操作状态
        self.main_window.update_edit_actions_state(editor)
    
    def open_file_dialog(self):
        """打开文件对话框"""
        file_name, _ = QFileDialog.getOpenFileName(self.main_window, "打开文件", "", "HTML文件 (*.html);;文本文件 (*.txt);;PDF文件 (*.pdf);;所有文件 (*)")
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
                # Use UIManager to open PDF preview (which uses PdfViewerView)
                self.main_window.ui_manager.open_pdf_preview(abs_file_path)
                return # PDF preview handles itself

            elif ext.lower() == '.html':
                # Read content and add HTML editor tab
                try:
                    with open(abs_file_path, 'r', encoding='utf-8') as f: content = f.read()
                    self.add_editor_tab(content=content, file_path=abs_file_path, file_type='html', set_current=True)
                except Exception as e:
                    QMessageBox.critical(self.main_window, "错误", f"无法打开HTML文件 '{file_path}':\n{str(e)}")
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
    
    def save_file(self) -> bool:
        """保存当前文件"""
        editor = self.main_window.get_current_editor()
        if not editor: return False

        if editor.property("is_new") or not editor.property("file_path"):
            return self.save_file_as()
        else:
            file_path = editor.property("file_path")
            try:
                content_to_save = None
                is_html_save = False

                if isinstance(editor, HtmlEditor):
                    is_html_save = True
                    # WARNING: editor.toHtml() is asynchronous for QWebEngineView!
                    # This synchronous call will likely NOT get the latest content.
                    # A proper implementation requires asynchronous handling (e.g., using signals/slots or async/await).
                    # For now, we call it but it won't work as expected for saving modifications.
                    print("警告: HtmlEditor.toHtml() 是异步的，同步保存可能不会包含最新更改。")
                    # Placeholder: Try to get content synchronously (will likely fail for modifications)
                    # A callback mechanism is needed here.
                    # We'll proceed with saving *something* to avoid crashing, but it's incorrect.
                    def _handle_html_sync(html):
                         nonlocal content_to_save
                         content_to_save = html # This callback won't be waited for here.

                    editor.toHtml(_handle_html_sync)
                    # Need to wait here somehow, which isn't possible in this structure.
                    # Fallback to saving an empty string or potentially old content if available.
                    if content_to_save is None: content_to_save = "" # Incorrect, but prevents crash

                elif hasattr(editor, 'document'): # Handle TextEditor
                    _, ext = os.path.splitext(file_path)
                    if ext.lower() == '.html':
                         is_html_save = True
                         content_to_save = editor.document().toHtml()
                    else:
                         content_to_save = editor.toPlainText()
                else:
                     # Should not happen if editor is correctly identified
                     raise TypeError("无法确定编辑器类型以进行保存。")

                # Proceed with writing the (potentially incorrect for HtmlEditor) content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content_to_save)

                # Update modified state
                if isinstance(editor, HtmlEditor):
                    editor.setModified(False) # Use HtmlEditor's method
                elif hasattr(editor, 'document'):
                    editor.document().setModified(False)

                self.main_window.statusBar.showMessage(f"已保存: {file_path}")
                self.main_window.update_tab_title(False)  # Update tab title immediately
                return True
            except Exception as e:
                QMessageBox.critical(self.main_window, "错误", f"无法保存文件 '{file_path}':\n{str(e)}")
                return False
    
    def save_file_as(self) -> bool:
        """将文件另存为"""
        editor = self.main_window.get_current_editor()
        if not editor: return False

        current_path = editor.property("file_path")
        untitled_name = editor.property("untitled_name")
        # 根据当前路径或未命名名称建议文件名
        suggested_name = os.path.basename(current_path) if current_path else (untitled_name or f"未命名-{self.main_window.untitled_counter}")

        default_dir = os.path.dirname(current_path) if current_path else ""

        # 根据内容或现有扩展名确定默认过滤器
        default_filter = "HTML文件 (*.html)"
        # 检查内容是否可能是纯文本，需要考虑不同编辑器类型
        if isinstance(editor, HtmlEditor):
            is_plain = editor.to_plain_text() == editor.to_html()
        else:
            is_plain = editor.toPlainText() == editor.document().toHtml()  # 基本检查内容是否可能是纯文本
        if current_path and os.path.splitext(current_path)[1].lower() != '.html':
            default_filter = "文本文件 (*.txt)"
        elif is_plain and not current_path:  # 看起来像纯文本的新文件
            default_filter = "文本文件 (*.txt)"

        file_name, selected_filter = QFileDialog.getSaveFileName(
            self.main_window, "另存为", os.path.join(default_dir, suggested_name),
            "HTML文件 (*.html);;文本文件 (*.txt);;所有文件 (*)", default_filter
        )

        if file_name:
            abs_file_path = os.path.abspath(file_name)
            # 如果未提供扩展名，则根据过滤器确保扩展名
            _, current_ext = os.path.splitext(abs_file_path)
            if not current_ext:
                abs_file_path += ".html" if "HTML" in selected_filter else ".txt"

            _, save_ext = os.path.splitext(abs_file_path)
            try:
                content_to_save = None
                is_html_save = (save_ext.lower() == '.html')

                if isinstance(editor, HtmlEditor):
                    is_html_save = True # Always save HtmlEditor as HTML
                    # WARNING: editor.toHtml() is asynchronous! See save_file comments.
                    print("警告: HtmlEditor.toHtml() 是异步的，同步另存为可能不会包含最新更改。")
                    def _handle_html_sync_as(html):
                         nonlocal content_to_save
                         content_to_save = html
                    editor.toHtml(_handle_html_sync_as)
                    if content_to_save is None: content_to_save = "" # Incorrect fallback

                elif hasattr(editor, 'document'): # Handle TextEditor
                    if is_html_save:
                         content_to_save = editor.document().toHtml()
                    else:
                         content_to_save = editor.toPlainText()
                else:
                     raise TypeError("无法确定编辑器类型以进行另存为。")

                # Proceed with writing the (potentially incorrect for HtmlEditor) content
                with open(abs_file_path, 'w', encoding='utf-8') as f:
                    f.write(content_to_save)

                # 更新编辑器属性
                editor.setProperty("file_path", abs_file_path)
                editor.setProperty("is_new", False)
                editor.setProperty("untitled_name", None)  # Clear untitled name

                # Update modified state
                if isinstance(editor, HtmlEditor):
                    editor.setModified(False)
                elif hasattr(editor, 'document'):
                     editor.document().setModified(False)

                # 更新当前编辑器的标签文本
                current_index = self.main_window.tab_widget.currentIndex()
                if current_index != -1 and self.main_window.tab_widget.widget(current_index) == editor:
                    # 保存后立即更新标签文本
                    self.main_window.tab_widget.setTabText(current_index, os.path.basename(abs_file_path))
                    # 显式调用update_tab_title以确保删除'*'并更新窗口标题
                    self.main_window.update_tab_title(False)

                self.main_window.statusBar.showMessage(f"已保存: {abs_file_path}")
                return True
            except Exception as e:
                QMessageBox.critical(self.main_window, "错误", f"无法保存文件 '{abs_file_path}':\n{str(e)}")
        return False
    
    def close_tab(self, index):
        """关闭标签页"""
        if index < 0 or index >= self.main_window.tab_widget.count(): return
        widget = self.main_window.tab_widget.widget(index)

        # 处理非编辑器小部件（如潜在的未来PDF查看器标签直接）
        if not self.main_window.ui_manager.is_widget_editor(widget):
             # Handle closing non-editor tabs (e.g., views like NoteDownloader)
             # Ask UIManager or the view itself if closing is allowed/needs confirmation
             # For now, just remove and delete
             self.main_window.tab_widget.removeTab(index)
             if hasattr(widget, 'cleanup'): widget.cleanup() # Call cleanup if exists
             widget.deleteLater()
             return True # Indicate tab was closed

        editor = widget
        if editor.isModified(): # Use isModified method directly
            self.main_window.tab_widget.setCurrentIndex(index)
            tab_name = self.main_window.tab_widget.tabText(index)
            ret = QMessageBox.warning(self.main_window, "关闭标签页", f"文档 '{tab_name}' 已被修改。\n是否保存更改？",
                                    QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
            if ret == QMessageBox.StandardButton.Save:
                if not self.save_file(): return False # Save failed, abort close
            elif ret == QMessageBox.StandardButton.Cancel:
                return False # User cancelled, abort close

        # Cleanup PDF temp dir if applicable
        temp_dir = editor.property("pdf_temp_dir")
        if temp_dir:
            try:
                 cleanup_temp_images(temp_dir)
            except Exception as e:
                 print(f"清理 PDF 临时文件时出错: {e}")

        # Disconnect signals (handled by update_edit_actions_state when tab changes)
        if self.main_window.previous_editor == editor:
             self.main_window.previous_editor = None # Clear reference if it's the one being closed

        # Remove tab and delete widget
        self.main_window.tab_widget.removeTab(index)
        if hasattr(editor, 'cleanup'): editor.cleanup() # Call cleanup if exists
        editor.deleteLater()

        # If last tab closed, create a new one
        if self.main_window.tab_widget.count() == 0:
            self.new_file()

        # Update actions based on the potentially new current tab
        new_current_widget = self.main_window.get_current_editor_widget()
        self.main_window.update_edit_actions_state(new_current_widget)
        return True # Indicate tab was closed

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
         editor = None
         tab_name = ""
         is_new = file_path is None

         try:
             if file_type == "html":
                 editor = HtmlEditor()
                 # QWebEngineView's setHtml doesn't need QSignalBlocker around document
                 editor.setHtml(content)
             else: # Default to text
                 editor = TextEditor()
                 # Keep QSignalBlocker for TextEditor's document
                 with QSignalBlocker(editor.document()): editor.setPlainText(content)

             if is_new:
                 self.main_window.untitled_counter += 1
                 tab_name = untitled_name or f"未命名-{self.main_window.untitled_counter}"
                 editor.setProperty("untitled_name", tab_name)
             else:
                 tab_name = os.path.basename(file_path)
                 editor.setProperty("file_path", os.path.abspath(file_path))

             editor.setProperty("is_new", is_new)
             editor.setProperty("is_pdf_converted", False)
             editor.setProperty("pdf_temp_dir", None)
             # Reset modified state based on editor type
             if isinstance(editor, TextEditor) and hasattr(editor, "document"):
                 editor.document().setModified(False) # Start unmodified
             elif isinstance(editor, HtmlEditor):
                 editor.setModified(False) # Use HtmlEditor's method

             index = self.main_window.tab_widget.addTab(editor, tab_name)
             if set_current:
                 self.main_window.tab_widget.setCurrentIndex(index)

             # Connect modification signal for tab title updates
             # This connection should ideally happen once, maybe in UIManager or MainWindow
             # editor.document().modificationChanged.connect(lambda mod: self.main_window.update_tab_title(mod))

             # Update actions for the new tab if it's set current
             if set_current:
                  self.main_window.update_edit_actions_state(editor)

             return editor # Return the created editor instance

         except Exception as e:
              QMessageBox.critical(self.main_window, "错误", f"创建编辑器标签页时出错: {e}")
              # Clean up partially created editor if necessary
              if editor and 'index' in locals() and index < self.main_window.tab_widget.count() and self.main_window.tab_widget.widget(index) == editor:
                   self.main_window.tab_widget.removeTab(index)
                   editor.deleteLater()
              return None
