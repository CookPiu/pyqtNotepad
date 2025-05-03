# src/ui/atomic/mini_tools/timer_widget.py
import sys
import time
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTimeEdit, QComboBox, QSpinBox, QMessageBox,
                             QTabWidget, QGridLayout, QCheckBox, QApplication)
from PyQt6.QtCore import Qt, QTimer, QTime, QSize, pyqtSignal
from PyQt6.QtGui import QFont, QIcon

# Correct relative import from atomic/mini_tools to core
from ...core.base_widget import BaseWidget
# Assuming ThemeManager might be needed later, potentially passed in or accessed globally
# from ...core.theme_manager import ThemeManager # Or get_theme_manager()

class TimerWidget(BaseWidget):
    """
    计时器原子组件，包含倒计时和闹钟功能。
    继承自 BaseWidget。
    """
    def __init__(self, parent=None, theme_manager=None): # Allow passing theme_manager
        # self.theme_manager = theme_manager # Store if passed
        super().__init__(parent) # Calls _init_ui, _connect_signals, _apply_theme

    def _init_ui(self):
        """初始化计时器 UI"""
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5) # Reduced margins for widget context

        # 创建选项卡部件
        self.tab_widget = QTabWidget()
        # Apply base styling, theme manager might override later
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #cccccc;
                border-radius: 4px;
            }
            QTabBar::tab {
                padding: 6px 12px; /* Slightly smaller padding */
                margin: 1px;
                border-radius: 4px;
            }
            QTabBar::tab:selected {
                font-weight: bold;
            }
        """)

        # 创建倒计时选项卡
        self.countdown_tab = QWidget()
        self._create_countdown_tab_content(self.countdown_tab) # Populate tab
        self.tab_widget.addTab(self.countdown_tab, "倒计时")

        # 创建闹钟选项卡
        self.alarm_tab = QWidget()
        self._create_alarm_tab_content(self.alarm_tab) # Populate tab
        self.tab_widget.addTab(self.alarm_tab, "闹钟")

        # 将选项卡部件添加到主布局
        main_layout.addWidget(self.tab_widget)
        self.setLayout(main_layout)

        # Initialize timers
        self.countdown_timer = QTimer()
        self.remaining_seconds = 0
        self.countdown_active = False

        self.alarm_timer = QTimer()
        self.time_update_timer = QTimer()
        self.alarm_time = None

        # Initial time update for alarm tab
        self.update_current_time()

    def _create_countdown_tab_content(self, tab_widget):
        """创建倒计时选项卡的内容"""
        layout = QVBoxLayout(tab_widget)
        layout.setSpacing(10) # Reduced spacing
        layout.setContentsMargins(10, 10, 10, 10) # Reduced margins

        # --- Time Setting Frame ---
        time_frame = QWidget()
        time_frame.setObjectName("countdownTimeFrame") # For styling
        time_layout = QVBoxLayout(time_frame)
        title_label = QLabel("设置倒计时时间")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 14px; margin-bottom: 5px;") # Smaller font
        time_layout.addWidget(title_label)
        spinbox_layout = QHBoxLayout()
        spinbox_layout.setSpacing(5)
        # Hour
        hour_layout = QVBoxLayout()
        self.hour_spinbox = QSpinBox()
        self.hour_spinbox.setRange(0, 23)
        self.hour_spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hour_spinbox.lineEdit().setReadOnly(True)
        hour_layout.addWidget(self.hour_spinbox)
        hour_layout.addWidget(QLabel("小时", alignment=Qt.AlignmentFlag.AlignCenter))
        spinbox_layout.addLayout(hour_layout)
        # Minute
        minute_layout = QVBoxLayout()
        self.minute_spinbox = QSpinBox()
        self.minute_spinbox.setRange(0, 59)
        self.minute_spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.minute_spinbox.lineEdit().setReadOnly(True)
        minute_layout.addWidget(self.minute_spinbox)
        minute_layout.addWidget(QLabel("分钟", alignment=Qt.AlignmentFlag.AlignCenter))
        spinbox_layout.addLayout(minute_layout)
        # Second
        second_layout = QVBoxLayout()
        self.second_spinbox = QSpinBox()
        self.second_spinbox.setRange(0, 59)
        self.second_spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.second_spinbox.lineEdit().setReadOnly(True)
        second_layout.addWidget(self.second_spinbox)
        second_layout.addWidget(QLabel("秒钟", alignment=Qt.AlignmentFlag.AlignCenter))
        spinbox_layout.addLayout(second_layout)
        time_layout.addLayout(spinbox_layout)
        layout.addWidget(time_frame)

        # --- Time Display Frame ---
        time_display_frame = QWidget()
        time_display_frame.setObjectName("countdownDisplayFrame")
        time_display_layout = QVBoxLayout(time_display_frame)
        time_label = QLabel("剩余时间")
        time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        time_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 3px;")
        time_display_layout.addWidget(time_label)
        self.time_display = QLabel("00:00:00")
        self.time_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_display.setFont(QFont("Arial", 28, QFont.Weight.Bold)) # Slightly smaller
        self.time_display.setStyleSheet("color: #2c3e50; margin: 3px 0;")
        time_display_layout.addWidget(self.time_display)
        layout.addWidget(time_display_frame)

        # --- Button Frame ---
        button_frame = QWidget()
        button_frame.setObjectName("countdownButtonFrame")
        button_layout = QHBoxLayout(button_frame)
        button_layout.setSpacing(10)
        self.start_button = QPushButton("开始")
        self.start_button.setObjectName("startButton")
        self.pause_button = QPushButton("暂停")
        self.pause_button.setObjectName("pauseButton")
        self.pause_button.setEnabled(False)
        self.reset_button = QPushButton("重置")
        self.reset_button.setObjectName("resetButton")
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.reset_button)
        layout.addWidget(button_frame)

        # --- Reminder Frame ---
        reminder_frame = QWidget()
        reminder_frame.setObjectName("countdownReminderFrame")
        reminder_layout = QVBoxLayout(reminder_frame)
        reminder_title = QLabel("提醒方式")
        reminder_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        reminder_title.setStyleSheet("font-size: 14px; margin-bottom: 3px;")
        reminder_layout.addWidget(reminder_title)
        checkbox_layout = QHBoxLayout()
        checkbox_layout.setSpacing(15)
        checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sound_checkbox = QCheckBox("声音")
        self.sound_checkbox.setChecked(True)
        self.popup_checkbox = QCheckBox("弹窗")
        self.popup_checkbox.setChecked(True)
        checkbox_layout.addWidget(self.sound_checkbox)
        checkbox_layout.addWidget(self.popup_checkbox)
        reminder_layout.addLayout(checkbox_layout)
        layout.addWidget(reminder_frame)

        # Apply initial common styling (theme manager will refine)
        self._apply_common_frame_style([time_frame, time_display_frame, button_frame, reminder_frame])
        self._apply_common_button_style([self.start_button, self.pause_button, self.reset_button])
        self._apply_common_spinbox_style([self.hour_spinbox, self.minute_spinbox, self.second_spinbox])
        self._apply_common_checkbox_style([self.sound_checkbox, self.popup_checkbox])

    def _create_alarm_tab_content(self, tab_widget):
        """创建闹钟选项卡的内容"""
        layout = QVBoxLayout(tab_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # --- Time Setting Frame ---
        time_frame = QWidget()
        time_frame.setObjectName("alarmTimeFrame")
        time_layout = QVBoxLayout(time_frame)
        title_label = QLabel("设置闹钟时间")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 14px; margin-bottom: 5px;")
        time_layout.addWidget(title_label)
        time_edit_layout = QHBoxLayout()
        time_edit_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.alarm_time_edit = QTimeEdit()
        self.alarm_time_edit.setDisplayFormat("HH:mm")
        self.alarm_time_edit.setTime(QTime.currentTime().addSecs(60))
        self.alarm_time_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.alarm_time_edit.setButtonSymbols(QTimeEdit.ButtonSymbols.UpDownArrows)
        self.alarm_time_edit.lineEdit().setReadOnly(True)
        time_edit_layout.addWidget(self.alarm_time_edit)
        time_layout.addLayout(time_edit_layout)
        layout.addWidget(time_frame)

        # --- Info Frame ---
        info_frame = QWidget()
        info_frame.setObjectName("alarmInfoFrame")
        info_layout = QVBoxLayout(info_frame)
        alarm_info_label = QLabel("闹钟状态")
        alarm_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        alarm_info_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 3px;")
        info_layout.addWidget(alarm_info_label)
        self.next_alarm_label = QLabel("下一个闹钟: 未设置")
        self.next_alarm_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.next_alarm_label.setStyleSheet("font-size: 12px; color: #e74c3c; margin: 3px 0;")
        info_layout.addWidget(self.next_alarm_label)
        time_now_label = QLabel("当前时间")
        time_now_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        time_now_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 5px;")
        info_layout.addWidget(time_now_label)
        self.current_time_label = QLabel("00:00:00")
        self.current_time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.current_time_label.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        self.current_time_label.setStyleSheet("color: #2c3e50; margin: 3px 0;")
        info_layout.addWidget(self.current_time_label)
        layout.addWidget(info_frame)

        # --- Button Frame ---
        button_frame = QWidget()
        button_frame.setObjectName("alarmButtonFrame")
        button_layout = QHBoxLayout(button_frame)
        button_layout.setSpacing(10)
        self.set_alarm_button = QPushButton("设置闹钟")
        self.set_alarm_button.setObjectName("setAlarmButton")
        self.cancel_alarm_button = QPushButton("取消闹钟")
        self.cancel_alarm_button.setObjectName("cancelAlarmButton")
        self.cancel_alarm_button.setEnabled(False)
        button_layout.addWidget(self.set_alarm_button)
        button_layout.addWidget(self.cancel_alarm_button)
        layout.addWidget(button_frame)

        # --- Reminder Frame ---
        reminder_frame = QWidget()
        reminder_frame.setObjectName("alarmReminderFrame")
        reminder_layout = QVBoxLayout(reminder_frame)
        reminder_title = QLabel("提醒方式")
        reminder_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        reminder_title.setStyleSheet("font-size: 14px; margin-bottom: 3px;")
        reminder_layout.addWidget(reminder_title)
        checkbox_layout = QHBoxLayout()
        checkbox_layout.setSpacing(15)
        checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.alarm_sound_checkbox = QCheckBox("声音")
        self.alarm_sound_checkbox.setChecked(True)
        self.alarm_popup_checkbox = QCheckBox("弹窗")
        self.alarm_popup_checkbox.setChecked(True)
        checkbox_layout.addWidget(self.alarm_sound_checkbox)
        checkbox_layout.addWidget(self.alarm_popup_checkbox)
        reminder_layout.addLayout(checkbox_layout)
        layout.addWidget(reminder_frame)

        # Apply initial common styling
        self._apply_common_frame_style([time_frame, info_frame, button_frame, reminder_frame])
        self._apply_common_button_style([self.set_alarm_button, self.cancel_alarm_button])
        self._apply_common_timeedit_style([self.alarm_time_edit])
        self._apply_common_checkbox_style([self.alarm_sound_checkbox, self.alarm_popup_checkbox])

    def _connect_signals(self):
        """连接信号与槽"""
        # Countdown signals
        self.start_button.clicked.connect(self.start_countdown)
        self.pause_button.clicked.connect(self.pause_countdown)
        self.reset_button.clicked.connect(self.reset_countdown)
        self.countdown_timer.timeout.connect(self.update_countdown)

        # Alarm signals
        self.set_alarm_button.clicked.connect(self.set_alarm)
        self.cancel_alarm_button.clicked.connect(self.cancel_alarm)
        self.alarm_timer.timeout.connect(self.check_alarm)
        self.time_update_timer.timeout.connect(self.update_current_time)

        # Start timers
        self.alarm_timer.start(1000)  # Check alarm every second
        self.time_update_timer.start(1000) # Update current time every second

    def _apply_theme(self):
        """应用主题样式 (由 BaseWidget 调用)"""
        # Placeholder: Assume we get theme status (e.g., from theme_manager)
        # For now, apply default light theme styles
        self.update_styles(is_dark=False)

    def update_styles(self, is_dark: bool):
        """根据主题更新控件样式"""
        bg_color = "rgba(45, 45, 45, 0.7)" if is_dark else "rgba(240, 240, 240, 0.7)"
        text_color = "#ecf0f1" if is_dark else "#2c3e50"
        border_color = "#555555" if is_dark else "#cccccc"
        frame_style = f"background-color: {bg_color}; border-radius: 6px; padding: 8px;"
        button_base_style = "min-height: 30px; border-radius: 15px; font-size: 12px; font-weight: bold; padding: 3px 10px;"
        button_disabled_style = "background-color: #bdc3c7; color: #7f8c8d;" if not is_dark else "background-color: #555; color: #999;"
        button_start_style = "background-color: #2ecc71; color: white;" if not is_dark else "background-color: #27ae60; color: white;"
        button_pause_style = "background-color: #f39c12; color: white;" if not is_dark else "background-color: #d35400; color: white;"
        button_reset_style = "background-color: #e74c3c; color: white;" if not is_dark else "background-color: #c0392b; color: white;"
        button_set_alarm_style = button_start_style
        button_cancel_alarm_style = button_reset_style
        spinbox_style = f"""
            QSpinBox {{
                min-height: 25px; min-width: 60px; border: 1px solid {border_color}; border-radius: 4px; padding: 2px 5px; font-size: 12px;
                background-color: {'#333' if is_dark else '#fff'}; color: {text_color};
            }}
            QSpinBox::drop-down {{ width: 15px; border-left: 1px solid {border_color}; }}
            QSpinBox QAbstractItemView {{ border: 1px solid {border_color}; background: {'#333' if is_dark else 'white'}; selection-background-color: #3498db; color: {text_color}; }}
        """
        timeedit_style = f"""
            QTimeEdit {{
                min-height: 25px; min-width: 90px; border: 1px solid {border_color}; border-radius: 4px; padding: 2px 5px; font-size: 12px;
                background-color: {'#333' if is_dark else '#fff'}; color: {text_color};
            }}
            QTimeEdit::drop-down {{ width: 15px; border-left: 1px solid {border_color}; }}
            QTimeEdit QAbstractItemView {{ border: 1px solid {border_color}; background: {'#333' if is_dark else 'white'}; selection-background-color: #3498db; color: {text_color}; }}
        """
        checkbox_style = f"""
            QCheckBox {{ font-size: 12px; spacing: 5px; color: {text_color}; }}
            QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 3px; border: 1px solid {border_color}; background-color: {'#444' if is_dark else '#eee'}; }}
            QCheckBox::indicator:checked {{ background-color: #3498db; border: 1px solid #3498db; }}
        """
        tab_style = f"""
            QTabWidget::pane {{ border: 1px solid {border_color}; border-radius: 4px; }}
            QTabBar::tab {{ padding: 6px 12px; margin: 1px; border-radius: 4px; background: {'#444' if is_dark else '#eee'}; color: {text_color}; border: 1px solid {border_color}; }}
            QTabBar::tab:selected {{ font-weight: bold; background: {'#555' if is_dark else '#f0f0f0'}; border-bottom-color: {'#555' if is_dark else '#f0f0f0'}; }}
            QTabBar::tab:!selected:hover {{ background: {'#666' if is_dark else '#ddd'}; }}
        """

        # Apply styles
        self.tab_widget.setStyleSheet(tab_style)
        for frame in self.findChildren(QWidget):
            if frame.objectName().endswith("Frame"):
                frame.setStyleSheet(frame_style)

        self.time_display.setStyleSheet(f"color: {text_color}; margin: 3px 0;")
        self.current_time_label.setStyleSheet(f"color: {text_color}; margin: 3px 0;")
        self.next_alarm_label.setStyleSheet(f"font-size: 12px; color: {'#f39c12' if is_dark else '#e74c3c'}; margin: 3px 0;") # Adjusted color

        # Countdown Buttons
        self.start_button.setStyleSheet(f"{button_base_style} {button_start_style}")
        self.pause_button.setStyleSheet(f"{button_base_style} {button_pause_style}")
        self.reset_button.setStyleSheet(f"{button_base_style} {button_reset_style}")
        # Apply disabled style separately if needed based on current state
        if not self.start_button.isEnabled(): self.start_button.setStyleSheet(f"{button_base_style} {button_disabled_style}")
        if not self.pause_button.isEnabled(): self.pause_button.setStyleSheet(f"{button_base_style} {button_disabled_style}")
        # Reset button is usually always enabled when timer is running or paused

        # Alarm Buttons
        self.set_alarm_button.setStyleSheet(f"{button_base_style} {button_set_alarm_style}")
        self.cancel_alarm_button.setStyleSheet(f"{button_base_style} {button_cancel_alarm_style}")
        if not self.set_alarm_button.isEnabled(): self.set_alarm_button.setStyleSheet(f"{button_base_style} {button_disabled_style}")
        if not self.cancel_alarm_button.isEnabled(): self.cancel_alarm_button.setStyleSheet(f"{button_base_style} {button_disabled_style}")

        # SpinBoxes & TimeEdit
        self.hour_spinbox.setStyleSheet(spinbox_style)
        self.minute_spinbox.setStyleSheet(spinbox_style)
        self.second_spinbox.setStyleSheet(spinbox_style)
        self.alarm_time_edit.setStyleSheet(timeedit_style)

        # CheckBoxes
        self.sound_checkbox.setStyleSheet(checkbox_style)
        self.popup_checkbox.setStyleSheet(checkbox_style)
        self.alarm_sound_checkbox.setStyleSheet(checkbox_style)
        self.alarm_popup_checkbox.setStyleSheet(checkbox_style)

    # --- Helper Styling Methods ---
    def _apply_common_frame_style(self, widgets):
        style = "background-color: rgba(240, 240, 240, 0.7); border-radius: 6px; padding: 8px;"
        for w in widgets: w.setStyleSheet(style)

    def _apply_common_button_style(self, buttons):
        style = """
            QPushButton { min-height: 30px; border-radius: 15px; font-size: 12px; font-weight: bold; padding: 3px 10px; }
            QPushButton:enabled { background-color: #3498db; color: white; border: none; }
            QPushButton:hover:enabled { background-color: #2980b9; }
            QPushButton:disabled { background-color: #bdc3c7; color: #7f8c8d; }
        """
        specific_styles = {
            "startButton": "QPushButton#startButton:enabled { background-color: #2ecc71; } QPushButton#startButton:hover:enabled { background-color: #27ae60; }",
            "pauseButton": "QPushButton#pauseButton:enabled { background-color: #f39c12; } QPushButton#pauseButton:hover:enabled { background-color: #d35400; }",
            "resetButton": "QPushButton#resetButton:enabled { background-color: #e74c3c; } QPushButton#resetButton:hover:enabled { background-color: #c0392b; }",
            "setAlarmButton": "QPushButton#setAlarmButton:enabled { background-color: #2ecc71; } QPushButton#setAlarmButton:hover:enabled { background-color: #27ae60; }",
            "cancelAlarmButton": "QPushButton#cancelAlarmButton:enabled { background-color: #e74c3c; } QPushButton#cancelAlarmButton:hover:enabled { background-color: #c0392b; }",
        }
        for btn in buttons:
            base_style = style + specific_styles.get(btn.objectName(), "")
            btn.setStyleSheet(base_style)

    def _apply_common_spinbox_style(self, spinboxes):
        style = """
            QSpinBox { min-height: 25px; min-width: 60px; border: 1px solid #cccccc; border-radius: 4px; padding: 2px 5px; font-size: 12px; }
            QSpinBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 15px; border-left: 1px solid #cccccc; }
            QSpinBox QAbstractItemView { border: 1px solid #cccccc; background: white; selection-background-color: #3498db; }
        """
        for sb in spinboxes: sb.setStyleSheet(style)

    def _apply_common_timeedit_style(self, timeedits):
        style = """
            QTimeEdit { min-height: 25px; min-width: 90px; border: 1px solid #cccccc; border-radius: 4px; padding: 2px 5px; font-size: 12px; }
            QTimeEdit::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 15px; border-left: 1px solid #cccccc; }
            QTimeEdit QAbstractItemView { border: 1px solid #cccccc; background: white; selection-background-color: #3498db; }
        """
        for te in timeedits: te.setStyleSheet(style)

    def _apply_common_checkbox_style(self, checkboxes):
        style = """
            QCheckBox { font-size: 12px; spacing: 5px; }
            QCheckBox::indicator { width: 16px; height: 16px; border-radius: 3px; border: 1px solid #bdc3c7; }
            QCheckBox::indicator:checked { background-color: #3498db; border: 1px solid #3498db; }
        """
        for cb in checkboxes: cb.setStyleSheet(style)

    # --- Countdown Logic ---
    def start_countdown(self):
        hours = self.hour_spinbox.value()
        minutes = self.minute_spinbox.value()
        seconds = self.second_spinbox.value()
        total_seconds = hours * 3600 + minutes * 60 + seconds

        if total_seconds <= 0:
            QMessageBox.warning(self, "警告", "请设置大于0的时间！")
            return

        if not self.countdown_active:
            self.remaining_seconds = total_seconds
            self.countdown_active = True
            self.countdown_timer.start(1000)
            self.start_button.setEnabled(False)
            self.pause_button.setEnabled(True)
            self.reset_button.setEnabled(True) # Enable reset when started
            self.hour_spinbox.setEnabled(False)
            self.minute_spinbox.setEnabled(False)
            self.second_spinbox.setEnabled(False)
        elif not self.countdown_timer.isActive(): # Resume from paused state
             self.countdown_timer.start(1000)
             self.countdown_active = True
             self.start_button.setEnabled(False) # Disable "Continue"
             self.pause_button.setEnabled(True) # Enable "Pause"


    def pause_countdown(self):
        if self.countdown_active and self.countdown_timer.isActive():
            self.countdown_timer.stop()
            # self.countdown_active = False # Keep active flag true, just timer stopped
            self.start_button.setText("继续")
            self.start_button.setEnabled(True)
            self.pause_button.setEnabled(False)

    def reset_countdown(self):
        self.countdown_timer.stop()
        self.countdown_active = False
        self.remaining_seconds = 0
        self.time_display.setText("00:00:00")
        self.start_button.setText("开始")
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        # Reset button might be disabled after reset, or kept enabled
        # self.reset_button.setEnabled(False)
        self.hour_spinbox.setEnabled(True)
        self.minute_spinbox.setEnabled(True)
        self.second_spinbox.setEnabled(True)

    def update_countdown(self):
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            hours = self.remaining_seconds // 3600
            minutes = (self.remaining_seconds % 3600) // 60
            seconds = self.remaining_seconds % 60
            self.time_display.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")

            if self.remaining_seconds == 0:
                self.countdown_timer.stop()
                self.countdown_active = False
                self.start_button.setText("开始")
                self.start_button.setEnabled(True)
                self.pause_button.setEnabled(False)
                self.hour_spinbox.setEnabled(True)
                self.minute_spinbox.setEnabled(True)
                self.second_spinbox.setEnabled(True)
                self.trigger_countdown_reminder()
        else: # Should not happen if timer is stopped correctly
             self.countdown_timer.stop()


    def trigger_countdown_reminder(self):
        message = "设定的倒计时时间已到！"
        sound = self.sound_checkbox.isChecked()
        popup = self.popup_checkbox.isChecked()
        self._trigger_reminder(message, sound, popup)

    # --- Alarm Logic ---
    def update_current_time(self):
        current_time = QTime.currentTime()
        self.current_time_label.setText(current_time.toString("HH:mm:ss"))

    def set_alarm(self):
        alarm_time = self.alarm_time_edit.time()
        current_time = QTime.currentTime()
        current_seconds = current_time.hour() * 3600 + current_time.minute() * 60 + current_time.second()
        alarm_seconds = alarm_time.hour() * 3600 + alarm_time.minute() * 60

        day_msg = ""
        if alarm_seconds <= current_seconds:
            day_msg = " (明天)"
            # QMessageBox.information(self, "闹钟设置", "闹钟时间已设置为明天！") # Maybe too intrusive

        self.alarm_time = alarm_time
        self.next_alarm_label.setText(f"下一个闹钟: {alarm_time.toString('HH:mm')}{day_msg}")
        self.set_alarm_button.setEnabled(False)
        self.cancel_alarm_button.setEnabled(True)
        self.alarm_time_edit.setEnabled(False)

    def cancel_alarm(self):
        self.alarm_time = None
        self.next_alarm_label.setText("下一个闹钟: 未设置")
        self.set_alarm_button.setEnabled(True)
        self.cancel_alarm_button.setEnabled(False)
        self.alarm_time_edit.setEnabled(True)

    def check_alarm(self):
        if self.alarm_time is None:
            return

        current_time = QTime.currentTime()
        # Check if hour and minute match, and second is 0 (trigger once per minute)
        if current_time.hour() == self.alarm_time.hour() and \
           current_time.minute() == self.alarm_time.minute() and \
           current_time.second() == 0:
            self.trigger_alarm_reminder()
            # Decide if alarm repeats or cancels itself
            self.cancel_alarm() # Assume one-shot alarm

    def trigger_alarm_reminder(self):
        message = "闹钟时间到！"
        sound = self.alarm_sound_checkbox.isChecked()
        popup = self.alarm_popup_checkbox.isChecked()
        self._trigger_reminder(message, sound, popup)

    # --- Common Reminder Logic ---
    def _trigger_reminder(self, message, sound, popup):
        """Triggers reminders based on settings."""
        if popup:
            # Use a non-modal message box if possible, or ensure it doesn't block UI thread
            # For simplicity, using standard QMessageBox here
            QMessageBox.information(self, "提醒", message)

        if sound:
            QApplication.beep()

    # Override closeEvent if necessary to stop timers
    def closeEvent(self, event):
        self.countdown_timer.stop()
        self.alarm_timer.stop()
        self.time_update_timer.stop()
        super().closeEvent(event)
