# src/ui/core/panel_widget.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QToolButton, QSizePolicy
from PyQt6.QtCore import pyqtSignal, Qt

class PanelWidget(QWidget):
    """
    A QWidget that wraps a content widget and provides a simple title bar
    with a title and a close button.
    Emits a 'closed' signal when its close button is clicked.
    """
    closed = pyqtSignal()

    def __init__(self, title: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("PanelWidget") # For QSS styling of the whole panel

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0) # Panel itself has no margins
        main_layout.setSpacing(0)

        # --- Title Bar ---
        self.title_bar_widget = QWidget(self)
        self.title_bar_widget.setObjectName("PanelTitleBar") # For QSS styling
        # self.title_bar_widget.setFixedHeight(22) # Optional: fixed height for title bar
        title_bar_layout = QHBoxLayout(self.title_bar_widget)
        title_bar_layout.setContentsMargins(5, 3, 3, 3) # Left, Top, Right, Bottom
        title_bar_layout.setSpacing(5)

        self.title_label = QLabel(title, self.title_bar_widget)
        self.title_label.setObjectName("PanelTitleLabel") # For QSS styling
        self.title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        self.close_button = QToolButton(self.title_bar_widget)
        self.close_button.setText("✕") # Unicode 'MULTIPLICATION X'
        self.close_button.setObjectName("PanelCloseButton") # For QSS styling
        self.close_button.setToolTip("关闭")
        # Basic styling for the close button to make it compact
        self.close_button.setStyleSheet("""
            QToolButton { border: none; background: transparent; padding: 1px; font-size: 11pt; }
            QToolButton:hover { background-color: #E81123; color: white; }
            QToolButton:pressed { background-color: #A30000; color: white; }
        """)
        self.close_button.clicked.connect(self._handle_close_request)

        title_bar_layout.addWidget(self.title_label)
        title_bar_layout.addStretch(1) # Pushes close button to the right if title is short
        title_bar_layout.addWidget(self.close_button)
        
        main_layout.addWidget(self.title_bar_widget)

        # --- Content Area ---
        # This container allows content to have its own margins if needed,
        # or for the PanelWidget to have a border that doesn't cut into content margins.
        self.content_container_widget = QWidget(self)
        self.content_container_widget.setObjectName("PanelContentContainer")
        self.content_layout = QVBoxLayout(self.content_container_widget)
        self.content_layout.setContentsMargins(0,0,0,0) # Content widget itself should manage its margins
        main_layout.addWidget(self.content_container_widget, 1) # Content expands

        self.setLayout(main_layout)
        self._content_widget = None

    def _handle_close_request(self):
        """Emits closed signal and hides the panel."""
        self.closed.emit()
        self.hide() 

    def setContentWidget(self, widget: QWidget | None):
        """Sets the main content widget for the panel."""
        if self._content_widget and self._content_widget == widget:
            return # No change

        # Clear previous content if any
        if self._content_widget:
            self._content_widget.setParent(None)
            self.content_layout.removeWidget(self._content_widget)
            self._content_widget = None
        
        if widget:
            self._content_widget = widget
            self.content_layout.addWidget(self._content_widget)

    def contentWidget(self) -> QWidget | None:
        return self._content_widget

    def setTitle(self, title: str):
        """Sets the text for the title label."""
        self.title_label.setText(title)

    # Override setVisible to ensure connected signals or buttons can react if needed,
    # though the primary mechanism is the 'closed' signal and activity bar button.
    # def setVisible(self, visible: bool) -> None:
    #     super().setVisible(visible)
    #     # If a button is directly tied to this panel's visibility, it might need an update.
    #     # However, the activity bar button's 'clicked' toggles this, and this panel's
    #     # 'closed' signal (connected to button.setChecked(False)) handles the other direction.
