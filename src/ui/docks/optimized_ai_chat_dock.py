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
        
        # 创建底部按钮布局
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(4, 0, 4, 4)
        button_layout.setSpacing(4)
        
        # 创建设置API密钥按钮
        self.api_key_button = QPushButton("设置API密钥", self)
        self.api_key_button.setStyleSheet(
            "QPushButton { background-color: #E0E0E0; border: none; border-radius: 3px; padding: 4px 8px; font-size: 12px; }"
            "QPushButton:hover { background-color: #BDBDBD; }"
        )
        self.api_key_button.clicked.connect(self.set_api_key)
        button_layout.addWidget(self.api_key_button)
        
        # 创建清空对话按钮
        self.clear_button = QPushButton("清空对话", self)
        self.clear_button.setStyleSheet(
            "QPushButton { background-color: #E0E0E0; border: none; border-radius: 3px; padding: 4px 8px; font-size: 12px; }"
            "QPushButton:hover { background-color: #BDBDBD; }"
        )
        self.clear_button.clicked.connect(self.clear_conversation)
        button_layout.addWidget(self.clear_button)
        
        layout.addLayout(button_layout)
        
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
        if is_dark_theme:
            self.api_key_button.setStyleSheet(
                "QPushButton { background-color: #424242; color: #E0E0E0; border: none; border-radius: 3px; padding: 4px 8px; font-size: 12px; }"
                "QPushButton:hover { background-color: #616161; }"
            )
            self.clear_button.setStyleSheet(
                "QPushButton { background-color: #424242; color: #E0E0E0; border: none; border-radius: 3px; padding: 4px 8px; font-size: 12px; }"
                "QPushButton:hover { background-color: #616161; }"
            )
        else:
            self.api_key_button.setStyleSheet(
                "QPushButton { background-color: #E0E0E0; border: none; border-radius: 3px; padding: 4px 8px; font-size: 12px; }"
                "QPushButton:hover { background-color: #BDBDBD; }"
            )
            self.clear_button.setStyleSheet(
                "QPushButton { background-color: #E0E0E0; border: none; border-radius: 3px; padding: 4px 8px; font-size: 12px; }"
                "QPushButton:hover { background-color: #BDBDBD; }"
            )