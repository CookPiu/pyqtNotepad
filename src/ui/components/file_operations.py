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
                    # 调用新的异步保存方法
                    self._save_html_editor_content(editor, file_path)
                    # 立即返回True，表示保存已启动
                    # 状态栏消息和 modified 状态将在回调中处理
                    return True
                elif hasattr(editor, 'document'): # Handle TextEditor (synchronous)
                    _, ext = os.path.splitext(file_path)
                    content_to_save = editor.document().toHtml() if ext.lower() == '.html' else editor.toPlainText()
                    # Ensure correct indentation within this block (Level 5 = 20 spaces)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content_to_save)
                    editor.document().setModified(False)
                    if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar:
                        self.main_window.statusBar.showMessage(f"已保存: {file_path}")
                    # Ensure correct indentation for these lines relative to the 'if' above
                    self.main_window.update_tab_title(False)
                    return True
                # Ensure 'else' is aligned with 'if/elif'
                else:
                    # Should not happen if editor is correctly identified
                    raise TypeError("无法确定编辑器类型以进行保存。")
            # Ensure 'except' is aligned with 'try'
            except Exception as e:
                QMessageBox.critical(self.main_window, "错误", f"无法保存文件 '{file_path}':\n{str(e)}")
                return False

    def save_file_as(self) -> bool:
        """将文件另存为 (处理异步HTML保存)"""
        editor = self.main_window.get_current_editor_widget() # Use the widget getter
        if not editor: return False

        current_path = editor.property("file_path")
        untitled_name = editor.property("untitled_name")
        suggested_name = os.path.basename(current_path) if current_path else (untitled_name or f"未命名-{self.untitled_counter}") # Use self.untitled_counter
        default_dir = os.path.dirname(current_path) if current_path else ""

        # Determine default filter based on editor type or current extension
        default_filter = "HTML文件 (*.html)"
        is_html_editor = isinstance(editor, HtmlEditor)

        if not is_html_editor:
            # For TextEditor, check current extension or content
            if current_path and os.path.splitext(current_path)[1].lower() != '.html':
                default_filter = "文本文件 (*.txt)"
            elif not current_path: # New file, check if content looks plain (basic check)
                 try:
                      if hasattr(editor, 'toPlainText') and hasattr(editor, 'document') and editor.toPlainText() == editor.document().toHtml():
                           default_filter = "文本文件 (*.txt)"
                 except Exception: pass # Ignore errors during check

        file_name, selected_filter = QFileDialog.getSaveFileName(
            self.main_window, "另存为", os.path.join(default_dir, suggested_name),
            "HTML文件 (*.html);;文本文件 (*.txt);;所有文件 (*)", default_filter
        )

        if file_name:
            abs_file_path = os.path.abspath(file_name)
            _, current_ext = os.path.splitext(abs_file_path)
            if not current_ext:
                abs_file_path += ".html" if "HTML" in selected_filter else ".txt"

            try:
                # --- Update editor properties and tab title BEFORE saving ---
                # This needs to happen synchronously regardless of save method
                editor.setProperty("file_path", abs_file_path)
                editor.setProperty("is_new", False)
                editor.setProperty("untitled_name", None)

                current_index = self.main_window.tab_widget.currentIndex()
                if current_index != -1 and self.main_window.tab_widget.widget(current_index) == editor:
                    self.main_window.tab_widget.setTabText(current_index, os.path.basename(abs_file_path))
                    # Update window title immediately, but modified state handled by save/callback
                    self.main_window.update_window_title()
                # -----------------------------------------------------------

                if isinstance(editor, HtmlEditor):
                    # Call the async save method
                    self._save_html_editor_content(editor, abs_file_path)
                    # Return True immediately, status/modified handled in callback
                    return True
                elif hasattr(editor, 'document'): # Handle TextEditor (synchronous)
                    _, save_ext = os.path.splitext(abs_file_path)
                    is_html_save = (save_ext.lower() == '.html')
                    content_to_save = editor.document().toHtml() if is_html_save else editor.toPlainText()

                    with open(abs_file_path, 'w', encoding='utf-8') as f:
                        f.write(content_to_save)

                    # Update modified state synchronously for TextEditor
                    editor.document().setModified(False)
                    # Update status bar and ensure tab title removes '*'
                    if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar:
                        self.main_window.statusBar.showMessage(f"已保存: {abs_file_path}")
                    self.main_window.update_tab_title(False) # Ensure '*' is removed
                    return True
                else:
                     raise TypeError("无法确定编辑器类型以进行另存为。")

            except Exception as e:
                QMessageBox.critical(self.main_window, "错误", f"无法另存为文件 '{abs_file_path}':\n{str(e)}")
                # Attempt to revert property changes if save fails? Maybe too complex.
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
                # Save might be async now, but close_tab needs synchronous result
                # We need to handle this better, maybe disable close while async save is pending
                # For now, assume save_file returns True if async started
                if not self.save_file():
                    # If save_file returns False (e.g., TextEditor save failed), abort close
                    return False
                # If save_file returns True (TextEditor saved OR HtmlEditor async started),
                # we might still need to wait for HtmlEditor. For now, proceed cautiously.
                # A better solution would involve disabling close until the callback confirms save.
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
