import sys
import os
from PyQt6.QtWidgets import QApplication

# 这些导入路径将在后续步骤中创建/移动相应文件后生效
from src.ui.main_window import MainWindow
from src.utils.theme_manager import ThemeManager

def initialize_theme(app):
    """初始化并应用主题到整个应用程序"""
    try:
        # 创建主题管理器 (假设 ThemeManager 将移至 src/utils)
        theme_mgr = ThemeManager()
        # 应用当前主题
        theme_mgr.apply_theme(app)
        # 返回主题管理器实例
        return theme_mgr
    except Exception as e:
        print(f"初始化主题时出错: {str(e)}")

def run_application():
    """创建并运行 PyQt 应用程序"""
    app = QApplication(sys.argv)

    # 初始化主题
    initialize_theme(app)

    # 创建并显示主窗口 (假设 MainWindow 将移至 src/ui)
    window = MainWindow()
    window.show()

    # 启动应用程序事件循环
    sys.exit(app.exec())
