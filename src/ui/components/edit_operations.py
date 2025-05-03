import base64 # For image pasting
from PyQt6.QtWidgets import QInputDialog, QMessageBox, QFileDialog, QApplication # Add QApplication
from PyQt6.QtGui import QTextCursor
from PyQt6.QtCore import QUrl, QBuffer, QByteArray # Add QBuffer, QByteArray
from src.services.format_service import FormatService
# Import editor types for direct checking
from ..atomic.editor.html_editor import HtmlEditor
from ..atomic.editor.text_editor import _InternalTextEdit # Import the internal class

class EditOperations:
    """处理MainWindow的编辑操作功能"""

    def __init__(self, main_window, ui_manager): # Accept ui_manager
        self.main_window = main_window
        self.ui_manager = ui_manager # Store ui_manager
        self.format_service = FormatService(main_window) # FormatService might need ui_manager later?

    # --- 基本编辑操作 ---
    def undo_action_handler(self):
        """撤销操作"""
        # get_current_editor_widget should now return the actual editor (_InternalTextEdit or HtmlEditor)
        if editor := self.main_window.get_current_editor_widget():
             if hasattr(editor, 'undo'): editor.undo()

    def redo_action_handler(self):
        """重做操作"""
        if editor := self.main_window.get_current_editor_widget():
             if hasattr(editor, 'redo'): editor.redo()

    def cut_action_handler(self):
        """剪切操作"""
        if editor := self.main_window.get_current_editor_widget():
             if hasattr(editor, 'cut'): editor.cut()

    def copy_action_handler(self):
        """复制操作"""
        if editor := self.main_window.get_current_editor_widget():
             if hasattr(editor, 'copy'): editor.copy()

    def paste(self): # Renamed from paste_action_handler to match trigger connection
        """粘贴操作，优先处理图片"""
        clipboard = QApplication.clipboard()
        mime = clipboard.mimeData()
        # Directly use the widget returned by get_current_editor_widget
        # This should be the actual _InternalTextEdit or HtmlEditor instance now
        editor = self.main_window.get_current_editor_widget()

        if not editor: # Ensure editor exists
            print("Error: No current editor widget found.")
            return

        # 1) 如果剪贴板有图片
        if mime.hasImage():
            # --- Detailed Debug Prints ---
            print("-" * 20)
            print(f"DEBUG (Image Paste): Editor Object: {editor}")
            print(f"DEBUG (Image Paste): type(editor): {type(editor)}")
            print(f"DEBUG (Image Paste): editor.__class__.__name__: {editor.__class__.__name__}")
            print(f"DEBUG (Image Paste): isinstance(editor, HtmlEditor): {isinstance(editor, HtmlEditor)}")
            # Re-import locally just for this check to ensure identity
            from ..atomic.editor.text_editor import _InternalTextEdit as LocalInternalTextEdit
            print(f"DEBUG (Image Paste): isinstance(editor, _InternalTextEdit (local)): {isinstance(editor, LocalInternalTextEdit)}")
            print(f"DEBUG (Image Paste): hasattr(editor, 'insertPlainText'): {hasattr(editor, 'insertPlainText')}")
            print("-" * 20)
            # --- End Detailed Debug Prints ---

            img = clipboard.image()  # QImage
            if img.isNull(): # Check if image is valid
                 print("Clipboard image is null.")
                 if mime.hasText():
                     if hasattr(editor, 'paste'): editor.paste()
                 return

            # 将 QImage 转成 PNG 格式的 base64
            buffer = QBuffer()
            buffer.open(QBuffer.OpenModeFlag.WriteOnly)
            if not img.save(buffer, "PNG"):
                 print("Failed to save image to buffer.")
                 if mime.hasText():
                     if hasattr(editor, 'paste'): editor.paste()
                 return
            buffer.close()

            ba: QByteArray = buffer.data()
            if ba.isEmpty():
                 print("Buffer data is empty after image save.")
                 if mime.hasText():
                     if hasattr(editor, 'paste'): editor.paste()
                 return

            b64 = bytes(ba.toBase64()).decode('utf-8')
            data_url = f"data:image/png;base64,{b64}"

            # Check type directly using isinstance for HtmlEditor
            if isinstance(editor, HtmlEditor):
                print("DEBUG: Pasting image into HtmlEditor")
                js = f"""
                (function(){{
                  var img = document.createElement('img');
                  img.src = '{data_url}';
                  var sel = window.getSelection();
                  if(sel.rangeCount > 0) {{
                    var range = sel.getRangeAt(0);
                    range.deleteContents();
                    range.insertNode(img);
                    range.setStartAfter(img);
                    range.setEndAfter(img);
                    sel.removeAllRanges();
                    sel.addRange(range);
                  }} else {{
                    document.body.appendChild(img);
                  }}
                }})();
                """
                editor.run_js(js)
                if hasattr(editor, 'setModified'): editor.setModified(True) # HtmlEditor needs explicit setModified
            # Check if it's _InternalTextEdit (which now inherits QTextEdit)
            # Use isinstance check now that the base class is correct
            elif isinstance(editor, _InternalTextEdit):
                print("DEBUG: Pasting image into _InternalTextEdit using insertHtml")
                # Use insertHtml to render the image
                cursor = editor.textCursor()
                cursor.insertHtml(f'<img src="{data_url}" alt="Clipboard Image"/>')
                if hasattr(editor, 'document'): editor.document().setModified(True)
            else:
                 # This block should ideally not be reached now
                 print(f"Pasting image not supported for this editor type: {type(editor)}")
                 if mime.hasText():
                     if hasattr(editor, 'paste'): editor.paste()
            return # Image handled (or attempted)

        # 2) 否则，如果剪贴板有文本
        elif mime.hasText():
            print(f"DEBUG: Pasting text into editor type: {type(editor)}") # Debug print
            if hasattr(editor, 'paste'):
                 editor.paste()
            else:
                 print(f"Standard paste not supported for editor type: {type(editor)}")
        else:
             print("Clipboard contains neither image nor text.")

    def select_all_action_handler(self):
        """全选操作"""
        if editor := self.main_window.get_current_editor_widget():
             if hasattr(editor, 'selectAll'): editor.selectAll()

    # --- 格式操作 ---
    def change_font(self):
        """更改字体"""
        editor = self.main_window.get_current_editor_widget()
        # Pass the actual editor instance to format service
        self.format_service.change_font(editor)

    def change_color(self):
        """更改文本颜色"""
        editor = self.main_window.get_current_editor_widget()
        # Pass the actual editor instance to format service
        self.format_service.change_color(editor)

    def insert_image(self):
        """插入图片 (from file)"""
        editor = self.main_window.get_current_editor_widget()
        # Need to import _InternalTextEdit here if not imported globally
        # from ..atomic.editor.text_editor import _InternalTextEdit # Already imported at top
        if isinstance(editor, HtmlEditor):
            file_path, _ = QFileDialog.getOpenFileName(
                self.main_window, "选择图片", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
            )
            if not file_path: return
            file_url = QUrl.fromLocalFile(file_path).toString()
            js = f"""
                (function(){{
                    var img = document.createElement('img');
                    img.src = '{file_url}';
                    var sel = window.getSelection();
                    if (sel.rangeCount > 0) {{
                        var range = sel.getRangeAt(0);
                        range.insertNode(img);
                    }} else {{
                        document.body.appendChild(img);
                    }}
                }})();
            """
            editor.run_js(js)
            if hasattr(editor, 'setModified'): editor.setModified(True)
        elif isinstance(editor, _InternalTextEdit):
             file_path, _ = QFileDialog.getOpenFileName(
                 self.main_window, "选择图片", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
             )
             if not file_path: return
             # Use insertHtml to insert an img tag pointing to the local file
             file_url = QUrl.fromLocalFile(file_path).toString()
             cursor = editor.textCursor()
             cursor.insertHtml(f'<img src="{file_url}" alt="{os.path.basename(file_path)}"/>')
             if hasattr(editor, 'document'): editor.document().setModified(True)
        else:
             print(f"Insert image from file not supported for editor type: {type(editor)}")


    # --- 查找和替换 ---
    def find_text(self):
        """查找文本"""
        editor = self.main_window.get_current_editor_widget()
        if not editor or not (hasattr(editor, 'find') and hasattr(editor, 'textCursor')):
             if hasattr(self.main_window, 'statusBar'): self.main_window.statusBar().showMessage("当前编辑器不支持查找。", 3000)
             return

        text, ok = QInputDialog.getText(self.main_window, "查找", "输入要查找的文本:")
        if ok and text:
            cursor = editor.textCursor()
            if cursor.hasSelection():
                cursor.setPosition(max(cursor.selectionStart(), cursor.selectionEnd()))
            editor.setTextCursor(cursor)

            found = editor.find(text)
            if not found:
                cursor.movePosition(QTextCursor.MoveOperation.Start)
                editor.setTextCursor(cursor)
                found = editor.find(text)
                if found:
                    if hasattr(self.main_window, 'statusBar'): self.main_window.statusBar().showMessage(f"找到文本（从文档开头）: {text}", 3000)
                else:
                    if hasattr(self.main_window, 'statusBar'): self.main_window.statusBar().showMessage(f"未找到文本: {text}", 3000)
            elif found:
                 if hasattr(self.main_window, 'statusBar'): self.main_window.statusBar().showMessage(f"找到文本: {text}", 3000)


    def replace_text(self):
        """替换文本"""
        editor = self.main_window.get_current_editor_widget()
        if not editor or not (hasattr(editor, 'find') and hasattr(editor, 'textCursor')):
             if hasattr(self.main_window, 'statusBar'): self.main_window.statusBar().showMessage("当前编辑器不支持替换。", 3000)
             return

        find_text, ok = QInputDialog.getText(self.main_window, "替换", "输入要查找的文本:")
        if not (ok and find_text): return

        replace_text, ok = QInputDialog.getText(self.main_window, "替换", "输入替换文本:")
        if not ok: return

        cursor = editor.textCursor()
        replaced_count = 0
        if cursor.hasSelection() and cursor.selectedText() == find_text:
            cursor.insertText(replace_text)
            replaced_count += 1

        cursor.movePosition(QTextCursor.MoveOperation.Start)
        editor.setTextCursor(cursor)
        while editor.find(find_text):
            cursor = editor.textCursor()
            cursor.insertText(replace_text)
            replaced_count += 1

        if replaced_count > 0:
            if hasattr(self.main_window, 'statusBar'): self.main_window.statusBar().showMessage(f"已替换 {replaced_count} 处。", 3000)
            if hasattr(editor, 'document'): editor.document().setModified(True)
        else:
            if hasattr(self.main_window, 'statusBar'): self.main_window.statusBar().showMessage(f"未找到要替换的文本: {find_text}", 3000)
