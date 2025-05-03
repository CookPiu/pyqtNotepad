# src/ui/views/sticky_notes_view.py
import sys
import os
import json
import uuid
import re # Import re for path validation if needed later
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QToolBar,
    QPushButton, QTextEdit, QColorDialog, QSizeGrip,
    QApplication, QMessageBox, QDialog, QListWidget, QListWidgetItem,
    QLabel, QStackedWidget, QMenu, QSizePolicy
)
from PyQt6.QtGui import QIcon, QAction, QColor, QPalette, QFont, QScreen, QContextMenuEvent
from PyQt6.QtCore import Qt, QSize, QPoint, QRect, pyqtSignal, QSettings, QSignalBlocker

# Correct relative import from views to core
from ..core.base_widget import BaseWidget
# from ..core.theme_manager import ThemeManager # Optional, if BaseWidget doesn't handle propagation

# --- Individual Sticky Note Window ---
class StickyNote(QWidget):
    """单个便签窗口 (保持独立窗口特性)"""
    closed = pyqtSignal(str)  # Emits note_id when closed
    data_changed = pyqtSignal(dict) # Emits note data when content/color/geometry changes

    def __init__(self, note_id=None, content="", color="#ffff99", geometry=None, parent=None):
        # Use Window flag for independent window, FramelessWindowHint for custom title bar
        super().__init__(parent, Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose) # Ensure cleanup

        self.note_id = note_id or str(uuid.uuid4())
        self._initial_content = content # Store initial content
        self._initial_color = QColor(color)
        self._initial_geometry = geometry

        self.is_dragging = False
        self.drag_start_position = QPoint()

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self._init_note_ui()
        self._apply_note_styles(is_dark=False) # Apply default style

        # Restore geometry or place centered
        if self._initial_geometry:
            try:
                self.setGeometry(self._initial_geometry["x"], self._initial_geometry["y"],
                                 self._initial_geometry["width"], self._initial_geometry["height"])
            except (KeyError, TypeError):
                 self._center_on_screen() # Fallback if geometry data is invalid
        else:
            self._center_on_screen()

    def _center_on_screen(self):
        """Centers the note on the primary screen."""
        try:
            center_point = QScreen.availableGeometry(QApplication.primaryScreen()).center()
            self.resize(200, 200) # Default size
            self.move(center_point - QPoint(int(self.width() / 2), int(self.height() / 2)))
        except Exception as e:
            print(f"Error centering window: {e}")
            self.resize(200, 200) # Default size fallback

    def _init_note_ui(self):
        self.setWindowTitle("便签")
        # self.setWindowIcon(QIcon.fromTheme("note")) # Icon might not show on frameless

        self.setMinimumSize(150, 100) # Smaller minimum size

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(3, 3, 3, 3) # Minimal margins
        main_layout.setSpacing(0) # No spacing

        # --- Custom Title Bar ---
        title_bar = QWidget()
        title_bar.setObjectName("StickyNoteTitleBar")
        title_bar.setFixedHeight(24)
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(3, 0, 3, 0)
        title_bar_layout.setSpacing(2)

        self.color_btn = QPushButton("🎨")
        self.color_btn.setFixedSize(18, 18)
        self.color_btn.setFlat(True)
        self.color_btn.clicked.connect(self.change_color)
        self.color_btn.setToolTip("更改颜色")

        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(18, 18)
        self.close_btn.setFlat(True)
        self.close_btn.clicked.connect(self.close)
        self.close_btn.setToolTip("关闭便签")

        title_bar_layout.addWidget(self.color_btn)
        title_bar_layout.addStretch() # Pushes close button to the right
        title_bar_layout.addWidget(self.close_btn)
        main_layout.addWidget(title_bar)

        # --- Text Edit Area ---
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(self._initial_content)
        self.text_edit.setFrameStyle(0) # No frame
        self.text_edit.setFont(QFont("Arial", 11)) # Slightly smaller font
        self.text_edit.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.text_edit.textChanged.connect(self._on_data_changed) # Connect text changes
        main_layout.addWidget(self.text_edit, 1) # Text edit takes expanding space

        # --- Size Grip ---
        size_grip_layout = QHBoxLayout()
        size_grip_layout.setContentsMargins(0,0,0,0)
        size_grip_layout.addStretch()
        self.size_grip = QSizeGrip(self)
        size_grip_layout.addWidget(self.size_grip)
        main_layout.addLayout(size_grip_layout)

        self.setLayout(main_layout)
        self.update_color(self._initial_color) # Apply initial color

    def update_color(self, color: QColor):
        """Updates the sticky note's color and emits data_changed."""
        if self._initial_color != color: # Only emit if color actually changed
            self._initial_color = color # Update internal state
            self._apply_note_styles() # Re-apply styles with new color
            self._on_data_changed() # Emit data changed signal

    def _apply_note_styles(self, is_dark=False): # is_dark can be passed from manager later
        """Applies styles based on the current color."""
        color = self._initial_color
        # Determine text color based on background brightness
        brightness = (color.red() * 299 + color.green() * 587 + color.blue() * 114) / 1000
        text_color = "#000000" if brightness > 128 else "#ffffff"
        # Darker border color
        border_color = color.darker(120).name()
        title_bar_bg = color.darker(110).name() # Slightly darker title bar
        button_hover_bg = color.lighter(110).name()
        close_hover_bg = "#ff6666"

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {color.name()};
                border: 1px solid {border_color};
                border-radius: 4px;
            }}
            QWidget#StickyNoteTitleBar {{
                background-color: {title_bar_bg};
                border-bottom: 1px solid {border_color};
                border-top-left-radius: 4px; /* Match main border */
                border-top-right-radius: 4px;
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }}
            QTextEdit {{
                background-color: {color.name()};
                color: {text_color};
                border: none;
                border-radius: 0px; /* No radius for text edit */
                padding: 3px;
            }}
            QPushButton {{
                color: {text_color};
                background-color: transparent;
                border: none;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {button_hover_bg};
                border-radius: 9px;
            }}
            QPushButton#close_btn:hover {{ /* Specific hover for close */
                 background-color: {close_hover_bg};
                 color: black;
            }}
            QSizeGrip {{
                /* Use image or keep default */
                /* image: url(path/to/grip.png); */
                background-color: transparent;
                border: none;
                width: 12px;
                height: 12px;
            }}
        """)
        # Find buttons by name if objectName is set, otherwise assume order/type
        self.close_btn.setObjectName("close_btn") # Ensure object name is set

    def change_color(self):
        """Opens color dialog to change note color."""
        new_color = QColorDialog.getColor(self._initial_color, self, "选择便签颜色")
        if new_color.isValid() and new_color != self._initial_color:
            self.update_color(new_color)

    def get_data(self) -> dict:
        """Returns current note data as a dictionary."""
        geo = self.geometry()
        return {
            "id": self.note_id,
            "content": self.text_edit.toPlainText(),
            "color": self._initial_color.name(), # Use the internal color state
            "geometry": {
                "x": geo.x(), "y": geo.y(),
                "width": geo.width(), "height": geo.height()
            }
        }

    def _on_data_changed(self):
        """Emits data_changed signal when content, color, or geometry changes."""
        # Geometry changes are handled in resizeEvent/moveEvent
        self.data_changed.emit(self.get_data())

    # --- Event Handlers for Dragging and Resizing ---
    def mousePressEvent(self, event: QContextMenuEvent):
        # Only drag when clicking on the title bar area
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() < 24: # Approx title bar height
            self.is_dragging = True
            self.drag_start_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            event.ignore() # Allow normal interaction with text edit / size grip

    def mouseMoveEvent(self, event: QContextMenuEvent):
        if self.is_dragging and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_start_position)
            event.accept()
        else:
            event.ignore()

    def mouseReleaseEvent(self, event: QContextMenuEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_dragging:
                self.is_dragging = False
                self._on_data_changed() # Emit data change after dragging stops
                event.accept()
            else:
                 event.ignore()
        else:
            event.ignore()

    def resizeEvent(self, event):
        """Emit data change on resize."""
        super().resizeEvent(event)
        # Use a timer to avoid emitting too frequently during resize
        if not hasattr(self, '_resize_timer'):
             self._resize_timer = QTimer(self)
             self._resize_timer.setSingleShot(True)
             self._resize_timer.timeout.connect(self._on_data_changed)
        self._resize_timer.start(500) # Emit after 500ms of no resizing

    def closeEvent(self, event):
        """Handles the close event, emits closed signal."""
        try:
            self.closed.emit(self.note_id)
        except Exception as e:
            print(f"Error emitting closed signal for note {self.note_id}: {e}")
        super().closeEvent(event)


# --- Notes List Widget (Internal Helper) ---
class NotesListWidget(QWidget):
    """Widget for displaying and managing the list of notes"""
    note_selected = pyqtSignal(dict)  # Emits note data on double-click
    add_new_note_requested = pyqtSignal() # Signal to request new note creation

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_list_ui()
        self._apply_list_styles()

    def _init_list_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        title_label = QLabel("便签列表")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setObjectName("NotesListTitle")
        layout.addWidget(title_label)

        instructions = QLabel("双击打开便签")
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instructions.setObjectName("NotesListInstructions")
        layout.addWidget(instructions)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("NotesList")
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.list_widget)

        self.add_btn = QPushButton("新建便签")
        self.add_btn.setObjectName("NotesListAddButton")
        self.add_btn.clicked.connect(self.add_new_note_requested) # Emit signal
        layout.addWidget(self.add_btn)

    def _apply_list_styles(self, is_dark=False):
        bg_color = "#1e1e1e" if is_dark else "#ffffff"
        text_color = "#f0f0f0" if is_dark else "#000000"
        border_color = "#555555" if is_dark else "#cccccc"
        list_bg = "#2d2d2d" if is_dark else "#ffffff"
        item_hover_bg = "#4a4a4a" if is_dark else "#f0f8ff"
        item_selected_bg = "#3498db"
        item_selected_text = "#ffffff"
        instr_color = "#95a5a6" if is_dark else "#666666"
        button_bg = "#27ae60" if not is_dark else "#229954" # Green button
        button_hover_bg = "#2ecc71" if not is_dark else "#27ae60"
        button_pressed_bg = "#229954" if not is_dark else "#1e8449"
        button_text = "#ffffff"

        self.setStyleSheet(f"QWidget {{ background-color: {bg_color}; color: {text_color}; }}") # Base for the widget
        self.findChild(QLabel, "NotesListTitle").setStyleSheet(f"font-size: 14px; font-weight: bold; margin-bottom: 5px; color: {text_color}; background: transparent;")
        self.findChild(QLabel, "NotesListInstructions").setStyleSheet(f"font-size: 10px; color: {instr_color}; margin-bottom: 5px; background: transparent;")
        self.list_widget.setStyleSheet(f"""
            QListWidget#NotesList {{
                background-color: {list_bg};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 3px;
                color: {text_color}; /* Default item text color */
            }}
            QListWidget#NotesList::item {{
                padding: 6px;
                border-radius: 3px;
                margin: 1px 0px;
                /* Background/text color set per item */
            }}
            QListWidget#NotesList::item:hover {{
                background-color: {item_hover_bg};
            }}
            QListWidget#NotesList::item:selected {{
                background-color: {item_selected_bg};
                color: {item_selected_text}; /* Ensure selected text is visible */
            }}
        """)
        self.add_btn.setStyleSheet(f"""
            QPushButton#NotesListAddButton {{
                background-color: {button_bg};
                color: {button_text};
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
            }}
            QPushButton#NotesListAddButton:hover {{ background-color: {button_hover_bg}; }}
            QPushButton#NotesListAddButton:pressed {{ background-color: {button_pressed_bg}; }}
        """)

    def update_note_list(self, notes: list[dict]):
        """Updates the list widget with note items."""
        self.list_widget.clear()
        for note_data in notes:
            item = QListWidgetItem()
            # Display first line of content or placeholder
            content_lines = note_data.get("content", "").strip().split('\n')
            display_text = content_lines[0].strip() if content_lines and content_lines[0].strip() else "无标题便签"
            item.setText(display_text)

            # Tooltip with more content
            full_content = note_data.get("content", "").strip()
            tooltip = (full_content[:150] + "...") if len(full_content) > 150 else full_content
            item.setToolTip(tooltip if tooltip else "空便签")

            item.setData(Qt.ItemDataRole.UserRole, note_data)

            # Set item color
            color = QColor(note_data.get("color", "#ffff99"))
            brightness = (color.red() * 299 + color.green() * 587 + color.blue() * 114) / 1000
            text_color = QColor("#000000") if brightness > 128 else QColor("#ffffff")
            item.setBackground(color)
            item.setForeground(text_color)

            self.list_widget.addItem(item)

    def _on_item_double_clicked(self, item: QListWidgetItem):
        """Emits note_selected signal when an item is double-clicked."""
        note_data = item.data(Qt.ItemDataRole.UserRole)
        if note_data:
            self.note_selected.emit(note_data)


# --- Main Sticky Notes View ---
class StickyNotesView(BaseWidget):
    """
    主便签管理视图。
    继承自 BaseWidget。
    """
    def __init__(self, parent=None):
        self.notes_data: list[dict] = [] # Stores data for all notes
        self.active_notes: dict[str, StickyNote] = {} # {note_id: StickyNote widget instance}
        self._data_file_path = self._get_data_file_path()
        self.load_notes()
        super().__init__(parent) # Calls _init_ui, _connect_signals, _apply_theme

    def _get_data_file_path(self):
        """Determines the path for the notes data file."""
        # Assumes this file is in src/ui/views
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(current_dir, "..", "..")) # Up two levels
            data_dir = os.path.join(project_root, "data")
            os.makedirs(data_dir, exist_ok=True)
            return os.path.join(data_dir, "notes.json")
        except Exception as e:
            print(f"Error determining notes data file path: {e}")
            return os.path.join(os.path.dirname(os.path.abspath(__file__)), "notes.json")

    def _init_ui(self):
        """初始化主视图 UI"""
        # This widget itself might just contain the list view,
        # as individual notes are separate windows.
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.notes_list_widget = NotesListWidget(self)
        main_layout.addWidget(self.notes_list_widget)

        self.setLayout(main_layout)
        self.update_notes_list_display() # Initial population of the list

    def _connect_signals(self):
        """连接信号"""
        self.notes_list_widget.add_new_note_requested.connect(self.create_new_note)
        self.notes_list_widget.note_selected.connect(self.open_note_from_data)

    def _apply_theme(self):
        """应用主题"""
        self.update_styles(is_dark=False) # Default light

    def update_styles(self, is_dark: bool):
        """更新样式"""
        # Propagate style update to child list widget
        self.notes_list_widget._apply_list_styles(is_dark)
        # Update styles of any currently open sticky note windows
        for note_widget in self.active_notes.values():
             if note_widget and not note_widget.isHidden(): # Check if widget exists and is visible
                 note_widget._apply_note_styles(is_dark)


    # --- Data Persistence ---
    def load_notes(self):
        """Loads notes data from the JSON file."""
        if not os.path.exists(self._data_file_path):
            self.notes_data = []
            return
        try:
            with open(self._data_file_path, "r", encoding="utf-8") as f:
                self.notes_data = json.load(f)
                # Basic validation (ensure it's a list of dicts)
                if not isinstance(self.notes_data, list):
                     print("Warning: notes.json does not contain a list. Resetting.")
                     self.notes_data = []
                self.notes_data = [n for n in self.notes_data if isinstance(n, dict) and 'id' in n]
        except (json.JSONDecodeError, IOError, Exception) as e:
            QMessageBox.warning(self, "加载便签失败", f"无法加载便签: {e}")
            self.notes_data = []

    def save_notes(self):
        """Saves the current state of notes_data to the JSON file."""
        try:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(self._data_file_path), exist_ok=True)
            with open(self._data_file_path, "w", encoding="utf-8") as f:
                json.dump(self.notes_data, f, indent=2, ensure_ascii=False)
        except (IOError, Exception) as e:
            QMessageBox.warning(self, "保存便签失败", f"无法保存便签: {e}")

    def update_notes_list_display(self):
        """Updates the list widget display."""
        self.notes_list_widget.update_note_list(self.notes_data)

    # --- Note Management ---
    def create_new_note(self):
        """Creates a new sticky note window and data entry."""
        new_note_widget = StickyNote(parent=None) # Create as top-level window
        new_note_widget.closed.connect(self._on_note_closed)
        new_note_widget.data_changed.connect(self._on_note_data_changed)

        note_id = new_note_widget.note_id
        self.active_notes[note_id] = new_note_widget

        # Add new note data to list and save
        new_note_data = new_note_widget.get_data()
        self.notes_data.append(new_note_data)
        self.save_notes()
        self.update_notes_list_display()

        new_note_widget.show()

    def open_note_from_data(self, note_data: dict):
        """Opens an existing note window from its data."""
        note_id = note_data.get("id")
        if not note_id: return

        # If already open, just activate it
        if note_id in self.active_notes:
            note_widget = self.active_notes[note_id]
            if note_widget:
                 note_widget.show()
                 note_widget.activateWindow()
                 note_widget.raise_()
                 return
            else:
                 # Reference exists but widget might have been deleted unexpectedly
                 del self.active_notes[note_id]

        # Create and show the note window
        note_widget = StickyNote(
            note_id=note_id,
            content=note_data.get("content", ""),
            color=note_data.get("color", "#ffff99"),
            geometry=note_data.get("geometry"),
            parent=None # Create as top-level window
        )
        note_widget.closed.connect(self._on_note_closed)
        note_widget.data_changed.connect(self._on_note_data_changed)
        self.active_notes[note_id] = note_widget
        note_widget.show()

    def _on_note_closed(self, note_id: str):
        """Handles the closed signal from a StickyNote window."""
        if note_id in self.active_notes:
            # Data should have been saved via data_changed or just before closing
            # Remove from active dictionary
            del self.active_notes[note_id]
            # No need to save here, saving happens on data change or main window close
            print(f"Note {note_id} closed and removed from active list.")
        self.update_notes_list_display() # Refresh list in case state changed visually

    def _on_note_data_changed(self, note_data: dict):
        """Handles data changes from an active StickyNote window."""
        note_id = note_data.get("id")
        if not note_id: return

        # Update the data in the main list
        found = False
        for i, existing_data in enumerate(self.notes_data):
            if existing_data.get("id") == note_id:
                self.notes_data[i] = note_data # Replace with new data
                found = True
                break
        if not found:
            # This shouldn't happen if the note was created correctly
            print(f"Warning: Data changed for note ID {note_id}, but not found in main list. Appending.")
            self.notes_data.append(note_data)

        # Save changes and update list display
        self.save_notes()
        self.update_notes_list_display()

    # --- Global Actions (Could be triggered externally) ---
    def show_all_notes(self):
        """Opens windows for all notes in the data list."""
        # Close existing ones first to ensure they reopen with latest data/position
        self.hide_all_notes()
        # Reopen all
        for note_data in self.notes_data:
            self.open_note_from_data(note_data)

    def hide_all_notes(self):
        """Closes all currently open sticky note windows."""
        # Iterate over a copy of keys as closing modifies the dictionary
        for note_id in list(self.active_notes.keys()):
            note_widget = self.active_notes.get(note_id)
            if note_widget:
                # Block signals temporarily to avoid redundant saves during mass close
                # with QSignalBlocker(note_widget): # Might cause issues if closeEvent needs signals
                note_widget.close() # This will trigger _on_note_closed

    # --- Cleanup ---
    def cleanup(self):
        """Called when the view is being destroyed or closed."""
        print("StickyNotesView cleanup called.")
        self.hide_all_notes() # Ensure all notes are closed and potentially save state
        self.save_notes() # Final save

    # Override closeEvent if this widget itself can be closed independently
    # def closeEvent(self, event):
    #     self.cleanup()
    #     super().closeEvent(event)
