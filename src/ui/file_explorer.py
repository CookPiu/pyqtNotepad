import os
from PyQt6.QtWidgets import QTreeView, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QInputDialog, QMessageBox
from PyQt6.QtGui import QFileSystemModel, QIcon
from PyQt6.QtCore import QDir, Qt, pyqtSignal, QEvent


class FileExplorer(QWidget):
    """文件浏览器组件，用于在侧边栏显示文件系统"""
    
    # 定义信号，当双击文件时发出
    file_double_clicked = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_path = os.path.expanduser("~")
        self.current_theme = "light"  # 默认使用浅色主题
        self.initUI()
        
    def update_theme(self, theme):
        """更新组件主题"""
        self.current_theme = theme
        # 根据主题更新图标和样式
        # 这里可以根据需要添加更多的主题相关设置
    
    def initUI(self):
        # 创建主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建文件系统模型
        self.model = QFileSystemModel()
        self.model.setRootPath(self.current_path)
        self.model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot)
        
        # 创建树状视图
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.model)
        self.tree_view.setRootIndex(self.model.index(self.current_path))
        self.tree_view.setAnimated(True)
        self.tree_view.setIndentation(20)
        self.tree_view.setSortingEnabled(True)
        
        # 只显示文件名列，隐藏其他列
        self.tree_view.setHeaderHidden(True)
        for i in range(1, self.model.columnCount()):
            self.tree_view.hideColumn(i)
        
        # 连接双击信号
        self.tree_view.doubleClicked.connect(self.on_item_double_clicked)
        
        # 添加组件到布局
        layout.addWidget(self.tree_view)
        
        self.setLayout(layout)
    
    def open_folder_dialog(self):
        """打开文件夹对话框"""
        folder_path = QFileDialog.getExistingDirectory(self, "选择文件夹", self.current_path)
        if folder_path:
            self.set_root_path(folder_path)
    
    def set_root_path(self, path):
        """设置根路径"""
        if os.path.exists(path):
            self.current_path = path
            self.tree_view.setRootIndex(self.model.index(path))
    
    def create_new_folder(self):
        """创建新文件夹"""
        folder_name, ok = QInputDialog.getText(self, "新建文件夹", "请输入文件夹名称:")
        if ok and folder_name:
            new_folder_path = os.path.join(self.current_path, folder_name)
            try:
                os.makedirs(new_folder_path, exist_ok=True)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建文件夹失败: {str(e)}")
    
    def on_item_double_clicked(self, index):
        """处理项目双击事件"""
        file_path = self.model.filePath(index)
        if os.path.isfile(file_path):
            # 发出信号，通知外部处理文件打开
            self.file_double_clicked.emit(file_path)
