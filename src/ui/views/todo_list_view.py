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
    QFrame, QSplitter, QMenu, QSizePolicy, QButtonGroup
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

        # 安全地获取初始值，避免空指针异常
        initial_title = "" if self.todo_item is None else self.todo_item.title
        initial_desc = "" if self.todo_item is None else self.todo_item.description
        initial_completed = False if self.todo_item is None else self.todo_item.completed

        self.title_edit = QLineEdit(initial_title)
        form_layout.addRow("标题*:", self.title_edit)

        self.desc_edit = QLineEdit(initial_desc)
        form_layout.addRow("描述:", self.desc_edit)

        self.date_edit = QDateEdit(calendarPopup=True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        
        # 安全地设置日期
        try:
            if self.todo_item and hasattr(self.todo_item, 'due_date') and self.todo_item.due_date:
                date = QDate.fromString(self.todo_item.due_date, "yyyy-MM-dd")
                if date.isValid():
                    self.date_edit.setDate(date)
                else:
                    print(f"无效的日期格式: {self.todo_item.due_date}，使用当前日期")
                    self.date_edit.setDate(QDate.currentDate())
            else:
                self.date_edit.setDate(QDate.currentDate())
        except Exception as e:
            print(f"设置日期时出错: {e}，使用当前日期")
            self.date_edit.setDate(QDate.currentDate())
        form_layout.addRow("截止日期:", self.date_edit)

        # Priority Buttons
        priority_layout = QHBoxLayout()
        self.priority_group = QButtonGroup(self)
        priorities = ["低", "中", "高"]
        self.priority_buttons = {}
        
        # 获取当前优先级，如果是新建则默认为"中"
        current_priority = "中"
        if self.todo_item is not None:
            try:
                # 确保todo_item是TodoItem类型
                if isinstance(self.todo_item, TodoItem) and hasattr(self.todo_item, 'priority'):
                    # 使用getter方法获取优先级，确保使用了property的验证逻辑
                    current_priority = self.todo_item.get_priority()
                    # 再次确保优先级是有效值
                    if current_priority not in ["低", "中", "高"]:
                        current_priority = "中"
                        print(f"无效的优先级值: {current_priority}，使用默认值'中'")
                else:
                    print(f"todo_item不是有效的TodoItem对象或没有priority属性，使用默认值'中'")
            except Exception as e:
                print(f"获取优先级时出错: {e}，使用默认值'中'")
        
        # 为每个优先级创建单选按钮并添加到按钮组
        for i, prio in enumerate(priorities):
            btn = QPushButton(prio)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)  # 确保按钮互斥，类似RadioButton
            btn.setObjectName(f"PrioBtn{prio}")
            # 使用ID添加按钮到按钮组
            self.priority_group.addButton(btn, i)
            priority_layout.addWidget(btn)
            self.priority_buttons[prio] = btn
            # 安全地设置选中状态
            if prio == current_priority:
                btn.setChecked(True)
        form_layout.addRow("优先级:", priority_layout)

        self.completed_checkbox = QCheckBox("已完成")
        self.completed_checkbox.setChecked(initial_completed)
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
        try:
            checked_button = self.priority_group.checkedButton()
            if checked_button:
                return checked_button.text()
            else:
                print("没有选中的优先级按钮，使用默认值'中'")
                return "中"
        except Exception as e:
            print(f"获取选中的优先级按钮时出错: {e}，使用默认值'中'")
            return "中"

    def get_todo_data(self) -> dict:
        """返回编辑/新建的待办事项数据，确保数据安全性"""
        # 标题处理（必填字段）
        title = self.title_edit.text().strip()
        if not title: 
            title = "未命名待办事项"
        
        # 安全地获取ID和创建时间
        item_id = str(uuid.uuid4())  # 默认为新ID
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 默认为当前时间
        
        # 如果是编辑现有项目，则保留原ID和创建时间
        if self.todo_item is not None:
            try:
                item_id = self.todo_item.id
                if hasattr(self.todo_item, 'created_at') and self.todo_item.created_at:
                    created_at = self.todo_item.created_at
            except Exception as e:
                print(f"获取待办事项原始数据时出错: {e}")
                # 出错时使用默认值，确保不会崩溃
        
        # 安全地获取日期
        try:
            due_date = self.date_edit.date().toString("yyyy-MM-dd")
        except Exception as e:
            print(f"获取日期时出错: {e}，使用当前日期")
            due_date = QDate.currentDate().toString("yyyy-MM-dd")
            
        # 安全地获取优先级
        try:
            priority = self.get_selected_priority()
            # 确保优先级是有效值
            if priority not in ["低", "中", "高"]:
                print(f"无效的优先级值: {priority}，使用默认值'中'")
                priority = "中"
        except Exception as e:
            print(f"获取优先级时出错: {e}，使用默认值'中'")
            priority = "中"  # 默认中优先级
            
        # 安全地获取完成状态
        try:
            completed = self.completed_checkbox.isChecked()
        except Exception as e:
            print(f"获取完成状态时出错: {e}，使用默认值'未完成'")
            completed = False
            
        # 构建并返回数据字典
        return {
            "id": item_id,
            "title": title,
            "description": self.desc_edit.text().strip(),
            "due_date": due_date,
            "priority": priority,
            "completed": completed,
            "created_at": created_at
        }

