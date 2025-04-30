import sys
import os
import json
import uuid
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QToolBar, 
    QPushButton, QLineEdit, QListWidget, QListWidgetItem, QCheckBox,
    QApplication, QMessageBox, QDialog, QLabel, QDateEdit, QComboBox,
    QFormLayout, QDialogButtonBox, QFrame, QSplitter, QMenu
)
from PyQt6.QtGui import QIcon, QAction, QColor, QFont, QBrush
from PyQt6.QtCore import Qt, QSize, QDate, pyqtSignal, QSignalBlocker

from src.utils.theme_manager import ThemeManager

class TodoItem:
    """表示一个待办事项"""
    
    def __init__(self, title="", description="", due_date=None, priority="中", completed=False, item_id=None):
        self.id = item_id or str(uuid.uuid4())
        self.title = title
        self.description = description
        self.due_date = due_date  # 格式：YYYY-MM-DD
        self._priority = "中"  # 默认中优先级
        self.set_priority(priority)  # 使用方法设置优先级
        self.completed = completed
        self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def get_priority(self):
        """获取优先级"""
        return self._priority
    
    def set_priority(self, priority):
        """设置优先级，并验证值的有效性"""
        if priority not in ["低", "中", "高"]:
            print(f"无效的优先级值: {priority}，设置为默认值'中'")
            self._priority = "中"
        else:
            print(f"设置优先级: {priority}")
            self._priority = priority
    
    # 使用property定义priority属性
    priority = property(get_priority, set_priority)
    
    @classmethod
    def from_dict(cls, data):
        """从字典创建待办事项"""
        try:
            print(f"从字典创建待办事项: {data}")
            if not isinstance(data, dict):
                print(f"待办事项数据不是字典格式: {data}")
                # 返回一个默认的待办事项对象
                return cls(title="错误数据", description="数据格式不正确")
            
            # 确保所有必要的字段都存在
            title = data.get("title", "")
            if not title:
                print(f"待办事项缺少标题: {data}")
                title = "未命名待办事项"
            
            # 确保优先级合法
            priority = data.get("priority", "中")
            if priority not in ["低", "中", "高"]:
                print(f"从字典中读取到无效的优先级: {priority}，使用默认值'中'")
                priority = "中"
            else:
                print(f"从字典中读取到有效的优先级: {priority}")
            
            todo_item = cls(
                title=title,
                description=data.get("description", ""),
                due_date=data.get("due_date"),
                priority=priority,
                completed=data.get("completed", False),
                item_id=data.get("id")
            )
            print(f"成功创建待办事项: {todo_item.title}, 优先级: {todo_item.priority}")
            return todo_item
        except Exception as e:
            print(f"创建待办事项对象时出错: {str(e)}, 数据: {data}")
            import traceback
            traceback.print_exc()
            # 返回一个默认的待办事项对象
            return cls(title="错误数据", description=f"解析错误: {str(e)}")
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "due_date": self.due_date,
            "priority": self.priority,
            "completed": self.completed,
            "created_at": self.created_at
        }


