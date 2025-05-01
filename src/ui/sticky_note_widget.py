import sys
import os
import json
import uuid
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QToolBar, 
    QPushButton, QTextEdit, QColorDialog, QSizeGrip,
    QApplication, QMessageBox, QDialog, QListWidget, QListWidgetItem,
    QLabel, QStackedWidget, QMenu
)
from PyQt6.QtGui import QIcon, QAction, QColor, QPalette, QFont, QScreen, QContextMenuEvent
from PyQt6.QtCore import Qt, QSize, QPoint, QRect, pyqtSignal, QSettings, QSignalBlocker

from src.utils.theme_manager import ThemeManager

class StickyNote(QWidget):
    """Individual sticky note widget"""
    
    closed = pyqtSignal(str)  # Signal emitted when this note is closed, passes note_id
    
    def __init__(self, note_id=None, content="", color="#ffff99", geometry=None, parent=None):
        super().__init__(parent, Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        self.note_id = note_id or str(uuid.uuid4())
        self.content = content
        self.color = QColor(color)
        self.initial_geometry = geometry
        
        self.is_dragging = False
        self.drag_start_position = None
        
        # 全局设置防止右键菜单
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("便签")
        self.setWindowIcon(QIcon.fromTheme("note"))
        
        # Set minimum size
        self.setMinimumSize(200, 200)
        
        # Set up the layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(3, 3, 3, 3)
        
        # Create toolbar
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(2)
        
        # Close button
        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setStyleSheet("QPushButton { border: none; border-radius: 10px; background-color: transparent; color: #555; font-weight: bold; } QPushButton:hover { background-color: #ff6666; color: black; }")
        self.close_btn.clicked.connect(self.close)
        self.close_btn.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        
        # Color change button
        self.color_btn = QPushButton("🎨")
        self.color_btn.setFixedSize(20, 20)
        self.color_btn.setStyleSheet("QPushButton { border: none; border-radius: 10px; background-color: transparent; color: #555; font-weight: bold; } QPushButton:hover { background-color: #e0e0e0; color: black; }")
        self.color_btn.clicked.connect(self.change_color)
        self.color_btn.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        
        # 添加按钮到工具栏
        toolbar_layout.addWidget(self.color_btn)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.close_btn)
        
        main_layout.addLayout(toolbar_layout)
        
        # Create text edit for note content
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(self.content)
        self.text_edit.setFrameStyle(0)  # No frame
        self.text_edit.setFont(QFont("Arial", 12))
        # 设置文本编辑框也不响应右键菜单
        self.text_edit.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        main_layout.addWidget(self.text_edit)
        
        # Add size grip to bottom right corner
        size_grip = QSizeGrip(self)
        main_layout.addWidget(size_grip, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
        
        # Set the background color
        self.update_color(self.color)
        
        # Set geometry if specified
        if self.initial_geometry:
            self.setGeometry(self.initial_geometry["x"], self.initial_geometry["y"], 
                         self.initial_geometry["width"], self.initial_geometry["height"])
        else:
            # Place in center of screen by default
            center_point = QScreen.availableGeometry(QApplication.primaryScreen()).center()
            self.move(center_point - QPoint(int(self.width() / 2), int(self.height() / 2)))
    
    def update_color(self, color):
        """Update the sticky note's color"""
        self.color = color
        
        # Create darker color for border
        darker_color = QColor(color)
        darker_color.setHsv(
            darker_color.hue(),
            min(darker_color.saturation() + 20, 255),
            max(darker_color.value() - 30, 0)
        )
        
        # Set stylesheet with the given color and black text
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {color.name()};
                border: 1px solid {darker_color.name()};
                border-radius: 5px;
                color: black;
            }}
            QTextEdit {{
                background-color: {color.name()};
                border: none;
                color: black;
            }}
        """)
    
    def change_color(self):
        """Open color dialog to change note color"""
        color = QColorDialog.getColor(self.color, self, "选择便签颜色")
        if color.isValid():
            self.update_color(color)
    
    def get_data(self):
        """Return note data as a dictionary"""
        return {
            "id": self.note_id,
            "content": self.text_edit.toPlainText(),
            "color": self.color.name(),
            "geometry": {
                "x": self.geometry().x(),
                "y": self.geometry().y(),
                "width": self.width(),
                "height": self.height()
            }
        }
    
    def mousePressEvent(self, event):
        """Handle mouse press events for dragging"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.drag_start_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move events for dragging"""
        if self.is_dragging and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_start_position)
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release events for dragging"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
        
        super().mouseReleaseEvent(event)
    
    def close(self):
        """安全关闭便签"""
        try:
            # 断开所有信号连接
            self.blockSignals(True)
            # 调用父类的关闭方法
            super().close()
        except Exception as e:
            print(f"关闭便签时出错: {str(e)}")
            # 确保窗口关闭
            self.hide()
            self.deleteLater()
            
    def closeEvent(self, event):
        """Handle close event and emit signal"""
        try:
            # 使用阻断器防止信号循环
            with QSignalBlocker(self) as blocker:
                self.closed.emit(self.note_id)
            event.accept()
        except Exception as e:
            print(f"关闭便签时出错: {str(e)}")
            event.accept()  # 确保无论如何都关闭窗口


