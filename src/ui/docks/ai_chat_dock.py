from PyQt6.QtWidgets import QDockWidget, QVBoxLayout, QWidget, QPushButton, QInputDialog, QLineEdit
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon

from ..atomic.ai.ai_chat_widget import AIChatWidget


class AIChatDock(QDockWidget):
    """AI聊天Dock组件"""
    
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
        
        # 创建AI聊天组件
        self.chat_widget = AIChatWidget(self)
        layout.addWidget(self.chat_widget)
        
        # 创建设置API密钥按钮
        self.api_key_button = QPushButton("设置API密钥", self)
        self.api_key_button.clicked.connect(self.set_api_key)
        layout.addWidget(self.api_key_button)
        
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