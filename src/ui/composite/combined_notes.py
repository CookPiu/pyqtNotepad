# src/ui/composite/combined_notes.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QLabel
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

# Correct relative imports from composite to core and views
from ..core.base_widget import BaseWidget
from ..views.sticky_notes_view import StickyNotesView
from ..views.todo_list_view import TodoListView

class CombinedNotes(BaseWidget):
    """
    复合容器，使用标签页组合显示便签和待办事项视图。
    继承自 BaseWidget。
    """
    def __init__(self, parent=None):
        super().__init__(parent) # Calls _init_ui, _connect_signals, _apply_theme

    def _init_ui(self):
        """初始化组合便签/待办的 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setTabsClosable(False)
        self.tab_widget.setObjectName("CombinedNotesTabs")

        # --- 便签视图 ---
        try:
            self.sticky_notes_view = StickyNotesView(self)
            self.tab_widget.addTab(self.sticky_notes_view, QIcon.fromTheme("document-properties"), "便签")
        except Exception as e:
            print(f"创建或添加 StickyNotesView 标签时出错: {e}")
            placeholder_sticky = QLabel("加载便签视图出错")
            placeholder_sticky.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tab_widget.addTab(placeholder_sticky, "便签 (错误)")

        # --- 待办事项视图 ---
        try:
            self.todo_list_view = TodoListView(self)
            self.tab_widget.addTab(self.todo_list_view, QIcon.fromTheme("view-list-text"), "待办事项")
        except Exception as e:
            print(f"创建或添加 TodoListView 标签时出错: {e}")
            placeholder_todo = QLabel("加载待办事项视图出错")
            placeholder_todo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tab_widget.addTab(placeholder_todo, "待办事项 (错误)")

        layout.addWidget(self.tab_widget)

    def _connect_signals(self):
        """连接内部信号 (if any)"""
        pass # No internal signals needed for basic combination

    def _apply_theme(self):
        """应用主题样式"""
        self.update_styles(is_dark=False) # Default light

    def update_styles(self, is_dark: bool):
        """根据主题更新样式"""
        border_color = "#555555" if is_dark else "#cccccc"
        tab_bg = "#2d2d2d" if is_dark else "#f0f0f0"
        tab_selected_bg = "#3c3c3c" if is_dark else "#ffffff"
        text_color = "#f0f0f0" if is_dark else "#2c3e50"

        self.tab_widget.setStyleSheet(f"""
            QTabWidget#CombinedNotesTabs::pane {{
                border: 1px solid {border_color};
                border-top: none;
                background-color: {tab_selected_bg};
            }}
            QTabWidget#CombinedNotesTabs::tab-bar {{
                alignment: left;
            }}
            QTabBar::tab {{
                background: {tab_bg};
                color: {text_color};
                border: 1px solid {border_color};
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 6px 12px;
                margin-right: 1px;
            }}
            QTabBar::tab:selected {{
                background: {tab_selected_bg};
                font-weight: bold;
            }}
            QTabBar::tab:!selected:hover {{
                background: {"#4a4a4a" if is_dark else "#e0e0e0"};
            }}
        """)

        # Propagate theme update to child views
        if hasattr(self, 'sticky_notes_view') and hasattr(self.sticky_notes_view, 'update_styles'):
            self.sticky_notes_view.update_styles(is_dark)
        if hasattr(self, 'todo_list_view') and hasattr(self.todo_list_view, 'update_styles'):
            self.todo_list_view.update_styles(is_dark)

    def cleanup(self):
        """Cleanup resources, especially for child views."""
        if hasattr(self, 'sticky_notes_view') and hasattr(self.sticky_notes_view, 'cleanup'):
            self.sticky_notes_view.cleanup()
        if hasattr(self, 'todo_list_view') and hasattr(self.todo_list_view, 'cleanup'):
            self.todo_list_view.cleanup()
        super().cleanup() # Call base class cleanup if it exists
