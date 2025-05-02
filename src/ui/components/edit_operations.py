from PyQt6.QtWidgets import QInputDialog, QMessageBox
from PyQt6.QtGui import QTextCursor
from src.services.format_service import FormatService

class EditOperations:
    """处理MainWindow的编辑操作功能"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.format_service = FormatService(main_window)
    
    # --- 基本编辑操作 ---
    def undo_action_handler(self):
        """撤销操作"""
        if editor := self.main_window.get_current_editor(): editor.undo()
    
    def redo_action_handler(self):
        """重做操作"""
        if editor := self.main_window.get_current_editor(): editor.redo()
    
    def cut_action_handler(self):
        """剪切操作"""
        if editor := self.main_window.get_current_editor(): editor.cut()
    
    def copy_action_handler(self):
        """复制操作"""
        if editor := self.main_window.get_current_editor(): editor.copy()
    
    def paste_action_handler(self):
        """粘贴操作"""
        if editor := self.main_window.get_current_editor(): editor.paste()
    
    def select_all_action_handler(self):
        """全选操作"""
        if editor := self.main_window.get_current_editor(): editor.selectAll()
    
    # --- 格式操作 ---
    def change_font(self):
        """更改字体"""
        editor = self.main_window.get_current_editor()
        self.format_service.change_font(editor)
    
    def change_color(self):
        """更改文本颜色"""
        editor = self.main_window.get_current_editor()
        self.format_service.change_color(editor)
    
    def insert_image(self):
        """插入图片"""
        editor = self.main_window.get_current_editor()
        self.format_service.insert_image(editor)
    
    # --- 查找和替换 ---
    def find_text(self):
        """查找文本"""
        editor = self.main_window.get_current_editor()
        if not editor: return
        
        text, ok = QInputDialog.getText(self.main_window, "查找", "输入要查找的文本:")
        if ok and text:
            # 从当前光标位置开始查找
            cursor = editor.textCursor()
            # 保存初始位置以检测循环
            initial_position = cursor.position()
            
            # 如果有选择，从选择的末尾开始查找
            if cursor.hasSelection():
                cursor.setPosition(max(cursor.selectionStart(), cursor.selectionEnd()))
            
            # 执行查找
            found = editor.find(text)
            
            # 如果没有找到，尝试从文档开头查找
            if not found:
                cursor.movePosition(QTextCursor.MoveOperation.Start)
                editor.setTextCursor(cursor)
                found = editor.find(text)
                
                if found:
                    self.main_window.statusBar.showMessage(f"找到文本（从文档开头）: {text}")
                else:
                    self.main_window.statusBar.showMessage(f"未找到文本: {text}")
            else:
                self.main_window.statusBar.showMessage(f"找到文本: {text}")
    
    def replace_text(self):
        """替换文本"""
        editor = self.main_window.get_current_editor()
        if not editor: return
        
        find_text, ok = QInputDialog.getText(self.main_window, "替换", "输入要查找的文本:")
        if not (ok and find_text): return
        
        replace_text, ok = QInputDialog.getText(self.main_window, "替换", "输入替换文本:")
        if not ok: return  # 用户可能取消了第二个对话框
        
        # 获取当前光标
        cursor = editor.textCursor()
        
        # 如果有选择并且选择的文本与查找文本匹配，直接替换
        if cursor.hasSelection() and cursor.selectedText() == find_text:
            cursor.insertText(replace_text)
            editor.setTextCursor(cursor)
        
        # 否则，查找下一个匹配项
        found = editor.find(find_text)
        if found:
            # 替换找到的文本
            cursor = editor.textCursor()
            cursor.insertText(replace_text)
            self.main_window.statusBar.showMessage(f"已替换: {find_text} -> {replace_text}")
        else:
            # 如果没有找到，尝试从文档开头查找
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            editor.setTextCursor(cursor)
            found = editor.find(find_text)
            
            if found:
                cursor = editor.textCursor()
                cursor.insertText(replace_text)
                self.main_window.statusBar.showMessage(f"已替换（从文档开头）: {find_text} -> {replace_text}")
            else:
                self.main_window.statusBar.showMessage(f"未找到要替换的文本: {find_text}")