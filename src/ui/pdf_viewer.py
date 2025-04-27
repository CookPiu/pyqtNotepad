import os
import fitz  # PyMuPDF库
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QScrollArea, QMessageBox, QDialog, QSizePolicy)
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt, pyqtSignal


class PDFViewer(QDialog):
    """PDF查看器组件，用于直接显示PDF文件内容"""
    
    # 定义信号：当用户选择转换为HTML时发出
    convert_to_html_signal = pyqtSignal(str)
    
    def __init__(self, pdf_path, parent=None):
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.pdf_document = None
        self.current_page = 0
        self.total_pages = 0
        self.page_images = []
        
        self.initUI()
        self.load_pdf()
    
    def initUI(self):
        # 设置窗口标题和大小
        self.setWindowTitle(f"PDF预览 - {os.path.basename(self.pdf_path)}")
        self.resize(800, 600)
        
        # 创建主布局
        main_layout = QVBoxLayout(self)
        
        # 创建滚动区域用于显示PDF页面
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)
        
        # 创建页面标签容器
        self.page_label = QLabel()
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 创建按钮布局
        button_layout = QHBoxLayout()
        
        # 创建导航按钮
        self.prev_button = QPushButton("上一页")
        self.prev_button.clicked.connect(self.prev_page)
        
        self.next_button = QPushButton("下一页")
        self.next_button.clicked.connect(self.next_page)
        
        # 创建转换按钮
        self.convert_button = QPushButton("转换为HTML")
        self.convert_button.clicked.connect(self.convert_to_html)
        
        # 添加按钮到布局
        button_layout.addWidget(self.prev_button)
        button_layout.addWidget(self.page_label)
        button_layout.addWidget(self.next_button)
        button_layout.addWidget(self.convert_button)
        
        # 添加组件到主布局
        main_layout.addWidget(self.scroll_area)
        main_layout.addLayout(button_layout)
    
    def load_pdf(self):
        """加载PDF文件并渲染第一页"""
        try:
            # 打开PDF文件
            self.pdf_document = fitz.open(self.pdf_path)
            self.total_pages = len(self.pdf_document)
            
            if self.total_pages > 0:
                # 更新页面标签
                self.update_page_label()
                # 显示第一页
                self.show_page(0)
            else:
                QMessageBox.warning(self, "警告", "PDF文件没有页面")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法加载PDF文件: {str(e)}")
    
    def show_page(self, page_num):
        """显示指定页面"""
        if not self.pdf_document or page_num < 0 or page_num >= self.total_pages:
            return
        
        # 清除当前页面内容
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        # 加载页面
        page = self.pdf_document.load_page(page_num)
        
        # 渲染页面为图像
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))  # 缩放因子
        
        # 将PyMuPDF的Pixmap转换为QImage
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
        
        # 创建QPixmap并设置到QLabel
        pixmap = QPixmap.fromImage(img)
        image_label = QLabel()
        image_label.setPixmap(pixmap)
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 添加到滚动区域
        self.scroll_layout.addWidget(image_label)
        
        # 更新当前页码
        self.current_page = page_num
        self.update_page_label()
        
        # 更新导航按钮状态
        self.prev_button.setEnabled(page_num > 0)
        self.next_button.setEnabled(page_num < self.total_pages - 1)
    
    def update_page_label(self):
        """更新页面标签"""
        self.page_label.setText(f"第 {self.current_page + 1} 页 / 共 {self.total_pages} 页")
    
    def prev_page(self):
        """显示上一页"""
        if self.current_page > 0:
            self.show_page(self.current_page - 1)
    
    def next_page(self):
        """显示下一页"""
        if self.current_page < self.total_pages - 1:
            self.show_page(self.current_page + 1)
    
    def convert_to_html(self):
        """发出转换为HTML的信号"""
        self.convert_to_html_signal.emit(self.pdf_path)
        self.accept()
    
    def closeEvent(self, event):
        """关闭窗口时清理资源"""
        if self.pdf_document:
            self.pdf_document.close()
        super().closeEvent(event)