class TodoItemWidget(QFrame):
    """显示单个待办事项的小部件"""
    
    completed_changed = pyqtSignal(str, bool)  # id, completed
    deleted = pyqtSignal(str)  # id
    edited = pyqtSignal(str)  # id
    
    def __init__(self, todo_item, parent=None):
        super().__init__(parent)
        self.todo_item = todo_item
        try:
            self.initUI()
        except Exception as e:
            print(f"初始化待办事项小部件UI时出错: {str(e)}")
            # 创建一个最小的UI来避免完全失败
            error_layout = QVBoxLayout(self)
            error_label = QLabel(f"加载出错: {todo_item.title if hasattr(todo_item, 'title') else '未知待办事项'}")
            error_label.setStyleSheet("color: red;")
            error_layout.addWidget(error_label)
    
    def initUI(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Safety check for todo_item
        if not hasattr(self, 'todo_item') or self.todo_item is None:
            # Create a simple error widget
            error_label = QLabel("错误: 无效的待办事项")
            error_label.setStyleSheet("color: red;")
            main_layout.addWidget(error_label)
            return
        
        # 完成状态复选框
        self.checkbox = QCheckBox()
        self.checkbox.setFixedSize(24, 24)  # 增大复选框尺寸
        
        # Safely get completion status
        try:
            completed = getattr(self.todo_item, 'completed', False)
            # 使用阻断信号的方式设置初始状态，避免触发不必要的信号
            with QSignalBlocker(self.checkbox):
                self.checkbox.setChecked(completed)
        except Exception as e:
            print(f"设置完成状态出错: {str(e)}")
            self.checkbox.setChecked(False)
            
        # 确保连接信号之前断开之前的连接
        try:
            self.checkbox.stateChanged.disconnect()
        except:
            pass  # 如果之前没有连接，忽略错误
            
        # 重新连接信号
        self.checkbox.stateChanged.connect(self.on_completed_changed)
        
        # 添加提示文本
        self.checkbox.setToolTip("点击标记为已完成/未完成")
        
        # 简化样式，使用更基本的样式，避免过于复杂的选择器
        self.checkbox.setStyleSheet("""
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #aaa;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #5cb85c;
            }
        """)
        
        # 确保复选框可见并能接收事件
        self.checkbox.setEnabled(True)
        self.checkbox.show()
        
        # 添加复选框到布局
        main_layout.addWidget(self.checkbox)
        
        # 内容布局
        content_layout = QVBoxLayout()
        
        # 标题和日期
        title_layout = QHBoxLayout()
        
        # Safely get title
        title = getattr(self.todo_item, 'title', "未命名待办事项")
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        # 根据完成状态设置样式
        self.update_title_style()
        
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        
        # 截止日期和优先级
        info_layout = QHBoxLayout()
        
        # 优先级 - 安全地获取
        try:
            priority = getattr(self.todo_item, 'priority', "中")
            priority_color = self.get_priority_color()
            priority_label = QLabel(f"优先级: {priority}")
            priority_label.setStyleSheet(f"color: {priority_color}; font-weight: bold;")
            info_layout.addWidget(priority_label)
        except Exception as e:
            print(f"设置优先级出错: {str(e)}")
            # 使用默认值
            priority_label = QLabel("优先级: 中")
            priority_label.setStyleSheet("color: #f0ad4e; font-weight: bold;")
            info_layout.addWidget(priority_label)
        
        info_layout.addStretch()
        
        # 截止日期 - 安全地获取
        try:
            due_date = getattr(self.todo_item, 'due_date', None)
            if due_date:
                date_str = due_date
                
                # 检查是否已过期
                try:
                    due_date_obj = QDate.fromString(date_str, "yyyy-MM-dd")
                    today = QDate.currentDate()
                    
                    if due_date_obj.isValid() and due_date_obj < today and not getattr(self.todo_item, 'completed', False):
                        date_label = QLabel(f"截止日期: {date_str} (已过期)")
                        date_label.setStyleSheet("color: red; font-weight: bold;")
                    else:
                        date_label = QLabel(f"截止日期: {date_str}")
                    
                    info_layout.addWidget(date_label)
                except Exception as e:
                    print(f"处理截止日期出错: {str(e)}")
                    date_label = QLabel(f"截止日期: {date_str}")
                    info_layout.addWidget(date_label)
        except Exception as e:
            print(f"设置截止日期出错: {str(e)}")
        
        # 描述 - 安全地获取
        try:
            description = getattr(self.todo_item, 'description', "")
            if description:
                description_label = QLabel(description)
                description_label.setWordWrap(True)
                description_label.setStyleSheet("color: #666;")
                
                content_layout.addLayout(title_layout)
                content_layout.addLayout(info_layout)
                content_layout.addWidget(description_label)
            else:
                content_layout.addLayout(title_layout)
                content_layout.addLayout(info_layout)
        except Exception as e:
            print(f"设置描述出错: {str(e)}")
            content_layout.addLayout(title_layout)
            content_layout.addLayout(info_layout)
        
        main_layout.addLayout(content_layout)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        # 编辑按钮 - 更加显眼的设计
        self.edit_btn = QPushButton("编辑")
        self.edit_btn.setFixedSize(60, 28)
        self.edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #337ab7;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #286090;
            }
            QPushButton:pressed {
                background-color: #1f4e79;
            }
        """)
        self.edit_btn.setToolTip("点击编辑待办事项详情，可修改优先级等属性")
        self.edit_btn.clicked.connect(self.on_edit_clicked)
        button_layout.addWidget(self.edit_btn)
        
        # 删除按钮
        self.delete_btn = QPushButton("删除")
        self.delete_btn.setFixedSize(60, 28)
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #d9534f;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #c9302c;
            }
            QPushButton:pressed {
                background-color: #a02622;
            }
        """)
        self.delete_btn.setToolTip("删除此待办事项")
        self.delete_btn.clicked.connect(self.on_delete_clicked)
        button_layout.addWidget(self.delete_btn)
        
        main_layout.addLayout(button_layout)
        
        # 添加分隔线和基本样式
        self.setFrameShape(QFrame.Shape.Box)
        self.setFrameShadow(QFrame.Shadow.Plain)
        
        # 设置基本样式，不包含复杂的选择器
        self.setStyleSheet("""
            TodoItemWidget {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: #f9f9f9;
                margin-bottom: 5px;
            }
        """)
        
        # 如果待办事项已完成，设置为已完成样式
        if getattr(self.todo_item, 'completed', False):
            self.setStyleSheet("""
                TodoItemWidget {
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    background-color: #f0f9f0;
                    margin-bottom: 5px;
                }
            """)
    
    def update_title_style(self):
        """根据完成状态更新标题样式"""
        try:
            if not hasattr(self, 'todo_item') or not hasattr(self, 'title_label'):
                return
                
            completed = getattr(self.todo_item, 'completed', False)
            if completed:
                self.title_label.setStyleSheet("text-decoration: line-through; color: #888;")
            else:
                self.title_label.setStyleSheet("")
        except Exception as e:
            print(f"更新标题样式时出错: {str(e)}")
    
    def get_priority_color(self):
        """获取优先级对应的颜色"""
        try:
            if not hasattr(self, 'todo_item'):
                return "#f0ad4e"  # 默认为中优先级颜色
                
            priority = getattr(self.todo_item, 'priority', "中")
            if priority == "高":
                return "#d9534f"  # 红色
            elif priority == "中":
                return "#f0ad4e"  # 橙色
            else:
                return "#5cb85c"  # 绿色
        except Exception as e:
            print(f"获取优先级颜色时出错: {str(e)}")
            return "#f0ad4e"  # 默认为中优先级颜色
    
    def on_completed_changed(self, state):
        """处理完成状态变化"""
        try:
            if not hasattr(self, 'todo_item'):
                print("无法找到待办事项对象")
                return
                
            # 获取新的完成状态
            completed = (state == Qt.CheckState.Checked)
            print(f"复选框状态变化: {state}, 完成状态: {completed}")
            
            # 获取todo_item ID
            item_id = getattr(self.todo_item, 'id', None)
            if not item_id:
                print("待办事项对象没有ID属性")
                return
                
            # 更新todo_item的completed属性
            self.todo_item.completed = completed
            
            # 更新UI显示
            self.update_title_style()
            
            # 设置背景颜色以提供视觉反馈
            if completed:
                self.setStyleSheet("""
                    TodoItemWidget {
                        border: 1px solid #ddd;
                        border-radius: 5px;
                        background-color: #f0f9f0;
                        margin-bottom: 5px;
                    }
                """)
            else:
                self.setStyleSheet("""
                    TodoItemWidget {
                        border: 1px solid #ddd;
                        border-radius: 5px;
                        background-color: #f9f9f9;
                        margin-bottom: 5px;
                    }
                """)
            
            # 发送信号通知主窗口更新数据
            print(f"发送完成状态变化信号: ID={item_id}, 完成状态={completed}")
            self.completed_changed.emit(item_id, completed)
            
        except Exception as e:
            print(f"处理完成状态变化时出错: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def on_edit_clicked(self):
        """处理编辑按钮点击"""
        try:
            if not hasattr(self, 'todo_item'):
                print("编辑按钮点击：无法找到待办事项对象")
                return
                
            # 确保todo_item有id属性
            item_id = getattr(self.todo_item, 'id', None)
            if not item_id:
                print("编辑按钮点击：待办事项对象没有ID属性")
                return
                
            print(f"编辑按钮点击：发出编辑信号，ID: {item_id}")
            self.edited.emit(item_id)
            
        except Exception as e:
            print(f"处理编辑按钮点击时出错: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def on_delete_clicked(self):
        """处理删除按钮点击"""
        try:
            if not hasattr(self, 'todo_item'):
                return
                
            # 确保todo_item有id属性
            item_id = getattr(self.todo_item, 'id', None)
            if item_id:
                self.deleted.emit(item_id)
        except Exception as e:
            print(f"处理删除按钮点击时出错: {str(e)}")


class TodoItemDialog(QDialog):
    """新增或编辑待办事项的对话框"""
    
    def __init__(self, todo_item=None, parent=None):
        super().__init__(parent)
        self.todo_item = todo_item
        self.setWindowTitle("编辑待办事项" if todo_item else "新建待办事项")
        self.resize(450, 300)
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # 表单布局
        form_layout = QFormLayout()
        
        # 标题
        self.title_edit = QLineEdit()
        if self.todo_item:
            self.title_edit.setText(self.todo_item.title)
        form_layout.addRow("标题:", self.title_edit)
        
        # 描述
        self.desc_edit = QLineEdit()
        if self.todo_item:
            self.desc_edit.setText(self.todo_item.description)
        form_layout.addRow("描述:", self.desc_edit)
        
        # 截止日期
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        if self.todo_item and self.todo_item.due_date:
            try:
                date = QDate.fromString(self.todo_item.due_date, "yyyy-MM-dd")
                if date.isValid():
                    self.date_edit.setDate(date)
            except:
                pass
        form_layout.addRow("截止日期:", self.date_edit)
        
        # 优先级 - 优化UI，使用彩色按钮
        priority_label = QLabel("优先级:")
        priority_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        form_layout.addRow(priority_label)
        
        # 使用水平布局来放置优先级选项
        priority_layout = QHBoxLayout()
        
        # 低优先级按钮
        self.low_priority_btn = QPushButton("低")
        self.low_priority_btn.setCheckable(True)
        self.low_priority_btn.setStyleSheet("""
            QPushButton {
                background-color: #5cb85c;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                min-width: 80px;
            }
            QPushButton:checked {
                background-color: #449d44;
                border: 2px solid black;
            }
            QPushButton:hover {
                background-color: #4cae4c;
            }
        """)
        
        # 中优先级按钮
        self.medium_priority_btn = QPushButton("中")
        self.medium_priority_btn.setCheckable(True)
        self.medium_priority_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0ad4e;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                min-width: 80px;
            }
            QPushButton:checked {
                background-color: #ec971f;
                border: 2px solid black;
            }
            QPushButton:hover {
                background-color: #eea236;
            }
        """)
        
        # 高优先级按钮
        self.high_priority_btn = QPushButton("高")
        self.high_priority_btn.setCheckable(True)
        self.high_priority_btn.setStyleSheet("""
            QPushButton {
                background-color: #d9534f;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                min-width: 80px;
            }
            QPushButton:checked {
                background-color: #c9302c;
                border: 2px solid black;
            }
            QPushButton:hover {
                background-color: #d43f3a;
            }
        """)
        
        # 将按钮添加到布局
        priority_layout.addWidget(self.low_priority_btn)
        priority_layout.addWidget(self.medium_priority_btn)
        priority_layout.addWidget(self.high_priority_btn)
        priority_layout.addStretch()
        
        # 设置按钮组，确保只有一个按钮被选中
        self.priority_buttons = [self.low_priority_btn, self.medium_priority_btn, self.high_priority_btn]
        for btn in self.priority_buttons:
            btn.clicked.connect(self.on_priority_clicked)
        
        # 设置默认优先级
        if self.todo_item:
            if self.todo_item.priority == "低":
                self.low_priority_btn.setChecked(True)
            elif self.todo_item.priority == "高":
                self.high_priority_btn.setChecked(True)
            else:
                self.medium_priority_btn.setChecked(True)
        else:
            # 默认中优先级
            self.medium_priority_btn.setChecked(True)
        
        # 添加优先级布局
        form_layout.addRow("", priority_layout)
        
        # 优先级说明
        priority_help = QLabel("优先级决定待办事项的排序顺序和显示颜色")
        priority_help.setStyleSheet("color: #666; font-style: italic;")
        form_layout.addRow("", priority_help)
        
        # 已完成
        self.completed_checkbox = QCheckBox("标记为已完成")
        if self.todo_item:
            self.completed_checkbox.setChecked(self.todo_item.completed)
        form_layout.addRow("", self.completed_checkbox)
        
        layout.addLayout(form_layout)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)
    
    def on_priority_clicked(self):
        """处理优先级按钮点击，确保只有一个按钮处于选中状态"""
        sender = self.sender()
        for btn in self.priority_buttons:
            if btn != sender:
                btn.setChecked(False)
            else:
                # 确保至少有一个按钮被选中
                if not btn.isChecked():
                    btn.setChecked(True)
    
    def get_priority(self):
        """获取当前选择的优先级"""
        if self.low_priority_btn.isChecked():
            return "低"
        elif self.high_priority_btn.isChecked():
            return "高"
        else:
            return "中"
    
    def get_todo_item(self):
        """获取对话框中的待办事项数据"""
        try:
            print("获取对话框中的待办事项数据")
            
            title = self.title_edit.text()
            if not title.strip():
                # 确保标题不为空
                title = "未命名待办事项"
                
            description = self.desc_edit.text()
            
            # 确保日期格式正确
            try:
                due_date = self.date_edit.date().toString("yyyy-MM-dd")
                # 验证日期格式
                if not QDate.fromString(due_date, "yyyy-MM-dd").isValid():
                    due_date = QDate.currentDate().toString("yyyy-MM-dd")
            except Exception as e:
                print(f"获取日期时出错: {str(e)}")
                due_date = QDate.currentDate().toString("yyyy-MM-dd")
                
            # 获取选择的优先级
            priority = self.get_priority()
            print(f"选择的优先级: {priority}")
                
            completed = self.completed_checkbox.isChecked()
            
            if self.todo_item:
                print(f"正在更新现有待办事项，ID: {self.todo_item.id}")
                # 更新现有项
                try:
                    # 记录原始值，用于调试
                    original_priority = getattr(self.todo_item, 'priority', '未知')
                    print(f"原始优先级: {original_priority}, 新优先级: {priority}")
                    
                    # 直接更新对象属性
                    self.todo_item.title = title
                    self.todo_item.description = description
                    self.todo_item.due_date = due_date
                    self.todo_item.priority = priority
                    self.todo_item.completed = completed
                    
                    # 验证更新是否成功
                    print(f"更新后的优先级: {self.todo_item.priority}")
                    
                    # 返回更新后的对象
                    return self.todo_item
                except Exception as e:
                    print(f"更新待办事项时出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    
                    # 如果更新失败，创建一个新对象返回
                    print("创建新对象替代更新失败的对象")
                    new_item = TodoItem(
                        title=title,
                        description=description,
                        due_date=due_date,
                        priority=priority,
                        completed=completed,
                        item_id=getattr(self.todo_item, 'id', None)
                    )
                    print(f"新对象优先级: {new_item.priority}")
                    return new_item
            else:
                # 创建新项
                print("创建全新的待办事项")
                new_item = TodoItem(
                    title=title,
                    description=description,
                    due_date=due_date,
                    priority=priority,
                    completed=completed
                )
                print(f"新建待办事项优先级: {new_item.priority}")
                return new_item
        except Exception as e:
            print(f"创建待办事项对象时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # 返回一个基本的待办事项对象，避免程序崩溃
            default_item = TodoItem(
                title="错误的待办事项",
                description="创建过程中出错",
                due_date=QDate.currentDate().toString("yyyy-MM-dd"),
                priority="中",
                completed=False
            )
            return default_item


class TodoWidget(QMainWindow):
    """待办事项管理窗口"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_manager = ThemeManager()
        self.todo_items = []
        
        self.initUI()
        self.load_todo_items()
        self.apply_current_theme()
    
    def initUI(self):
        self.setWindowTitle("待办事项")
        self.setGeometry(100, 100, 700, 500)
        
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 工具栏
        toolbar = QToolBar("待办事项工具栏")
        toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(toolbar)
        
        # 添加新待办事项按钮
        add_action = QAction(QIcon.fromTheme("list-add"), "新建待办事项", self)
        add_action.triggered.connect(self.add_todo_item)
        toolbar.addAction(add_action)
        
        # 过滤器工具栏
        filter_layout = QHBoxLayout()
        
        # 状态过滤器
        filter_status_label = QLabel("状态:")
        filter_layout.addWidget(filter_status_label)
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部", "未完成", "已完成"])
        self.filter_combo.currentTextChanged.connect(self.apply_filter)
        filter_layout.addWidget(self.filter_combo)
        
        filter_layout.addSpacing(20)  # 添加间距
        
        # 优先级过滤器
        filter_priority_label = QLabel("优先级:")
        filter_layout.addWidget(filter_priority_label)
        
        self.priority_filter_combo = QComboBox()
        self.priority_filter_combo.addItems(["全部", "低", "中", "高"])
        self.priority_filter_combo.currentTextChanged.connect(self.apply_filter)
        
        # 为优先级选项设置颜色
        self.priority_filter_combo.setItemData(1, QColor("#5cb85c"), Qt.ItemDataRole.BackgroundRole)  # 低 - 绿色
        self.priority_filter_combo.setItemData(2, QColor("#f0ad4e"), Qt.ItemDataRole.BackgroundRole)  # 中 - 橙色
        self.priority_filter_combo.setItemData(3, QColor("#d9534f"), Qt.ItemDataRole.BackgroundRole)  # 高 - 红色
        
        # 确保文本在有色背景上可见
        self.priority_filter_combo.setItemData(1, QColor("white"), Qt.ItemDataRole.ForegroundRole)
        self.priority_filter_combo.setItemData(2, QColor("white"), Qt.ItemDataRole.ForegroundRole)
        self.priority_filter_combo.setItemData(3, QColor("white"), Qt.ItemDataRole.ForegroundRole)
        
        filter_layout.addWidget(self.priority_filter_combo)
        
        filter_layout.addStretch()
        
        main_layout.addLayout(filter_layout)
        
        # 主分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 待办事项列表
        self.todo_list = QListWidget()
        self.todo_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: white;
                padding: 5px;
            }
            QListWidget::item {
                border-bottom: 1px solid #eee;
                padding: 5px;
            }
        """)
        splitter.addWidget(self.todo_list)
        
        main_layout.addWidget(splitter)
        
        # 底部快速添加栏
        quick_add_layout = QHBoxLayout()
        
        self.quick_add_edit = QLineEdit()
        self.quick_add_edit.setPlaceholderText("快速添加待办事项...")
        self.quick_add_edit.returnPressed.connect(self.quick_add_todo)
        quick_add_layout.addWidget(self.quick_add_edit)
        
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self.quick_add_todo)
        quick_add_layout.addWidget(add_btn)
        
        main_layout.addLayout(quick_add_layout)
    
    def add_todo_item(self):
        """添加新待办事项"""
        dialog = TodoItemDialog(parent=self)
        if dialog.exec():
            todo_item = dialog.get_todo_item()
            self.todo_items.append(todo_item)
            self.save_todo_items()
            self.refresh_todo_list()
    
    def edit_todo_item(self, item_id):
        """编辑待办事项"""
        print(f"开始编辑待办事项，ID: {item_id}")
        
        # 查找待办事项
        todo_item = next((item for item in self.todo_items if item.id == item_id), None)
        if not todo_item:
            print(f"找不到ID为 {item_id} 的待办事项")
            return
        
        print(f"找到待办事项: {todo_item.title}, 优先级: {todo_item.priority}")
        
        dialog = TodoItemDialog(todo_item, parent=self)
        if dialog.exec():
            try:
                # 从对话框获取编辑后的待办事项
                updated_item = dialog.get_todo_item()
                print(f"编辑完成: {updated_item.title}, 新优先级: {updated_item.priority}")
                
                # 更新对应的待办事项
                for i, item in enumerate(self.todo_items):
                    if item.id == item_id:
                        # 手动更新每个字段以确保更改被应用
                        item.title = updated_item.title
                        item.description = updated_item.description
                        item.due_date = updated_item.due_date
                        item.priority = updated_item.priority
                        item.completed = updated_item.completed
                        print(f"更新了待办事项列表中的项目 #{i}, 新优先级: {item.priority}")
                        break
                
                # 保存并刷新
                self.save_todo_items()
                print("已保存更改")
                self.refresh_todo_list()
                print("已刷新UI")
            except Exception as e:
                print(f"更新待办事项时出错: {str(e)}")
                import traceback
                traceback.print_exc()
    
    def delete_todo_item(self, item_id):
        """删除待办事项"""
        # 查找并删除
        for i, item in enumerate(self.todo_items):
            if item.id == item_id:
                del self.todo_items[i]
                self.save_todo_items()
                self.refresh_todo_list()
                break
    
    def update_todo_item_status(self, item_id, completed):
        """更新待办事项完成状态"""
        try:
            print(f"接收到状态更新请求: ID={item_id}, 完成状态={completed}")
            
            # 查找待办事项
            found = False
            for i, item in enumerate(self.todo_items):
                if item.id == item_id:
                    old_status = item.completed
                    item.completed = completed
                    found = True
                    
                    # 记录状态变化并打印更多详情便于调试
                    status_text = "已完成" if completed else "未完成"
                    print(f"待办事项 #{i} ({item.title}) 状态已从 {old_status} 更新为: {completed} ({status_text})")
                    break
            
            if not found:
                print(f"找不到ID为 {item_id} 的待办事项")
                return
                
            # 保存更改
            print(f"保存待办事项状态更改")
            self.save_todo_items()
            
            # 重新应用过滤器（可能会隐藏或显示项目）
            print(f"刷新待办事项列表显示")
            self.apply_filter()  # 刷新列表显示
            
            # 控制台状态更新
            print(f"成功更新待办事项完成状态: ID={item_id}, 状态={completed}")
            
        except Exception as e:
            print(f"更新待办事项状态时出错: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def quick_add_todo(self):
        """快速添加待办事项"""
        title = self.quick_add_edit.text().strip()
        if not title:
            return
        
        # 创建新待办事项
        todo_item = TodoItem(
            title=title,
            due_date=QDate.currentDate().toString("yyyy-MM-dd"),
            priority="中"
        )
        
        self.todo_items.append(todo_item)
        self.save_todo_items()
        self.refresh_todo_list()
        
        # 清空输入框
        self.quick_add_edit.clear()
    
    def load_todo_items(self):
        """从文件加载待办事项"""
        try:
            print("开始加载待办事项")
            file_path = os.path.join("data", "todo.json")
            if os.path.exists(file_path):
                print(f"找到待办事项文件: {file_path}")
                with open(file_path, "r", encoding="utf-8") as f:
                    items_data = json.load(f)
                    print(f"加载到 {len(items_data)} 个待办事项")
                    self.todo_items = []
                    for item_data in items_data:
                        try:
                            todo_item = TodoItem.from_dict(item_data)
                            self.todo_items.append(todo_item)
                            print(f"成功加载待办事项: {todo_item.title}")
                        except Exception as e:
                            print(f"加载单个待办事项时出错: {str(e)}, 数据: {item_data}")
            else:
                # 确保data目录存在
                print(f"待办事项文件不存在，创建新的待办事项列表")
                os.makedirs("data", exist_ok=True)
                self.todo_items = []
            
            print(f"总共加载了 {len(self.todo_items)} 个待办事项")
            self.refresh_todo_list()
        except Exception as e:
            print(f"加载待办事项出错: {str(e)}")
            import traceback
            traceback.print_exc()
            self.todo_items = []
    
    def save_todo_items(self):
        """保存待办事项到文件"""
        try:
            # 确保目录存在
            os.makedirs("data", exist_ok=True)
            
            file_path = os.path.join("data", "todo.json")
            with open(file_path, "w", encoding="utf-8") as f:
                items_data = [item.to_dict() for item in self.todo_items]
                json.dump(items_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存待办事项出错: {str(e)}")
    
    def apply_filter(self):
        """应用过滤器"""
        self.refresh_todo_list()
    
    def refresh_todo_list(self):
        """刷新待办事项列表"""
        try:
            print("开始刷新待办事项列表")
            self.todo_list.clear()
            
            # 应用状态过滤器
            status_filter = self.filter_combo.currentText()
            print(f"当前状态过滤选项: {status_filter}")
            
            # 应用优先级过滤器
            priority_filter = self.priority_filter_combo.currentText()
            print(f"当前优先级过滤选项: {priority_filter}")
            
            # 先按状态过滤
            status_filtered_items = []
            if status_filter == "全部":
                status_filtered_items = self.todo_items
            elif status_filter == "未完成":
                status_filtered_items = [item for item in self.todo_items if not item.completed]
            elif status_filter == "已完成":
                status_filtered_items = [item for item in self.todo_items if item.completed]
            
            # 再按优先级过滤
            filtered_items = []
            if priority_filter == "全部":
                filtered_items = status_filtered_items
            else:
                filtered_items = [item for item in status_filtered_items if item.priority == priority_filter]
            
            print(f"过滤后的待办事项数量: {len(filtered_items)}")
            
            # 按照截止日期和优先级排序
            def sort_key(item):
                priority_value = {"高": 0, "中": 1, "低": 2}.get(item.priority, 1)
                
                # 如果没有截止日期，设置为最后
                if not item.due_date:
                    date_value = "9999-99-99"
                else:
                    date_value = item.due_date
                
                # 完成的排在最后
                completed_value = 1 if item.completed else 0
                
                return (completed_value, date_value, priority_value)
            
            print("开始排序待办事项")
            sorted_items = sorted(filtered_items, key=sort_key)
            print(f"排序后的待办事项数量: {len(sorted_items)}")
            
            # 添加到列表
            print("开始向列表添加待办事项")
            for todo_item in sorted_items:
                print(f"添加待办事项: {todo_item.title}")
                item = QListWidgetItem()
                item.setSizeHint(QSize(self.todo_list.width(), 80))  # 设置项高度
                
                try:
                    widget = TodoItemWidget(todo_item)
                    
                    # 确保信号连接正确
                    print(f"连接待办事项 {todo_item.title} 的信号")
                    
                    # 明确地连接信号和槽函数
                    widget.completed_changed.connect(self.update_todo_item_status)
                    widget.edited.connect(self.edit_todo_item)
                    widget.deleted.connect(self.delete_todo_item)
                    
                    # 验证连接状态
                    print(f"待办事项 {todo_item.title} 信号已连接")
                    
                    self.todo_list.addItem(item)
                    self.todo_list.setItemWidget(item, widget)
                except Exception as e:
                    print(f"创建待办事项小部件时出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
            
            # 显示过滤结果统计
            item_count = len(sorted_items)
            if item_count == 0:
                empty_item = QListWidgetItem("没有符合筛选条件的待办事项")
                empty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.todo_list.addItem(empty_item)
            
            print("待办事项列表刷新完成")
        except Exception as e:
            print(f"刷新待办事项列表出错: {str(e)}")
            # 打印更详细的错误信息
            import traceback
            traceback.print_exc()
    
    def apply_current_theme(self):
        """应用当前主题"""
        self.theme_manager.apply_theme(self)
    
    def resizeEvent(self, event):
        """处理窗口大小变化"""
        super().resizeEvent(event)
        self.refresh_todo_list()
    
    def closeEvent(self, event):
        """处理窗口关闭事件"""
        try:
            self.save_todo_items()
        except Exception as e:
            print(f"关闭时保存待办事项出错: {str(e)}")
        event.accept()


# 独立测试
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TodoWidget()
    window.show()
    sys.exit(app.exec()) 