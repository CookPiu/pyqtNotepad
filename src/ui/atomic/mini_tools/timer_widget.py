# src/ui/atomic/mini_tools/timer_widget.py
import sys
import time
# os import will be in the __main__ block if needed for path adjustment there
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTimeEdit, QComboBox, QSpinBox, QMessageBox,
                             QTabWidget, QGridLayout, QCheckBox, QApplication)
from PyQt6.QtCore import Qt, QTimer, QTime, QSize, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QColor

# These relative imports are fine when the module is imported as part of the package
from ...core.base_widget import BaseWidget
from .circular_timer_display import CircularTimerDisplay
from ...dialogs.set_time_dialog import SetTimeDialog
from ...dialogs.alarm_settings_dialog import AlarmSettingsDialog # Import new dialog
from PyQt6.QtWidgets import QListWidget, QListWidgetItem # Removed UISwitch as it's not standard

# Using QCheckBox as a toggle for alarm enabled state.

class TimerWidget(BaseWidget):
    """
    计时器原子组件，包含倒计时和闹钟功能。
    继承自 BaseWidget。
    """
    def __init__(self, parent=None, theme_manager=None): 
        super().__init__(parent) 

    def _init_ui(self):
        self.setObjectName("TimerFrame") 

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        
        # Initialize core data members first
        self.alarms = []
        self.alarm_check_timer = QTimer(self)
        self.countdown_timer = QTimer(self)
        self.remaining_seconds = 0
        self.total_countdown_seconds = 0 
        self.countdown_active = False

        # Create UI elements
        self.tab_widget = QTabWidget()

        self.countdown_tab = QWidget()
        self._create_countdown_tab_content(self.countdown_tab)
        self.tab_widget.addTab(self.countdown_tab, "倒计时")

        self.alarm_tab = QWidget()
        self._create_alarm_tab_content(self.alarm_tab) # This uses self.alarms
        self.tab_widget.addTab(self.alarm_tab, "闹钟")

        main_layout.addWidget(self.tab_widget)
        self.setLayout(main_layout)
        
        self._apply_theme()

    def _create_countdown_tab_content(self, tab_widget):
        layout = QVBoxLayout(tab_widget)
        layout.setSpacing(15) 
        layout.setContentsMargins(20, 20, 20, 20) 
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.circular_countdown_display = CircularTimerDisplay()
        self.circular_countdown_display.setObjectName("circularCountdownDisplay")
        self.circular_countdown_display.update_time(0, 1) 
        layout.addWidget(self.circular_countdown_display, 1, Qt.AlignmentFlag.AlignCenter) 

        button_group = QWidget()
        button_group.setObjectName("countdownButtonGroup")
        button_layout = QHBoxLayout(button_group)
        button_layout.setContentsMargins(0,0,0,0)
        button_layout.setSpacing(20)

        self.start_button = QPushButton("▶︎") 
        self.start_button.setObjectName("startButton")
        self.start_button.setToolTip("开始/继续")
        self.start_button.setFixedSize(QSize(48, 48)) 
        self.start_button.setEnabled(False) 

        self.pause_button = QPushButton("❚❚") 
        self.pause_button.setObjectName("pauseButton")
        self.pause_button.setToolTip("暂停")
        self.pause_button.setEnabled(False)
        self.pause_button.setFixedSize(QSize(48, 48))

        self.reset_button = QPushButton("↺") 
        self.reset_button.setObjectName("resetButton")
        self.reset_button.setToolTip("重置")
        self.reset_button.setFixedSize(QSize(48, 48))
        self.reset_button.setEnabled(False) 
        
        button_layout.addStretch()
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.reset_button)
        button_layout.addStretch()
        layout.addWidget(button_group)

        reminder_group = QWidget()
        reminder_group.setObjectName("countdownReminderGroup")
        reminder_layout = QHBoxLayout(reminder_group)
        reminder_layout.setContentsMargins(0,10,0,0) 
        reminder_layout.setSpacing(15)
        reminder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.sound_checkbox = QCheckBox("声音") 
        self.sound_checkbox.setChecked(True)
        self.sound_checkbox.setToolTip("完成时播放声音提醒")
        
        self.popup_checkbox = QCheckBox("弹窗") 
        self.popup_checkbox.setChecked(True)
        self.popup_checkbox.setToolTip("完成时弹出通知窗口")

        reminder_layout.addWidget(self.sound_checkbox)
        reminder_layout.addWidget(self.popup_checkbox)
        layout.addWidget(reminder_group)

    def _create_alarm_tab_content(self, tab_widget):
        layout = QVBoxLayout(tab_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        self.alarm_list_widget = QListWidget()
        self.alarm_list_widget.setObjectName("alarmListWidget")
        layout.addWidget(self.alarm_list_widget, 1) 

        add_alarm_button_layout = QHBoxLayout()
        add_alarm_button_layout.addStretch()
        self.add_alarm_button = QPushButton("＋ 添加闹钟")
        self.add_alarm_button.setObjectName("addAlarmButton")
        add_alarm_button_layout.addWidget(self.add_alarm_button)
        add_alarm_button_layout.addStretch()
        layout.addLayout(add_alarm_button_layout)

        tab_widget.setLayout(layout)
        self._populate_alarm_list() 

    def _connect_signals(self):
        self.start_button.clicked.connect(self.start_countdown)
        self.pause_button.clicked.connect(self.pause_countdown)
        self.reset_button.clicked.connect(self.reset_countdown)
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.circular_countdown_display.clicked.connect(self._show_set_time_dialog)

        if hasattr(self, 'add_alarm_button'):
            self.add_alarm_button.clicked.connect(self._add_alarm_triggered)
        self.alarm_check_timer.timeout.connect(self.check_alarms) 
        self.alarm_check_timer.start(1000) 

    def _add_alarm_triggered(self):
        dialog = AlarmSettingsDialog(self)
        if dialog.exec():
            settings = dialog.get_alarm_settings()
            settings['id'] = time.time() 
            self.alarms.append(settings)
            self._populate_alarm_list()

    def _edit_alarm_triggered(self, alarm_id):
        alarm_to_edit = next((alarm for alarm in self.alarms if alarm.get('id') == alarm_id), None)
        if not alarm_to_edit: return

        dialog = AlarmSettingsDialog(self, alarm_data=alarm_to_edit)
        if dialog.exec():
            updated_settings = dialog.get_alarm_settings()
            updated_settings['id'] = alarm_id 
            for i, alarm in enumerate(self.alarms):
                if alarm.get('id') == alarm_id:
                    self.alarms[i] = updated_settings
                    break
            self._populate_alarm_list()
            
    def _toggle_alarm_enabled(self, alarm_id, checked):
        alarm_to_toggle = next((alarm for alarm in self.alarms if alarm.get('id') == alarm_id), None)

        # Timer for updating current time on alarm tab (if displayed)
        if hasattr(self, 'alarm_tab_current_time_label'):
            self.current_time_display_timer = QTimer(self)
            self.current_time_display_timer.timeout.connect(self._update_alarm_tab_current_time)
            self.current_time_display_timer.start(1000)


    def _update_alarm_tab_current_time(self):
        if hasattr(self, 'alarm_tab_current_time_label'):
            self.alarm_tab_current_time_label.setText(QTime.currentTime().toString("HH:mm:ss"))

    def _add_alarm_triggered(self):
        dialog = AlarmSettingsDialog(self)
        if dialog.exec():
            settings = dialog.get_alarm_settings()
            # Add a unique ID to the alarm for easier management (e.g., editing/deleting)
            settings['id'] = time.time() # Simple unique ID using timestamp
            self.alarms.append(settings)
            self._populate_alarm_list()
            # Potentially save alarms to a file here

    def _edit_alarm_triggered(self, alarm_id):
        alarm_to_edit = next((alarm for alarm in self.alarms if alarm.get('id') == alarm_id), None)
        if not alarm_to_edit:
            return

        dialog = AlarmSettingsDialog(self, alarm_data=alarm_to_edit)
        if dialog.exec():
            updated_settings = dialog.get_alarm_settings()
            updated_settings['id'] = alarm_id # Ensure ID is preserved
            # Update the alarm in the list
            for i, alarm in enumerate(self.alarms):
                if alarm.get('id') == alarm_id:
                    self.alarms[i] = updated_settings
                    break
            self._populate_alarm_list()
            # Potentially save alarms to a file here
            
    def _toggle_alarm_enabled(self, alarm_id, checked):
        alarm_to_toggle = next((alarm for alarm in self.alarms if alarm.get('id') == alarm_id), None)
        if alarm_to_toggle:
            alarm_to_toggle['enabled'] = checked
            # print(f"Alarm {alarm_id} enabled: {checked}") # For debugging
            self._populate_alarm_list() # Refresh to show visual state change if any
            # Potentially save alarms

    def _delete_alarm_triggered(self, alarm_id):
        self.alarms = [alarm for alarm in self.alarms if alarm.get('id') != alarm_id]
        self._populate_alarm_list()
        # Potentially save alarms

    def _populate_alarm_list(self):
        self.alarm_list_widget.clear()
        sorted_alarms = sorted(self.alarms, key=lambda x: QTime.fromString(x['time'], "HH:mm"))

        for alarm_data in sorted_alarms:
            item = QListWidgetItem(self.alarm_list_widget)
            item_widget = self._create_alarm_list_item_widget(alarm_data)
            item.setSizeHint(item_widget.sizeHint())
            self.alarm_list_widget.addItem(item)
            self.alarm_list_widget.setItemWidget(item, item_widget)
            
    def _create_alarm_list_item_widget(self, alarm_data):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)

        time_label = QLabel(alarm_data['time'])
        time_label.setObjectName("alarmItemTimeLabel")
        font = QFont()
        font.setPointSize(16) # Larger time
        font.setWeight(QFont.Weight.Bold)
        time_label.setFont(font)

        label_text = alarm_data['label']
        if not label_text: # Handle empty label
            days_str = ", ".join(alarm_data.get('repeat', []))
            label_text = f"闹钟 {days_str}" if days_str else "闹钟"

        info_layout = QVBoxLayout()
        info_label = QLabel(label_text)
        info_label.setObjectName("alarmItemInfoLabel")
        
        # Display repeat days concisely
        repeat_days = alarm_data.get('repeat', [])
        days_map = {"Mon": "周一", "Tue": "周二", "Wed": "周三", "Thu": "周四", "Fri": "周五", "Sat": "周六", "Sun": "周日"}
        repeat_str = ", ".join([days_map.get(day, day) for day in repeat_days])
        if not repeat_str:
            # Check if alarm is for today or tomorrow if not repeating
            alarm_qtime = QTime.fromString(alarm_data['time'], "HH:mm")
            now_qtime = QTime.currentTime()
            if alarm_qtime < now_qtime and not repeat_days: # And not already passed today for a non-repeating
                repeat_str = "明天"
            else:
                repeat_str = "一次性"


        repeat_label = QLabel(repeat_str)
        repeat_label.setObjectName("alarmItemRepeatLabel")
        font_small = QFont()
        font_small.setPointSize(9)
        repeat_label.setFont(font_small)

        info_layout.addWidget(info_label)
        info_layout.addWidget(repeat_label)

        # Toggle switch (using QCheckBox for now)
        toggle_switch = QCheckBox() # Style this as a switch using QSS
        toggle_switch.setObjectName("alarmItemToggleSwitch")
        toggle_switch.setChecked(alarm_data.get('enabled', True))
        toggle_switch.setToolTip("启用/禁用闹钟")
        toggle_switch.stateChanged.connect(lambda state, aid=alarm_data['id']: self._toggle_alarm_enabled(aid, state == Qt.CheckState.Checked.value))


        # Edit and Delete buttons
        edit_button = QPushButton("编辑") # Use icons later
        edit_button.setObjectName("alarmItemEditButton")
        edit_button.setFixedSize(QSize(50,24))
        edit_button.clicked.connect(lambda _, aid=alarm_data['id']: self._edit_alarm_triggered(aid))

        delete_button = QPushButton("删除") # Use icons later
        delete_button.setObjectName("alarmItemDeleteButton")
        delete_button.setFixedSize(QSize(50,24))
        delete_button.clicked.connect(lambda _, aid=alarm_data['id']: self._delete_alarm_triggered(aid))

        button_container = QHBoxLayout()
        button_container.addWidget(edit_button)
        button_container.addWidget(delete_button)


        layout.addWidget(time_label)
        layout.addLayout(info_layout, 1) # Stretch for info
        layout.addLayout(button_container)
        layout.addWidget(toggle_switch)
        
        widget.setLayout(layout)
        # Dim the widget if disabled
        if not alarm_data.get('enabled', True):
            widget.setProperty("disabled", True) # For QSS: QWidget[disabled="true"] { ... }
            # Or iterate and disable children, or use QGraphicsOpacityEffect

        return widget


    def _show_set_time_dialog(self):
        current_h = self.total_countdown_seconds // 3600
        current_m = (self.total_countdown_seconds % 3600) // 60
        current_s = self.total_countdown_seconds % 60
        
        dialog = SetTimeDialog(self, current_h, current_m, current_s)
        if dialog.exec():
            hours, minutes, seconds = dialog.get_time()
            new_total_seconds = hours * 3600 + minutes * 60 + seconds

            if self.countdown_active and new_total_seconds != self.total_countdown_seconds :
                self.reset_countdown() 
            
            self.total_countdown_seconds = new_total_seconds
            self.remaining_seconds = self.total_countdown_seconds
            self.circular_countdown_display.update_time(self.remaining_seconds, self.total_countdown_seconds if self.total_countdown_seconds > 0 else 1)
            
            can_start = self.total_countdown_seconds > 0
            self.start_button.setEnabled(can_start and not self.countdown_active)
            self.reset_button.setEnabled(can_start) # Enable reset if time is set
            if not can_start: # If time is zero, ensure pause is disabled
                 self.pause_button.setEnabled(False)


    def _apply_theme(self):
        self.update_styles(is_dark=False) # Default to light theme for now

    def update_styles(self, is_dark: bool):
        if is_dark:
            timer_frame_bg = "rgba(45, 45, 45, 0.95)"
            button_play_bg = "#0A84FF" 
            button_play_text = "white"
            button_pause_bg = "#FF9F0A" 
            button_pause_text = "white"
            button_reset_bg = "rgba(120, 120, 128, 0.36)"
            button_reset_text = "#E0E0E0"
            button_reset_border = "rgba(120, 120, 128, 0.5)"
            checkbox_text_color = "#E0E0E0"
            checkbox_indicator_bg = "#5A5A5A"
            checkbox_indicator_border = "#707070"
            checkbox_indicator_checked_bg = button_play_bg
            tab_pane_border_color = "#505050"
            tab_bg_color = "#3A3A3C"
            tab_text_color = "#E0E0E0"
            tab_selected_bg_color = "#2C2C2E"
            tab_hover_bg_color = "#4A4A4E"
            circular_progress_color = button_play_bg 
            circular_bg_progress_color = "#5A5A5A" 
            circular_text_color = "#F0F0F0"
        else: # Light Theme
            timer_frame_bg = "rgba(242, 242, 247, 0.9)"
            button_play_bg = "#007AFF" 
            button_play_text = "white"
            button_pause_bg = "#FF9500" 
            button_pause_text = "white"
            button_reset_bg = "rgba(142, 142, 147, 0.12)"
            button_reset_text = "#333333"
            button_reset_border = "rgba(142, 142, 147, 0.25)"
            checkbox_text_color = "#333333"
            checkbox_indicator_bg = "#E9E9EB"
            checkbox_indicator_border = "#D1D1D6"
            checkbox_indicator_checked_bg = button_play_bg
            tab_pane_border_color = "#D1D1D6"
            tab_bg_color = "#F2F2F7" 
            tab_text_color = "#333333"
            tab_selected_bg_color = "white" 
            tab_hover_bg_color = "#E5E5EA"
            circular_progress_color = button_play_bg
            circular_bg_progress_color = "#E9E9EB" 
            circular_text_color = "#1C1C1E"

        if hasattr(self, 'circular_countdown_display'):
            self.circular_countdown_display.set_progress_color(QColor(circular_progress_color))
            self.circular_countdown_display.set_background_progress_color(QColor(circular_bg_progress_color))
            self.circular_countdown_display.set_text_color(QColor(circular_text_color))

        qss = f"""
            TimerWidget#TimerFrame {{ background: {timer_frame_bg}; border-radius: 12px; }}
            QWidget {{ color: {checkbox_text_color}; }}
            QTabWidget::pane {{ border: 1px solid {tab_pane_border_color}; border-radius: 8px; background-color: transparent; margin-top: -1px; }}
            QTabBar::tab {{ 
                padding: 8px 18px; margin-right: 2px; 
                border-top-left-radius: 7px; border-top-right-radius: 7px; 
                border: 1px solid {tab_pane_border_color}; border-bottom: none; 
                background: {tab_bg_color}; color: {tab_text_color};
                min-width: 80px; /* Ensure tabs have some minimum width */
            }}
            QTabBar::tab:selected {{ font-weight: 600; background: {tab_selected_bg_color}; border-bottom: 1px solid {tab_selected_bg_color}; }}
            QTabBar::tab:!selected:hover {{ background: {tab_hover_bg_color}; }}
            
            CircularTimerDisplay#circularCountdownDisplay {{ 
                min-height: 390px; /* Increased by 50% from 260px */
                min-width: 390px;  /* Increased by 50% from 260px */
            }}

            QWidget#countdownButtonGroup QPushButton {{
                min-height: 44px; min-width: 44px; max-height: 48px; max-width: 48px;
                border-radius: 24px; /* Perfect circle */
                border: none; font-size: 20px; font-weight: 500;
            }}
            QPushButton#startButton {{ background: {button_play_bg}; color: {button_play_text}; }}
            QPushButton#startButton:hover {{ background: {self.adjust_color(button_play_bg, 15 if not is_dark else -15)}; }}
            QPushButton#startButton:disabled {{ background-color: {self.adjust_color(button_play_bg, -30 if is_dark else 30, alpha=0.5)}; color: rgba(255,255,255,0.7); }}

            QPushButton#pauseButton {{ background: {button_pause_bg}; color: {button_pause_text}; }}
            QPushButton#pauseButton:hover {{ background: {self.adjust_color(button_pause_bg, 15 if not is_dark else -15)}; }}
            QPushButton#pauseButton:disabled {{ background-color: {self.adjust_color(button_pause_bg, -30 if is_dark else 30, alpha=0.5)}; color: rgba(255,255,255,0.7);}}

            QPushButton#resetButton {{ 
                background: {button_reset_bg}; color: {button_reset_text}; 
                border: 1px solid {button_reset_border};
            }}
            QPushButton#resetButton:hover {{ background: {self.adjust_color(button_reset_bg, 10 if not is_dark else -10)}; }}
            QPushButton#resetButton:disabled {{ background-color: {self.adjust_color(button_reset_bg, 0, alpha=0.5)}; color: {self.adjust_color(button_reset_text,0,alpha=0.5)}; border-color: {self.adjust_color(button_reset_border,0,alpha=0.5)};}}

            QWidget#countdownReminderGroup QCheckBox {{ font-size: 13px; spacing: 6px; color: {checkbox_text_color}; background: transparent; }}
            QWidget#countdownReminderGroup QCheckBox::indicator {{
                width: 18px; height: 18px; border-radius: 5px; 
                border: 1px solid {checkbox_indicator_border}; background-color: {checkbox_indicator_bg};
            }}
            QWidget#countdownReminderGroup QCheckBox::indicator:checked {{
                background-color: {checkbox_indicator_checked_bg}; border: 1px solid {self.adjust_color(checkbox_indicator_checked_bg, -20)};
            }}
        """
        self.setStyleSheet(qss)

    @staticmethod
    def adjust_color(hex_color, amount, alpha=None):
        try:
            if hex_color.startswith("rgba"): # Handle rgba input for alpha adjustments
                parts = hex_color.replace("rgba(", "").replace(")", "").split(',')
                r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
                current_alpha = float(parts[3])
                if alpha is None: alpha = current_alpha # Keep original alpha if not specified
            elif hex_color.startswith("rgb"):
                parts = hex_color.replace("rgb(", "").replace(")", "").split(',')
                r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
            elif hex_color.startswith("#"):
                hex_color = hex_color.lstrip('#')
                if len(hex_color) == 3: # Expand shorthand hex
                    hex_color = "".join([c*2 for c in hex_color])
                r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            else: # Simple color names
                if "white" in hex_color.lower(): r,g,b = 255,255,255
                elif "black" in hex_color.lower(): r,g,b = 0,0,0
                else: return hex_color # Fallback for unknown color names

            r = min(255, max(0, r + amount))
            g = min(255, max(0, g + amount))
            b = min(255, max(0, b + amount))

            if alpha is not None:
                return f"rgba({r}, {g}, {b}, {alpha})"
            else:
                return f"rgb({r}, {g}, {b})"
        except Exception:
            return hex_color # Fallback

    def start_countdown(self):
        if self.total_countdown_seconds <= 0:
            self._show_set_time_dialog() 
            if self.total_countdown_seconds <= 0:
                 QMessageBox.warning(self, "设置时间", "请点击计时器圆盘设置倒计时时间。")
                 return

        if not self.countdown_active: 
            self.remaining_seconds = self.total_countdown_seconds 
            self.countdown_active = True
            self.countdown_timer.start(1000)
            self.start_button.setText("▶︎") 
            self.start_button.setToolTip("开始") 
            self.start_button.setEnabled(False)
            self.pause_button.setEnabled(True)
            self.reset_button.setEnabled(True) 
            self.circular_countdown_display.update_time(self.remaining_seconds, self.total_countdown_seconds)
        elif not self.countdown_timer.isActive(): 
             self.countdown_timer.start(1000)
             self.start_button.setText("▶︎") 
             self.start_button.setToolTip("开始")
             self.start_button.setEnabled(False) 
             self.pause_button.setEnabled(True)

    def pause_countdown(self):
        if self.countdown_active and self.countdown_timer.isActive():
            self.countdown_timer.stop()
            self.start_button.setText("▶︎") 
            self.start_button.setToolTip("继续")
            self.start_button.setEnabled(True)
            self.pause_button.setEnabled(False)

    def reset_countdown(self):
        self.countdown_timer.stop()
        self.countdown_active = False
        self.remaining_seconds = self.total_countdown_seconds 
        self.circular_countdown_display.update_time(self.remaining_seconds, self.total_countdown_seconds if self.total_countdown_seconds > 0 else 1)
        self.start_button.setText("▶︎") 
        self.start_button.setToolTip("开始")
        self.start_button.setEnabled(self.total_countdown_seconds > 0) 
        self.pause_button.setEnabled(False)
        self.reset_button.setEnabled(self.total_countdown_seconds > 0) # Enable if time is set

    def update_countdown(self):
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self.circular_countdown_display.update_time(self.remaining_seconds, self.total_countdown_seconds)

            if self.remaining_seconds == 0:
                self.countdown_timer.stop()
                self.countdown_active = False
                self.start_button.setText("▶︎") 
                self.start_button.setToolTip("开始")
                self.start_button.setEnabled(True) 
                self.pause_button.setEnabled(False)
                self.trigger_countdown_reminder()
        else: 
             self.countdown_timer.stop()

    def trigger_countdown_reminder(self):
        message = "设定的倒计时时间已到！"
        sound = self.sound_checkbox.isChecked()
        popup = self.popup_checkbox.isChecked()
        self._trigger_reminder(message, sound, popup)

    def update_current_time(self):
        # This method is part of the old alarm tab, will be refactored or removed.
        pass

    def check_alarms(self): # Renamed from check_alarm
        """Checks all active alarms."""
        now = QTime.currentTime()
        today_day_str = datetime.now().strftime("%a") # Mon, Tue, etc.

        for alarm in self.alarms:
            if not alarm.get('enabled', False):
                continue

            alarm_time = QTime.fromString(alarm['time'], "HH:mm")
            
            # Check if it's time
            if alarm_time.hour() == now.hour() and alarm_time.minute() == now.minute() and now.second() == 0:
                is_today = True
                if alarm.get('repeat'): # Check repeat days
                    if today_day_str not in alarm['repeat']:
                        is_today = False
                
                if is_today:
                    # Check if this alarm has already triggered in the last minute to avoid multiple triggers
                    last_triggered_key = f"last_triggered_{alarm['id']}"
                    current_minute_epoch = int(time.time() / 60) # Integer minutes since epoch

                    if getattr(self, last_triggered_key, 0) != current_minute_epoch:
                        setattr(self, last_triggered_key, current_minute_epoch)
                        self.trigger_specific_alarm_reminder(alarm)
                        if not alarm.get('repeat'): # Disable one-time alarm after it triggers
                            alarm['enabled'] = False
                            self._populate_alarm_list() # Refresh list to show disabled state
                        break # Only trigger one alarm per check cycle to be safe

    def trigger_specific_alarm_reminder(self, alarm_data):
        """Triggers reminder for a specific alarm."""
        message = f"闹钟时间到: {alarm_data['label']} ({alarm_data['time']})"
        # Sound and popup logic will depend on how these are stored/accessed in new alarm_data
        # For now, using a default or placeholder
        # sound_setting = alarm_data.get("sound", "默认铃声") != "无声"
        sound_setting = True # Placeholder
        popup_setting = True # Placeholder
        self._trigger_reminder(message, sound_setting, popup_setting)


    def _trigger_reminder(self, message, sound, popup):
        if popup:
            QMessageBox.information(self, "提醒", message)
        if sound:
            QApplication.beep()

    def closeEvent(self, event):
        self.countdown_timer.stop()
        if hasattr(self, 'alarm_check_timer'): self.alarm_check_timer.stop()
        if hasattr(self, 'current_time_display_timer'): self.current_time_display_timer.stop()
        super().closeEvent(event)

