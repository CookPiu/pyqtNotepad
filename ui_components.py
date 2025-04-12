#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
UI组件模块
包含应用程序中使用的自定义UI组件
"""

import sys
from PyQt6.QtWidgets import QWidget, QTextEdit
from PyQt6.QtGui import QPainter, QTextCursor
from PyQt6.QtCore import Qt, QRect, QPointF, pyqtSignal


class LineNumberArea(QWidget):
    """行号区域组件，用于在文本编辑器左侧显示行号"""
    
    def __init__(self, editor):
        """初始化行号区域
        
        Args:
            editor: 父文本编辑器组件
        """
        super().__init__(editor)
        self.editor = editor
        self.setFixedWidth(40)  # 初始宽度，会根据行号数量自动调整

    def paintEvent(self, event):
        # 绘制行号区域
        painter = QPainter(self)
        painter.fillRect(event.rect(), Qt.GlobalColor.lightGray)
        
        # 获取可见区域的第一个块
        block = self.editor.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.editor.blockBoundingGeometry(block).translated(self.editor.contentOffset()).top()
        bottom = top + self.editor.blockBoundingRect(block).height()
        
        # 绘制行号
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(Qt.GlobalColor.black)
                # 创建一个矩形区域来绘制文本
                rect = QRect(0, int(top), self.width() - 5, self.editor.fontMetrics().height())
                painter.drawText(rect, Qt.AlignmentFlag.AlignRight, number)
            
            block = block.next()
            top = bottom
            bottom = top + self.editor.blockBoundingRect(block).height()
            block_number += 1


class TextEditWithLineNumbers(QTextEdit):
    """带行号的文本编辑器组件"""
    
    def __init__(self, parent=None):
        """初始化带行号的文本编辑器
        
        Args:
            parent: 父组件
        """
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)
        
        # 连接信号以更新行号区域
        self.document().blockCountChanged.connect(self.update_line_number_area_width)
        self.verticalScrollBar().valueChanged.connect(self.update_line_number_area)
        self.textChanged.connect(self.update_line_number_area)
        self.document().documentLayoutChanged.connect(self.update_line_number_area)
        self.textChanged.connect(self.document_modified)
        
        # 初始化行号区域宽度
        self.update_line_number_area_width(0)
        
        # 设置文档修改状态标志
        self.document().setModified(False)
    
    def firstVisibleBlock(self):
        # 获取可见区域的第一个文本块
        cursor = QTextCursor(self.document())
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        for i in range(self.document().blockCount()):
            block = self.document().findBlockByNumber(i)
            rect = self.document().documentLayout().blockBoundingRect(block)
            if rect.translated(0, -self.verticalScrollBar().value()).top() >= 0:
                return block
            cursor.movePosition(QTextCursor.MoveOperation.NextBlock)
        return self.document().firstBlock()
    
    def blockBoundingGeometry(self, block):
        # 获取块的几何信息
        return self.document().documentLayout().blockBoundingRect(block)
    
    def blockBoundingRect(self, block):
        # 获取块的边界矩形
        return self.document().documentLayout().blockBoundingRect(block)
    
    def contentOffset(self):
        # 获取内容偏移
        return QPointF(0, -self.verticalScrollBar().value())
    
    def update_line_number_area_width(self, _):
        # 更新行号区域宽度
        digits = len(str(max(1, self.document().blockCount())))
        width = 10 + self.fontMetrics().horizontalAdvance('9') * digits
        if self.line_number_area.width() != width:
            self.line_number_area.setFixedWidth(width)
            self.setViewportMargins(width, 0, 0, 0)
    
    def update_line_number_area(self):
        # 更新行号区域
        self.line_number_area.update(0, 0, self.line_number_area.width(), self.height())
        if self.verticalScrollBar().value() != self.verticalScrollBar().maximum():
            self.setViewportMargins(self.line_number_area.width(), 0, 0, 0)
    
    def resizeEvent(self, event):
        """处理调整大小事件
        
        Args:
            event: 调整大小事件
        """
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area.width(), cr.height()))
    
    def paintEvent(self, event):
        """处理绘制事件
        
        Args:
            event: 绘制事件
        """
        # 绘制间隔行的半阴影效果
        painter = QPainter(self.viewport())
        painter.fillRect(event.rect(), self.palette().base())
        
        # 获取可见区域的第一个块
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        
        # 绘制间隔行背景
        while block.isValid():
            # 获取当前块的位置和高度
            rect = self.blockBoundingGeometry(block).translated(self.contentOffset())
            top = rect.top()
            
            # 如果已经超出可见区域，退出循环
            if top > event.rect().bottom():
                break
                
            if block.isVisible():
                # 为偶数行添加半阴影效果
                if block_number % 2 == 1:
                    # 使用块的实际几何信息创建矩形
                    rect = QRect(0, int(top), self.viewport().width(), int(rect.height()))
                    
                    # 根据当前主题选择合适的阴影颜色
                    if self.palette().base().color().lightness() < 128:  # 深色主题
                        # 使用更深的颜色作为深色主题的间隔行背景色
                        painter.fillRect(rect, QColor(45, 45, 45, 150))
                    else:  # 浅色主题
                        # 使用浅灰色作为浅色主题的间隔行背景色
                        painter.fillRect(rect, QColor(240, 240, 240, 100))
            
            block = block.next()
            block_number += 1
        
        # 调用父类的绘制事件以绘制文本
        painter.end()
        super().paintEvent(event)
    
    def document_modified(self):
        """标记文档为已修改状态"""
        self.document().setModified(True)