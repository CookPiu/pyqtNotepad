# src/ui/core/base_widget.py
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSignal

class BaseWidget(QWidget):
    """
    所有自定义 QWidget 的基类。
    提供统一样式管理、信号连接等基础功能。
    """
    # 定义通用信号，例如状态变化、数据更新等
    status_changed = pyqtSignal(str)
    data_updated = pyqtSignal(object)

    def __init__(self, parent=None):
        """初始化基类"""
        super().__init__(parent)
        self._connections = {} # 用于管理信号连接
        self._init_ui()
        self._connect_signals()
        self._apply_theme()

    def _init_ui(self):
        """初始化 UI 元素（子类重写）"""
        pass

    def _connect_signals(self):
        """连接内部信号与槽（子类重写）"""
        pass

    def _apply_theme(self):
        """应用当前主题样式（可被主题管理器调用）"""
        # TODO: 实现从 theme_manager 获取并应用样式的逻辑
        # 例如: self.setStyleSheet(ThemeManager.get_widget_style(self.__class__.__name__))
        pass

    def register_signal_connection(self, signal, slot, connection_key):
        """注册并管理信号连接，防止重复连接"""
        if connection_key in self._connections:
            try:
                self._connections[connection_key].disconnect()
            except TypeError: # 连接可能已失效
                pass
        connection = signal.connect(slot)
        self._connections[connection_key] = connection
        return connection

    def disconnect_signal(self, connection_key):
        """断开指定的信号连接"""
        if connection_key in self._connections:
            try:
                self._connections[connection_key].disconnect()
                del self._connections[connection_key]
            except TypeError:
                 # 连接可能已失效
                if connection_key in self._connections:
                    del self._connections[connection_key]

    def closeEvent(self, event):
        """窗口关闭事件，自动断开所有管理的信号连接"""
        for key in list(self._connections.keys()):
            self.disconnect_signal(key)
        super().closeEvent(event)

    # 可以添加更多通用方法，如加载/保存状态、日志记录等
