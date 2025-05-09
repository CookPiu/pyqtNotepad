from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QFileDialog
from PyQt6.QtCore import Qt
import sys
import os

# 导入新的WangEditor组件
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.ui.atomic.editor.wang_editor import WangEditor


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WangEditor集成示例")
        self.resize(800, 600)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建按钮布局
        button_layout = QHBoxLayout()
        
        # 创建按钮
        self.open_button = QPushButton("打开HTML文件")
        self.save_button = QPushButton("保存HTML文件")
        
        # 连接按钮信号
        self.open_button.clicked.connect(self.open_html_file)
        self.save_button.clicked.connect(self.save_html_file)
        
        # 添加按钮到布局
        button_layout.addWidget(self.open_button)
        button_layout.addWidget(self.save_button)
        
        # 创建WangEditor实例
        self.editor = WangEditor()
        
        # 监听编辑器内容变化
        self.editor.document_modified.connect(self.on_document_modified)
        
        # 添加组件到主布局
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.editor)
        
        # 设置初始HTML内容
        self.editor.setHtml("<h1>WangEditor集成示例</h1><p>这是一个富文本编辑器示例。</p>")
        
        # 重置修改状态
        self.editor.setModified(False)
    
    def open_html_file(self):
        """打开HTML文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开HTML文件", "", "HTML文件 (*.html *.htm)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    html_content = file.read()
                    self.editor.setHtml(html_content)
                self.setWindowTitle(f"WangEditor集成示例 - {os.path.basename(file_path)}")
            except Exception as e:
                print(f"打开文件时出错: {e}")
    
    def save_html_file(self):
        """保存HTML文件"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存HTML文件", "", "HTML文件 (*.html *.htm)"
        )
        
        if file_path:
            def save_content(html):
                try:
                    with open(file_path, 'w', encoding='utf-8') as file:
                        file.write(html)
                    self.editor.setModified(False)
                    self.setWindowTitle(f"WangEditor集成示例 - {os.path.basename(file_path)}")
                except Exception as e:
                    print(f"保存文件时出错: {e}")
            
            # 获取HTML内容并保存
            self.editor.toHtml(save_content)
    
    def on_document_modified(self, modified):
        """当文档被修改时更新窗口标题"""
        title = self.windowTitle()
        if modified and not title.endswith(" *"):
            self.setWindowTitle(f"{title} *")
        elif not modified and title.endswith(" *"):
            self.setWindowTitle(title[:-2])


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())