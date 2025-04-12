#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
格式操作模块
负责处理文本格式化、字体颜色更改、图片插入等操作
"""

import os
import base64
from PyQt6.QtWidgets import QFontDialog, QColorDialog, QFileDialog, QMessageBox
from PyQt6.QtGui import QImage, QImageWriter, QTextDocument
from PyQt6.QtCore import Qt, QUrl, QByteArray, QBuffer


class FormatOperations:
    """格式操作类，处理文本格式化、字体颜色更改、图片插入等操作"""
    
    def __init__(self, parent, text_edit, status_bar):
        """初始化格式操作类
        
        Args:
            parent: 父窗口，用于显示对话框
            text_edit: 文本编辑器组件
            status_bar: 状态栏组件，用于显示操作状态
        """
        self.parent = parent
        self.text_edit = text_edit
        self.statusBar = status_bar
    
    def change_font(self):
        current = self.text_edit.currentFont()
        font, ok = QFontDialog.getFont(current, self.parent, "选择字体")
        if ok:
            self.text_edit.setCurrentFont(font)
    
    def change_color(self):
        color = QColorDialog.getColor(self.text_edit.textColor(), self.parent, "选择颜色")
        if color.isValid():
            self.text_edit.setTextColor(color)
    
    def insert_image(self):
        # 打开文件对话框选择图片
        file_name, _ = QFileDialog.getOpenFileName(self.parent, "选择图片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif)")
        if file_name:
            # 获取当前光标位置
            cursor = self.text_edit.textCursor()
            
            # 创建图片对象
            image = QImage(file_name)
            if image.isNull():
                QMessageBox.warning(self.parent, "插入图片", "无法加载图片！")
                return
            
            # 如果图片太大，调整大小
            if image.width() > 800:
                image = image.scaledToWidth(800, Qt.TransformationMode.SmoothTransformation)
            
            # 将图片转换为Base64编码
            
            # 确定图片格式
            _, ext = os.path.splitext(file_name)
            img_format = ext[1:].upper()  # 去掉点号，转为大写
            if img_format.lower() == 'jpg':
                img_format = 'JPEG'
            
            # 将图片转换为字节数组
            byte_array = QByteArray()
            buffer = QBuffer(byte_array)
            buffer.open(QBuffer.OpenModeFlag.WriteOnly)
            image_writer = QImageWriter(buffer, img_format.encode())
            image_writer.write(image)
            buffer.close()
            
            # 转换为Base64编码
            img_data = byte_array.data()
            base64_data = base64.b64encode(img_data).decode('utf-8')
            
            # 创建内联图片URL
            img_url = f"data:image/{img_format.lower()};base64,{base64_data}"
            
            # 将图片插入到文档中
            document = self.text_edit.document()
            document.addResource(QTextDocument.ResourceType.ImageResource, QUrl(img_url), image)
            cursor.insertImage(img_url)
            
            self.statusBar.showMessage(f"已插入图片: {os.path.basename(file_name)}")