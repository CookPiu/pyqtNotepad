#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件操作模块
负责处理文件的打开、保存等操作
"""

import os
from PyQt6.QtWidgets import QFileDialog, QMessageBox


class FileOperations:
    """文件操作类，处理文件的新建、打开、保存等操作"""
    
    def __init__(self, parent, text_edit, status_bar):
        """初始化文件操作类
        
        Args:
            parent: 父窗口，用于显示对话框
            text_edit: 文本编辑器组件
            status_bar: 状态栏组件，用于显示操作状态
        """
        self.parent = parent
        self.text_edit = text_edit
        self.statusBar = status_bar
        self.current_file = None
    
    def new_file(self):
        if self.maybe_save():
            self.text_edit.clear()
            self.current_file = None
            self.statusBar.showMessage("新建文件")
    
    def open_file(self):
        if self.maybe_save():
            file_name, _ = QFileDialog.getOpenFileName(self.parent, "打开文件", "", "HTML文件 (*.html);;文本文件 (*.txt);;所有文件 (*)")
            if file_name:
                # 根据文件扩展名决定如何打开
                _, ext = os.path.splitext(file_name)
                if ext.lower() == '.html':
                    with open(file_name, 'r', encoding='utf-8') as f:
                        html = f.read()
                    self.text_edit.setHtml(html)
                else:
                    with open(file_name, 'r', encoding='utf-8') as f:
                        text = f.read()
                    self.text_edit.setPlainText(text)
                self.current_file = file_name
                self.statusBar.showMessage(f"已打开: {file_name}")
    
    def save_file(self):
        if self.current_file:
            # 根据文件扩展名决定如何保存
            _, ext = os.path.splitext(self.current_file)
            with open(self.current_file, 'w', encoding='utf-8') as f:
                if ext.lower() == '.html':
                    f.write(self.text_edit.toHtml())
                else:
                    f.write(self.text_edit.toPlainText())
            self.statusBar.showMessage(f"已保存: {self.current_file}")
            return True
        else:
            return self.save_file_as()
    
    def save_file_as(self):
        file_name, selected_filter = QFileDialog.getSaveFileName(self.parent, "保存文件", "", "HTML文件 (*.html);;文本文件 (*.txt);;所有文件 (*)")
        if file_name:
            # 确保文件有正确的扩展名
            _, ext = os.path.splitext(file_name)
            if not ext:
                if "HTML" in selected_filter:
                    file_name += ".html"
                elif "文本" in selected_filter:
                    file_name += ".txt"
            
            # 根据扩展名决定保存格式
            _, ext = os.path.splitext(file_name)
            with open(file_name, 'w', encoding='utf-8') as f:
                if ext.lower() == '.html':
                    f.write(self.text_edit.toHtml())
                else:
                    f.write(self.text_edit.toPlainText())
            self.current_file = file_name
            self.statusBar.showMessage(f"已保存: {file_name}")
            return True
        return False
    
    def maybe_save(self):
        if not self.text_edit.document().isModified():
            return True
        
        ret = QMessageBox.warning(self.parent, "多功能记事本",
                                "文档已被修改。\n是否保存更改？",
                                QMessageBox.StandardButton.Save | 
                                QMessageBox.StandardButton.Discard | 
                                QMessageBox.StandardButton.Cancel)
        
        if ret == QMessageBox.StandardButton.Save:
            return self.save_file()
        elif ret == QMessageBox.StandardButton.Cancel:
            return False
        return True