import sys
import time
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTimeEdit, QComboBox, QSpinBox, QMessageBox,
                             QTabWidget, QGridLayout, QCheckBox, QApplication)
from PyQt6.QtCore import Qt, QTimer, QTime, QSize, pyqtSignal
from PyQt6.QtGui import QFont, QIcon
from src.utils.theme_manager import ThemeManager # Updated import path


class TimerWindow(QMainWindow):
    """计时器窗口，包含倒计时和闹钟功能"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 初始化主题管理器
        self.theme_manager = ThemeManager()
        
        # 初始化UI
        self.initUI()
        
        # 应用当前主题
        self.apply_current_theme()
    
    def initUI(self):
        # 设置窗口标题和大小
        self.setWindowTitle("计时器")
        self.setGeometry(200, 200, 380, 320)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建选项卡部件
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane { 
                border: 1px solid #cccccc; 
                border-radius: 4px;
            }
            QTabBar::tab { 
                padding: 8px 16px; 
                margin: 2px;
                border-radius: 4px;
            }
            QTabBar::tab:selected { 
                font-weight: bold; 
            }
        """)
        
        # 创建倒计时选项卡
        self.countdown_tab = QWidget()
        self.create_countdown_tab()
        self.tab_widget.addTab(self.countdown_tab, "倒计时")
        
        # 创建闹钟选项卡
        self.alarm_tab = QWidget()
        self.create_alarm_tab()
        self.tab_widget.addTab(self.alarm_tab, "闹钟")
        
        # 将选项卡部件添加到主布局
        main_layout.addWidget(self.tab_widget)
    
    def create_countdown_tab(self):
        # 创建倒计时选项卡的布局
        layout = QVBoxLayout(self.countdown_tab)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建时间设置部分
        time_frame = QWidget()
        time_frame.setStyleSheet("""
            QWidget { 
                background-color: rgba(240, 240, 240, 50); 
                border-radius: 8px; 
                padding: 8px;
            }
            QSpinBox { 
                min-height: 25px; 
                min-width: 70px; 
                border: 1px solid #cccccc; 
                border-radius: 4px; 
                padding: 2px 5px;
                font-size: 13px;
            }
            QSpinBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 15px;
                border-left: 1px solid #cccccc;
            }
            QSpinBox QAbstractItemView {
                border: 1px solid #cccccc;
                background: white;
                selection-background-color: #3498db;
            }
            QLabel { 
                font-size: 13px; 
                font-weight: bold;
            }
        """)
        time_layout = QVBoxLayout(time_frame)
        
        # 添加时间设置标签
        title_label = QLabel("设置倒计时时间")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; margin-bottom: 10px;")
        time_layout.addWidget(title_label)
        
        # 创建时分秒选择器布局
        spinbox_layout = QHBoxLayout()
        spinbox_layout.setSpacing(8)
        spinbox_layout.setContentsMargins(8, 3, 8, 3)
        
        # 添加小时设置
        hour_layout = QVBoxLayout()
        hour_layout.setSpacing(3)
        hour_label = QLabel("小时")
        hour_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hour_spinbox = QSpinBox()
        self.hour_spinbox.setRange(0, 23)
        self.hour_spinbox.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)
        self.hour_spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # 启用下拉候选项功能
        self.hour_spinbox.lineEdit().setReadOnly(True)
        hour_layout.addWidget(self.hour_spinbox)
        hour_layout.addWidget(hour_label)
        spinbox_layout.addLayout(hour_layout)
        
        # 添加分钟设置
        minute_layout = QVBoxLayout()
        minute_layout.setSpacing(3)
        minute_label = QLabel("分钟")
        minute_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.minute_spinbox = QSpinBox()
        self.minute_spinbox.setRange(0, 59)
        self.minute_spinbox.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)
        self.minute_spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # 启用下拉候选项功能
        self.minute_spinbox.lineEdit().setReadOnly(True)
        minute_layout.addWidget(self.minute_spinbox)
        minute_layout.addWidget(minute_label)
        spinbox_layout.addLayout(minute_layout)
        
        # 添加秒钟设置
        second_layout = QVBoxLayout()
        second_layout.setSpacing(3)
        second_label = QLabel("秒钟")
        second_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.second_spinbox = QSpinBox()
        self.second_spinbox.setRange(0, 59)
        self.second_spinbox.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)
        self.second_spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # 启用下拉候选项功能
        self.second_spinbox.lineEdit().setReadOnly(True)
        second_layout.addWidget(self.second_spinbox)
        second_layout.addWidget(second_label)
        spinbox_layout.addLayout(second_layout)
        
        time_layout.addLayout(spinbox_layout)
        layout.addWidget(time_frame)
        
        # 创建显示剩余时间的标签
        time_display_frame = QWidget()
        time_display_frame.setStyleSheet("""
            QWidget { 
                background-color: rgba(240, 240, 240, 50); 
                border-radius: 8px; 
                padding: 10px;
                margin-top: 10px;
            }
        """)
        time_display_layout = QVBoxLayout(time_display_frame)
        
        time_label = QLabel("剩余时间")
        time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        time_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 5px;")
        time_display_layout.addWidget(time_label)
        
        self.time_display = QLabel("00:00:00")
        self.time_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_display.setFont(QFont("Arial", 36, QFont.Weight.Bold))
        self.time_display.setStyleSheet("color: #2c3e50; margin: 5px 0;")
        time_display_layout.addWidget(self.time_display)
        
        layout.addWidget(time_display_frame)
        
        # 创建按钮布局
        button_frame = QWidget()
        button_frame.setStyleSheet("""
            QWidget { 
                background-color: rgba(240, 240, 240, 50); 
                border-radius: 8px; 
                padding: 10px;
                margin-top: 10px;
            }
            QPushButton {
                min-height: 35px;
                border-radius: 17px;
                font-size: 13px;
                font-weight: bold;
                padding: 3px 12px;
            }
            QPushButton:enabled {
                background-color: #3498db;
                color: white;
                border: none;
            }
            QPushButton:hover:enabled {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
            #startButton:enabled {
                background-color: #2ecc71;
            }
            #startButton:hover:enabled {
                background-color: #27ae60;
            }
            #pauseButton:enabled {
                background-color: #f39c12;
            }
            #pauseButton:hover:enabled {
                background-color: #d35400;
            }
            #resetButton:enabled {
                background-color: #e74c3c;
            }
            #resetButton:hover:enabled {
                background-color: #c0392b;
            }
        """)
        button_layout = QHBoxLayout(button_frame)
        button_layout.setSpacing(15)
        
        # 添加开始按钮
        self.start_button = QPushButton("开始")
        self.start_button.setObjectName("startButton")
        self.start_button.clicked.connect(self.start_countdown)
        self.start_button.setMinimumWidth(100)
        button_layout.addWidget(self.start_button)
        
        # 添加暂停按钮
        self.pause_button = QPushButton("暂停")
        self.pause_button.setObjectName("pauseButton")
        self.pause_button.clicked.connect(self.pause_countdown)
        self.pause_button.setEnabled(False)
        self.pause_button.setMinimumWidth(100)
        button_layout.addWidget(self.pause_button)
        
        # 添加重置按钮
        self.reset_button = QPushButton("重置")
        self.reset_button.setObjectName("resetButton")
        self.reset_button.clicked.connect(self.reset_countdown)
        self.reset_button.setMinimumWidth(100)
        button_layout.addWidget(self.reset_button)
        
        layout.addWidget(button_frame)
        
        # 创建提醒方式选择
        reminder_frame = QWidget()
        reminder_frame.setStyleSheet("""
            QWidget { 
                background-color: rgba(240, 240, 240, 50); 
                border-radius: 8px; 
                padding: 10px;
                margin-top: 10px;
            }
            QCheckBox {
                font-size: 14px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 3px;
                border: 1px solid #bdc3c7;
            }
            QCheckBox::indicator:checked {
                background-color: #3498db;
                border: 1px solid #3498db;
            }
            QLabel { 
                font-size: 14px; 
                font-weight: bold;
            }
        """)
        reminder_layout = QVBoxLayout(reminder_frame)
        
        reminder_title = QLabel("提醒方式")
        reminder_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        reminder_title.setStyleSheet("font-size: 16px; margin-bottom: 5px;")
        reminder_layout.addWidget(reminder_title)
        
        checkbox_layout = QHBoxLayout()
        checkbox_layout.setSpacing(20)
        checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.sound_checkbox = QCheckBox("声音提醒")
        self.sound_checkbox.setChecked(True)
        checkbox_layout.addWidget(self.sound_checkbox)
        
        self.popup_checkbox = QCheckBox("弹窗提醒")
        self.popup_checkbox.setChecked(True)
        checkbox_layout.addWidget(self.popup_checkbox)
        
        reminder_layout.addLayout(checkbox_layout)
        layout.addWidget(reminder_frame)
        
        # 初始化计时器
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.remaining_seconds = 0
        self.countdown_active = False
    
    def create_alarm_tab(self):
        # 创建闹钟选项卡的布局
        layout = QVBoxLayout(self.alarm_tab)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建时间设置部分
        time_frame = QWidget()
        time_frame.setStyleSheet("""
            QWidget { 
                background-color: rgba(240, 240, 240, 50); 
                border-radius: 8px; 
                padding: 8px;
            }
            QTimeEdit { 
                min-height: 25px; 
                min-width: 100px; 
                border: 1px solid #cccccc; 
                border-radius: 4px; 
                padding: 2px 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QLabel { 
                font-size: 13px; 
                font-weight: bold;
            }
        """)
        time_layout = QVBoxLayout(time_frame)
        
        # 添加时间设置标签
        title_label = QLabel("设置闹钟时间")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; margin-bottom: 10px;")
        time_layout.addWidget(title_label)
        
        # 添加时间编辑器
        time_edit_layout = QHBoxLayout()
        time_edit_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.alarm_time_edit = QTimeEdit()
        self.alarm_time_edit.setDisplayFormat("HH:mm")
        self.alarm_time_edit.setTime(QTime.currentTime().addSecs(60))  # 默认设置为当前时间后1分钟
        self.alarm_time_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.alarm_time_edit.setButtonSymbols(QTimeEdit.ButtonSymbols.UpDownArrows)
        # 设置样式以支持下拉候选项
        self.alarm_time_edit.setStyleSheet("""
            QTimeEdit {
                min-height: 25px;
                min-width: 100px;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 2px 5px;
                font-size: 13px;
            }
            QTimeEdit::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 15px;
                border-left: 1px solid #cccccc;
            }
            QTimeEdit QAbstractItemView {
                border: 1px solid #cccccc;
                background: white;
                selection-background-color: #3498db;
            }
        """)
        # 启用下拉候选项功能
        self.alarm_time_edit.lineEdit().setReadOnly(True)
        time_edit_layout.addWidget(self.alarm_time_edit)
        
        time_layout.addLayout(time_edit_layout)
        layout.addWidget(time_frame)
        
        # 创建显示当前时间和下一个闹钟的部分
        info_frame = QWidget()
        info_frame.setStyleSheet("""
            QWidget { 
                background-color: rgba(240, 240, 240, 50); 
                border-radius: 8px; 
                padding: 10px;
                margin-top: 10px;
            }
        """)
        info_layout = QVBoxLayout(info_frame)
        
        # 创建显示下一个闹钟时间的标签
        alarm_info_label = QLabel("闹钟状态")
        alarm_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        alarm_info_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 5px;")
        info_layout.addWidget(alarm_info_label)
        
        self.next_alarm_label = QLabel("下一个闹钟: 未设置")
        self.next_alarm_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.next_alarm_label.setStyleSheet("font-size: 14px; color: #e74c3c; margin: 5px 0;")
        info_layout.addWidget(self.next_alarm_label)
        
        # 创建显示当前时间的标签
        time_now_label = QLabel("当前时间")
        time_now_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        time_now_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 10px;")
        info_layout.addWidget(time_now_label)
        
        self.current_time_label = QLabel()
        self.current_time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.current_time_label.setFont(QFont("Arial", 36, QFont.Weight.Bold))
        self.current_time_label.setStyleSheet("color: #2c3e50; margin: 5px 0;")
        info_layout.addWidget(self.current_time_label)
        
        # 更新当前时间
        self.update_current_time()
        
        layout.addWidget(info_frame)
        
        # 创建按钮布局
        button_frame = QWidget()
        button_frame.setStyleSheet("""
            QWidget { 
                background-color: rgba(240, 240, 240, 50); 
                border-radius: 8px; 
                padding: 10px;
                margin-top: 10px;
            }
            QPushButton {
                min-height: 35px;
                border-radius: 17px;
                font-size: 13px;
                font-weight: bold;
                padding: 3px 12px;
            }
            QPushButton:enabled {
                background-color: #3498db;
                color: white;
                border: none;
            }
            QPushButton:hover:enabled {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
            #setAlarmButton:enabled {
                background-color: #2ecc71;
            }
            #setAlarmButton:hover:enabled {
                background-color: #27ae60;
            }
            #cancelAlarmButton:enabled {
                background-color: #e74c3c;
            }
            #cancelAlarmButton:hover:enabled {
                background-color: #c0392b;
            }
        """)
        button_layout = QHBoxLayout(button_frame)
        button_layout.setSpacing(15)
        
        # 添加设置闹钟按钮
        self.set_alarm_button = QPushButton("设置闹钟")
        self.set_alarm_button.setObjectName("setAlarmButton")
        self.set_alarm_button.clicked.connect(self.set_alarm)
        self.set_alarm_button.setMinimumWidth(120)
        button_layout.addWidget(self.set_alarm_button)
        
        # 添加取消闹钟按钮
        self.cancel_alarm_button = QPushButton("取消闹钟")
        self.cancel_alarm_button.setObjectName("cancelAlarmButton")
        self.cancel_alarm_button.clicked.connect(self.cancel_alarm)
        self.cancel_alarm_button.setEnabled(False)
        self.cancel_alarm_button.setMinimumWidth(120)
        button_layout.addWidget(self.cancel_alarm_button)
        
        layout.addWidget(button_frame)
        
        # 创建提醒方式选择
        reminder_frame = QWidget()
        reminder_frame.setStyleSheet("""
            QWidget { 
                background-color: rgba(240, 240, 240, 50); 
                border-radius: 8px; 
                padding: 10px;
                margin-top: 10px;
            }
            QCheckBox {
                font-size: 14px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 3px;
                border: 1px solid #bdc3c7;
            }
            QCheckBox::indicator:checked {
                background-color: #3498db;
                border: 1px solid #3498db;
            }
            QLabel { 
                font-size: 14px; 
                font-weight: bold;
            }
        """)
        reminder_layout = QVBoxLayout(reminder_frame)
        
        reminder_title = QLabel("提醒方式")
        reminder_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        reminder_title.setStyleSheet("font-size: 16px; margin-bottom: 5px;")
        reminder_layout.addWidget(reminder_title)
        
        checkbox_layout = QHBoxLayout()
        checkbox_layout.setSpacing(20)
        checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.alarm_sound_checkbox = QCheckBox("声音提醒")
        self.alarm_sound_checkbox.setChecked(True)
        checkbox_layout.addWidget(self.alarm_sound_checkbox)
        
        self.alarm_popup_checkbox = QCheckBox("弹窗提醒")
        self.alarm_popup_checkbox.setChecked(True)
        checkbox_layout.addWidget(self.alarm_popup_checkbox)
        
        reminder_layout.addLayout(checkbox_layout)
        layout.addWidget(reminder_frame)
        
        # 初始化闹钟计时器
        self.alarm_timer = QTimer()
        self.alarm_timer.timeout.connect(self.check_alarm)
        self.alarm_timer.start(1000)  # 每秒检查一次
        
        # 初始化更新当前时间的计时器
        self.time_update_timer = QTimer()
        self.time_update_timer.timeout.connect(self.update_current_time)
        self.time_update_timer.start(1000)  # 每秒更新一次
        
        # 初始化闹钟时间
        self.alarm_time = None
    
    def update_current_time(self):
        # 更新当前时间显示
        current_time = QTime.currentTime()
        self.current_time_label.setText(current_time.toString("HH:mm:ss"))
    
    def start_countdown(self):
        # 获取设置的时间
        hours = self.hour_spinbox.value()
        minutes = self.minute_spinbox.value()
        seconds = self.second_spinbox.value()
        
        # 计算总秒数
        total_seconds = hours * 3600 + minutes * 60 + seconds
        
        if total_seconds <= 0:
            QMessageBox.warning(self, "警告", "请设置大于0的时间！")
            return
        
        # 如果计时器未激活，则设置剩余时间并启动计时器
        if not self.countdown_active:
            self.remaining_seconds = total_seconds
            self.countdown_active = True
            self.countdown_timer.start(1000)  # 每秒更新一次
            
            # 更新按钮状态
            self.start_button.setEnabled(False)
            self.pause_button.setEnabled(True)
            self.reset_button.setEnabled(True)
            
            # 禁用时间设置
            self.hour_spinbox.setEnabled(False)
            self.minute_spinbox.setEnabled(False)
            self.second_spinbox.setEnabled(False)
    
    def pause_countdown(self):
        if self.countdown_active:
            # 暂停计时器
            self.countdown_timer.stop()
            self.countdown_active = False
            
            # 更新按钮状态
            self.start_button.setText("继续")
            self.start_button.setEnabled(True)
            self.pause_button.setEnabled(False)
        else:
            # 继续计时器
            self.countdown_timer.start(1000)
            self.countdown_active = True
            
            # 更新按钮状态
            self.start_button.setEnabled(False)
            self.pause_button.setEnabled(True)
    
    def reset_countdown(self):
        # 停止计时器
        self.countdown_timer.stop()
        self.countdown_active = False
        
        # 重置剩余时间
        self.remaining_seconds = 0
        self.time_display.setText("00:00:00")
        
        # 更新按钮状态
        self.start_button.setText("开始")
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        
        # 启用时间设置
        self.hour_spinbox.setEnabled(True)
        self.minute_spinbox.setEnabled(True)
        self.second_spinbox.setEnabled(True)
    
    def update_countdown(self):
        # 更新剩余时间
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            
            # 计算时、分、秒
            hours = self.remaining_seconds // 3600
            minutes = (self.remaining_seconds % 3600) // 60
            seconds = self.remaining_seconds % 60
            
            # 更新显示
            self.time_display.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            
            # 如果剩余时间为0，则触发提醒
            if self.remaining_seconds == 0:
                self.countdown_timer.stop()
                self.countdown_active = False
                
                # 更新按钮状态
                self.start_button.setText("开始")
                self.start_button.setEnabled(True)
                self.pause_button.setEnabled(False)
                self.reset_button.setEnabled(True)
                
                # 启用时间设置
                self.hour_spinbox.setEnabled(True)
                self.minute_spinbox.setEnabled(True)
                self.second_spinbox.setEnabled(True)
                
                # 触发提醒
                self.trigger_countdown_reminder()
    
    def trigger_countdown_reminder(self):
        # 根据选择的提醒方式触发提醒
        if self.popup_checkbox.isChecked():
            QMessageBox.information(self, "倒计时结束", "设定的倒计时时间已到！")
        
        if self.sound_checkbox.isChecked():
            # 这里可以添加声音提醒的代码
            # 由于PyQt6没有直接的声音播放功能，可以使用系统命令或第三方库
            # 这里简单地使用系统提示音
            QApplication.beep()
    
    def set_alarm(self):
        # 获取设置的闹钟时间
        alarm_time = self.alarm_time_edit.time()
        
        # 获取当前时间
        current_time = QTime.currentTime()
        
        # 计算闹钟时间与当前时间的差值（秒）
        current_seconds = current_time.hour() * 3600 + current_time.minute() * 60 + current_time.second()
        alarm_seconds = alarm_time.hour() * 3600 + alarm_time.minute() * 60
        
        # 如果闹钟时间早于当前时间，则认为是第二天的闹钟
        if alarm_seconds <= current_seconds:
            QMessageBox.information(self, "闹钟设置", "闹钟时间已设置为明天！")
        
        # 设置闹钟时间
        self.alarm_time = alarm_time
        
        # 更新下一个闹钟时间显示
        self.next_alarm_label.setText(f"下一个闹钟: {alarm_time.toString('HH:mm')}")
        
        # 更新按钮状态
        self.set_alarm_button.setEnabled(False)
        self.cancel_alarm_button.setEnabled(True)
        
        # 禁用时间编辑器
        self.alarm_time_edit.setEnabled(False)
    
    def cancel_alarm(self):
        # 取消闹钟
        self.alarm_time = None
        
        # 更新下一个闹钟时间显示
        self.next_alarm_label.setText("下一个闹钟: 未设置")
        
        # 更新按钮状态
        self.set_alarm_button.setEnabled(True)
        self.cancel_alarm_button.setEnabled(False)
        
        # 启用时间编辑器
        self.alarm_time_edit.setEnabled(True)
    
    def check_alarm(self):
        # 检查是否有设置的闹钟
        if self.alarm_time is None:
            return
        
        # 获取当前时间
        current_time = QTime.currentTime()
        
        # 检查当前时间是否达到闹钟时间（忽略秒数）
        if current_time.hour() == self.alarm_time.hour() and current_time.minute() == self.alarm_time.minute() and current_time.second() == 0:
            # 触发闹钟提醒
            self.trigger_alarm_reminder()
            
            # 取消闹钟（一次性闹钟）
            self.cancel_alarm()
    
    def trigger_alarm_reminder(self):
        # 根据选择的提醒方式触发提醒
        if self.alarm_popup_checkbox.isChecked():
            QMessageBox.information(self, "闹钟提醒", "闹钟时间到！")
        
        if self.alarm_sound_checkbox.isChecked():
            # 这里可以添加声音提醒的代码
            # 由于PyQt6没有直接的声音播放功能，可以使用系统命令或第三方库
            # 这里简单地使用系统提示音
            QApplication.beep()
    
    def toggle_theme(self):
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
            
            # 根据当前主题调整UI元素的样式
            is_dark = self.theme_manager.is_dark_theme()
            
            # 调整背景颜色
            bg_color = "rgba(45, 45, 45, 80)" if is_dark else "rgba(240, 240, 240, 50)"
            text_color = "#ecf0f1" if is_dark else "#2c3e50"
            border_color = "#555555" if is_dark else "#cccccc"
            
            # 更新所有框架的样式
            for widget in self.findChildren(QWidget):
                if widget.styleSheet() and "background-color: rgba(240, 240, 240, 50)" in widget.styleSheet():
                    new_style = widget.styleSheet().replace(
                        "background-color: rgba(240, 240, 240, 50)", 
                        f"background-color: {bg_color}"
                    )
                    widget.setStyleSheet(new_style)
            
            # 更新时间显示颜色
            if hasattr(self, 'time_display'):
                self.time_display.setStyleSheet(f"color: {text_color}; margin: 10px 0;")
            
            if hasattr(self, 'current_time_label'):
                self.current_time_label.setStyleSheet(f"color: {text_color}; margin: 5px 0;")
            
        except Exception as e:
            print(f"应用主题时出错: {str(e)}")


# 用于测试
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TimerWindow()
    window.show()
    sys.exit(app.exec())
