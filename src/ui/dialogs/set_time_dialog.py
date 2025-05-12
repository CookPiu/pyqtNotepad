# src/ui/dialogs/set_time_dialog.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QSpinBox, QPushButton, QDialogButtonBox)
from PyQt6.QtCore import Qt

class SetTimeDialog(QDialog):
    """
    一个用于设置小时、分钟和秒的对话框。
    """
    def __init__(self, parent=None, current_hours=0, current_minutes=0, current_seconds=0):
        super().__init__(parent)
        self.setWindowTitle("设置时间")
        self.setMinimumWidth(250)

        layout = QVBoxLayout(self)

        # Time selection layout
        time_layout = QHBoxLayout()

        self.hour_spinbox = QSpinBox()
        self.hour_spinbox.setRange(0, 23)
        self.hour_spinbox.setValue(current_hours)
        self.hour_spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hour_spinbox.setToolTip("小时")
        time_layout.addWidget(QLabel("时:"))
        time_layout.addWidget(self.hour_spinbox)

        self.minute_spinbox = QSpinBox()
        self.minute_spinbox.setRange(0, 59)
        self.minute_spinbox.setValue(current_minutes)
        self.minute_spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.minute_spinbox.setToolTip("分钟")
        time_layout.addWidget(QLabel("分:"))
        time_layout.addWidget(self.minute_spinbox)

        self.second_spinbox = QSpinBox()
        self.second_spinbox.setRange(0, 59)
        self.second_spinbox.setValue(current_seconds)
        self.second_spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.second_spinbox.setToolTip("秒钟")
        time_layout.addWidget(QLabel("秒:"))
        time_layout.addWidget(self.second_spinbox)

        layout.addLayout(time_layout)

        # Dialog buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self.setLayout(layout)

    def get_time(self):
        """返回用户选择的时间 (小时, 分钟, 秒)"""
        return self.hour_spinbox.value(), self.minute_spinbox.value(), self.second_spinbox.value()

if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    dialog = SetTimeDialog(current_hours=1, current_minutes=30, current_seconds=15)
    if dialog.exec():
        hours, minutes, seconds = dialog.get_time()
        print(f"设置的时间: {hours:02d}:{minutes:02d}:{seconds:02d}")
    else:
        print("取消设置")

    sys.exit(app.exec())
