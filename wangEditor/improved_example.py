import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, 
                             QPushButton, QFileDialog, QMessageBox, QLabel, QHBoxLayout)
from PyQt6.QtCore import QDir
from PyQt6.QtNetwork import QSslSocket
from wang_editor import WangEditor


class ImprovedEditorDemo(QMainWindow):
    """改进的WangEditor演示应用"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WangEditor图片上传演示")
        self.setGeometry(100, 100, 900, 700)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 添加说明标签
        info_label = QLabel("本示例演示了WangEditor的图片上传功能，您可以使用工具栏中的图片按钮上传图片")
        info_label.setStyleSheet("padding: 10px; background-color: #f0f0f0; border-radius: 5px;")
        main_layout.addWidget(info_label)
        
        # 添加SSL支持信息
        ssl_info = f"SSL支持状态: {'已启用' if QSslSocket.supportsSsl() else '未启用'} | SSL库版本: {QSslSocket.sslLibraryVersionString()}"
        ssl_label = QLabel(ssl_info)
        ssl_label.setStyleSheet("padding: 5px; background-color: #e8f4f8; border-radius: 3px; font-size: 11px; color: #555;")
        main_layout.addWidget(ssl_label)
        
        # 添加SSL错误处理提示
        ssl_note = QLabel("注意: 已配置自动处理SSL证书错误，如遇到SSL握手失败问题将自动忽略")
        ssl_note.setStyleSheet("padding: 5px; background-color: #fff8e1; border-radius: 3px; font-size: 11px; color: #856404;")
        main_layout.addWidget(ssl_note)
        
        # 创建上传目录设置区域
        upload_layout = QHBoxLayout()
        upload_label = QLabel("上传目录:")
        self.upload_path_label = QLabel()
        self.upload_path_label.setStyleSheet("font-weight: bold; padding: 5px; background-color: #e0e0e0;")
        change_dir_btn = QPushButton("更改目录")
        change_dir_btn.clicked.connect(self.change_upload_dir)
        upload_layout.addWidget(upload_label)
        upload_layout.addWidget(self.upload_path_label, 1)  # 1表示拉伸因子
        upload_layout.addWidget(change_dir_btn)
        main_layout.addLayout(upload_layout)
        
        # 设置默认上传目录
        self.upload_dir = os.path.join(QDir.currentPath(), "uploads")
        self.upload_path_label.setText(self.upload_dir)
        
        # 确保上传目录存在
        if not os.path.exists(self.upload_dir):
            os.makedirs(self.upload_dir)
        
        # 创建WangEditor实例
        self.editor = WangEditor(upload_dir=self.upload_dir)
        main_layout.addWidget(self.editor)
        
        # 创建按钮区域
        button_layout = QHBoxLayout()
        
        # 添加按钮用于获取内容
        self.get_content_btn = QPushButton("获取内容")
        self.get_content_btn.clicked.connect(self.get_editor_content)
        button_layout.addWidget(self.get_content_btn)
        
        # 添加按钮用于保存内容
        self.save_content_btn = QPushButton("保存内容")
        self.save_content_btn.clicked.connect(self.save_editor_content)
        button_layout.addWidget(self.save_content_btn)
        
        # 添加按钮用于查看上传的图片
        self.view_uploads_btn = QPushButton("查看已上传图片")
        self.view_uploads_btn.clicked.connect(self.view_uploaded_images)
        button_layout.addWidget(self.view_uploads_btn)
        
        main_layout.addLayout(button_layout)
        
        # 初始化编辑器内容
        self.editor.loadFinished.connect(self.on_editor_loaded)
    
    def on_editor_loaded(self, ok):
        """编辑器加载完成后设置初始内容"""
        if ok:
            initial_html = """
            <h2>WangEditor图片上传演示</h2>
            <p>这是一个演示WangEditor图片上传功能的示例。</p>
            <p>您可以：</p>
            <ol>
                <li>点击工具栏中的<strong>图片按钮</strong>上传本地图片</li>
                <li>图片将保存到指定的上传目录中</li>
                <li>上传成功后，图片将显示在编辑器中</li>
            </ol>
            <p>请尝试上传一张图片！</p>
            """
            self.editor.setHtml(initial_html)
    
    def change_upload_dir(self):
        """更改图片上传目录"""
        new_dir = QFileDialog.getExistingDirectory(self, "选择图片上传目录", self.upload_dir)
        if new_dir:
            self.upload_dir = new_dir
            self.upload_path_label.setText(self.upload_dir)
            self.editor.setUploadDir(self.upload_dir)
            QMessageBox.information(self, "上传目录已更改", f"图片将上传到: {self.upload_dir}")
    
    def get_editor_content(self):
        """获取编辑器内容并显示"""
        def handle_content(html):
            # 显示内容长度
            QMessageBox.information(
                self, 
                "编辑器内容", 
                f"内容长度: {len(html)}字符\n\n内容包含{html.count('<img')}张图片"
            )
        
        # 获取编辑器内容
        self.editor.getHtml(handle_content)
    
    def save_editor_content(self):
        """保存编辑器内容到文件"""
        def handle_content(html):
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存内容", "", "HTML文件 (*.html);;所有文件 (*)"
            )
            if file_path:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(html)
                QMessageBox.information(self, "保存成功", f"内容已保存到: {file_path}")
        
        # 获取编辑器内容
        self.editor.getHtml(handle_content)
    
    def view_uploaded_images(self):
        """查看已上传的图片"""
        if not os.path.exists(self.upload_dir):
            QMessageBox.warning(self, "目录不存在", f"上传目录不存在: {self.upload_dir}")
            return
        
        # 获取上传目录中的图片文件
        image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
        image_files = [f for f in os.listdir(self.upload_dir) 
                      if os.path.isfile(os.path.join(self.upload_dir, f)) and 
                      os.path.splitext(f)[1].lower() in image_extensions]
        
        if not image_files:
            QMessageBox.information(self, "没有图片", "上传目录中没有图片文件")
            return
        
        # 显示图片文件列表
        message = f"上传目录: {self.upload_dir}\n\n已上传的图片({len(image_files)}个):\n"
        message += "\n".join(image_files[:20])  # 最多显示20个文件
        if len(image_files) > 20:
            message += f"\n...还有{len(image_files) - 20}个文件未显示"
        
        QMessageBox.information(self, "已上传的图片", message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImprovedEditorDemo()
    window.show()
    sys.exit(app.exec())