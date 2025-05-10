from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                             QFileDialog, QProgressBar, QMessageBox, QCheckBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QDir
import os
import shutil
from pathlib import Path

from ...services.pdf_conversion_service import PDFConversionService


class PDFConversionThread(QThread):
    """PDF转换线程，用于在后台执行PDF到HTML的转换"""
    conversion_complete = pyqtSignal(str)  # 转换完成信号，参数为输出文件路径
    conversion_error = pyqtSignal(str)     # 转换错误信号，参数为错误信息
    
    def __init__(self, pdf_path, output_dir, use_admin=True, options=None):
        super().__init__()
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.use_admin = use_admin
        self.options = options
        self.service = PDFConversionService()
    
    def run(self):
        try:
            # 设置输出HTML文件路径
            html_filename = Path(self.pdf_path).stem + ".html"
            output_html_path = os.path.join(self.output_dir, html_filename)
            
            # 执行转换
            result = self.service.convert_pdf_to_html(
                self.pdf_path, 
                output_html_path, 
                self.use_admin, 
                self.options
            )
            
            # 发出转换完成信号
            self.conversion_complete.emit(result)
            
        except Exception as e:
            # 发出错误信号
            self.conversion_error.emit(str(e))


class PDFConversionDialog(QDialog):
    """PDF转HTML转换对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PDF转HTML")
        self.resize(500, 200)
        self.setup_ui()
        
        # 初始化转换服务
        self.conversion_thread = None
        
        # 连接信号
        self.select_pdf_button.clicked.connect(self.select_pdf_file)
        self.select_output_button.clicked.connect(self.select_output_directory)
        self.convert_button.clicked.connect(self.start_conversion)
        self.cancel_button.clicked.connect(self.reject)
    
    def setup_ui(self):
        # 创建主布局
        main_layout = QVBoxLayout(self)
        
        # PDF文件选择
        pdf_layout = QHBoxLayout()
        pdf_layout.addWidget(QLabel("PDF文件:"))
        self.pdf_path_label = QLabel("未选择文件")
        self.pdf_path_label.setStyleSheet("background-color: #f0f0f0; padding: 5px; border-radius: 3px;")
        pdf_layout.addWidget(self.pdf_path_label, 1)
        self.select_pdf_button = QPushButton("浏览...")
        pdf_layout.addWidget(self.select_pdf_button)
        main_layout.addLayout(pdf_layout)
        
        # 输出目录选择
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("输出目录:"))
        self.output_dir_label = QLabel("未选择目录")
        self.output_dir_label.setStyleSheet("background-color: #f0f0f0; padding: 5px; border-radius: 3px;")
        output_layout.addWidget(self.output_dir_label, 1)
        self.select_output_button = QPushButton("浏览...")
        output_layout.addWidget(self.select_output_button)
        main_layout.addLayout(output_layout)
        
        # 选项
        options_layout = QHBoxLayout()
        self.admin_checkbox = QCheckBox("使用管理员权限")
        self.admin_checkbox.setChecked(True)
        self.admin_checkbox.setToolTip("使用管理员权限执行转换，可能需要UAC确认")
        options_layout.addWidget(self.admin_checkbox)
        options_layout.addStretch(1)
        main_layout.addLayout(options_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # 设置为不确定模式
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        self.convert_button = QPushButton("转换")
        self.convert_button.setEnabled(False)
        self.cancel_button = QPushButton("取消")
        button_layout.addWidget(self.convert_button)
        button_layout.addWidget(self.cancel_button)
        main_layout.addLayout(button_layout)
        
        # 设置布局
        self.setLayout(main_layout)
    
    def select_pdf_file(self):
        """选择PDF文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择PDF文件", "", "PDF文件 (*.pdf)"
        )
        
        if file_path:
            self.pdf_path_label.setText(file_path)
            self.update_convert_button_state()
    
    def select_output_directory(self):
        """选择输出目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择输出目录", "", QFileDialog.Option.ShowDirsOnly
        )
        
        if dir_path:
            self.output_dir_label.setText(dir_path)
            self.update_convert_button_state()
    
    def update_convert_button_state(self):
        """更新转换按钮状态"""
        pdf_selected = self.pdf_path_label.text() != "未选择文件"
        output_selected = self.output_dir_label.text() != "未选择目录"
        
        self.convert_button.setEnabled(pdf_selected and output_selected)
    
    def start_conversion(self):
        """开始转换"""
        pdf_path = self.pdf_path_label.text()
        output_dir = self.output_dir_label.text()
        use_admin = self.admin_checkbox.isChecked()
        
        # 验证文件和目录
        if not os.path.exists(pdf_path):
            QMessageBox.critical(self, "错误", f"PDF文件不存在: {pdf_path}")
            return
        
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法创建输出目录: {e}")
                return
        
        # 禁用UI元素
        self.convert_button.setEnabled(False)
        self.select_pdf_button.setEnabled(False)
        self.select_output_button.setEnabled(False)
        self.admin_checkbox.setEnabled(False)
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        
        # 创建并启动转换线程
        self.conversion_thread = PDFConversionThread(pdf_path, output_dir, use_admin)
        self.conversion_thread.conversion_complete.connect(self.on_conversion_complete)
        self.conversion_thread.conversion_error.connect(self.on_conversion_error)
        self.conversion_thread.start()
    
    def on_conversion_complete(self, output_path):
        """转换完成处理"""
        # 隐藏进度条
        self.progress_bar.setVisible(False)
        
        # 启用UI元素
        self.convert_button.setEnabled(True)
        self.select_pdf_button.setEnabled(True)
        self.select_output_button.setEnabled(True)
        self.admin_checkbox.setEnabled(True)
        
        # 显示成功消息
        result = QMessageBox.information(
            self, 
            "转换成功", 
            f"PDF已成功转换为HTML:\n{output_path}\n\n是否打开输出目录?", 
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if result == QMessageBox.StandardButton.Yes:
            # 打开输出目录
            QDir.setCurrent(os.path.dirname(output_path))
            os.startfile(os.path.dirname(output_path))
        
        # 关闭对话框
        self.accept()
    
    def on_conversion_error(self, error_message):
        """转换错误处理"""
        # 隐藏进度条
        self.progress_bar.setVisible(False)
        
        # 启用UI元素
        self.convert_button.setEnabled(True)
        self.select_pdf_button.setEnabled(True)
        self.select_output_button.setEnabled(True)
        self.admin_checkbox.setEnabled(True)
        
        # 显示错误消息
        QMessageBox.critical(self, "转换失败", f"PDF转换失败:\n{error_message}")