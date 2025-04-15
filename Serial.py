import sys
import os

from MainWindow import MainWindow
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QFile, QTextStream
from theme_manager import ThemeManager

def initialize_theme(app):
    """初始化并应用主题到整个应用程序"""
    try:
        # 创建主题管理器
        theme_mgr = ThemeManager()
        # 应用当前主题
        theme_mgr.apply_theme(app)
        # 返回主题管理器实例
        return theme_mgr
    except Exception as e:
        print(f"初始化主题时出错: {str(e)}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # 初始化主题
    initialize_theme(app)
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    sys.exit(app.exec())