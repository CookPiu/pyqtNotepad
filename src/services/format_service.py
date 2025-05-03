# -*- coding: utf-8 -*-
"""
Handles text formatting operations like changing font, color, and inserting images.
# Interacts with the current editor provided by the MainWindow or UIManager.
"""
from typing import Union # For type hinting
from PyQt6.QtWidgets import QFontDialog, QColorDialog, QFileDialog, QMessageBox, QWidget # Use QWidget
from PyQt6.QtGui import QFont, QColor, QImage, QTextDocument
from PyQt6.QtCore import QUrl, Qt, QDateTime
import os

# Import specific editor types for checking capabilities
from src.ui.atomic.editor.text_editor import TextEditor
from src.ui.atomic.editor.html_editor import HtmlEditor

class FormatService:
    def __init__(self, main_window):
        """
        Initialize the FormatService.
        Args:
            main_window: Reference to the MainWindow instance for UI interactions.
        """
        self.main_window = main_window

    def change_font(self, editor: QWidget):
        """Opens font dialog and applies selected font to the editor."""
        # Check if editor supports required methods
        if not editor or not hasattr(editor, 'currentFont') or not hasattr(editor, 'setCurrentFont') or not hasattr(editor, 'document'):
             QMessageBox.warning(self.main_window, "错误", "当前控件不支持字体更改。")
             return
        font, ok = QFontDialog.getFont(editor.currentFont(), self.main_window, "选择字体")
        if ok:
            # Use forwarded methods if available
            if hasattr(editor, 'setCurrentFont'):
                 editor.setCurrentFont(font)
            if hasattr(editor, 'document'):
                 editor.document().setModified(True)

    def change_color(self, editor: QWidget):
        """Opens color dialog and applies selected color to the editor."""
        # Check if editor supports required methods
        if not editor or not hasattr(editor, 'textColor') or not hasattr(editor, 'setTextColor') or not hasattr(editor, 'document'):
             QMessageBox.warning(self.main_window, "错误", "当前控件不支持颜色更改。")
             return
        color = QColorDialog.getColor(editor.textColor(), self.main_window, "选择颜色")
        if color.isValid():
            # Use forwarded methods if available
            if hasattr(editor, 'setTextColor'):
                 editor.setTextColor(color)
            if hasattr(editor, 'document'):
                 editor.document().setModified(True)

    def insert_image(self, editor: QWidget):
        """Opens file dialog to insert an image into the editor, handling different editor types."""
        if not editor:
             QMessageBox.warning(self.main_window, "插入图片", "没有活动的编辑器。")
             return

        file_name, _ = QFileDialog.getOpenFileName(self.main_window, "选择图片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif)")
        if not file_name:
            return # User cancelled

        try:
            if isinstance(editor, HtmlEditor):
                # --- HTML Editor Logic (Using QWebEngineView) ---
                # Convert file path to file:// URL for JS
                file_url = QUrl.fromLocalFile(file_name).toString()
                # Escape backslashes for JS string literal
                js_file_url = file_url.replace("\\", "\\\\")

                # Use the JS snippet provided by the user
                js_code = f"""
                  var img = document.createElement("img");
                  img.src = "{js_file_url}";
                  img.alt = "{os.path.basename(file_name)}"; // Add alt text
                  // Attempt to insert at cursor/selection (basic example)
                  var sel = window.getSelection();
                  if (sel.rangeCount > 0) {{
                      var range = sel.getRangeAt(0);
                      range.deleteContents(); // Remove selected content if any
                      range.insertNode(img);
                      // Optional: Move cursor after image
                      range.setStartAfter(img);
                      range.collapse(true);
                      sel.removeAllRanges();
                      sel.addRange(range);
                  }} else {{
                      // Fallback: Append to body if no selection
                      document.body.appendChild(img);
                  }}
                  // Manually trigger modification state change
                  // This requires a way for JS to call back to Python or polling
                  // For now, we assume insertion modifies the document
                """
                # Use page().runJavaScript()
                editor.page().runJavaScript(js_code)
                self.main_window.statusBar.showMessage(f"已插入图片: {os.path.basename(file_name)}")
                # Manually set modified state as JS changes might not trigger signals
                editor.setModified(True)

            # Keep the TextEditor logic as fallback, ensure it still uses document/textCursor check
            elif hasattr(editor, 'document') and hasattr(editor, 'textCursor'):
                # --- Text Editor Logic (Existing, with viewport check) ---
                target_viewport = None
                if isinstance(editor, TextEditor) and hasattr(editor, '_editor'):
                     target_viewport = editor._editor.viewport()
                elif hasattr(editor, 'viewport'):
                     target_viewport = editor.viewport()

                if not target_viewport:
                     QMessageBox.warning(self.main_window, "插入图片", "无法确定编辑器的视口。")
                     return

                image = QImage(file_name)
                if image.isNull():
                    QMessageBox.warning(self.main_window, "插入图片", "无法加载图片！")
                    return

                max_width = target_viewport.width() - 40 # Adjust margin as needed
                if image.width() > max_width:
                    image = image.scaledToWidth(max_width, Qt.TransformationMode.SmoothTransformation)

                image_url = QUrl.fromLocalFile(file_name)
                document = editor.document()
                # Create a unique resource name
                resource_name = f"{image_url.toString()}_{QDateTime.currentMSecsSinceEpoch()}"
                document.addResource(QTextDocument.ResourceType.ImageResource, QUrl(resource_name), image)

                cursor = editor.textCursor()
                cursor.insertImage(resource_name)
                self.main_window.statusBar.showMessage(f"已插入图片: {os.path.basename(file_name)}")
                editor.document().setModified(True)
            else:
                # Fallback for unsupported editor types
                QMessageBox.warning(self.main_window, "插入图片", "当前控件不支持插入图片。")

        except Exception as e:
            QMessageBox.critical(self.main_window, "插入图片错误", f"插入图片时出错: {str(e)}")


# Note: This service might need refinement. Currently, it directly uses methods
# that were part of MainWindow. Ideally, UI interactions (dialogs, status bar)
# should be signaled back to the MainWindow or handled via callbacks/interfaces.
# For this initial refactoring, we keep the direct interaction for simplicity.
pass
