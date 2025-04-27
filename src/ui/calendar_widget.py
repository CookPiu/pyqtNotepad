import sys
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QPushButton, QGridLayout, QCalendarWidget, QApplication,
                            QTextEdit, QDialog, QLineEdit, QTimeEdit, QCheckBox,
                            QComboBox, QMessageBox, QSplitter, QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt, QSize, QDate, QTime, QDateTime, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QColor, QTextCharFormat
import json
import os
from src.utils.theme_manager import ThemeManager


class EventDialog(QDialog):
    """事件添加/编辑对话框"""
    
    def __init__(self, parent=None, event_data=None):
        super().__init__(parent)
        self.event_data = event_data or {}
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("添加/编辑事件")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # 事件标题
        title_layout = QHBoxLayout()
        title_label = QLabel("标题:")
        self.title_edit = QLineEdit(self.event_data.get('title', ''))
        title_layout.addWidget(title_label)
        title_layout.addWidget(self.title_edit)
        layout.addLayout(title_layout)
        
        # 事件日期
        date_layout = QHBoxLayout()
        date_label = QLabel("日期:")
        self.date_edit = QLineEdit()
        if 'date' in self.event_data:
            self.date_edit.setText(self.event_data['date'])
        else:
            self.date_edit.setText(QDate.currentDate().toString("yyyy-MM-dd"))
        self.date_edit.setReadOnly(True)  # 日期通过日历选择，不直接编辑
        date_layout.addWidget(date_label)
        date_layout.addWidget(self.date_edit)
        layout.addLayout(date_layout)
        
        # 事件时间
        time_layout = QHBoxLayout()
        time_label = QLabel("时间:")
        self.time_edit = QTimeEdit()
        if 'time' in self.event_data:
            self.time_edit.setTime(QTime.fromString(self.event_data['time'], "hh:mm"))
        else:
            self.time_edit.setTime(QTime.currentTime())
        time_layout.addWidget(time_label)
        time_layout.addWidget(self.time_edit)
        layout.addLayout(time_layout)
        
        # 事件类型
        type_layout = QHBoxLayout()
        type_label = QLabel("类型:")
        self.type_combo = QComboBox()
        event_types = ["会议", "约会", "生日", "纪念日", "提醒", "其他"]
        self.type_combo.addItems(event_types)
        if 'type' in self.event_data:
            index = event_types.index(self.event_data['type']) if self.event_data['type'] in event_types else 0
            self.type_combo.setCurrentIndex(index)
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.type_combo)
        layout.addLayout(type_layout)
        
        # 提醒选项
        reminder_layout = QHBoxLayout()
        reminder_label = QLabel("提醒:")
        self.reminder_check = QCheckBox("启用")
        self.reminder_check.setChecked(self.event_data.get('reminder', False))
        reminder_layout.addWidget(reminder_label)
        reminder_layout.addWidget(self.reminder_check)
        layout.addLayout(reminder_layout)
        
        # 事件描述
        desc_label = QLabel("描述:")
        self.desc_edit = QTextEdit(self.event_data.get('description', ''))
        layout.addWidget(desc_label)
        layout.addWidget(self.desc_edit)
        
        # 按钮
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("保存")
        self.cancel_btn = QPushButton("取消")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
    
    def get_event_data(self):
        """获取事件数据"""
        return {
            'title': self.title_edit.text(),
            'date': self.date_edit.text(),
            'time': self.time_edit.time().toString("hh:mm"),
            'type': self.type_combo.currentText(),
            'reminder': self.reminder_check.isChecked(),
            'description': self.desc_edit.toPlainText(),
            'id': self.event_data.get('id', datetime.now().strftime("%Y%m%d%H%M%S"))
        }


