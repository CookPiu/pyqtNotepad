import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QFileDialog
from PyQt6.QtCore import QDir
from wang_editor import WangEditor


class MainWindow(QMainWindow):
    """演示WangEditor使用的主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WangEditor示例")
        self.setGeometry(100, 100, 800, 600)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 创建WangEditor实例
        # 设置上传目录为当前目录下的uploads文件夹
        uploads_dir = os.path.join(QDir.currentPath(), "uploads")
        self.editor = WangEditor(upload_dir=uploads_dir)
        layout.addWidget(self.editor)
        
        # 添加按钮用于获取内容
        self.get_content_btn = QPushButton("获取内容")
        self.get_content_btn.clicked.connect(self.get_editor_content)
        layout.addWidget(self.get_content_btn)
        
        # 初始化编辑器内容
        self.editor.loadFinished.connect(self.on_editor_loaded)
    
    def on_editor_loaded(self, ok):
        """编辑器加载完成后设置初始内容"""
        if ok:
            initial_html = "<p>这是初始内容，您可以尝试上传图片。</p>"
            self.editor.setHtml(initial_html)
    
    def get_editor_content(self):
        """获取编辑器内容并保存"""
        def handle_content(html):
            # 显示内容长度
            print(f"编辑器内容长度: {len(html)}字符")
            
            # 保存内容到文件
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存内容", "", "HTML文件 (*.html);;所有文件 (*)"
            )
            if file_path:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(html)
                print(f"内容已保存到: {file_path}")
        
        # 获取编辑器内容
        self.editor.getHtml(handle_content)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())