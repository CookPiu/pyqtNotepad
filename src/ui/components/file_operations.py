import os
from PyQt6.QtWidgets import (QFileDialog, QMessageBox, QApplication)
from PyQt6.QtCore import QSignalBlocker
from src.ui.editor import TextEditWithLineNumbers
from src.utils.pdf_utils import cleanup_temp_images

class FileOperations:
    """处理MainWindow的文件操作功能"""
    
    def __init__(self, main_window):
        self.main_window = main_window
    
    def new_file(self):
        """创建新文件"""
        # 使用导入的TextEditWithLineNumbers（现在基于QPlainTextEdit）
        editor = TextEditWithLineNumbers()
        # 为QPlainTextEdit设置字体大小
        font = editor.font()
        font.setPointSize(12)
        editor.setFont(font)
        self.main_window.untitled_counter += 1
        tab_name = f"未命名-{self.main_window.untitled_counter}"
        editor.setProperty("untitled_name", tab_name)
        # 不需要手动连接在TextEditWithLineNumbers中处理的信号
        index = self.main_window.tab_widget.addTab(editor, tab_name)
        self.main_window.tab_widget.setCurrentIndex(index)
        # 直接在编辑器实例上设置属性
        editor.setProperty("file_path", None)
        editor.setProperty("is_new", True)
        editor.setProperty("is_pdf_converted", False)
        editor.setProperty("pdf_temp_dir", None)
        editor.document().setModified(False)  # 确保新文件开始时未修改
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
        # 检查文件是否已经打开
        for i in range(self.main_window.tab_widget.count()):
            widget = self.main_window.tab_widget.widget(i)
            if isinstance(widget, TextEditWithLineNumbers) and widget.property("file_path") == abs_file_path:
                self.main_window.tab_widget.setCurrentIndex(i)
                self.main_window.statusBar.showMessage(f"切换到已打开文件: {file_path}")
                return

        # 使用导入的TextEditWithLineNumbers
        editor = TextEditWithLineNumbers()
        editor.setFontPointSize(12)
        try:
            _, ext = os.path.splitext(file_path)
            file_base_name = os.path.basename(file_path)

            if ext.lower() == '.pdf':
                self.main_window.open_pdf_preview(abs_file_path)
                # PDF预览是模态的或处理自己的生命周期，不要在这里添加编辑器标签
                return
            elif ext.lower() == '.html':
                # 使用QSignalBlocker防止过早的修改信号
                with open(abs_file_path, 'r', encoding='utf-8') as f: content = f.read()
                with QSignalBlocker(editor.document()): editor.setHtml(content)
            else:  # 处理文本文件
                try:
                    with open(abs_file_path, 'r', encoding='utf-8') as f: content = f.read()
                except UnicodeDecodeError:  # 回退编码
                    with open(abs_file_path, 'r', encoding='gbk') as f: content = f.read()
                # 这里也使用QSignalBlocker
                with QSignalBlocker(editor.document()): editor.setPlainText(content)

            # 将新编辑器添加为标签
            index = self.main_window.tab_widget.addTab(editor, file_base_name)
            self.main_window.tab_widget.setCurrentIndex(index)
            editor.setProperty("file_path", abs_file_path)
            editor.setProperty("is_new", False)
            editor.setProperty("is_pdf_converted", False)  # 重置PDF标志
            editor.setProperty("pdf_temp_dir", None)    # 重置临时目录
            editor.document().setModified(False)  # 最初标记为未修改
            self.main_window.statusBar.showMessage(f"已打开: {file_path}")
            self.main_window.update_edit_actions_state(editor)  # 更新新标签的操作

        except Exception as e:
            QMessageBox.critical(self.main_window, "错误", f"无法打开文件 '{file_path}':\n{str(e)}")
            # 如果编辑器创建中途失败，清理标签
            # 检查'index'是否存在，以及该索引处的小部件是否是有问题的编辑器
            if 'index' in locals() and index < self.main_window.tab_widget.count() and self.main_window.tab_widget.widget(index) == editor:
                self.main_window.tab_widget.removeTab(index)
                editor.deleteLater()
    
    def save_file(self) -> bool:
        """保存当前文件"""
        editor = self.main_window.get_current_editor()
        if not editor: return False

        if editor.property("is_new") or not editor.property("file_path"):
            return self.save_file_as()
        else:
            file_path = editor.property("file_path")
            try:
                _, ext = os.path.splitext(file_path)
                # 根据扩展名检查是保存为HTML还是纯文本
                content_to_save = editor.toHtml() if ext.lower() == '.html' else editor.toPlainText()
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content_to_save)
                editor.document().setModified(False)
                self.main_window.statusBar.showMessage(f"已保存: {file_path}")
                self.main_window.update_tab_title(False)  # 立即更新标签标题
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
        is_plain = editor.toPlainText() == editor.toHtml()  # 基本检查内容是否可能是纯文本
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
                # 根据最终扩展名保存为HTML或纯文本
                content_to_save = editor.toHtml() if save_ext.lower() == '.html' else editor.toPlainText()
                with open(abs_file_path, 'w', encoding='utf-8') as f:
                    f.write(content_to_save)

                # 更新编辑器属性
                editor.setProperty("file_path", abs_file_path)
                editor.setProperty("is_new", False)
                editor.setProperty("untitled_name", None)  # 清除未命名名称
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
        if not isinstance(widget, TextEditWithLineNumbers):
            self.main_window.tab_widget.removeTab(index)
            widget.deleteLater()  # 确保非编辑器小部件被清理
            return

        editor = widget  # 现在我们知道它是一个编辑器
        if editor.document().isModified():
            self.main_window.tab_widget.setCurrentIndex(index)  # 确保要关闭的标签对话框处于活动状态
            tab_name = self.main_window.tab_widget.tabText(index)
            ret = QMessageBox.warning(self.main_window, "关闭标签页", f"文档 '{tab_name}' 已被修改。\n是否保存更改？",
                                    QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
            if ret == QMessageBox.StandardButton.Save:
                if not self.save_file(): return  # 如果保存失败，不要关闭
            elif ret == QMessageBox.StandardButton.Cancel: return  # 如果取消，不要关闭

        # 如果此标签是转换后的PDF，则清理PDF临时文件
        temp_dir = editor.property("pdf_temp_dir")
        if temp_dir:
            cleanup_temp_images(temp_dir)  # 使用导入的函数

        # 在移除之前安全地断开信号
        if self.main_window.previous_editor == editor: self.main_window.previous_editor = None
        try: editor.document().undoAvailable.disconnect()
        except TypeError: pass
        try: editor.document().redoAvailable.disconnect()
        except TypeError: pass
        try: editor.copyAvailable.disconnect()
        except TypeError: pass
        try: editor.document().modificationChanged.disconnect()
        except TypeError: pass

        self.main_window.tab_widget.removeTab(index)
        editor.deleteLater()  # 安排删除

        # 如果关闭了最后一个标签，创建一个新标签
        if self.main_window.tab_widget.count() == 0:
            self.new_file()
        else:
            # 根据可能的新当前标签更新操作状态
            current_editor = self.main_window.get_current_editor()
            if current_editor:
                self.main_window.update_edit_actions_state(current_editor)
            else:  # 关闭后没有编辑器？如果调用new_file，这不应该发生
                self.main_window.update_edit_actions_state(None)