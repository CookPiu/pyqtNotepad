# src/ui/combined_tools_widget.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from src.ui.calendar_widget import CalendarWindow
from src.ui.combined_notes_widget import CombinedNotesWidget
from src.ui.timer_widget import TimerWindow

class CombinedToolsWidget(QWidget):
    """把 日历 / 便签与待办 / 计时器 三项合并成一个分页控件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CombinedToolsWidget")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget(self) # Assign to self.tabs
        self.tabs.setDocumentMode(True)
        # ① 日历
        self.tabs.addTab(CalendarWindow(self), "日历")
        # ② 便签与待办
        self.tabs.addTab(CombinedNotesWidget(self), "便签与待办")
        # ③ 计时器
        self.tabs.addTab(TimerWindow(self), "计时器")
        layout.addWidget(self.tabs)
