# src/ui/composite/combined_tools.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from PyQt6.QtCore import Qt

# 导入所需的组件
from ..core.base_widget import BaseWidget
from ..atomic.calendar.calendar_widget import CalendarWidget
from ..atomic.mini_tools.timer_widget import TimerWidget
from ..atomic.mini_tools.calculator_widget import CalculatorWidget
from ..atomic.mini_tools.speech_recognition_widget import SpeechRecognitionWidget
from .combined_notes import CombinedNotes


class CombinedTools(BaseWidget):
    """
    复合容器，将 日历 / 便签与待办 / 计时器 等工具组合成分页控件。
    继承自 BaseWidget。
    """
    def __init__(self, parent=None):
        super().__init__(parent) # Calls _init_ui, _connect_signals, _apply_theme

    def _init_ui(self):
        """初始化组合工具的 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True) # 使用文档模式获得更清爽的外观
        self.tabs.setObjectName("CombinedToolsTabs") # 用于样式设置

        # 1. 计算器
        try:
            self.calculator_tool = CalculatorWidget(self)
            self.tabs.addTab(self.calculator_tool, "计算器")
        except Exception as e:
            print(f"创建计算器组件时出错: {e}")

        # 2. 定时器
        try:
            self.timer_tool = TimerWidget(self)
            self.tabs.addTab(self.timer_tool, "定时器")
        except Exception as e:
            print(f"创建定时器组件时出错: {e}")

        # 3. 语音识别
        try:
            self.speech_tool = SpeechRecognitionWidget(self)
            self.tabs.addTab(self.speech_tool, "语音识别")
        except Exception as e:
            print(f"创建语音识别组件时出错: {e}")

        # 4. 日历
        try:
            self.calendar_tool = CalendarWidget(self)
            self.tabs.addTab(self.calendar_tool, "日历")
        except Exception as e:
            print(f"创建日历组件时出错: {e}")

        # 5. 便签与待办
        try:
            self.notes_tool = CombinedNotes(self)
            self.tabs.addTab(self.notes_tool, "便签与待办")
        except Exception as e:
            print(f"创建便签与待办组件时出错: {e}")

        layout.addWidget(self.tabs)

    def _connect_signals(self):
        """连接内部信号 (if any)"""
        # Example: Connect signals from child widgets if needed
        # self.calendar_tool.event_selected.connect(self._handle_event_selection)
        pass

    def _apply_theme(self):
        """应用主题样式"""
        # This will be called by BaseWidget.
        # We might need to propagate theme updates to child widgets.
        self.update_styles(is_dark=False) # Default light

    def update_styles(self, is_dark: bool):
        """根据主题更新样式"""
        border_color = "#555555" if is_dark else "#cccccc"
        tab_bg = "#2d2d2d" if is_dark else "#f0f0f0"
        tab_selected_bg = "#3c3c3c" if is_dark else "#ffffff"
        text_color = "#f0f0f0" if is_dark else "#2c3e50"

        self.tabs.setStyleSheet(f"""
            QTabWidget#CombinedToolsTabs::pane {{
                border: 1px solid {border_color};
                border-top: none; /* Pane border only on sides/bottom */
                background-color: {tab_selected_bg}; /* Background for the content area */
            }}
            QTabWidget#CombinedToolsTabs::tab-bar {{
                alignment: left;
            }}
            QTabBar::tab {{
                background: {tab_bg};
                color: {text_color};
                border: 1px solid {border_color};
                border-bottom: none; /* Remove bottom border for tabs */
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 6px 12px;
                margin-right: 1px; /* Space between tabs */
            }}
            QTabBar::tab:selected {{
                background: {tab_selected_bg}; /* Match pane background */
                font-weight: bold;
                /* border-bottom: 1px solid {tab_selected_bg}; */ /* Make bottom border match bg */
            }}
            QTabBar::tab:!selected:hover {{
                background: {"#4a4a4a" if is_dark else "#e0e0e0"};
            }}
        """)

        # Propagate theme update to child widgets if they have update_styles method
        if hasattr(self.calendar_tool, 'update_styles'):
            self.calendar_tool.update_styles(is_dark)
        if hasattr(self.notes_tool, 'update_styles'): # Check if the temp widget has it
            self.notes_tool.update_styles(is_dark)
        if hasattr(self.timer_tool, 'update_styles'):
            self.timer_tool.update_styles(is_dark)

    # Add methods to access or control the child widgets if necessary
