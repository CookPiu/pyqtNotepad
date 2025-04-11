from PyQt6.QtWidgets import QInputDialog, QMessageBox
from PyQt6.QtGui import QTextCursor


class TextOperations:
    def __init__(self, parent, text_edit):
        self.parent = parent
        self.text_edit = text_edit
    
    def find_text(self):
        # 简单实现，实际应用中可以添加一个查找对话框
        text, ok = QInputDialog.getText(self.parent, "查找", "输入要查找的文本:")
        if ok and text:
            cursor = self.text_edit.textCursor()
            # 保存原始位置
            original_position = cursor.position()
            # 从头开始查找
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.text_edit.setTextCursor(cursor)
            if not self.text_edit.find(text):
                # 如果没找到，恢复原始位置
                cursor.setPosition(original_position)
                self.text_edit.setTextCursor(cursor)
                QMessageBox.information(self.parent, "查找", f"未找到 '{text}'")
    
    def replace_text(self):
        # 简单实现，实际应用中可以添加一个替换对话框
        find_text, ok = QInputDialog.getText(self.parent, "替换", "输入要查找的文本:")
        if ok and find_text:
            replace_text, ok = QInputDialog.getText(self.parent, "替换", "输入要替换的文本:")
            if ok:
                cursor = self.text_edit.textCursor()
                # 保存原始位置
                original_position = cursor.position()
                # 从头开始查找
                cursor.movePosition(QTextCursor.MoveOperation.Start)
                self.text_edit.setTextCursor(cursor)
                found = False
                while self.text_edit.find(find_text):
                    found = True
                    cursor = self.text_edit.textCursor()
                    cursor.insertText(replace_text)
                
                if not found:
                    # 如果没找到，恢复原始位置
                    cursor.setPosition(original_position)
                    self.text_edit.setTextCursor(cursor)
                    QMessageBox.information(self.parent, "替换", f"未找到 '{find_text}'")