class NotesListWidget(QWidget):
    """Widget for displaying and managing the list of notes"""
    
    note_selected = pyqtSignal(dict)  # Signal emitted when a note is selected, passes note data
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("便签列表")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px; color: black;")
        layout.addWidget(title_label)
        
        # Instructions
        instructions = QLabel("双击打开便签")
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instructions.setStyleSheet("font-size: 12px; color: #666; margin-bottom: 10px;")
        layout.addWidget(instructions)
        
        # Notes list
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 5px;
                color: black;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
                margin: 2px 0px;
                color: black;
            }
            QListWidget::item:hover {
                background-color: #f0f8ff;
                color: black;
            }
            QListWidget::item:selected {
                background-color: #e0f0ff;
                color: black;
            }
        """)
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.list_widget)
        
        # Button bar
        button_layout = QHBoxLayout()
        
        # Add new note button
        self.add_btn = QPushButton("新建便签")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: black;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #45a049;
                color: black;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
                color: black;
            }
        """)
        button_layout.addWidget(self.add_btn)
        
        layout.addLayout(button_layout)
    
    def update_note_list(self, notes):
        """Update the list with the current notes"""
        self.list_widget.clear()
        
        for note in notes:
            item = QListWidgetItem()
            item.setText(f"便签 {notes.index(note) + 1}")
            
            # Set a hint of the content as tooltip
            content = note.get("content", "").strip()
            if content:
                # Limit to first 100 characters
                preview = content[:100] + ("..." if len(content) > 100 else "")
                item.setToolTip(preview)
            else:
                item.setToolTip("空便签")
            
            # Store the note data with the item
            item.setData(Qt.ItemDataRole.UserRole, note)
            
            # Set the background color to match the note with black text
            color = QColor(note.get("color", "#ffff99"))
            item.setBackground(color)
            item.setForeground(QColor("black"))
            
            self.list_widget.addItem(item)
    
    def on_item_double_clicked(self, item):
        """Handle double-click on a note item"""
        note_data = item.data(Qt.ItemDataRole.UserRole)
        if note_data:
            self.note_selected.emit(note_data)


