# src/ui/dialogs/alarm_settings_dialog.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit, 
    QTimeEdit, QCheckBox, QPushButton, QDialogButtonBox, QComboBox, QGroupBox,
    QSizePolicy
)
from PyQt6.QtCore import Qt, QTime

class AlarmSettingsDialog(QDialog):
    """
    用于添加或编辑闹钟设置的对话框。
    """
    def __init__(self, parent=None, alarm_data=None):
        super().__init__(parent)
        self.setWindowTitle("设置闹钟" if alarm_data is None else "编辑闹钟")
        self.setMinimumWidth(350)

        self.alarm_data = alarm_data if alarm_data else {}

        main_layout = QVBoxLayout(self)

        # --- Time and Label ---
        form_layout = QFormLayout()
        form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(QTime.fromString(self.alarm_data.get("time", QTime.currentTime().addSecs(300).toString("HH:mm")), "HH:mm"))
        form_layout.addRow("时间:", self.time_edit)

        self.label_edit = QLineEdit(self.alarm_data.get("label", "闹钟"))
        form_layout.addRow("标签:", self.label_edit)
        
        main_layout.addLayout(form_layout)

        # --- Repeat Days ---
        repeat_group = QGroupBox("重复")
        repeat_layout = QHBoxLayout()
        self.day_checkboxes = {}
        days = {"周一": "Mon", "周二": "Tue", "周三": "Wed", "周四": "Thu", "周五": "Fri", "周六": "Sat", "周日": "Sun"}
        current_repeat_days = self.alarm_data.get("repeat", [])
        for day_name_cn, day_name_en in days.items():
            cb = QCheckBox(day_name_cn)
            cb.setChecked(day_name_en in current_repeat_days)
            self.day_checkboxes[day_name_en] = cb
            repeat_layout.addWidget(cb)
        repeat_group.setLayout(repeat_layout)
        main_layout.addWidget(repeat_group)

        # --- Sound and Snooze ---
        sound_snooze_layout = QFormLayout()

        self.sound_combo = QComboBox()
        self.sound_combo.addItems(["默认铃声", "铃声1", "铃声2", "无声"]) # Placeholder sounds
        current_sound = self.alarm_data.get("sound", "默认铃声")
        if self.sound_combo.findText(current_sound) != -1:
            self.sound_combo.setCurrentText(current_sound)
        sound_snooze_layout.addRow("铃声:", self.sound_combo)

        self.snooze_combo = QComboBox()
        self.snooze_combo.addItems(["关闭", "5 分钟", "10 分钟", "15 分钟", "30 分钟"])
        current_snooze = self.alarm_data.get("snooze", "10 分钟")
        if self.snooze_combo.findText(current_snooze) != -1:
            self.snooze_combo.setCurrentText(current_snooze)
        sound_snooze_layout.addRow("小睡:", self.snooze_combo)
        
        main_layout.addLayout(sound_snooze_layout)
        main_layout.addStretch()

        # --- Dialog Buttons ---
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self.setLayout(main_layout)

    def get_alarm_settings(self):
        """返回用户设置的闹钟数据字典"""
        repeat_days = [day_en for day_en, cb in self.day_checkboxes.items() if cb.isChecked()]
        return {
            "time": self.time_edit.time().toString("HH:mm"),
            "label": self.label_edit.text(),
            "repeat": repeat_days,
            "sound": self.sound_combo.currentText(),
            "snooze": self.snooze_combo.currentText(),
            "enabled": self.alarm_data.get("enabled", True) # Preserve enabled state or default to True for new
        }

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)

    # Test creating a new alarm
    dialog_new = AlarmSettingsDialog()
    if dialog_new.exec():
        settings = dialog_new.get_alarm_settings()
        print("New Alarm Settings:", settings)
    else:
        print("Cancelled new alarm.")

    # Test editing an existing alarm
    existing_data = {
        "time": "08:30",
        "label": "晨间提醒",
        "repeat": ["Mon", "Wed", "Fri"],
        "sound": "铃声1",
        "snooze": "5 分钟",
        "enabled": True
    }
    dialog_edit = AlarmSettingsDialog(alarm_data=existing_data)
    if dialog_edit.exec():
        settings = dialog_edit.get_alarm_settings()
        print("Edited Alarm Settings:", settings)
    else:
        print("Cancelled alarm edit.")
        
    sys.exit(app.exec())
