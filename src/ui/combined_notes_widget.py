import sys
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QApplication, QMainWindow
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

# 导入所需的子控件
# 注意：导入QMainWindow可能导致嵌套问题，后续可能需要重构
try:
    from src.ui.sticky_note_widget import StickyNoteWindow, NotesListWidget
except ImportError as e:
    print(f"无法导入 StickyNoteWindow: {e}")
    # 提供一个占位符类，避免完全崩溃
    class StickyNoteWindow(QWidget): pass
    class NotesListWidget(QWidget): pass

try:
    from src.ui.todo_widget import TodoWidget
except ImportError as e:
    print(f"无法导入 TodoWidget: {e}")
    # 提供一个占位符类
    class TodoWidget(QWidget): pass

class CombinedNotesWidget(QWidget):
    """
    一个组合控件，使用标签页显示便签和待办事项管理窗口。
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0) # 无边距以填充父容器

        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True) # Mac风格标签
        self.tab_widget.setTabsClosable(False) # 标签不可关闭

        # --- 创建并添加待办事项页面 ---
        try:
            self.todo_tab = TodoWidget(self) # 创建 TodoWidget 实例
            # 尝试移除窗口装饰（如果它是QMainWindow）
            if isinstance(self.todo_tab, QMainWindow):
                self.todo_tab.setWindowFlags(Qt.WindowType.Widget) # 尝试转换为普通Widget
                if self.todo_tab.menuBar():
                    self.todo_tab.menuBar().setVisible(False)
                if self.todo_tab.statusBar():
                    self.todo_tab.statusBar().setVisible(False)
                # 可能还需要移除工具栏等
            self.tab_widget.addTab(self.todo_tab, QIcon.fromTheme("view-list-text"), "待办事项")
        except Exception as e:
            print(f"创建或添加 TodoWidget 标签时出错: {e}")
            # 添加一个占位符标签
            placeholder_todo = QWidget()
            placeholder_todo_layout = QVBoxLayout(placeholder_todo)
            placeholder_todo_layout.addWidget(QLabel("加载待办事项出错"))
            self.tab_widget.addTab(placeholder_todo, "待办事项 (错误)")


        # --- 创建并添加便签页面 ---
        # 方案1: 直接添加 StickyNoteWindow (QMainWindow) - 可能有问题
        try:
            self.sticky_tab = StickyNoteWindow(self)
            # 尝试移除窗口装饰
            if isinstance(self.sticky_tab, QMainWindow):
                 self.sticky_tab.setWindowFlags(Qt.WindowType.Widget)
                 if self.sticky_tab.menuBar():
                     self.sticky_tab.menuBar().setVisible(False)
                 if self.sticky_tab.statusBar():
                     self.sticky_tab.statusBar().setVisible(False)
            self.tab_widget.addTab(self.sticky_tab, QIcon.fromTheme("note"), "便签管理")

        # 方案2: 使用 NotesListWidget (如果它足够独立)
        # try:
        #     self.notes_list_tab = NotesListWidget(self)
        #     self.tab_widget.addTab(self.notes_list_tab, QIcon.fromTheme("document-properties"), "便签列表")
        except Exception as e:
            print(f"创建或添加 StickyNote 标签时出错: {e}")
            # 添加一个占位符标签
            placeholder_sticky = QWidget()
            placeholder_sticky_layout = QVBoxLayout(placeholder_sticky)
            placeholder_sticky_layout.addWidget(QLabel("加载便签管理出错"))
            self.tab_widget.addTab(placeholder_sticky, "便签管理 (错误)")


        layout.addWidget(self.tab_widget)

    # 你可能需要添加方法来处理子窗口的关闭和数据保存逻辑
    # 例如，在父窗口关闭时调用子窗口的保存方法

# 用于独立测试
if __name__ == '__main__':
    app = QApplication(sys.argv)
    # 因为内部可能包含QMainWindow，所以最好在一个主窗口中测试
    main_test_window = QMainWindow()
    widget = CombinedNotesWidget()
    main_test_window.setCentralWidget(widget)
    main_test_window.setWindowTitle("Combined Notes Widget Test")
    main_test_window.resize(800, 600)
    main_test_window.show()
    sys.exit(app.exec())
