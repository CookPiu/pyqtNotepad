# src/ui/atomic/calendar/calendar_widget.py
import sys
from datetime import datetime, timedelta
import json
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QGridLayout, QCalendarWidget, QApplication,
                             QTextEdit, QDialog, QLineEdit, QTimeEdit, QCheckBox,
                             QComboBox, QMessageBox, QSplitter, QListWidget, QListWidgetItem,
                             QSizePolicy)
from PyQt6.QtCore import Qt, QSize, QDate, QTime, QDateTime, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QColor, QTextCharFormat, QPalette

# Correct relative import from atomic/calendar to core
from ...core.base_widget import BaseWidget
# from ...core.theme_manager import ThemeManager # Optional: if needed directly

# --- Event Dialog Helper Class ---
class EventDialog(QDialog):
    """事件添加/编辑对话框"""
    def __init__(self, parent=None, event_data=None, selected_date=None):
        super().__init__(parent)
        self.event_data = event_data or {}
        self.selected_date = selected_date or QDate.currentDate()
        self._init_dialog_ui()
        self._apply_styles() # Apply initial styles

    def _init_dialog_ui(self):
        self.setWindowTitle("添加/编辑事件")
        self.setMinimumWidth(350)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Title
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("标题:"))
        self.title_edit = QLineEdit(self.event_data.get('title', ''))
        title_layout.addWidget(self.title_edit)
        layout.addLayout(title_layout)

        # Date (Read-only, set from calendar)
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("日期:"))
        self.date_edit = QLineEdit(self.event_data.get('date', self.selected_date.toString("yyyy-MM-dd")))
        self.date_edit.setReadOnly(True)
        date_layout.addWidget(self.date_edit)
        layout.addLayout(date_layout)

        # Time
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("时间:"))
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("hh:mm")
        if 'time' in self.event_data:
            self.time_edit.setTime(QTime.fromString(self.event_data['time'], "hh:mm"))
        else:
            self.time_edit.setTime(QTime.currentTime())
        time_layout.addWidget(self.time_edit)
        layout.addLayout(time_layout)

        # Type
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("类型:"))
        self.type_combo = QComboBox()
        self.event_types = ["会议", "约会", "生日", "纪念日", "提醒", "其他"]
        self.type_combo.addItems(self.event_types)
        if 'type' in self.event_data:
            try:
                index = self.event_types.index(self.event_data['type'])
                self.type_combo.setCurrentIndex(index)
            except ValueError:
                self.type_combo.setCurrentIndex(self.event_types.index("其他")) # Default to '其他' if type not found
        type_layout.addWidget(self.type_combo)
        layout.addLayout(type_layout)

        # Reminder
        reminder_layout = QHBoxLayout()
        reminder_layout.addWidget(QLabel("提醒:"))
        self.reminder_check = QCheckBox("启用")
        self.reminder_check.setChecked(self.event_data.get('reminder', False))
        reminder_layout.addStretch()
        reminder_layout.addWidget(self.reminder_check)
        layout.addLayout(reminder_layout)

        # Description
        layout.addWidget(QLabel("描述:"))
        self.desc_edit = QTextEdit(self.event_data.get('description', ''))
        self.desc_edit.setAcceptRichText(False) # Plain text description
        self.desc_edit.setFixedHeight(80) # Limit height
        layout.addWidget(self.desc_edit)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.save_btn = QPushButton("保存")
        self.cancel_btn = QPushButton("取消")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

    def _apply_styles(self, is_dark=False):
        """Apply basic styling to the dialog."""
        bg_color = "#2d2d2d" if is_dark else "#ffffff"
        text_color = "#f0f0f0" if is_dark else "#000000"
        border_color = "#555555" if is_dark else "#cccccc"
        input_bg = "#3c3c3c" if is_dark else "#ffffff"
        button_bg = "#555" if is_dark else "#f0f0f0"
        button_text = text_color

        self.setStyleSheet(f"""
            QDialog {{ background-color: {bg_color}; color: {text_color}; }}
            QLabel {{ background-color: transparent; }}
            QLineEdit, QTimeEdit, QComboBox, QTextEdit {{
                background-color: {input_bg};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 4px;
            }}
            QComboBox QAbstractItemView {{ /* Dropdown style */
                 background-color: {input_bg};
                 color: {text_color};
                 selection-background-color: #3498db;
            }}
            QPushButton {{
                background-color: {button_bg};
                color: {button_text};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 5px 15px;
            }}
            QPushButton:hover {{ background-color: {"#666" if is_dark else "#e0e0e0"}; }}
            QPushButton:pressed {{ background-color: {"#444" if is_dark else "#d0d0d0"}; }}
            QCheckBox {{ background-color: transparent; }}
        """)

    def get_event_data(self):
        """获取事件数据"""
        return {
            'title': self.title_edit.text().strip(),
            'date': self.date_edit.text(),
            'time': self.time_edit.time().toString("hh:mm"),
            'type': self.type_combo.currentText(),
            'reminder': self.reminder_check.isChecked(),
            'description': self.desc_edit.toPlainText().strip(),
            'id': self.event_data.get('id', datetime.now().strftime("%Y%m%d%H%M%S%f")) # More precise ID
        }