# --- Main Todo List View ---
class TodoListView(BaseWidget):
    """待办事项管理视图"""
    def __init__(self, parent=None):
        # 使用数据管理器处理数据逻辑
        from ...data.data_manager import TodoDataManager
        self.data_manager = TodoDataManager()
        super().__init__(parent)

    # 数据文件路径现在由数据管理器处理

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
    # 数据加载和保存现在由数据管理器处理

    # --- UI Refresh ---
    def refresh_display_list(self):
        """过滤、排序并显示待办事项列表，包含错误处理机制"""
        try:
            # 获取过滤条件
            try:
                status_filter = self.filter_combo.currentText()
                priority_filter = self.priority_filter_combo.currentText()
            except Exception as e:
                print(f"获取过滤条件时出错: {e}")
                status_filter = "全部"
                priority_filter = "全部"

            # 使用数据管理器过滤和排序数据
            try:
                filtered_data = self.data_manager.filter_items(status_filter, priority_filter)
                sorted_data = self.data_manager.sort_items(filtered_data)
            except Exception as e:
                print(f"过滤和排序数据时出错: {e}")
                # 出错时尝试获取所有数据
                try:
                    sorted_data = self.data_manager.get_data()
                except:
                    sorted_data = []

            # 清空列表并显示数据
            try:
                self.todo_list_widget.clear()
                
                # 无数据时显示提示
                if not sorted_data:
                    item = QListWidgetItem("无待办事项")
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable) # 设为不可选
                    self.todo_list_widget.addItem(item)
                else:
                    # 添加每个待办事项
                    for item_data in sorted_data:
                        try:
                            # 创建待办事项对象和小部件
                            todo_item = TodoItem.from_dict(item_data) # 为小部件创建对象
                            widget = TodoItemWidget(todo_item)
                            
                            # 连接信号
                            widget.completed_changed.connect(self._handle_item_status_change)
                            widget.edited.connect(self._handle_item_edit)
                            widget.deleted.connect(self._handle_item_delete)

                            # 创建列表项
                            list_item = QListWidgetItem()
                            list_item.setSizeHint(widget.sizeHint()) # 使用小部件的首选大小
                            # 在项目数据中存储ID以便于检索
                            list_item.setData(Qt.ItemDataRole.UserRole, todo_item.id)

                            # 添加到列表
                            self.todo_list_widget.addItem(list_item)
                            self.todo_list_widget.setItemWidget(list_item, widget)
                            
                            # 添加后应用主题样式
                            try:
                                widget._apply_item_styles(is_dark=False) # TODO: 获取实际主题状态
                            except Exception as style_error:
                                print(f"应用样式时出错: {style_error}")
                        except Exception as item_error:
                            print(f"创建待办事项小部件时出错 {item_data.get('id')}: {item_error}")
                            # 显示错误项
                            try:
                                error_item = QListWidgetItem(f"加载错误: {item_data.get('title', '未知')}")
                                error_item.setForeground(QColor("red"))
                                self.todo_list_widget.addItem(error_item)
                            except:
                                # 如果连错误项都无法创建，至少添加一个通用错误项
                                self.todo_list_widget.addItem("加载项目时出错")
            except Exception as ui_error:
                print(f"更新UI时出错: {ui_error}")
                # 尝试显示错误消息
                try:
                    self.todo_list_widget.clear()
                    error_item = QListWidgetItem("刷新列表时出错，请重试")
                    error_item.setForeground(QColor("red"))
                    self.todo_list_widget.addItem(error_item)
                except:
                    pass # 无法恢复的UI错误
        except Exception as e:
            print(f"刷新待办事项列表时发生严重错误: {e}")
            # 这里不再尝试恢复UI，因为可能会导致更多错误

    # --- Item Actions ---
    def add_new_item_dialog(self):
        """打开对话框添加新的待办事项，包含错误处理机制"""
        try:
            dialog = TodoItemDialog(parent=self)
            # 应用当前主题
            # dialog._apply_dialog_styles(is_dark=self.is_dark_mode) # 如果有主题管理
            
            if dialog.exec():
                try:
                    # 安全地获取数据
                    new_data = dialog.get_todo_data()
                    
                    # 验证必要字段
                    if not new_data.get("title"):
                        new_data["title"] = "未命名待办事项"
                    
                    # 添加到数据管理器
                    success = self.data_manager.add_item(new_data)
                    
                    if success:
                        self.refresh_display_list()
                    else:
                        QMessageBox.warning(self, "添加失败", "无法保存新的待办事项，请稍后再试。")
                        
                except Exception as e:
                    print(f"处理新待办事项数据时出错: {e}")
                    QMessageBox.critical(self, "错误", f"创建待办事项时发生错误: {str(e)}")
        except Exception as e:
            print(f"创建待办事项对话框时出错: {e}")
            QMessageBox.critical(self, "错误", "无法创建新待办事项对话框。")

    def quick_add_item(self):
        """从快速添加输入框添加新待办事项，包含错误处理机制"""
        try:
            # 获取并验证标题
            title = self.quick_add_edit.text().strip()
            if not title: 
                return
                
            try:
                # 创建新的待办事项对象
                new_item = TodoItem(title=title) # 使用默认值创建对象
                
                # 添加到数据管理器
                success = self.data_manager.add_item(new_item.to_dict())
                
                if success:
                    self.refresh_display_list()
                    self.quick_add_edit.clear()
                else:
                    QMessageBox.warning(self, "添加失败", "无法保存新的待办事项，请稍后再试。")
            except Exception as e:
                print(f"快速添加待办事项时出错: {e}")
                QMessageBox.warning(self, "添加失败", "创建待办事项时发生错误，请尝试使用完整表单添加。")
        except Exception as e:
            print(f"处理快速添加输入时出错: {e}")
            # 清空输入框，避免用户反复尝试导致同样的错误
            self.quick_add_edit.clear()

    def _handle_item_status_change(self, item_id: str, completed: bool):
        """更新待办事项的完成状态并保存，包含错误处理机制"""
        try:
            # 获取待办事项数据
            item_data = self.data_manager.get_item_by_id(item_id)
            if not item_data:
                print(f"找不到ID为{item_id}的待办事项")
                return
                
            try:
                # 更新完成状态
                item_data["completed"] = completed
                success = self.data_manager.update_item(item_id, item_data)
                
                if success:
                    # 找到列表中的小部件并立即更新其样式
                    try:
                        list_item = self._find_list_item_by_id(item_id)
                        if list_item:
                            widget = self.todo_list_widget.itemWidget(list_item)
                            if isinstance(widget, TodoItemWidget):
                                widget._update_dynamic_content() # 根据新状态更新样式
                    except Exception as e:
                        print(f"更新待办事项UI时出错: {e}")
                        # 如果UI更新失败，刷新整个列表
                        self.refresh_display_list()
                else:
                    print(f"更新ID为{item_id}的待办事项状态失败")
                    # 如果状态更新失败，刷新整个列表以恢复正确状态
                    self.refresh_display_list()
            except Exception as e:
                print(f"更新待办事项状态时出错: {e}")
                # 出错时刷新列表以确保显示正确状态
                self.refresh_display_list()
        except Exception as e:
            print(f"处理待办事项状态变更时出错: {e}")
            # 严重错误时完全刷新列表
            self.refresh_display_list()

    def _handle_item_edit(self, item_id: str):
        """打开编辑对话框编辑指定的待办事项，包含错误处理机制"""
        try:
            # 获取待办事项数据
            print(f"正在获取ID为{item_id}的待办事项数据...")
            item_data = self.data_manager.get_item_by_id(item_id)
            if not item_data: 
                print(f"找不到ID为{item_id}的待办事项")
                QMessageBox.warning(self, "编辑失败", f"找不到ID为{item_id}的待办事项")
                return
            print(f"成功获取待办事项数据: {item_data}")
                
            try:
                # 创建待办事项对象
                print("正在创建TodoItem对象...")
                todo_item_obj = TodoItem.from_dict(item_data) # 为对话框创建对象
                print(f"TodoItem对象创建结果: {todo_item_obj}")
                
                # 确保待办事项对象是有效的
                if not isinstance(todo_item_obj, TodoItem):
                    print(f"创建的待办事项对象无效: {todo_item_obj}")
                    QMessageBox.warning(self, "编辑失败", "无法创建有效的待办事项对象")
                    return
                    
                # 确保待办事项对象包含所有必要的属性
                print(f"检查待办事项属性 - 优先级: {todo_item_obj.priority if hasattr(todo_item_obj, 'priority') else '未设置'}")
                if not hasattr(todo_item_obj, 'priority') or todo_item_obj.priority not in ["低", "中", "高"]:
                    print(f"设置默认优先级为'中'")
                    todo_item_obj.set_priority(item_data.get("priority", "中"))
                    
                print(f"检查待办事项属性 - 截止日期: {todo_item_obj.due_date if hasattr(todo_item_obj, 'due_date') else '未设置'}")
                if not hasattr(todo_item_obj, 'due_date'):
                    print(f"设置默认截止日期")
                    todo_item_obj.due_date = item_data.get("due_date")
                    
                # 创建并显示对话框
                print("正在创建TodoItemDialog对话框...")
                try:
                    dialog = TodoItemDialog(todo_item=todo_item_obj, parent=self)
                    print("TodoItemDialog对话框创建成功")
                    # dialog._apply_dialog_styles(is_dark=self.is_dark_mode) # 如果有主题管理
                    
                    print("正在显示对话框...")
                    result = dialog.exec()
                    print(f"对话框结果: {result}")
                    
                    if result:
                        try:
                            # 安全地获取更新后的数据
                            print("正在获取更新后的数据...")
                            updated_data = dialog.get_todo_data()
                            print(f"更新后的数据: {updated_data}")
                            
                            # 验证必要字段
                            if not updated_data.get("title"):
                                updated_data["title"] = "未命名待办事项"
                            
                            # 确保保留原始ID
                            updated_data["id"] = item_id
                            
                            # 更新数据
                            print("正在更新数据...")
                            success = self.data_manager.update_item(item_id, updated_data)
                            print(f"数据更新结果: {success}")
                            
                            if success:
                                self.refresh_display_list() # 刷新整个列表
                            else:
                                QMessageBox.warning(self, "更新失败", "无法保存更新的待办事项，请稍后再试。")
                        except Exception as e:
                            print(f"处理编辑后的待办事项数据时出错: {e}")
                            import traceback
                            traceback.print_exc()
                            QMessageBox.critical(self, "错误", f"更新待办事项时发生错误: {str(e)}")
                except Exception as dialog_error:
                    print(f"创建或显示对话框时出错: {dialog_error}")
                    import traceback
                    traceback.print_exc()
                    QMessageBox.critical(self, "错误", f"无法创建或显示编辑对话框: {str(dialog_error)}")
            except Exception as e:
                print(f"创建编辑对话框时出错: {e}")
                import traceback
                traceback.print_exc()
                QMessageBox.critical(self, "错误", "无法创建编辑对话框。")
        except Exception as e:
            print(f"处理待办事项编辑请求时出错: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "错误", "处理编辑请求时发生错误。")

    def _handle_item_delete(self, item_id: str):
        """删除指定ID的待办事项，包含错误处理机制"""
        try:
            # 确认删除
            confirm = QMessageBox.question(
                self, 
                "确认删除", 
                "确定要删除这个待办事项吗？", 
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if confirm == QMessageBox.StandardButton.Yes:
                try:
                    # 执行删除操作
                    success = self.data_manager.delete_item(item_id)
                    
                    if success:
                        self.refresh_display_list()
                    else:
                        print(f"删除ID为{item_id}的待办事项失败")
                        QMessageBox.warning(self, "删除失败", "无法删除该待办事项，请稍后再试。")
                except Exception as e:
                    print(f"删除待办事项时出错: {e}")
                    QMessageBox.critical(self, "错误", f"删除待办事项时发生错误: {str(e)}")
        except Exception as e:
            print(f"处理删除请求时出错: {e}")
            QMessageBox.critical(self, "错误", "处理删除请求时发生错误。")

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
        # 数据已经由数据管理器保存，无需额外操作
        pass # Ensure data is saved

    # def closeEvent(self, event): # If needed
    #     self.cleanup()
    #     super().closeEvent(event)
