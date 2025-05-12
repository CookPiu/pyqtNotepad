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
        self.setObjectName("TimerFrame") # Set object name for QSS styling

        # 创建主布局
        main_layout = QVBoxLayout(self)
        # As per plan: main.setContentsMargins(16, 16, 16, 16)
        main_layout.setContentsMargins(16, 16, 16, 16)
        # As per plan: main.setSpacing(12) - applied to tab content layout later

        # 创建选项卡部件
        self.tab_widget = QTabWidget()
        # Removed inline QTabWidget styling, will be handled by theme_manager or specific QSS

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
        layout.setSpacing(12) # As per plan: spacing=12
        layout.setContentsMargins(10, 10, 10, 10) # Add some padding within the tab

        # --- Time Setting Group ---
        time_setting_group = QWidget()
        time_setting_group.setObjectName("countdownTimeSettingGroup")
        time_setting_layout = QHBoxLayout(time_setting_group)
        time_setting_layout.setContentsMargins(0,0,0,0)
        time_setting_layout.setSpacing(8)

        self.hour_spinbox = QSpinBox()
        self.hour_spinbox.setRange(0, 23)
        self.hour_spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hour_spinbox.lineEdit().setReadOnly(True)
        self.hour_spinbox.setToolTip("小时")
        time_setting_layout.addWidget(QLabel("时:"))
        time_setting_layout.addWidget(self.hour_spinbox)

        self.minute_spinbox = QSpinBox()
        self.minute_spinbox.setRange(0, 59)
        self.minute_spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.minute_spinbox.lineEdit().setReadOnly(True)
        self.minute_spinbox.setToolTip("分钟")
        time_setting_layout.addWidget(QLabel("分:"))
        time_setting_layout.addWidget(self.minute_spinbox)

        self.second_spinbox = QSpinBox()
        self.second_spinbox.setRange(0, 59)
        self.second_spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.second_spinbox.lineEdit().setReadOnly(True)
        self.second_spinbox.setToolTip("秒钟")
        time_setting_layout.addWidget(QLabel("秒:"))
        time_setting_layout.addWidget(self.second_spinbox)
        time_setting_layout.addStretch()
        layout.addWidget(time_setting_group)

        # --- Time Display Group ---
        time_display_group = QWidget()
        time_display_group.setObjectName("countdownDisplayGroup")
        time_display_layout = QVBoxLayout(time_display_group)
        time_display_layout.setContentsMargins(0,0,0,0)
        self.time_display = QLabel("00:00:00")
        self.time_display.setObjectName("TimerDisplay") # For QSS
        self.time_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont("'SF Mono', 'Consolas', monospace", 48)
        font.setWeight(QFont.Weight.DemiBold)
        self.time_display.setFont(font)
        time_display_layout.addWidget(self.time_display)
        layout.addWidget(time_display_group)

        # --- Button Group ---
        button_group = QWidget()
        button_group.setObjectName("countdownButtonGroup")
        button_layout = QHBoxLayout(button_group)
        button_layout.setContentsMargins(0,0,0,0)
        button_layout.setSpacing(10)
        self.start_button = QPushButton("▶︎ 开始") # Icon + Text
        self.start_button.setObjectName("startButton")
        self.start_button.setIconSize(QSize(16, 16)) # Example icon size

        self.pause_button = QPushButton("❚❚ 暂停") # Icon + Text
        self.pause_button.setObjectName("pauseButton")
        self.pause_button.setIconSize(QSize(16, 16))
        self.pause_button.setEnabled(False)

        self.reset_button = QPushButton("↺ 重置") # Icon + Text
        self.reset_button.setObjectName("resetButton")
        self.reset_button.setIconSize(QSize(16, 16))

        button_layout.addStretch()
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.reset_button)
        button_layout.addStretch()
        layout.addWidget(button_group)

        # --- Reminder Group ---
        reminder_group = QWidget()
        reminder_group.setObjectName("countdownReminderGroup")
        reminder_layout = QHBoxLayout(reminder_group)
        reminder_layout.setContentsMargins(0,0,0,0)
        reminder_layout.setSpacing(15)
        reminder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.sound_checkbox = QCheckBox("声音提醒")
        self.sound_checkbox.setChecked(True)
        self.popup_checkbox = QCheckBox("弹窗提醒")
        self.popup_checkbox.setChecked(True)

        reminder_layout.addWidget(self.sound_checkbox)
        reminder_layout.addWidget(self.popup_checkbox)
        layout.addWidget(reminder_group)

        layout.addStretch() # Add stretch to push content to the top

    def _create_alarm_tab_content(self, tab_widget):
        """创建闹钟选项卡的内容"""
        layout = QVBoxLayout(tab_widget)
        layout.setSpacing(12) # Consistent spacing
        layout.setContentsMargins(10, 10, 10, 10) # Add some padding within the tab

        # --- Alarm Time Setting Group ---
        alarm_setting_group = QWidget()
        alarm_setting_group.setObjectName("alarmTimeSettingGroup")
        alarm_setting_layout = QHBoxLayout(alarm_setting_group)
        alarm_setting_layout.setContentsMargins(0,0,0,0)
        alarm_setting_layout.setSpacing(8)
        alarm_setting_layout.addWidget(QLabel("设置闹钟时间:"))
        self.alarm_time_edit = QTimeEdit()
        self.alarm_time_edit.setObjectName("alarmTimeEdit") # For QSS
        self.alarm_time_edit.setDisplayFormat("HH:mm")
        self.alarm_time_edit.setTime(QTime.currentTime().addSecs(60))
        self.alarm_time_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.alarm_time_edit.setButtonSymbols(QTimeEdit.ButtonSymbols.UpDownArrows)
        self.alarm_time_edit.lineEdit().setReadOnly(True)
        alarm_setting_layout.addWidget(self.alarm_time_edit)
        alarm_setting_layout.addStretch()
        layout.addWidget(alarm_setting_group)

        # --- Alarm Info Group ---
        alarm_info_group = QWidget()
        alarm_info_group.setObjectName("alarmInfoGroup")
        alarm_info_layout = QVBoxLayout(alarm_info_group)
        alarm_info_layout.setContentsMargins(0,0,0,0)
        alarm_info_layout.setSpacing(5)

        self.next_alarm_label = QLabel("下一个闹钟: 未设置")
        self.next_alarm_label.setObjectName("nextAlarmLabel") # For QSS
        self.next_alarm_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        alarm_info_layout.addWidget(self.next_alarm_label)

        self.current_time_label = QLabel("00:00:00")
        self.current_time_label.setObjectName("currentTimeLabel") # For QSS
        self.current_time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont("'SF Mono', 'Consolas', monospace", 36) # Slightly smaller for current time
        font.setWeight(QFont.Weight.Normal)
        self.current_time_label.setFont(font)
        alarm_info_layout.addWidget(self.current_time_label)
        layout.addWidget(alarm_info_group)

        # --- Alarm Button Group ---
        alarm_button_group = QWidget()
        alarm_button_group.setObjectName("alarmButtonGroup")
        alarm_button_layout = QHBoxLayout(alarm_button_group)
        alarm_button_layout.setContentsMargins(0,0,0,0)
        alarm_button_layout.setSpacing(10)

        self.set_alarm_button = QPushButton("✓ 设置闹钟") # Icon + Text
        self.set_alarm_button.setObjectName("setAlarmButton")
        self.set_alarm_button.setIconSize(QSize(16,16))

        self.cancel_alarm_button = QPushButton("✗ 取消闹钟") # Icon + Text
        self.cancel_alarm_button.setObjectName("cancelAlarmButton")
        self.cancel_alarm_button.setIconSize(QSize(16,16))
        self.cancel_alarm_button.setEnabled(False)

        alarm_button_layout.addStretch()
        alarm_button_layout.addWidget(self.set_alarm_button)
        alarm_button_layout.addWidget(self.cancel_alarm_button)
        alarm_button_layout.addStretch()
        layout.addWidget(alarm_button_group)

        # --- Alarm Reminder Group ---
        alarm_reminder_group = QWidget()
        alarm_reminder_group.setObjectName("alarmReminderGroup")
        alarm_reminder_layout = QHBoxLayout(alarm_reminder_group)
        alarm_reminder_layout.setContentsMargins(0,0,0,0)
        alarm_reminder_layout.setSpacing(15)
        alarm_reminder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.alarm_sound_checkbox = QCheckBox("声音提醒")
        self.alarm_sound_checkbox.setChecked(True)
        self.alarm_popup_checkbox = QCheckBox("弹窗提醒")
        self.alarm_popup_checkbox.setChecked(True)

        alarm_reminder_layout.addWidget(self.alarm_sound_checkbox)
        alarm_reminder_layout.addWidget(self.alarm_popup_checkbox)
        layout.addWidget(alarm_reminder_group)

        layout.addStretch() # Add stretch to push content to the top

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
        """根据主题更新控件样式，使用QSS"""
        # Define colors based on theme
        if is_dark:
            # Dark Theme Colors (example, adjust as needed)
            timer_frame_bg = "rgba(30, 30, 30, 0.9)" # Darker background for the main widget
            timer_display_color = "#E0E0E0"
            button_primary_bg = "#007ACC" # Example: Blue
            button_primary_text = "white"
            button_secondary_bg = "#555555"
            button_secondary_text = "#E0E0E0"
            button_reset_bg = "transparent"
            button_reset_text = "#FF6B6B" # Example: Reddish for reset/cancel
            button_reset_border = "#FF6B6B"
            spinbox_bg = "#2D2D2D"
            spinbox_text = "#E0E0E0"
            spinbox_border = "#555555"
            checkbox_text = "#E0E0E0"
            checkbox_indicator_bg = "#444444"
            checkbox_indicator_border = "#666666"
            checkbox_indicator_checked_bg = button_primary_bg
            tab_pane_border = "#555555"
            tab_bg = "#3C3C3C"
            tab_text = "#E0E0E0"
            tab_selected_bg = "#2D2D2D"
            tab_hover_bg = "#4A4A4A"
            next_alarm_text_color = "#FFA726" # Orange for visibility
            frame_elements_bg = "transparent" # Frames for countdown/alarm parts
        else:
            # Light Theme Colors (as per plan)
            timer_frame_bg = "rgba(245,245,245,0.85)"
            timer_display_color = "#2c3e50"
            button_primary_bg = "#3D5AFE"  # Indigo A400
            button_primary_text = "white"
            button_secondary_bg = "#F9A826" # Pause button color from original QSS example
            button_secondary_text = "white"
            button_reset_bg = "transparent"
            button_reset_text = "#00C853"  # Green A700
            button_reset_border = "#00C853"
            spinbox_bg = "white"
            spinbox_text = "#2c3e50"
            spinbox_border = "#cccccc"
            checkbox_text = "#2c3e50"
            checkbox_indicator_bg = "#eee"
            checkbox_indicator_border = "#bdc3c7"
            checkbox_indicator_checked_bg = button_primary_bg
            tab_pane_border = "#cccccc"
            tab_bg = "#eee"
            tab_text = "#2c3e50"
            tab_selected_bg = "#f0f0f0"
            tab_hover_bg = "#ddd"
            next_alarm_text_color = "#e74c3c"
            frame_elements_bg = "transparent" # No specific background for inner frames

        qss = f"""
            TimerWidget#TimerFrame {{
                background: {timer_frame_bg};
                border-radius: 12px;
            }}

            QWidget {{ /* General text color for labels inside tabs if not specified */
                color: {checkbox_text}; /* Use checkbox_text as a general text color */
            }}

            /* Countdown and Alarm Tab Panes */
            QTabWidget::pane {{
                border: 1px solid {tab_pane_border};
                border-radius: 4px;
                background-color: {timer_frame_bg}; /* Match main background or be slightly different */
            }}
            QTabBar::tab {{
                padding: 6px 12px;
                margin: 1px;
                border-radius: 4px;
                background: {tab_bg};
                color: {tab_text};
                border: 1px solid {tab_pane_border};
            }}
            QTabBar::tab:selected {{
                font-weight: bold;
                background: {tab_selected_bg};
                border-bottom-color: {tab_selected_bg}; /* Makes selected tab blend with pane */
            }}
            QTabBar::tab:!selected:hover {{
                background: {tab_hover_bg};
            }}

            QLabel#TimerDisplay, QLabel#currentTimeLabel {{
                color: {timer_display_color};
                font-family: "SF Mono", Consolas, monospace;
                /* font-size is set in _init_ui, font-weight in _init_ui */
                padding: 8px 16px;
                background: transparent;
            }}
            QLabel#nextAlarmLabel {{
                color: {next_alarm_text_color};
                font-size: 12px;
                margin: 3px 0;
                background: transparent;
            }}

            /* Frames within tabs */
            QWidget#countdownTimeFrame, QWidget#countdownDisplayFrame, 
            QWidget#countdownButtonFrame, QWidget#countdownReminderFrame,
            QWidget#alarmTimeFrame, QWidget#alarmInfoFrame,
            QWidget#alarmButtonFrame, QWidget#alarmReminderFrame {{
                background-color: {frame_elements_bg}; /* Transparent or very subtle */
                border: none; /* No borders for inner frames */
                padding: 0px; /* No extra padding for inner frames */
            }}


            QPushButton {{
                min-height: 36px;
                border-radius: 8px;
                border: none;
                font-weight: 600;
                padding: 6px 14px;
                /* transition: background 120ms ease; Not directly supported in QSS, use hover/pressed */
            }}
            QPushButton:hover {{
                /* filter: brightness(1.06); Not directly supported, change background directly */
                /* Placeholder, specific hover for each button type below */
            }}
            QPushButton:pressed {{
                /* transform: scale(0.96); Not directly supported, can change padding or border */
            }}

            QPushButton#startButton {{
                background: {button_primary_bg};
                color: {button_primary_text};
            }}
            QPushButton#startButton:hover {{ background: {self.adjust_color(button_primary_bg, -20)}; }}
            QPushButton#startButton:disabled {{ background-color: #bdc3c7; color: #7f8c8d; }}


            QPushButton#pauseButton {{
                background: {button_secondary_bg}; /* Using secondary color for pause */
                color: {button_secondary_text};
            }}
            QPushButton#pauseButton:hover {{ background: {self.adjust_color(button_secondary_bg, -20)}; }}
            QPushButton#pauseButton:disabled {{ background-color: #bdc3c7; color: #7f8c8d; }}

            QPushButton#resetButton, QPushButton#cancelAlarmButton {{
                background: {button_reset_bg};
                color: {button_reset_text};
                border: 1px solid {button_reset_border};
            }}
            QPushButton#resetButton:hover, QPushButton#cancelAlarmButton:hover {{
                 background: {self.adjust_color(button_reset_border, 20, alpha=0.1)}; /* Slight tint on hover */
            }}
            /* Disabled state for reset/cancel can be default or specific */
             QPushButton#resetButton:disabled, QPushButton#cancelAlarmButton:disabled {{
                background-color: #bdc3c7; color: #7f8c8d; border: 1px solid #a0a0a0;
            }}


            QPushButton#setAlarmButton {{
                background: {button_primary_bg}; /* Same as start button */
                color: {button_primary_text};
            }}
            QPushButton#setAlarmButton:hover {{ background: {self.adjust_color(button_primary_bg, -20)}; }}
            QPushButton#setAlarmButton:disabled {{ background-color: #bdc3c7; color: #7f8c8d; }}


            QSpinBox, QTimeEdit {{
                min-height: 28px; /* Slightly taller for better touch */
                min-width: 60px;
                border: 1px solid {spinbox_border};
                border-radius: 6px; /* More rounded */
                padding: 3px 6px;
                font-size: 13px; /* Slightly larger font */
                background-color: {spinbox_bg};
                color: {spinbox_text};
            }}
            QSpinBox::up-button, QSpinBox::down-button,
            QTimeEdit::up-button, QTimeEdit::down-button {{
                subcontrol-origin: border; /* Changed from padding */
                subcontrol-position: {{ 'top right' if not is_dark else 'center right' }}; /* Example adjustment */
                width: 20px; /* Wider buttons */
                border-left-width: 1px;
                border-left-color: {spinbox_border};
                border-left-style: solid;
                border-top-right-radius: 5px; /* Match parent radius */
                border-bottom-right-radius: 5px;
                background-color: {self.adjust_color(spinbox_bg, 10 if not is_dark else -10)};
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover,
            QTimeEdit::up-button:hover, QTimeEdit::down-button:hover {{
                background-color: {self.adjust_color(spinbox_bg, 20 if not is_dark else -20)};
            }}
            /* QSpinBox::up-arrow, QTimeEdit::up-arrow {{ image: url(assets/icons/arrow_up_{{'light' if not is_dark else 'dark'}}.png); }} */ /* Placeholder for icons - Commented out */
            /* QSpinBox::down-arrow, QTimeEdit::down-arrow {{ image: url(assets/icons/arrow_down_{{'light' if not is_dark else 'dark'}}.png); }} */ /* Placeholder for icons - Commented out */

            QSpinBox QAbstractItemView, QTimeEdit QAbstractItemView {{ /* Dropdown list */
                border: 1px solid {spinbox_border};
                background: {spinbox_bg};
                selection-background-color: {button_primary_bg};
                color: {spinbox_text};
                padding: 2px;
            }}

            QCheckBox {{
                font-size: 13px; /* Slightly larger */
                spacing: 6px;
                color: {checkbox_text};
                background: transparent; /* Ensure checkbox itself is transparent */
            }}
            QCheckBox::indicator {{
                width: 18px; /* Slightly larger */
                height: 18px;
                border-radius: 4px; /* More rounded */
                border: 1px solid {checkbox_indicator_border};
                background-color: {checkbox_indicator_bg};
            }}
            QCheckBox::indicator:checked {{
                background-color: {checkbox_indicator_checked_bg};
                border: 1px solid {self.adjust_color(checkbox_indicator_checked_bg, -20)};
                /* image: url(assets/icons/checkmark_{{'light' if not is_dark else 'dark'}}.png); */ /* Placeholder for checkmark icon - Commented out */
            }}
            QCheckBox::indicator:disabled {{
                background-color: #cccccc;
                border: 1px solid #aaaaaa;
            }}
        """
        self.setStyleSheet(qss)

    @staticmethod
    def adjust_color(hex_color, amount, alpha=None):
        """Adjusts hex color brightness. Amount can be positive (lighter) or negative (darker). Alpha is 0-1."""
        try:
            if hex_color == "transparent": return "rgba(0,0,0,0.1)" # Default for transparent hover
            
            hex_color = hex_color.lstrip('#')
            rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            
            # Adjust brightness
            new_rgb = [min(255, max(0, c + amount)) for c in rgb]

            if alpha is not None:
                return f"rgba({new_rgb[0]}, {new_rgb[1]}, {new_rgb[2]}, {alpha})"
            else:
                return f"rgb({new_rgb[0]}, {new_rgb[1]}, {new_rgb[2]})"
        except ValueError: # Handle cases like "white", "black" or invalid hex
            # Basic fallback for common color names
            if "white" in hex_color.lower(): return f"rgb({max(0,min(255,255+amount))},{max(0,min(255,255+amount))},{max(0,min(255,255+amount))})"
            if "black" in hex_color.lower(): return f"rgb({max(0,min(255,0+amount))},{max(0,min(255,0+amount))},{max(0,min(255,0+amount))})"
            return hex_color # Return original if not parsable

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
            self.start_button.setText("▶︎ 继续") # Updated text
            self.start_button.setEnabled(True)
            self.pause_button.setEnabled(False)

    def reset_countdown(self):
        self.countdown_timer.stop()
        self.countdown_active = False
        self.remaining_seconds = 0
        self.time_display.setText("00:00:00")
        self.start_button.setText("▶︎ 开始") # Updated text
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
                self.start_button.setText("▶︎ 开始") # Updated text
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