if __name__ == '__main__':
    import sys
    import os

    # This block is executed only when the script is run directly
    # Adjust Python path to find project root for imports
    current_script_path = os.path.abspath(__file__)
    # Navigate up from src/ui/atomic/mini_tools to the project root (f:/Project/pyqtNotepad)
    project_root_directory = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_script_path))))
    
    if project_root_directory not in sys.path:
        sys.path.insert(0, project_root_directory)

    # Now, we can use absolute imports from the project root for the test
    # The TimerWidget class itself uses relative imports which are fine when it's part of a package
    # For the test script, we re-import what's needed if the class itself isn't found due to context
    # However, the class TimerWidget should now be found because its file's package context
    # can be resolved due to project_root being in sys.path.

    # We need to re-import TimerWidget specifically for the __main__ context if it wasn't found
    # This is a common pattern for making a module runnable directly.
    # The class definition above uses relative imports.
    # To make it runnable, the test part needs to ensure it can find its own components.
    
    # The class TimerWidget is defined in *this* file.
    # The issue is its *own* relative imports like `from ...core.base_widget import BaseWidget`.
    # The sys.path modification above should allow Python to resolve these when this script is run.

    app = QApplication(sys.argv)
    
    # We can directly instantiate TimerWidget as it's defined in this file.
    # The sys.path modification helps its internal relative imports.
    timer_widget_instance = TimerWidget()
    timer_widget_instance.setWindowTitle("Timer Widget Test")
    timer_widget_instance.setGeometry(100, 100, 380, 500) 
    timer_widget_instance.show()
    sys.exit(app.exec())
