# src/ui/views/todo_list_view.py
import sys
import os
import json
import uuid
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QListWidget, QListWidgetItem, QCheckBox, QApplication, QMessageBox,
    QDialog, QLabel, QDateEdit, QComboBox, QFormLayout, QDialogButtonBox,
    QFrame, QSplitter, QMenu, QSizePolicy
)
from PyQt6.QtGui import QIcon, QAction, QColor, QFont, QBrush, QPalette
from PyQt6.QtCore import Qt, QSize, QDate, pyqtSignal, QSignalBlocker

# Correct relative import from views to core
from ..core.base_widget import BaseWidget
# from ..core.theme_manager import ThemeManager # Optional

# --- Data Class ---
class TodoItem:
    """表示一个待办事项"""
    def __init__(self, title="", description="", due_date=None, priority="中", completed=False, item_id=None):
        self.id = item_id or str(uuid.uuid4())
        self.title = title
        self.description = description
        self.due_date = due_date  # Format: YYYY-MM-DD
        self._priority = "中"
        self.set_priority(priority) # Use setter for validation
        self.completed = completed
        # Store created_at if not present in loaded data
        self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def get_priority(self): return self._priority
    def set_priority(self, priority):
        if priority not in ["低", "中", "高"]: self._priority = "中"
        else: self._priority = priority
    priority = property(get_priority, set_priority)

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict): return cls(title="错误数据", description="数据格式不正确")
        priority = data.get("priority", "中")
        if priority not in ["低", "中", "高"]: priority = "中"
        item = cls(
            title=data.get("title", "未命名待办事项"),
            description=data.get("description", ""),
            due_date=data.get("due_date"),
            priority=priority,
            completed=data.get("completed", False),
            item_id=data.get("id")
        )
        # Preserve original creation time if available
        item.created_at = data.get("created_at", item.created_at)
        return item

    def to_dict(self):
        return {
            "id": self.id, "title": self.title, "description": self.description,
            "due_date": self.due_date, "priority": self.priority,
            "completed": self.completed, "created_at": self.created_at
        }

