# src/ui/core/base_dialog.py
from PyQt6.QtWidgets import QDialog, QVBoxLayout
from .base_widget import BaseWidget # 基础 Widget 功能复用

class BaseDialog(QDialog):
    """
    所有自定义 QDialog 的基类。
    提供弹窗初始化、布局支持和统一样式（通过 BaseWidget 复用）。
    """
    def __init__(self, parent=None):
        """初始化基类对话框"""
        super().__init__(parent)
        # 基础布局
        self.main_layout = QVBoxLayout(self)
        self.setLayout(self.main_layout)

        # 复用 BaseWidget 的部分逻辑（如果需要）
        # 注意：QDialog 不是 QWidget，不能直接继承 BaseWidget
        # 但可以创建一个 BaseWidget 实例作为内容面板，或直接调用其方法
        # self._base_widget_helper = BaseWidget() # 示例：辅助对象

        self._init_dialog_ui()
        self._connect_dialog_signals()
        self._apply_dialog_theme()

        # 设置默认属性，如模态、标题等
        # self.setWindowTitle("Dialog")
        # self.setModal(True)

    def _init_dialog_ui(self):
        """初始化对话框 UI 元素（子类重写）"""
        # 子类在此方法中向 self.main_layout 添加控件
        pass

    def _connect_dialog_signals(self):
        """连接对话框内部信号与槽（子类重写）"""
        pass

    def _apply_dialog_theme(self):
        """应用当前主题样式"""
        # TODO: 实现从 theme_manager 获取并应用样式的逻辑
        # 可以参考 BaseWidget._apply_theme
        pass

    # 可以添加更多通用对话框方法，如显示/隐藏逻辑、结果处理等
    def show_dialog(self):
        """显示对话框"""
        self.exec() # 或者 self.show() 取决于是模态还是非模态
