# -*- coding: utf-8 -*-
"""
Handles text formatting operations like changing font, color, and inserting images.
Interacts with the current editor provided by the MainWindow.
"""

from PyQt6.QtWidgets import QFontDialog, QColorDialog, QFileDialog, QMessageBox, QTextEdit
from PyQt6.QtGui import QFont, QColor, QImage, QTextDocument
from PyQt6.QtCore import QUrl, Qt, QDateTime
import os

class FormatService:
    def __init__(self, main_window):
        """
        Initialize the FormatService.
        Args:
            main_window: Reference to the MainWindow instance for UI interactions.
        """
        self.main_window = main_window

    def change_font(self, editor: QTextEdit):
        """Opens font dialog and applies selected font to the editor."""
        # Logic to be extracted from MainWindow.change_font
        if not editor: return
        font, ok = QFontDialog.getFont(editor.currentFont(), self.main_window, "选择字体")
        if ok:
            editor.setCurrentFont(font)
            editor.document().setModified(True)

    def change_color(self, editor: QTextEdit):
        """Opens color dialog and applies selected color to the editor."""
        # Logic to be extracted from MainWindow.change_color
        if not editor: return
        color = QColorDialog.getColor(editor.textColor(), self.main_window, "选择颜色")
        if color.isValid():
            editor.setTextColor(color)
            editor.document().setModified(True)

    def insert_image(self, editor: QTextEdit):
        """Opens file dialog to insert an image into the editor."""
        # Logic to be extracted from MainWindow.insert_image
        if not editor:
             QMessageBox.warning(self.main_window, "插入图片", "没有活动的编辑窗口！")
             return

        file_name, _ = QFileDialog.getOpenFileName(self.main_window, "选择图片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif)")
        if file_name:
            try:
                image = QImage(file_name)
                if image.isNull():
                    QMessageBox.warning(self.main_window, "插入图片", "无法加载图片！")
                    return

                max_width = editor.viewport().width() - 40
                if image.width() > max_width:
                    image = image.scaledToWidth(max_width, Qt.TransformationMode.SmoothTransformation)

                image_url = QUrl.fromLocalFile(file_name)
                document = editor.document()
                resource_name = f"{image_url.toString()}_{QDateTime.currentMSecsSinceEpoch()}"
                document.addResource(QTextDocument.ResourceType.ImageResource, QUrl(resource_name), image)

                editor.textCursor().insertImage(resource_name)
                self.main_window.statusBar.showMessage(f"已插入图片: {os.path.basename(file_name)}")
                editor.document().setModified(True)
            except Exception as e:
                QMessageBox.critical(self.main_window, "插入图片错误", f"插入图片时出错: {str(e)}")


# Note: This service might need refinement. Currently, it directly uses methods
# that were part of MainWindow. Ideally, UI interactions (dialogs, status bar)
# should be signaled back to the MainWindow or handled via callbacks/interfaces.
# For this initial refactoring, we keep the direct interaction for simplicity.
pass
