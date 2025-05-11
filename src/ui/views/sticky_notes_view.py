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
from PyQt6.QtCore import Qt, QSize, QPoint, QRect, pyqtSignal, QSettings, QSignalBlocker, QTimer

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
        self.text_edit.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.text_edit.customContextMenuRequested.connect(self._show_context_menu)
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
        """Emit data change on resize with error handling."""
        try:
            super().resizeEvent(event)
            # 使用计时器避免调整大小时过于频繁地发出信号
            try:
                if not hasattr(self, '_resize_timer'):
                    self._resize_timer = QTimer(self)
                    self._resize_timer.setSingleShot(True)
                    self._resize_timer.timeout.connect(self._on_data_changed)
                self._resize_timer.start(500) # 500毫秒无调整后发出信号
            except Exception as e:
                print(f"设置调整大小计时器时出错: {e}")
                # 如果计时器失败，直接发出数据变更信号
                self._on_data_changed()
        except Exception as e:
            print(f"处理便签调整大小事件时出错: {e}")

    def _show_context_menu(self, position):
        """显示自定义右键菜单"""
        try:
            # 只有当有文本被选中时才显示菜单
            if not self.text_edit.textCursor().hasSelection():
                return
                
            context_menu = QMenu(self)
            
            # 添加发送到翻译工具的选项
            translate_action = context_menu.addAction("发送到翻译工具")
            translate_action.triggered.connect(self._send_to_translator)
            
            # 添加发送到AI对话的选项
            ai_action = context_menu.addAction("发送到AI对话")
            ai_action.triggered.connect(self._send_to_ai_chat)
            
            # 显示菜单
            context_menu.exec(self.text_edit.mapToGlobal(position))
        except Exception as e:
            print(f"显示上下文菜单时出错: {e}")
    
    def _send_to_translator(self):
        """将选中文本发送到翻译工具"""
        try:
            selected_text = self.text_edit.textCursor().selectedText()
            if not selected_text:
                return
                
            # 尝试导入并使用翻译对话框
            try:
                from ...dialogs.translation_dialog import TranslationDialog
                dialog = TranslationDialog(self)
                dialog.set_source_text(selected_text)
                dialog.show()
            except ImportError:
                # 备选方案：尝试使用翻译面板
                try:
                    from ...docks.translation_dock import TranslationDock
                    # 获取主窗口
                    main_window = QApplication.activeWindow()
                    if main_window:
                        # 查找或创建翻译面板
                        translation_dock = None
                        for dock in main_window.findChildren(TranslationDock):
                            translation_dock = dock
                            break
                            
                        if translation_dock:
                            translation_dock.set_source_text(selected_text)
                            translation_dock.show()
                            translation_dock.raise_()
                except ImportError:
                    QMessageBox.warning(self, "功能不可用", "翻译功能不可用，请确保翻译组件已正确安装。")
        except Exception as e:
            print(f"发送文本到翻译工具时出错: {e}")
    
    def _send_to_ai_chat(self):
        """将选中文本发送到AI对话"""
        try:
            selected_text = self.text_edit.textCursor().selectedText()
            if not selected_text:
                return
                
            # 尝试导入并使用AI对话组件
            try:
                from ...atomic.ai.ai_chat_widget import AIChatWidget
                # 获取主窗口
                main_window = QApplication.activeWindow()
                if main_window:
                    # 查找或创建AI对话组件
                    ai_chat = None
                    for widget in main_window.findChildren(AIChatWidget):
                        ai_chat = widget
                        break
                        
                    if ai_chat:
                        ai_chat.set_input_text(selected_text)
                        ai_chat.show()
                        ai_chat.raise_()
                    else:
                        QMessageBox.warning(self, "组件未找到", "未找到AI对话组件，请确保AI对话功能已启用。")
            except ImportError:
                QMessageBox.warning(self, "功能不可用", "AI对话功能不可用，请确保AI组件已正确安装。")
        except Exception as e:
            print(f"发送文本到AI对话时出错: {e}")
    
    def closeEvent(self, event):
        """Handles the close event, emits closed signal with improved error handling."""
        try:
            # 尝试发出关闭信号
            try:
                self.closed.emit(self.note_id)
            except Exception as e:
                print(f"便签 {self.note_id} 发出关闭信号时出错: {e}")
                # 即使信号发送失败，仍然继续关闭窗口
            
            # 保存当前数据作为最后的尝试
            try:
                # 发出最后的数据变更信号，确保数据被保存
                self._on_data_changed()
            except Exception as e:
                print(f"便签关闭前保存数据时出错: {e}")
            
            # 调用父类的关闭事件处理
            super().closeEvent(event)
        except Exception as e:
            print(f"处理便签关闭事件时出错: {e}")
            # 确保窗口被关闭，即使出现错误
            try:
                super().closeEvent(event)
            except:
                # 如果父类的关闭事件也失败，强制接受事件
                event.accept()


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
        # 先初始化基本属性
        self.active_notes: dict[str, StickyNote] = {} # {note_id: StickyNote widget instance}
        
        # 使用数据管理器处理数据逻辑
        try:
            from ...data.data_manager import StickyNoteDataManager
            self.data_manager = StickyNoteDataManager()
        except Exception as e:
            print(f"初始化便签数据管理器时出错: {e}")
            # 创建一个空的数据管理器作为后备
            from ...data.data_manager import DataManager
            self.data_manager = DataManager("sticky_notes.json")
            
        # 调用父类初始化 (会调用 _init_ui, _connect_signals, _apply_theme)
        super().__init__(parent)

    # 数据文件路径现在由数据管理器处理

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
    # 数据加载和保存现在由数据管理器处理

    def update_notes_list_display(self):
        """Updates the list widget display with error handling."""
        try:
            notes_data = self.data_manager.get_data()
            self.notes_list_widget.update_note_list(notes_data)
        except Exception as e:
            print(f"更新便签列表显示时出错: {e}")
            # 显示空列表作为后备
            self.notes_list_widget.update_note_list([])

    # --- Note Management ---
    def create_new_note(self):
        """Creates a new sticky note window and data entry with error handling."""
        try:
            # 创建新便签窗口
            new_note_widget = StickyNote(parent=None) # Create as top-level window
            
            # 连接信号
            try:
                new_note_widget.closed.connect(self._on_note_closed)
                new_note_widget.data_changed.connect(self._on_note_data_changed)
            except Exception as e:
                print(f"连接便签信号时出错: {e}")
                # 如果信号连接失败，仍然继续，但可能无法保存数据

            # 获取便签ID并保存到活动便签字典
            note_id = new_note_widget.note_id
            self.active_notes[note_id] = new_note_widget

            # 添加新便签数据并保存
            try:
                new_note_data = new_note_widget.get_data()
                save_success = self.data_manager.add_item(new_note_data)
                if not save_success:
                    print(f"警告: 便签数据保存失败，ID: {note_id}")
            except Exception as e:
                print(f"保存便签数据时出错: {e}")
                # 即使保存失败，仍然显示便签窗口
            
            # 更新便签列表显示
            self.update_notes_list_display()

            # 显示便签窗口
            new_note_widget.show()
            
        except Exception as e:
            print(f"创建新便签时出错: {e}")
            # 可以在这里添加用户提示，例如显示错误消息框
            try:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "创建便签失败", f"无法创建新便签: {e}")
            except:
                # 如果连消息框都无法显示，至少在控制台记录错误
                print("无法显示错误消息框")

    def open_note_from_data(self, note_data: dict):
        """Opens an existing note window from its data with error handling."""
        try:
            # 验证便签数据
            if not isinstance(note_data, dict):
                print(f"警告: 无效的便签数据格式: {type(note_data)}")
                return
                
            note_id = note_data.get("id")
            if not note_id:
                print("警告: 便签数据缺少ID字段")
                return

            # 如果便签已经打开，只需激活它
            if note_id in self.active_notes:
                try:
                    note_widget = self.active_notes[note_id]
                    if note_widget and not note_widget.isHidden():
                        note_widget.show()
                        note_widget.activateWindow()
                        note_widget.raise_()
                        return
                    else:
                        # 引用存在但窗口可能已被意外删除
                        print(f"便签窗口 {note_id} 引用存在但无效，将重新创建")
                        del self.active_notes[note_id]
                except Exception as e:
                    print(f"激活现有便签时出错: {e}")
                    # 删除无效引用并继续创建新窗口
                    del self.active_notes[note_id]

            # 创建并显示便签窗口
            try:
                note_widget = StickyNote(
                    note_id=note_id,
                    content=note_data.get("content", ""),
                    color=note_data.get("color", "#ffff99"),
                    geometry=note_data.get("geometry"),
                    parent=None # 创建为顶级窗口
                )
                
                # 连接信号
                try:
                    note_widget.closed.connect(self._on_note_closed)
                    note_widget.data_changed.connect(self._on_note_data_changed)
                except Exception as e:
                    print(f"连接便签信号时出错: {e}")
                    # 如果信号连接失败，仍然继续，但可能无法保存数据
                
                # 保存到活动便签字典并显示
                self.active_notes[note_id] = note_widget
                note_widget.show()
                
            except Exception as e:
                print(f"创建便签窗口时出错: {e}")
                # 可以在这里添加用户提示
                
        except Exception as e:
            print(f"打开便签时出错: {e}")
            # 记录错误但不中断程序流程

    def _on_note_closed(self, note_id: str):
        """Handles the closed signal from a StickyNote window with error handling."""
        try:
            if not note_id:
                print("警告: 收到空的便签ID关闭信号")
                return
                
            if note_id in self.active_notes:
                # 数据应该已经通过data_changed信号或关闭前保存
                # 从活动字典中移除
                try:
                    del self.active_notes[note_id]
                    print(f"便签 {note_id} 已关闭并从活动列表中移除。")
                except Exception as e:
                    print(f"从活动列表移除便签时出错: {e}")
            
            # 刷新列表以防状态视觉上发生变化
            self.update_notes_list_display()
            
        except Exception as e:
            print(f"处理便签关闭信号时出错: {e}")
            # 尝试更新列表显示，即使出错
            try:
                self.update_notes_list_display()
            except:
                pass

    def _on_note_data_changed(self, note_data: dict):
        """Handles data changes from an active StickyNote window with error handling."""
        try:
            # 验证便签数据
            if not isinstance(note_data, dict):
                print(f"警告: 无效的便签数据格式: {type(note_data)}")
                return
                
            note_id = note_data.get("id")
            if not note_id:
                print("警告: 便签数据缺少ID字段")
                return

            # 使用数据管理器更新数据
            try:
                save_success = self.data_manager.update_item(note_id, note_data)
                if not save_success:
                    print(f"警告: 便签数据更新失败，ID: {note_id}")
            except Exception as e:
                print(f"更新便签数据时出错: {e}")
                # 即使保存失败，仍然继续更新UI
            
            # 更新便签列表显示
            self.update_notes_list_display()
            
        except Exception as e:
            print(f"处理便签数据变更时出错: {e}")
            # 尝试更新列表显示，即使出错
            try:
                self.update_notes_list_display()
            except:
                pass

    # --- Global Actions (Could be triggered externally) ---
    def show_all_notes(self):
        """Opens windows for all notes in the data list with error handling."""
        try:
            # 关闭现有便签，确保它们以最新的数据/位置重新打开
            self.hide_all_notes()
            
            # 重新打开所有便签
            try:
                notes_data = self.data_manager.get_data()
                for note_data in notes_data:
                    try:
                        self.open_note_from_data(note_data)
                    except Exception as e:
                        print(f"打开便签 {note_data.get('id', '未知ID')} 时出错: {e}")
                        # 继续处理下一个便签
            except Exception as e:
                print(f"获取便签数据时出错: {e}")
                # 如果无法获取数据，显示错误消息
                try:
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "便签加载失败", "无法加载便签数据，请检查数据文件。")
                except:
                    print("无法显示错误消息框")
        except Exception as e:
            print(f"显示所有便签时出错: {e}")

    def hide_all_notes(self):
        """Closes all currently open sticky note windows with error handling."""
        try:
            # 遍历键的副本，因为关闭会修改字典
            note_ids = list(self.active_notes.keys())
            for note_id in note_ids:
                try:
                    note_widget = self.active_notes.get(note_id)
                    if note_widget and not note_widget.isHidden():
                        # 关闭便签窗口，这将触发 _on_note_closed
                        note_widget.close()
                except Exception as e:
                    print(f"关闭便签 {note_id} 时出错: {e}")
                    # 如果关闭失败，从活动列表中移除
                    try:
                        if note_id in self.active_notes:
                            del self.active_notes[note_id]
                    except:
                        pass
        except Exception as e:
            print(f"隐藏所有便签时出错: {e}")

    # --- Cleanup ---
    def cleanup(self):
        """Called when the view is being destroyed or closed with error handling."""
        try:
            print("StickyNotesView cleanup called.")
            self.hide_all_notes()
            
            # 确保所有活动便签都被清理
            try:
                if self.active_notes:
                    print(f"警告: 清理后仍有 {len(self.active_notes)} 个活动便签引用")
                    self.active_notes.clear()
            except Exception as e:
                print(f"清理活动便签引用时出错: {e}")
                
        except Exception as e:
            print(f"便签视图清理时出错: {e}")
            # 尝试强制清理
            try:
                self.active_notes.clear()
            except:
                pass # Ensure all notes are closed and potentially save state
        # 数据已经由数据管理器保存，无需额外操作 # Final save

    # Override closeEvent if this widget itself can be closed independently
    # def closeEvent(self, event):
    #     self.cleanup()
    #     super().closeEvent(event)