class CalendarWindow(QMainWindow):
    """日历窗口，提供日历查看和事件管理功能"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 初始化主题管理器
        self.theme_manager = ThemeManager()
        
        # 初始化数据
        self.events = {}  # 存储格式: {日期字符串: [事件1, 事件2, ...]}
        self.load_events()
        
        # 初始化UI
        self.initUI()
        
        # 应用当前主题
        self.apply_current_theme()
    
    def initUI(self):
        # 设置窗口标题和大小
        self.setWindowTitle("日历")
        self.setGeometry(300, 300, 800, 600)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 创建分割器
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 创建日历部件
        calendar_widget = QWidget()
        calendar_layout = QVBoxLayout(calendar_widget)
        
        # 创建日历控件
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.calendar.setSelectionMode(QCalendarWidget.SelectionMode.SingleSelection)
        self.calendar.clicked.connect(self.date_selected)
        
        # 设置日历样式
        self.calendar.setStyleSheet("""
            QCalendarWidget {
                background-color: white;
                color: #2c3e50;
            }
            QCalendarWidget QToolButton {
                height: 30px;
                width: 100px;
                color: #2c3e50;
                background-color: #f1f1f1;
                font-size: 14px;
                icon-size: 20px, 20px;
                border-radius: 4px;
            }
            QCalendarWidget QMenu {
                width: 150px;
                font-size: 14px;
                color: #2c3e50;
                background-color: white;
            }
            QCalendarWidget QSpinBox {
                width: 100px;
                font-size: 14px;
                color: #2c3e50;
                background-color: white;
                selection-background-color: #3498db;
                selection-color: white;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #f1f1f1;
                border-radius: 4px;
            }
            QCalendarWidget QAbstractItemView:enabled {
                font-size: 14px;
                color: #2c3e50;
                background-color: white;
                selection-background-color: #3498db;
                selection-color: white;
            }
            QCalendarWidget QAbstractItemView:disabled {
                color: #bdc3c7;
            }
        """)
        
        calendar_layout.addWidget(self.calendar)
        
        # 添加按钮区域
        buttons_layout = QHBoxLayout()
        
        self.add_event_btn = QPushButton("添加事件")
        self.add_event_btn.clicked.connect(self.add_event)
        buttons_layout.addWidget(self.add_event_btn)
        
        self.today_btn = QPushButton("今天")
        self.today_btn.clicked.connect(self.go_to_today)
        buttons_layout.addWidget(self.today_btn)
        
        calendar_layout.addLayout(buttons_layout)
        
        # 创建事件列表部件
        events_widget = QWidget()
        events_layout = QVBoxLayout(events_widget)
        
        # 添加日期标签
        self.date_label = QLabel()
        self.date_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        events_layout.addWidget(self.date_label)
        
        # 添加事件列表
        self.event_list = QListWidget()
        self.event_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.event_list.itemDoubleClicked.connect(self.edit_event)
        self.event_list.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 5px;
                font-size: 14px;
            }
            QListWidget::item {
                border-bottom: 1px solid #ecf0f1;
                padding: 8px;
            }
            QListWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)
        events_layout.addWidget(self.event_list)
        
        # 添加事件详情
        self.event_details = QTextEdit()
        self.event_details.setReadOnly(True)
        self.event_details.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 5px;
                font-size: 14px;
                color: #2c3e50;
            }
        """)
        events_layout.addWidget(self.event_details)
        
        # 添加详情按钮区域
        detail_buttons_layout = QHBoxLayout()
        
        self.edit_event_btn = QPushButton("编辑")
        self.edit_event_btn.clicked.connect(self.edit_selected_event)
        detail_buttons_layout.addWidget(self.edit_event_btn)
        
        self.delete_event_btn = QPushButton("删除")
        self.delete_event_btn.clicked.connect(self.delete_selected_event)
        detail_buttons_layout.addWidget(self.delete_event_btn)
        
        events_layout.addLayout(detail_buttons_layout)
        
        # 将部件添加到分割器
        self.splitter.addWidget(calendar_widget)
        self.splitter.addWidget(events_widget)
        self.splitter.setSizes([400, 400])
        
        # 将分割器添加到主布局
        main_layout.addWidget(self.splitter)
        
        # 更新日期显示
        self.update_date_display()
        
        # 标记有事件的日期
        self.mark_event_dates()
    
    def update_date_display(self):
        """更新日期显示"""
        selected_date = self.calendar.selectedDate()
        date_str = selected_date.toString("yyyy-MM-dd")
        weekday = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][selected_date.dayOfWeek() - 1]
        self.date_label.setText(f"{date_str} {weekday}")
        
        # 更新事件列表
        self.update_event_list(date_str)
    
    def update_event_list(self, date_str):
        """更新事件列表"""
        self.event_list.clear()
        self.event_details.clear()
        
        if date_str in self.events:
            # 按时间排序
            sorted_events = sorted(self.events[date_str], key=lambda x: x.get('time', '00:00'))
            
            for event in sorted_events:
                item = QListWidgetItem(f"{event['time']} - {event['title']}")
                item.setData(Qt.ItemDataRole.UserRole, event)
                
                # 设置不同类型的事件颜色
                event_type = event.get('type', '其他')
                if event_type == "会议":
                    item.setForeground(QColor("#3498db"))  # 蓝色
                elif event_type == "约会":
                    item.setForeground(QColor("#e74c3c"))  # 红色
                elif event_type == "生日":
                    item.setForeground(QColor("#9b59b6"))  # 紫色
                elif event_type == "纪念日":
                    item.setForeground(QColor("#f39c12"))  # 橙色
                elif event_type == "提醒":
                    item.setForeground(QColor("#2ecc71"))  # 绿色
                
                self.event_list.addItem(item)
    
    def mark_event_dates(self):
        """在日历上标记有事件的日期"""
        # 重置所有日期的格式
        self.calendar.setDateTextFormat(QDate(), QTextCharFormat())
        
        # 设置有事件日期的格式
        bold_format = QTextCharFormat()
        bold_format.setFontWeight(QFont.Weight.Bold)
        bold_format.setBackground(QColor(52, 152, 219, 50))  # 浅蓝色背景
        
        for date_str in self.events:
            try:
                year, month, day = map(int, date_str.split('-'))
                date = QDate(year, month, day)
                self.calendar.setDateTextFormat(date, bold_format)
            except (ValueError, IndexError):
                continue
    
    def date_selected(self, date):
        """日期被选中时的处理函数"""
        self.update_date_display()
    
    def go_to_today(self):
        """转到今天"""
        self.calendar.setSelectedDate(QDate.currentDate())
        self.update_date_display()
    
    def add_event(self):
        """添加新事件"""
        selected_date = self.calendar.selectedDate()
        date_str = selected_date.toString("yyyy-MM-dd")
        
        dialog = EventDialog(self)
        dialog.date_edit.setText(date_str)
        
        if dialog.exec():
            event_data = dialog.get_event_data()
            self.save_event(event_data)
    
    def edit_event(self, item):
        """编辑事件"""
        event_data = item.data(Qt.ItemDataRole.UserRole)
        
        dialog = EventDialog(self, event_data)
        if dialog.exec():
            updated_data = dialog.get_event_data()
            # 保留原始ID
            updated_data['id'] = event_data['id']
            
            # 如果日期改变，需要从原日期中删除
            if event_data['date'] != updated_data['date']:
                self.delete_event(event_data)
            
            self.save_event(updated_data)
    
    def edit_selected_event(self):
        """编辑选中的事件"""
        selected_items = self.event_list.selectedItems()
        if selected_items:
            self.edit_event(selected_items[0])
    
    def delete_selected_event(self):
        """删除选中的事件"""
        selected_items = self.event_list.selectedItems()
        if selected_items:
            event_data = selected_items[0].data(Qt.ItemDataRole.UserRole)
            reply = QMessageBox.question(self, "确认删除", 
                                        f"确定要删除事件 '{event_data['title']}' 吗？",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                self.delete_event(event_data)
    
    def save_event(self, event_data):
        """保存事件数据"""
        date_str = event_data['date']
        
        if date_str not in self.events:
            self.events[date_str] = []
        
        # 检查是否已存在相同ID的事件
        for i, event in enumerate(self.events[date_str]):
            if event.get('id') == event_data['id']:
                # 更新已有事件
                self.events[date_str][i] = event_data
                break
        else:
            # 添加新事件
            self.events[date_str].append(event_data)
        
        # 保存到文件
        self.save_events()
        
        # 更新界面
        self.update_date_display()
        self.mark_event_dates()
        
        # 显示事件详情
        self.display_event_details(event_data)
    
    def delete_event(self, event_data):
        """删除事件数据"""
        date_str = event_data['date']
        
        if date_str in self.events:
            event_id = event_data.get('id')
            self.events[date_str] = [e for e in self.events[date_str] if e.get('id') != event_id]
            
            # 如果该日期已没有事件，删除整个日期条目
            if not self.events[date_str]:
                del self.events[date_str]
            
            # 保存到文件
            self.save_events()
            
            # 更新界面
            self.update_date_display()
            self.mark_event_dates()
            self.event_details.clear()
    
    def display_event_details(self, event_data):
        """显示事件详情"""
        details = f"""
        <h3>{event_data['title']}</h3>
        <p><b>日期:</b> {event_data['date']}</p>
        <p><b>时间:</b> {event_data['time']}</p>
        <p><b>类型:</b> {event_data['type']}</p>
        <p><b>提醒:</b> {'是' if event_data.get('reminder') else '否'}</p>
        <p><b>描述:</b><br>{event_data.get('description', '').replace('\n', '<br>')}</p>
        """
        self.event_details.setHtml(details)
    
    def load_events(self):
        """从文件加载事件数据"""
        try:
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
            os.makedirs(data_dir, exist_ok=True)
            
            file_path = os.path.join(data_dir, "calendar_events.json")
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.events = json.load(f)
        except Exception as e:
            print(f"加载事件数据时出错: {str(e)}")
            self.events = {}
    
    def save_events(self):
        """保存事件数据到文件"""
        try:
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
            os.makedirs(data_dir, exist_ok=True)
            
            file_path = os.path.join(data_dir, "calendar_events.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.events, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"保存事件数据时出错: {str(e)}")
    
    def toggle_theme(self):
        """切换主题"""
        # 切换主题
        self.theme_manager.toggle_theme()
        # 应用新主题
        self.apply_current_theme()
    
    def apply_current_theme(self):
        """应用当前主题样式表"""
        try:
            # 获取当前应用程序实例
            app = QApplication.instance()
            # 应用主题
            self.theme_manager.apply_theme(app)
        except Exception as e:
            print(f"应用主题时出错: {str(e)}")


# 用于独立测试
if __name__ == '__main__':
    app = QApplication(sys.argv)
    calendar = CalendarWindow()
    calendar.show()
    sys.exit(app.exec()) 