# --- Calendar Widget ---
class CalendarWidget(BaseWidget):
    """
    日历原子组件，提供日历查看和事件管理功能。
    继承自 BaseWidget。
    """
    event_saved = pyqtSignal(object) # Signal emitted when an event is saved/deleted
    event_selected = pyqtSignal(object) # Signal emitted when an event is selected in the list

    def __init__(self, parent=None):
        self.events = {}  # {date_str: [event_dict, ...]}
        self._data_file_path = self._get_data_file_path()
        self.load_events()
        super().__init__(parent) # Calls _init_ui, _connect_signals, _apply_theme

    def _get_data_file_path(self):
        """Determines the path for the events data file."""
        # Assumes this file is in src/ui/atomic/calendar
        # Go up 4 levels to project root, then into data/
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
            data_dir = os.path.join(project_root, "data")
            os.makedirs(data_dir, exist_ok=True)
            return os.path.join(data_dir, "calendar_events.json")
        except Exception as e:
            print(f"Error determining data file path: {e}")
            # Fallback to current directory (less ideal)
            return os.path.join(os.path.dirname(os.path.abspath(__file__)), "calendar_events.json")


    def _init_ui(self):
        """初始化日历 UI"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0) # No margins for the main widget

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False) # Prevent collapsing

        # --- Left Pane: Calendar and Buttons ---
        calendar_pane = QWidget()
        calendar_layout = QVBoxLayout(calendar_pane)
        calendar_layout.setContentsMargins(5, 5, 5, 5)
        calendar_layout.setSpacing(5)

        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.calendar.setSelectionMode(QCalendarWidget.SelectionMode.SingleSelection)
        calendar_layout.addWidget(self.calendar)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        self.add_event_btn = QPushButton("添加事件")
        self.today_btn = QPushButton("今天")
        buttons_layout.addWidget(self.add_event_btn)
        buttons_layout.addWidget(self.today_btn)
        calendar_layout.addLayout(buttons_layout)

        # --- Right Pane: Event List and Details ---
        events_pane = QWidget()
        events_layout = QVBoxLayout(events_pane)
        events_layout.setContentsMargins(5, 5, 5, 5)
        events_layout.setSpacing(5)

        self.date_label = QLabel()
        self.date_label.setFont(QFont("Arial", 12, QFont.Weight.Bold)) # Slightly smaller
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        events_layout.addWidget(self.date_label)

        self.event_list = QListWidget()
        self.event_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.event_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        events_layout.addWidget(self.event_list, 1) # Give list more stretch factor

        self.event_details = QTextEdit()
        self.event_details.setReadOnly(True)
        self.event_details.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        self.event_details.setFixedHeight(100) # Fixed height for details preview
        events_layout.addWidget(self.event_details)

        detail_buttons_layout = QHBoxLayout()
        detail_buttons_layout.setSpacing(10)
        self.edit_event_btn = QPushButton("编辑")
        self.delete_event_btn = QPushButton("删除")
        detail_buttons_layout.addStretch()
        detail_buttons_layout.addWidget(self.edit_event_btn)
        detail_buttons_layout.addWidget(self.delete_event_btn)
        events_layout.addLayout(detail_buttons_layout)

        # --- Add panes to splitter ---
        self.splitter.addWidget(calendar_pane)
        self.splitter.addWidget(events_pane)
        self.splitter.setSizes([350, 450]) # Adjust initial sizes

        main_layout.addWidget(self.splitter)
        self.setLayout(main_layout)

        # Initial display update
        self.update_date_display()
        self.mark_event_dates()

    def _connect_signals(self):
        """连接信号与槽"""
        self.calendar.clicked.connect(self.date_selected)
        self.add_event_btn.clicked.connect(self.add_event)
        self.today_btn.clicked.connect(self.go_to_today)
        self.event_list.itemSelectionChanged.connect(self.display_selected_event_details)
        self.event_list.itemDoubleClicked.connect(self.edit_event_item) # Edit on double click
        self.edit_event_btn.clicked.connect(self.edit_selected_event)
        self.delete_event_btn.clicked.connect(self.delete_selected_event)

    def _apply_theme(self):
        """应用主题样式 (由 BaseWidget 调用)"""
        self.update_styles(is_dark=False) # Default light

    def update_styles(self, is_dark: bool):
        """根据主题更新控件样式"""
        bg_color = "#1e1e1e" if is_dark else "#ffffff"
        text_color = "#f0f0f0" if is_dark else "#2c3e50"
        border_color = "#555555" if is_dark else "#cccccc"
        list_item_bg = "#2d2d2d" if is_dark else "#ffffff"
        list_item_selected_bg = "#3498db"
        list_item_selected_text = "#ffffff"
        calendar_bg = bg_color
        calendar_text = text_color
        calendar_header_bg = "#3c3c3c" if is_dark else "#f1f1f1"
        calendar_toolbutton_bg = "#555" if is_dark else "#f0f0f0"
        calendar_disabled_text = "#777" if is_dark else "#bdc3c7"
        button_bg = "#555" if is_dark else "#f0f0f0"
        button_text = text_color

        # Main widget background (might be inherited)
        # palette = self.palette()
        # palette.setColor(QPalette.ColorRole.Window, QColor(bg_color))
        # self.setPalette(palette)
        # self.setAutoFillBackground(True)

        # Calendar Styles
        self.calendar.setStyleSheet(f"""
            QCalendarWidget {{
                background-color: {calendar_bg};
                color: {calendar_text};
                border: 1px solid {border_color}; /* Add border */
                border-radius: 4px;
            }}
            QCalendarWidget QToolButton {{ /* Prev/Next Month, Year buttons */
                height: 28px; /* Adjust size */
                width: 80px;
                color: {calendar_text};
                background-color: {calendar_toolbutton_bg};
                font-size: 12px;
                border-radius: 4px;
                border: 1px solid {border_color};
                margin: 2px;
            }}
            QCalendarWidget QToolButton:hover {{ background-color: {"#666" if is_dark else "#e0e0e0"}; }}
            QCalendarWidget QMenu {{ /* Month/Year selection menu */
                background-color: {calendar_bg};
                color: {calendar_text};
                border: 1px solid {border_color};
            }}
            QCalendarWidget QSpinBox {{ /* Year selection spinbox */
                color: {calendar_text};
                background-color: {calendar_bg};
                border: 1px solid {border_color};
                selection-background-color: {list_item_selected_bg};
                selection-color: {list_item_selected_text};
            }}
            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background-color: {calendar_header_bg};
                border-bottom: 1px solid {border_color};
                border-top-left-radius: 4px; /* Match main border */
                border-top-right-radius: 4px;
            }}
            QCalendarWidget QAbstractItemView:enabled {{ /* Date grid */
                font-size: 12px;
                color: {calendar_text};
                background-color: {calendar_bg};
                selection-background-color: {list_item_selected_bg};
                selection-color: {list_item_selected_text};
                outline: 0; /* Remove focus outline */
            }}
            QCalendarWidget QAbstractItemView:disabled {{ /* Dates outside current month */
                color: {calendar_disabled_text};
            }}
            /* Weekend/Weekday colors - QTextCharFormat overrides this for specific dates */
            /* QCalendarWidget QAbstractItemView::item:weekday {{ color: {calendar_text}; }} */
            /* QCalendarWidget QAbstractItemView::item:weekend {{ color: #e74c3c; }} */
        """)

        # Event List and Details Styles
        self.date_label.setStyleSheet(f"color: {text_color}; background-color: transparent;")
        self.event_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {list_item_bg};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 3px;
                font-size: 12px;
                color: {text_color};
            }}
            QListWidget::item {{
                border-bottom: 1px solid {border_color};
                padding: 5px;
            }}
            QListWidget::item:selected {{
                background-color: {list_item_selected_bg};
                color: {list_item_selected_text};
            }}
        """)
        self.event_details.setStyleSheet(f"""
            QTextEdit {{
                background-color: {list_item_bg};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 5px;
                font-size: 12px;
                color: {text_color};
            }}
        """)

        # Button Styles
        button_style = f"""
            QPushButton {{
                background-color: {button_bg};
                color: {button_text};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 5px 10px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: {"#666" if is_dark else "#e0e0e0"}; }}
            QPushButton:pressed {{ background-color: {"#444" if is_dark else "#d0d0d0"}; }}
        """
        for btn in [self.add_event_btn, self.today_btn, self.edit_event_btn, self.delete_event_btn]:
            btn.setStyleSheet(button_style)

        # Re-apply date formats which might be affected by stylesheet changes
        self.mark_event_dates()
        # Update event list item colors
        self.update_event_list(self.calendar.selectedDate().toString("yyyy-MM-dd"))


    # --- Event Handling Logic ---
    def update_date_display(self):
        """Updates the date label and event list for the selected date."""
        selected_date = self.calendar.selectedDate()
        date_str = selected_date.toString("yyyy-MM-dd")
        try:
            # Handle potential locale issues with dayOfWeek() names
            weekday_map = {1: "星期一", 2: "星期二", 3: "星期三", 4: "星期四", 5: "星期五", 6: "星期六", 7: "星期日"}
            weekday = weekday_map.get(selected_date.dayOfWeek(), "")
        except Exception:
            weekday = "" # Fallback
        self.date_label.setText(f"{date_str} {weekday}")
        self.update_event_list(date_str)

    def update_event_list(self, date_str):
        """Updates the QListWidget with events for the given date string."""
        self.event_list.clear()
        self.event_details.clear()
        self.edit_event_btn.setEnabled(False) # Disable buttons initially
        self.delete_event_btn.setEnabled(False)

        if date_str in self.events:
            sorted_events = sorted(self.events[date_str], key=lambda x: x.get('time', '00:00'))
            for event in sorted_events:
                item = QListWidgetItem(f"{event.get('time', '??:??')} - {event.get('title', '无标题')}")
                item.setData(Qt.ItemDataRole.UserRole, event)
                # Apply color based on type
                event_type = event.get('type', '其他')
                color = self._get_event_type_color(event_type)
                item.setForeground(color)
                self.event_list.addItem(item)

    def _get_event_type_color(self, event_type):
        """Returns a QColor based on the event type."""
        # TODO: Make these colors theme-dependent
        colors = {
            "会议": QColor("#3498db"), "约会": QColor("#e74c3c"),
            "生日": QColor("#9b59b6"), "纪念日": QColor("#f39c12"),
            "提醒": QColor("#2ecc71"), "其他": QColor("#7f8c8d")
        }
        return colors.get(event_type, colors["其他"])

    def mark_event_dates(self):
        """Applies formatting to dates with events in the QCalendarWidget."""
        # Reset all formats first
        default_format = QTextCharFormat()
        self.calendar.setDateTextFormat(QDate(), default_format) # Reset all dates

        # Apply format for dates with events
        event_format = QTextCharFormat()
        event_format.setFontWeight(QFont.Weight.Bold)
        # Use a subtle background or underline instead of changing text color
        # event_format.setBackground(QColor(52, 152, 219, 30)) # Very light blue background
        event_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SingleUnderline)
        event_format.setUnderlineColor(QColor("#3498db")) # Blue underline

        for date_str in self.events:
            if self.events[date_str]: # Only mark if there are events
                try:
                    date = QDate.fromString(date_str, "yyyy-MM-dd")
                    if date.isValid():
                        self.calendar.setDateTextFormat(date, event_format)
                except Exception as e:
                    print(f"Error parsing date {date_str} for marking: {e}")


    def date_selected(self, date):
        """Handles selection of a date in the calendar."""
        self.update_date_display()

    def go_to_today(self):
        """Selects today's date in the calendar."""
        today = QDate.currentDate()
        self.calendar.setSelectedDate(today)
        self.date_selected(today) # Trigger update

    def add_event(self):
        """Opens the dialog to add a new event for the selected date."""
        selected_date = self.calendar.selectedDate()
        dialog = EventDialog(self, selected_date=selected_date)
        # Apply theme to dialog if possible
        # dialog._apply_styles(is_dark=self.theme_manager.is_dark_theme()) # Example
        if dialog.exec():
            event_data = dialog.get_event_data()
            if not event_data['title']:
                QMessageBox.warning(self, "缺少标题", "事件标题不能为空。")
                return
            self.save_event(event_data)

    def edit_event_item(self, item):
        """Handles double-clicking an event item in the list."""
        if item:
            self.edit_event(item.data(Qt.ItemDataRole.UserRole))

    def edit_selected_event(self):
        """Opens the dialog to edit the currently selected event."""
        selected_items = self.event_list.selectedItems()
        if selected_items:
            self.edit_event(selected_items[0].data(Qt.ItemDataRole.UserRole))

    def edit_event(self, event_data):
        """Opens the dialog to edit an existing event."""
        if not event_data: return
        dialog = EventDialog(self, event_data=event_data)
        # dialog._apply_styles(is_dark=...) # Apply theme
        if dialog.exec():
            updated_data = dialog.get_event_data()
            if not updated_data['title']:
                QMessageBox.warning(self, "缺少标题", "事件标题不能为空。")
                return
            # Ensure ID is preserved
            updated_data['id'] = event_data.get('id')
            # Handle date change: remove from old date list
            if event_data.get('date') != updated_data.get('date'):
                 self._remove_event_from_date(event_data.get('date'), event_data.get('id'))
            self.save_event(updated_data)


    def delete_selected_event(self):
        """Deletes the currently selected event after confirmation."""
        selected_items = self.event_list.selectedItems()
        if selected_items:
            event_data = selected_items[0].data(Qt.ItemDataRole.UserRole)
            reply = QMessageBox.question(self, "确认删除",
                                        f"确定要删除事件 '{event_data.get('title', '无标题')}' 吗？",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                        QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.delete_event(event_data)

    def display_selected_event_details(self):
        """Displays details of the selected event in the QTextEdit."""
        selected_items = self.event_list.selectedItems()
        if selected_items:
            event_data = selected_items[0].data(Qt.ItemDataRole.UserRole)
            self.display_event_details(event_data)
            self.edit_event_btn.setEnabled(True)
            self.delete_event_btn.setEnabled(True)
            self.event_selected.emit(event_data) # Emit signal
        else:
            self.event_details.clear()
            self.edit_event_btn.setEnabled(False)
            self.delete_event_btn.setEnabled(False)
            self.event_selected.emit(None) # Emit signal with None

    def display_event_details(self, event_data):
        """Formats and displays event details in the QTextEdit."""
        if not event_data:
            self.event_details.clear()
            return
        desc_html = event_data.get('description', '').replace('\n', '<br>')
        details = f"""
        <p style="margin-bottom: 5px;"><b>{event_data.get('title', '无标题')}</b></p>
        <p style="font-size: 9pt; margin-bottom: 3px;"><b>时间:</b> {event_data.get('time', '未指定')}</p>
        <p style="font-size: 9pt; margin-bottom: 3px;"><b>类型:</b> {event_data.get('type', '未指定')}</p>
        <p style="font-size: 9pt; margin-bottom: 3px;"><b>提醒:</b> {'是' if event_data.get('reminder') else '否'}</p>
        <hr>
        <p style="font-size: 9pt;">{desc_html if desc_html else '无描述'}</p>
        """
        self.event_details.setHtml(details)

    # --- Data Persistence ---
    def save_event(self, event_data):
        """Saves or updates an event and persists to file."""
        date_str = event_data.get('date')
        event_id = event_data.get('id')
        if not date_str or not event_id:
            print("Error: Event data missing date or id.")
            return

        if date_str not in self.events:
            self.events[date_str] = []

        # Find existing event by ID and update, or append new
        found = False
        for i, existing_event in enumerate(self.events[date_str]):
            if existing_event.get('id') == event_id:
                self.events[date_str][i] = event_data
                found = True
                break
        if not found:
            self.events[date_str].append(event_data)

        self.save_events_to_file()
        self.update_date_display() # Refresh list for current date
        self.mark_event_dates()    # Refresh calendar markings
        self.event_saved.emit(event_data) # Emit signal

        # Try to re-select the saved event in the list
        self._select_event_in_list(event_id)


    def delete_event(self, event_data):
        """Deletes an event and persists changes."""
        date_str = event_data.get('date')
        event_id = event_data.get('id')
        if not date_str or not event_id: return

        removed = self._remove_event_from_date(date_str, event_id)

        if removed:
            self.save_events_to_file()
            self.update_date_display() # Refresh list
            self.mark_event_dates()    # Refresh markings
            self.event_details.clear() # Clear details view
            self.event_saved.emit(None) # Emit signal indicating deletion

    def _remove_event_from_date(self, date_str, event_id):
        """Removes an event with a specific ID from a specific date list."""
        removed = False
        if date_str in self.events:
            initial_len = len(self.events[date_str])
            self.events[date_str] = [e for e in self.events[date_str] if e.get('id') != event_id]
            removed = len(self.events[date_str]) < initial_len
            if not self.events[date_str]: # Remove date entry if empty
                del self.events[date_str]
        return removed

    def load_events(self):
        """Loads event data from the JSON file."""
        if not os.path.exists(self._data_file_path):
            self.events = {}
            return
        try:
            with open(self._data_file_path, 'r', encoding='utf-8') as f:
                self.events = json.load(f)
        except (json.JSONDecodeError, IOError, Exception) as e:
            print(f"加载事件数据时出错 ({self._data_file_path}): {e}")
            self.events = {} # Reset on error

    def save_events_to_file(self):
        """Saves the current events dictionary to the JSON file."""
        try:
            with open(self._data_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.events, f, ensure_ascii=False, indent=4, sort_keys=True)
        except (IOError, Exception) as e:
            print(f"保存事件数据时出错 ({self._data_file_path}): {e}")
            QMessageBox.critical(self, "保存错误", f"无法保存事件数据到文件:\n{e}")

    def _select_event_in_list(self, event_id):
         """Tries to find and select an event by ID in the current list."""
         for i in range(self.event_list.count()):
             item = self.event_list.item(i)
             event_data = item.data(Qt.ItemDataRole.UserRole)
             if event_data and event_data.get('id') == event_id:
                 item.setSelected(True)
                 self.event_list.scrollToItem(item, QListWidget.ScrollHint.PositionAtCenter)
                 self.display_selected_event_details() # Ensure details are shown
                 break
