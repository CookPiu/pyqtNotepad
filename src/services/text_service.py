# -*- coding: utf-8 -*-
"""
Handles text manipulation operations like find and replace.
Interacts with the current editor provided by the MainWindow.
"""

from PyQt6.QtWidgets import QInputDialog, QMessageBox, QTextEdit
from PyQt6.QtGui import QTextCursor
from PyQt6.QtCore import QSignalBlocker

class TextService:
    def __init__(self, main_window):
        """
        Initialize the TextService.
        Args:
            main_window: Reference to the MainWindow instance for UI interactions
                         and potentially storing last search/replace terms.
        """
        self.main_window = main_window
        self._last_find_text = ""
        self._last_replace_text = ""

    def find_text(self, editor: QTextEdit):
        """Handles the find text operation."""
        # Logic extracted and adapted from MainWindow.find_text
        if not editor: return

        text, ok = QInputDialog.getText(self.main_window, "查找", "输入要查找的文本:", text=self._last_find_text)
        if ok and text:
            self._last_find_text = text
            if not editor.find(text):
                cursor = editor.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.Start)
                editor.setTextCursor(cursor)
                if not editor.find(text):
                    QMessageBox.information(self.main_window, "查找", f"未找到 '{text}'")
                else:
                    editor.ensureCursorVisible()
            else:
                editor.ensureCursorVisible()

    def replace_text(self, editor: QTextEdit):
        """Handles the replace text operation."""
        # Logic extracted and adapted from MainWindow.replace_text
        if not editor: return

        find_text, ok1 = QInputDialog.getText(self.main_window, "查找", "输入要查找的文本:", text=self._last_find_text)
        if ok1 and find_text:
            self._last_find_text = find_text
            replace_text, ok2 = QInputDialog.getText(self.main_window, "替换", "输入要替换的文本:", text=self._last_replace_text)
            if ok2:
                self._last_replace_text = replace_text
                reply = QMessageBox.question(self.main_window, '替换', f"查找 '{find_text}' 并替换为 '{replace_text}'？\n选择 'Yes' 替换所有, 'No' 查找下一个。",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)

                if reply == QMessageBox.StandardButton.Cancel: return

                if reply == QMessageBox.StandardButton.Yes: # Replace All
                    cursor = editor.textCursor()
                    cursor.movePosition(QTextCursor.MoveOperation.Start)
                    editor.setTextCursor(cursor)
                    count = 0
                    editor.document().beginMacro("Replace All")
                    while editor.find(find_text):
                        cursor = editor.textCursor()
                        if cursor.selectedText() == find_text:
                             cursor.insertText(replace_text)
                             count += 1
                        else: break
                    editor.document().endMacro()

                    if count > 0:
                         self.main_window.statusBar.showMessage(f"已替换 {count} 处匹配项")
                    else:
                         self.main_window.statusBar.showMessage("未找到匹配项")
                elif reply == QMessageBox.StandardButton.No: # Find Next
                    if not editor.find(find_text):
                        cursor = editor.textCursor()
                        cursor.movePosition(QTextCursor.MoveOperation.Start)
                        editor.setTextCursor(cursor)
                        if not editor.find(find_text):
                            QMessageBox.information(self.main_window, "查找", f"未找到 '{find_text}'")
                        else: editor.ensureCursorVisible()
                    else: editor.ensureCursorVisible()

                # Consider notifying MainWindow to update action states if needed
                # self.main_window.update_edit_actions_state(editor) # Example

# Note: Similar to FormatService, direct UI interaction (dialogs, status bar)
# might ideally be handled differently in a stricter MVC/MVP pattern.
pass
