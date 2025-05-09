from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSplitter
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFocusEvent
from ..core.dockable_tab_widget import DockableTabWidget

class EditorGroupWidget(QWidget):
    """
    A widget that represents a group of editors, typically displayed in a DockableTabWidget.
    This widget will be placed into a QSplitter when a view is split.
    """
    gainedFocus = pyqtSignal(object) # Emits self when focus is gained
    groupEmpty = pyqtSignal(object) # Emits self when the group becomes empty

    def __init__(self, parent=None):
        super().__init__(parent)
        print(f"EditorGroupWidget.__init__ called for {id(self)}, parent: {id(parent) if parent else None}")
        self._setup_ui()
        if self.tab_widget is None:
            print(f"CRITICAL DEBUG: EditorGroupWidget {id(self)} - self.tab_widget is None AFTER _setup_ui()")
        else:
            print(f"DEBUG: EditorGroupWidget {id(self)} - self.tab_widget is {type(self.tab_widget)} with id {id(self.tab_widget)}")

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tab_widget = DockableTabWidget(self)
        layout.addWidget(self.tab_widget)
        self.setLayout(layout)

        self.tab_widget.currentChanged.connect(self._handle_internal_tab_change)
        self.tab_widget.tabCloseRequested.connect(self._handle_tab_close_requested)

    def _handle_tab_close_requested(self, index: int):
        """Handles the tabCloseRequested signal from the DockableTabWidget."""
        print(f"DEBUG: EditorGroupWidget {id(self)} - Tab close requested for index {index}")
        self.remove_editor_tab(index)
        if self.count() == 0:
            print(f"DEBUG: EditorGroupWidget {id(self)} is now empty after closing tab. Emitting groupEmpty signal.")
            self.groupEmpty.emit(self)

    def _handle_internal_tab_change(self, index: int):
        """When the current tab changes, this group is considered to have gained focus."""
        if index != -1: 
            self.gainedFocus.emit(self)
            current_editor_content = self.tab_widget.widget(index)
            if current_editor_content:
                current_editor_content.setFocus()

    def add_editor_tab(self, widget: QWidget, title: str) -> int:
        """Adds an editor widget as a new tab."""
        return self.tab_widget.addTab(widget, title)

    def remove_editor_tab(self, index: int):
        """Removes a tab at the given index."""
        widget = self.tab_widget.widget(index)
        self.tab_widget.removeTab(index)
        # Important: The widget is just removed from the tab widget, not deleted.
        # The caller (or the mechanism that created it) is responsible for its lifecycle if needed.
        # For tabs created by FileOperations, they are typically managed elsewhere or might be reparented.
        return widget 

    def current_widget(self) -> QWidget | None:
        """Returns the current widget in the tab widget."""
        return self.tab_widget.currentWidget()

    def widget(self, index: int) -> QWidget | None:
        """Returns the widget at the given tab index."""
        return self.tab_widget.widget(index)
    
    def tab_text(self, index: int) -> str:
        """Returns the text of the tab at the given index."""
        return self.tab_widget.tabText(index)

    def set_tab_text(self, index: int, text: str):
        """Sets the text of the tab at the given index."""
        self.tab_widget.setTabText(index, text)

    def count(self) -> int:
        """Returns the number of tabs."""
        return self.tab_widget.count()

    def set_current_index(self, index: int):
        """Sets the current tab by index."""
        self.tab_widget.setCurrentIndex(index)

    def current_index(self) -> int:
        """Gets the current tab index."""
        return self.tab_widget.currentIndex()

    def get_tab_widget(self) -> DockableTabWidget:
        """Returns the internal DockableTabWidget instance."""
        return self.tab_widget

    def focusInEvent(self, event: QFocusEvent):
        """Override to detect when the group (or its tab widget) gains focus."""
        super().focusInEvent(event)
        self.gainedFocus.emit(self)

    def childEvent(self, event):
        super().childEvent(event)

if __name__ == '__main__':
    from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow
    app = QApplication([])

    main_win = QMainWindow()
    main_win.setWindowTitle("EditorGroupWidget Test")
    
    group1 = EditorGroupWidget()
    group1.add_editor_tab(QLabel("Content of Tab 1 in Group 1"), "Tab 1.1")
    group1.add_editor_tab(QLabel("Content of Tab 2 in Group 1"), "Tab 1.2")

    main_win.setCentralWidget(group1)
    main_win.resize(400, 300)
    main_win.show()
    
    app.exec()