# --- List Item Widget ---
class TodoItemWidget(QFrame):
    """显示单个待办事项的小部件"""
    completed_changed = pyqtSignal(str, bool)  # id, completed
    deleted = pyqtSignal(str)  # id
    edited = pyqtSignal(str)  # id

    def __init__(self, todo_item: TodoItem, parent=None):
        super().__init__(parent)
        self.todo_item = todo_item
        self._init_item_ui()
        self._apply_item_styles() # Apply initial styles

    def _init_item_ui(self):
        self.setObjectName("TodoItemWidgetFrame")
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 5, 8, 5) # Add some padding
        main_layout.setSpacing(8)

        # Checkbox
        self.checkbox = QCheckBox()
        self.checkbox.setFixedSize(20, 20) # Consistent size
        self.checkbox.setChecked(self.todo_item.completed)
        self.checkbox.stateChanged.connect(self._on_completed_changed)
        self.checkbox.setToolTip("标记完成/未完成")
        main_layout.addWidget(self.checkbox)

        # Content Area (Title, Info, Description)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(2)

        # Top Row: Title + Priority
        top_row_layout = QHBoxLayout()
        top_row_layout.setContentsMargins(0,0,0,0)
        self.title_label = QLabel(self.todo_item.title)
        self.title_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.title_label.setObjectName("TodoTitleLabel")
        top_row_layout.addWidget(self.title_label, 1) # Title takes expanding space

        self.priority_label = QLabel(f"[{self.todo_item.priority}]")
        self.priority_label.setObjectName("TodoPriorityLabel")
        self.priority_label.setToolTip(f"优先级: {self.todo_item.priority}")
        top_row_layout.addWidget(self.priority_label)
        content_layout.addLayout(top_row_layout)

        # Bottom Row: Due Date + Description Snippet (Optional)
        bottom_row_layout = QHBoxLayout()
        bottom_row_layout.setContentsMargins(0,0,0,0)
        self.due_date_label = QLabel()
        self.due_date_label.setObjectName("TodoDueDateLabel")
        self.due_date_label.setToolTip("截止日期")
        bottom_row_layout.addWidget(self.due_date_label)
        bottom_row_layout.addStretch()
        content_layout.addLayout(bottom_row_layout)

        # Update dynamic content
        self._update_dynamic_content()

        main_layout.addWidget(content_widget, 1) # Content takes expanding space

        # Buttons Area
        button_layout = QVBoxLayout() # Vertical buttons
        button_layout.setSpacing(3)
        self.edit_btn = QPushButton("编辑")
        self.edit_btn.setFixedSize(50, 24)
        self.edit_btn.setObjectName("TodoEditButton")
        self.edit_btn.setToolTip("编辑详情")
        self.edit_btn.clicked.connect(self._on_edit_clicked)
        button_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("删除")
        self.delete_btn.setFixedSize(50, 24)
        self.delete_btn.setObjectName("TodoDeleteButton")
        self.delete_btn.setToolTip("删除此项")
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        button_layout.addWidget(self.delete_btn)
        button_layout.addStretch() # Push buttons up

        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

    def _update_dynamic_content(self):
        """Updates labels based on current todo_item state."""
        # Update Title Style (Strikethrough)
        font = self.title_label.font()
        font.setStrikeOut(self.todo_item.completed)
        self.title_label.setFont(font)
        self.title_label.setEnabled(not self.todo_item.completed) # Grey out if completed

        # Update Due Date Label and Color
        if self.todo_item.due_date:
            date_str = self.todo_item.due_date
            try:
                due_date_obj = QDate.fromString(date_str, "yyyy-MM-dd")
                today = QDate.currentDate()
                if due_date_obj.isValid():
                    if not self.todo_item.completed and due_date_obj < today:
                        self.due_date_label.setText(f"{date_str} (已过期)")
                        self.due_date_label.setProperty("status", "overdue")
                    elif due_date_obj == today:
                         self.due_date_label.setText(f"{date_str} (今天)")
                         self.due_date_label.setProperty("status", "due_today")
                    else:
                        self.due_date_label.setText(f"{date_str}")
                        self.due_date_label.setProperty("status", "normal")
                else:
                    self.due_date_label.setText(f"{date_str} (无效日期)")
                    self.due_date_label.setProperty("status", "invalid")
            except Exception:
                self.due_date_label.setText(f"{date_str} (日期错误)")
                self.due_date_label.setProperty("status", "invalid")
        else:
            self.due_date_label.setText("无截止日期")
            self.due_date_label.setProperty("status", "no_date")

        # Update Priority Label Color
        self.priority_label.setText(f"[{self.todo_item.priority}]")
        self.priority_label.setProperty("priority", self.todo_item.priority.lower())

        # Re-apply styles to update property-based selectors
        self._apply_item_styles()


    def _apply_item_styles(self, is_dark=False):
        """Applies styles based on completion, priority, and due date."""
        base_bg = "#f0f9f0" if self.todo_item.completed else ("#2d2d2d" if is_dark else "#f9f9f9")
        border_color = "#555" if is_dark else "#ddd"
        text_color = "#888" if self.todo_item.completed else ("#ccc" if is_dark else "#333")
        title_color = "#aaa" if self.todo_item.completed else ("#eee" if is_dark else "#000") # Title color separate
        priority_colors = {
            "高": "#d9534f", "中": "#f0ad4e", "低": "#5cb85c",
            "high": "#d9534f", "medium": "#f0ad4e", "low": "#5cb85c"
        }
        priority_color = priority_colors.get(self.todo_item.priority.lower(), "#777")
        due_date_color = text_color # Default
        if not self.todo_item.completed:
             status = self.due_date_label.property("status")
             if status == "overdue": due_date_color = "#d9534f" # Red
             elif status == "due_today": due_date_color = "#f0ad4e" # Orange

        edit_button_bg = "#337ab7" if not is_dark else "#286090"
        delete_button_bg = "#d9534f" if not is_dark else "#c9302c"
        button_text = "#ffffff"

        self.setStyleSheet(f"""
            QFrame#TodoItemWidgetFrame {{
                border: 1px solid {border_color};
                border-radius: 4px;
                background-color: {base_bg};
                margin-bottom: 3px; /* Spacing between items */
            }}
            QLabel#TodoTitleLabel {{
                color: {title_color};
                background: transparent;
                /* Strikethrough handled by font property */
            }}
            QLabel#TodoPriorityLabel {{
                color: {priority_color};
                font-weight: bold;
                background: transparent;
                font-size: 9pt;
            }}
            QLabel#TodoDueDateLabel {{
                color: {due_date_color};
                font-size: 9pt;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 16px; height: 16px; border: 1px solid #aaa; border-radius: 3px;
            }}
            QCheckBox::indicator:checked {{ background-color: #5cb85c; }}
            QPushButton {{
                color: {button_text}; font-weight: bold; border: none; border-radius: 3px; padding: 3px; font-size: 9pt;
            }}
            QPushButton#TodoEditButton {{ background-color: {edit_button_bg}; }}
            QPushButton#TodoEditButton:hover {{ background-color: {QColor(edit_button_bg).darker(110).name()}; }}
            QPushButton#TodoDeleteButton {{ background-color: {delete_button_bg}; }}
            QPushButton#TodoDeleteButton:hover {{ background-color: {QColor(delete_button_bg).darker(110).name()}; }}
        """)

    def _on_completed_changed(self, state):
        completed = (state == Qt.CheckState.Checked.value) # Use .value for comparison
        if self.todo_item.completed != completed:
            self.todo_item.completed = completed
            self._update_dynamic_content() # Update styles (strikethrough, colors)
            self.completed_changed.emit(self.todo_item.id, completed)

    def _on_edit_clicked(self):
        self.edited.emit(self.todo_item.id)

    def _on_delete_clicked(self):
        self.deleted.emit(self.todo_item.id)