class StickyNoteWindow(QMainWindow):
    """Main window for managing sticky notes"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_manager = ThemeManager()
        self.notes = []
        self.active_notes = {}  # Dict of open notes: {note_id: StickyNote object}
        
        self.load_notes()
        self.initUI()
        self.apply_current_theme()
    
    def initUI(self):
        self.setWindowTitle("便签管理器")
        self.setGeometry(300, 300, 400, 500)
        
        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create stacked widget for different views
        self.stacked_widget = QStackedWidget()
        
        # Create notes list widget
        self.notes_list = NotesListWidget()
        self.notes_list.add_btn.clicked.connect(self.create_new_note)
        self.notes_list.note_selected.connect(self.open_note)
        
        # Add pages to stacked widget
        self.stacked_widget.addWidget(self.notes_list)
        
        main_layout.addWidget(self.stacked_widget)
        
        # Create toolbar with actions
        toolbar = QToolBar("便签工具栏")
        toolbar.setIconSize(QSize(20, 20))
        toolbar.setStyleSheet("QToolBar { color: black; } QToolButton { color: black; }")
        self.addToolBar(toolbar)
        
        # Add new note action
        new_note_action = QAction(QIcon.fromTheme("document-new"), "新建便签", self)
        new_note_action.triggered.connect(self.create_new_note)
        toolbar.addAction(new_note_action)
        
        # Show all notes action
        show_all_action = QAction(QIcon.fromTheme("view-grid"), "显示所有便签", self)
        show_all_action.triggered.connect(self.show_all_notes)
        toolbar.addAction(show_all_action)
        
        # Hide all notes action
        hide_all_action = QAction(QIcon.fromTheme("window-close"), "隐藏所有便签", self)
        hide_all_action.triggered.connect(self.hide_all_notes)
        toolbar.addAction(hide_all_action)
        
        # Initialize by showing the notes list
        self.update_notes_list()
    
    def load_notes(self):
        """Load notes from the JSON file"""
        try:
            notes_file = os.path.join("data", "notes.json")
            if os.path.exists(notes_file):
                with open(notes_file, "r", encoding="utf-8") as f:
                    self.notes = json.load(f)
            else:
                # Create the data directory if it doesn't exist
                os.makedirs("data", exist_ok=True)
                self.notes = []
        except Exception as e:
            QMessageBox.warning(self, "加载便签失败", f"无法加载便签: {str(e)}")
            self.notes = []
    
    def save_notes(self):
        """Save notes to the JSON file"""
        try:
            # Update self.notes with data from active notes
            for note_id, note_widget in self.active_notes.items():
                # Find the note in the list
                for i, note in enumerate(self.notes):
                    if note.get("id") == note_id:
                        # Update with current data
                        self.notes[i] = note_widget.get_data()
                        break
                else:
                    # Note not found, add it
                    self.notes.append(note_widget.get_data())
            
            # Write to file
            with open(os.path.join("data", "notes.json"), "w", encoding="utf-8") as f:
                json.dump(self.notes, f, indent=2, ensure_ascii=False)
        except Exception as e:
            QMessageBox.warning(self, "保存便签失败", f"无法保存便签: {str(e)}")
    
    def update_notes_list(self):
        """Update the notes list widget"""
        self.notes_list.update_note_list(self.notes)
    
    def create_new_note(self):
        """Create a new sticky note"""
        note = StickyNote(parent=self)
        note.closed.connect(self.on_note_closed)
        
        # Add to active notes
        self.active_notes[note.note_id] = note
        
        # Show the note
        note.show()
        
        # Save the new note
        self.notes.append(note.get_data())
        self.save_notes()
        self.update_notes_list()
    
    def open_note(self, note_data):
        """Open an existing note"""
        note_id = note_data.get("id")
        
        # Check if note is already open
        if note_id in self.active_notes and self.active_notes[note_id].isVisible():
            # Bring to front
            self.active_notes[note_id].activateWindow()
            self.active_notes[note_id].raise_()
            return
        
        # Create new note with existing data
        note = StickyNote(
            note_id=note_id,
            content=note_data.get("content", ""),
            color=note_data.get("color", "#ffff99"),
            geometry=note_data.get("geometry"),
            parent=self
        )
        note.closed.connect(self.on_note_closed)
        
        # Add to active notes
        self.active_notes[note_id] = note
        
        # Show the note
        note.show()
    
    def on_note_closed(self, note_id):
        """Handle note closed signal"""
        if note_id in self.active_notes:
            # Save the note data before removing from active notes
            note_widget = self.active_notes[note_id]
            note_data = note_widget.get_data()
            
            # Update the notes list
            for i, note in enumerate(self.notes):
                if note.get("id") == note_id:
                    self.notes[i] = note_data
                    break
            
            # Remove from active notes
            del self.active_notes[note_id]
            
            # Save notes
            self.save_notes()
            self.update_notes_list()
    
    def show_all_notes(self):
        """Show all notes"""
        # First close any already open notes to refresh them
        for note_id in list(self.active_notes.keys()):
            if self.active_notes[note_id].isVisible():
                self.active_notes[note_id].close()
        
        # Now open all notes
        for note_data in self.notes:
            self.open_note(note_data)
    
    def hide_all_notes(self):
        """Hide all currently open notes"""
        for note_id, note_widget in list(self.active_notes.items()):
            if note_widget.isVisible():
                note_widget.close()
    
    def apply_current_theme(self):
        """Apply the current theme to the window"""
        self.theme_manager.apply_theme(self)
    
    def closeEvent(self, event):
        """Handle closing of the main window"""
        # Save all open notes
        self.save_notes()
        
        # Close all open note windows
        for note_id, note_widget in list(self.active_notes.items()):
            if note_widget.isVisible():
                # Use a signal blocker to prevent saving the same note multiple times
                with QSignalBlocker(note_widget):
                    note_widget.close()
        
        # Accept the event to close the window
        event.accept()


# For standalone testing
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StickyNoteWindow()
    window.show()
    sys.exit(app.exec()) 