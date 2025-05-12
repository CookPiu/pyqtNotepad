from PyQt6.QtWidgets import QDockWidget, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QInputDialog, QLineEdit, QToolButton, QMenu
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon

from ..atomic.ai.optimized_chat_widget import OptimizedChatWidget


class OptimizedAIChatDock(QDockWidget):
    """优化的AI聊天Dock组件"""
    
    def __init__(self, parent=None):
        super().__init__("AI对话助手", parent)
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | 
                             Qt.DockWidgetArea.RightDockWidgetArea)
        self.setup_ui()
    
    def setup_ui(self):
        # 创建主容器和布局
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)  # 减小间距
        
        # 创建优化的AI聊天组件
        self.chat_widget = OptimizedChatWidget(self)
        layout.addWidget(self.chat_widget)
        
        # 底部按钮已移除，将通过主窗口菜单控制
        
        # 设置主容器
        container.setLayout(layout)
        self.setWidget(container)
    
    def set_api_key(self):
        """设置API密钥对话框"""
        api_key, ok = QInputDialog.getText(
            self, 
            "设置API密钥", 
            "请输入您的API密钥：", 
            QLineEdit.EchoMode.Password
        )
        
        if ok and api_key:
            self.chat_widget.set_api_key(api_key)
    
    def clear_conversation(self):
        """清空当前对话"""
        self.chat_widget.clear_conversation()
    
    def update_styles(self, is_dark_theme=False):
        """更新样式以适应当前主题"""
        # 按钮已移除，此方法可能不再需要，或者只更新chat_widget的样式（如果它有的话）
        # if hasattr(self.chat_widget, 'update_styles'):
        #     self.chat_widget.update_styles(is_dark_theme)
        pass # 按钮已移除