# --- Edit/Add Dialog ---
class TodoItemDialog(QDialog):
    """新增或编辑待办事项的对话框"""
    def __init__(self, todo_item: TodoItem | None = None, parent=None):
        super().__init__(parent)
        self.todo_item = todo_item # Store the original item for potential update
        self._init_dialog_ui()
        self._apply_dialog_styles()

    def _init_dialog_ui(self):
        self.setWindowTitle("编辑待办事项" if self.todo_item else "新建待办事项")
        self.setMinimumWidth(400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.title_edit = QLineEdit(self.todo_item.title if self.todo_item else "")
        form_layout.addRow("标题*:", self.title_edit)

        self.desc_edit = QLineEdit(self.todo_item.description if self.todo_item else "")
        form_layout.addRow("描述:", self.desc_edit)

        self.date_edit = QDateEdit(calendarPopup=True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        if self.todo_item and self.todo_item.due_date:
            date = QDate.fromString(self.todo_item.due_date, "yyyy-MM-dd")
            self.date_edit.setDate(date if date.isValid() else QDate.currentDate())
        else:
            self.date_edit.setDate(QDate.currentDate())
        form_layout.addRow("截止日期:", self.date_edit)

        # Priority Buttons
        priority_layout = QHBoxLayout()
        self.priority_group = QButtonGroup(self)
        priorities = ["低", "中", "高"]
        self.priority_buttons = {}
        for prio in priorities:
            btn = QPushButton(prio)
            btn.setCheckable(True)
            btn.setObjectName(f"PrioBtn{prio}")
            self.priority_group.addButton(btn)
            priority_layout.addWidget(btn)
            self.priority_buttons[prio] = btn
            if self.todo_item and self.todo_item.priority == prio:
                btn.setChecked(True)
            elif not self.todo_item and prio == "中": # Default for new
                btn.setChecked(True)
        form_layout.addRow("优先级:", priority_layout)

        self.completed_checkbox = QCheckBox("已完成")
        if self.todo_item:
            self.completed_checkbox.setChecked(self.todo_item.completed)
        form_layout.addRow("", self.completed_checkbox)

        layout.addLayout(form_layout)

        # Dialog Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _apply_dialog_styles(self, is_dark=False):
        # Basic styling, similar to EventDialog
        bg_color = "#2d2d2d" if is_dark else "#ffffff"
        text_color = "#f0f0f0" if is_dark else "#000000"
        border_color = "#555555" if is_dark else "#cccccc"
        input_bg = "#3c3c3c" if is_dark else "#ffffff"
        button_bg = "#555" if is_dark else "#f0f0f0"

        self.setStyleSheet(f"QDialog {{ background-color: {bg_color}; color: {text_color}; }} QLabel {{ background: transparent; }}")
        for widget in self.findChildren(QLineEdit) + self.findChildren(QDateEdit):
             widget.setStyleSheet(f"background-color: {input_bg}; color: {text_color}; border: 1px solid {border_color}; border-radius: 3px; padding: 4px;")
        # Priority button styling
        prio_colors = {"低": "#5cb85c", "中": "#f0ad4e", "高": "#d9534f"}
        for prio, btn in self.priority_buttons.items():
             p_bg = prio_colors[prio]
             p_hover = QColor(p_bg).lighter(110).name()
             p_checked = QColor(p_bg).darker(110).name()
             btn.setStyleSheet(f"""
                 QPushButton {{ background-color: {p_bg}; color: white; border: none; border-radius: 3px; padding: 5px 10px; font-weight: bold; }}
                 QPushButton:hover {{ background-color: {p_hover}; }}
                 QPushButton:checked {{ background-color: {p_checked}; border: 2px solid {text_color}; }}
             """)

    def get_selected_priority(self) -> str:
        """Gets the selected priority from the button group."""
        checked_button = self.priority_group.checkedButton()
        return checked_button.text() if checked_button else "中"

    def get_todo_data(self) -> dict:
        """Returns the edited/new todo data as a dictionary."""
        title = self.title_edit.text().strip()
        if not title: title = "未命名待办事项"
        return {
            "id": self.todo_item.id if self.todo_item else str(uuid.uuid4()),
            "title": title,
            "description": self.desc_edit.text().strip(),
            "due_date": self.date_edit.date().toString("yyyy-MM-dd"),
            "priority": self.get_selected_priority(),
            "completed": self.completed_checkbox.isChecked(),
            # Preserve created_at if editing
            "created_at": self.todo_item.created_at if self.todo_item else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

# --- Main Todo List View ---
class TodoListView(BaseWidget):
    """待办事项管理视图"""
    def __init__(self, parent=None):
        self.todo_items_data: list[dict] = [] # Store raw data dicts
        self._data_file_path = self._get_data_file_path()
        self.load_todo_items()
        super().__init__(parent)

    def _get_data_file_path(self):
        """Determines the path for the todo data file."""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
            data_dir = os.path.join(project_root, "data")
            os.makedirs(data_dir, exist_ok=True)
            return os.path.join(data_dir, "todo.json")
        except Exception as e:
            print(f"Error determining todo data file path: {e}")
            return os.path.join(os.path.dirname(os.path.abspath(__file__)), "todo.json")

    def _init_ui(self):
        """初始化主视图 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # --- Filter Bar ---
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("状态:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部", "未完成", "已完成"])
        filter_layout.addWidget(self.filter_combo)
        filter_layout.addSpacing(15)
        filter_layout.addWidget(QLabel("优先级:"))
        self.priority_filter_combo = QComboBox()
        self.priority_filter_combo.addItems(["全部", "低", "中", "高"])
        filter_layout.addWidget(self.priority_filter_combo)
        filter_layout.addStretch()
        self.add_button = QPushButton("新建")
        self.add_button.setIcon(QIcon.fromTheme("list-add"))
        filter_layout.addWidget(self.add_button)
        main_layout.addLayout(filter_layout)

        # --- Todo List ---
        self.todo_list_widget = QListWidget()
        self.todo_list_widget.setObjectName("TodoListViewList")
        self.todo_list_widget.setAlternatingRowColors(True) # Helps distinguish items
        main_layout.addWidget(self.todo_list_widget, 1) # List takes expanding space

        # --- Quick Add Bar ---
        quick_add_layout = QHBoxLayout()
        self.quick_add_edit = QLineEdit()
        self.quick_add_edit.setPlaceholderText("输入新待办事项标题，按 Enter 添加...")
        quick_add_layout.addWidget(self.quick_add_edit)
        # Add button removed, using Enter key instead
        main_layout.addLayout(quick_add_layout)

        self.setLayout(main_layout)
        self.refresh_display_list() # Initial population

    def _connect_signals(self):
        """连接信号"""
        self.filter_combo.currentTextChanged.connect(self.refresh_display_list)
        self.priority_filter_combo.currentTextChanged.connect(self.refresh_display_list)
        self.add_button.clicked.connect(self.add_new_item_dialog)
        self.quick_add_edit.returnPressed.connect(self.quick_add_item)

    def _apply_theme(self):
        """应用主题"""
        self.update_styles(is_dark=False) # Default light

    def update_styles(self, is_dark: bool):
        """更新样式"""
        bg_color = "#1e1e1e" if is_dark else "#ffffff"
        text_color = "#f0f0f0" if is_dark else "#000000"
        border_color = "#555555" if is_dark else "#cccccc"
        list_bg = "#2d2d2d" if is_dark else "#ffffff"
        list_alt_bg = "#3c3c3c" if is_dark else "#f8f8f8"
        input_bg = "#3c3c3c" if is_dark else "#ffffff"
        button_bg = "#555" if is_dark else "#f0f0f0"

        self.setStyleSheet(f"QWidget {{ background-color: {bg_color}; color: {text_color}; }}")
        for combo in [self.filter_combo, self.priority_filter_combo]:
             combo.setStyleSheet(f"QComboBox {{ background-color: {input_bg}; color: {text_color}; border: 1px solid {border_color}; border-radius: 3px; padding: 3px; }} QComboBox QAbstractItemView {{ background-color: {input_bg}; color: {text_color}; selection-background-color: #3498db; }}")
        self.add_button.setStyleSheet(f"QPushButton {{ background-color: {button_bg}; color: {text_color}; border: 1px solid {border_color}; border-radius: 3px; padding: 4px 8px; }} QPushButton:hover {{ background-color: {QColor(button_bg).lighter(110).name()}; }}")
        self.quick_add_edit.setStyleSheet(f"QLineEdit {{ background-color: {input_bg}; color: {text_color}; border: 1px solid {border_color}; border-radius: 3px; padding: 4px; }}")
        self.todo_list_widget.setStyleSheet(f"""
            QListWidget#TodoListViewList {{
                background-color: {list_bg};
                alternate-background-color: {list_alt_bg};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 0px; /* No padding for list, item widget handles it */
            }}
            QListWidget#TodoListViewList::item {{
                border: none; /* No border for the item itself */
                padding: 0px; /* No padding for the item itself */
            }}
        """)
        # Update item widgets already in the list
        for i in range(self.todo_list_widget.count()):
             item = self.todo_list_widget.item(i)
             widget = self.todo_list_widget.itemWidget(item)
             if isinstance(widget, TodoItemWidget):
                 widget._apply_item_styles(is_dark)


    # --- Data Handling ---
    def load_todo_items(self):
        """Loads todo data from the JSON file."""
        if not os.path.exists(self._data_file_path):
            self.todo_items_data = []
            return
        try:
            with open(self._data_file_path, "r", encoding="utf-8") as f:
                self.todo_items_data = json.load(f)
                if not isinstance(self.todo_items_data, list): self.todo_items_data = []
                # Validate data structure minimally
                self.todo_items_data = [d for d in self.todo_items_data if isinstance(d, dict) and 'id' in d]
        except (json.JSONDecodeError, IOError, Exception) as e:
            QMessageBox.warning(self, "加载待办事项失败", f"无法加载: {e}")
            self.todo_items_data = []

    def save_todo_items(self):
        """Saves the current todo_items_data list to the JSON file."""
        try:
            os.makedirs(os.path.dirname(self._data_file_path), exist_ok=True)
            with open(self._data_file_path, "w", encoding="utf-8") as f:
                json.dump(self.todo_items_data, f, ensure_ascii=False, indent=2)
        except (IOError, Exception) as e:
            QMessageBox.warning(self, "保存待办事项失败", f"无法保存: {e}")

    # --- UI Refresh ---
    def refresh_display_list(self):
        """Filters, sorts, and displays todo items in the list widget."""
        status_filter = self.filter_combo.currentText()
        priority_filter = self.priority_filter_combo.currentText()

        # Filter
        filtered_data = []
        for item_data in self.todo_items_data:
            # Status filter
            show = True
            if status_filter == "未完成" and item_data.get("completed", False): show = False
            if status_filter == "已完成" and not item_data.get("completed", False): show = False
            # Priority filter
            if priority_filter != "全部" and item_data.get("priority", "中") != priority_filter: show = False
            if show: filtered_data.append(item_data)

        # Sort
        def sort_key(item_data):
            prio_val = {"高": 0, "中": 1, "低": 2}.get(item_data.get("priority", "中"), 1)
            due_date = item_data.get("due_date", "9999-99-99") or "9999-99-99"
            completed = 1 if item_data.get("completed", False) else 0
            created = item_data.get("created_at", "")
            return (completed, due_date, prio_val, created) # Sort by completed, due date, priority, created

        sorted_data = sorted(filtered_data, key=sort_key)

        # Display
        self.todo_list_widget.clear()
        if not sorted_data:
            item = QListWidgetItem("无待办事项")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable) # Make it non-selectable
            self.todo_list_widget.addItem(item)
        else:
            for item_data in sorted_data:
                try:
                    todo_item = TodoItem.from_dict(item_data) # Create object for widget
                    widget = TodoItemWidget(todo_item)
                    widget.completed_changed.connect(self._handle_item_status_change)
                    widget.edited.connect(self._handle_item_edit)
                    widget.deleted.connect(self._handle_item_delete)

                    list_item = QListWidgetItem()
                    list_item.setSizeHint(widget.sizeHint()) # Use widget's preferred size
                    # Store ID in item data for easy retrieval
                    list_item.setData(Qt.ItemDataRole.UserRole, todo_item.id)

                    self.todo_list_widget.addItem(list_item)
                    self.todo_list_widget.setItemWidget(list_item, widget)
                    # Apply theme styles after adding
                    widget._apply_item_styles(is_dark=False) # TODO: Get actual theme state
                except Exception as e:
                    print(f"Error creating widget for item {item_data.get('id')}: {e}")
                    error_item = QListWidgetItem(f"加载错误: {item_data.get('title', '未知')}")
                    error_item.setForeground(QColor("red"))
                    self.todo_list_widget.addItem(error_item)

    # --- Item Actions ---
    def add_new_item_dialog(self):
        """Opens the dialog to add a new item."""
        dialog = TodoItemDialog(parent=self)
        # dialog._apply_dialog_styles(is_dark=...) # Apply theme
        if dialog.exec():
            new_data = dialog.get_todo_data()
            self.todo_items_data.append(new_data)
            self.save_todo_items()
            self.refresh_display_list()

    def quick_add_item(self):
        """Adds a new item from the quick add line edit."""
        title = self.quick_add_edit.text().strip()
        if not title: return
        new_item = TodoItem(title=title) # Create object with default values
        self.todo_items_data.append(new_item.to_dict()) # Add data dict to list
        self.save_todo_items()
        self.refresh_display_list()
        self.quick_add_edit.clear()

    def _handle_item_status_change(self, item_id: str, completed: bool):
        """Updates the completion status in the data list and saves."""
        for i, item_data in enumerate(self.todo_items_data):
            if item_data.get("id") == item_id:
                self.todo_items_data[i]["completed"] = completed
                self.save_todo_items()
                # Find the widget in the list and update its style immediately
                list_item = self._find_list_item_by_id(item_id)
                if list_item:
                     widget = self.todo_list_widget.itemWidget(list_item)
                     if isinstance(widget, TodoItemWidget):
                         widget._update_dynamic_content() # Update styles based on new status
                # Optionally re-filter/re-sort if status change affects visibility/order
                # self.refresh_display_list() # Can be slow if list is long
                break

    def _handle_item_edit(self, item_id: str):
        """Opens the edit dialog for the specified item."""
        item_data = next((d for d in self.todo_items_data if d.get("id") == item_id), None)
        if not item_data: return
        todo_item_obj = TodoItem.from_dict(item_data) # Create object for dialog

        dialog = TodoItemDialog(todo_item=todo_item_obj, parent=self)
        # dialog._apply_dialog_styles(is_dark=...) # Apply theme
        if dialog.exec():
            updated_data = dialog.get_todo_data()
            # Find and update the data in the list
            for i, data in enumerate(self.todo_items_data):
                if data.get("id") == item_id:
                    self.todo_items_data[i] = updated_data
                    self.save_todo_items()
                    self.refresh_display_list() # Refresh the whole list
                    break

    def _handle_item_delete(self, item_id: str):
        """Deletes the item with the specified ID."""
        initial_len = len(self.todo_items_data)
        self.todo_items_data = [d for d in self.todo_items_data if d.get("id") != item_id]
        if len(self.todo_items_data) < initial_len:
            self.save_todo_items()
            self.refresh_display_list()

    def _find_list_item_by_id(self, item_id: str) -> QListWidgetItem | None:
         """Finds the QListWidgetItem corresponding to a given data ID."""
         for i in range(self.todo_list_widget.count()):
             item = self.todo_list_widget.item(i)
             if item and item.data(Qt.ItemDataRole.UserRole) == item_id:
                 return item
         return None

    # --- Cleanup ---
    def cleanup(self):
        """Called when the view is closing."""
        self.save_todo_items() # Ensure data is saved

    # def closeEvent(self, event): # If needed
    #     self.cleanup()
    #     super().closeEvent(event)
