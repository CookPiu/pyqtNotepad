# src/ui/atomic/mini_tools/circular_timer_display.py
from PyQt6.QtWidgets import QWidget, QLabel
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush
from PyQt6.QtCore import Qt, QRectF, QTimer, pyqtSignal, QPointF

class CircularTimerDisplay(QWidget):
    """
    一个显示圆形进度和居中时间文本的计时器组件。
    """
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.remaining_seconds = 0
        self.total_seconds = 1  # Avoid division by zero initially
        self.progress_color = QColor("#3D5AFE")  # Default: Indigo A400
        self.background_progress_color = QColor("#E0E0E0") # Light grey for background track
        self.text_color = QColor("#2c3e50") # Default text color
        self.time_font_size = 35 # Reduced by 40% from 58 (58 * 0.6 = 34.8)
        self.time_font_family = "'SF Mono', 'Consolas', monospace"
        self.setMinimumSize(420, 420) # Increased by 50% from 280

        # For blinking colon effect
        self._colon_visible = True
        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._toggle_colon)
        self._blink_timer.start(500) # Blink every 500ms

    def _toggle_colon(self):
        self._colon_visible = not self._colon_visible
        self.update()

    def update_time(self, remaining_seconds: int, total_seconds: int):
        """更新剩余时间和总时间"""
        self.remaining_seconds = remaining_seconds
        self.total_seconds = max(1, total_seconds) # Ensure total_seconds is at least 1
        if remaining_seconds <= 0:
            self._blink_timer.stop() # Stop blinking when timer ends
            self._colon_visible = True # Ensure colon is visible when stopped
        elif not self._blink_timer.isActive():
            self._blink_timer.start(500)
        self.update() # Trigger repaint

    def set_progress_color(self, color: QColor):
        self.progress_color = color
        self.update()

    def set_background_progress_color(self, color: QColor):
        self.background_progress_color = color
        self.update()

    def set_text_color(self, color: QColor):
        self.text_color = color
        self.update()

    def set_time_font_size(self, size: int):
        self.time_font_size = size
        self.update()
    
    def set_time_font_family(self, family: str):
        self.time_font_family = family
        self.update()

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        side = min(rect.width(), rect.height())
        padding = side * 0.1  # 10% padding around the circle
        
        # Define the drawing area for the circle
        draw_rect = QRectF(
            (rect.width() - (side - padding * 2)) / 2,
            (rect.height() - (side - padding * 2)) / 2,
            side - padding * 2,
            side - padding * 2
        )

        pen_width = max(2, int(side * 0.08)) # Dynamic pen width, at least 2px

        # Draw background track
        pen = QPen(self.background_progress_color, pen_width, Qt.PenStyle.SolidLine)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(draw_rect, 0 * 16, 360 * 16)

        # Draw progress arc
        if self.total_seconds > 0 and self.remaining_seconds > 0:
            progress_angle = (self.remaining_seconds / self.total_seconds) * 360
            pen.setColor(self.progress_color)
            painter.setPen(pen)
            # Arcs are drawn counter-clockwise from 3 o'clock. Start at 90 degrees (12 o'clock).
            painter.drawArc(draw_rect, 90 * 16, -int(progress_angle * 16))


        # Draw time text
        hours = self.remaining_seconds // 3600
        minutes = (self.remaining_seconds % 3600) // 60
        seconds = self.remaining_seconds % 60
        
        colon = ":" if self._colon_visible else " "
        time_str = f"{hours:02d}{colon}{minutes:02d}{colon}{seconds:02d}"
        if self.total_seconds == 0 or self.remaining_seconds == 0 : # Initial state or finished
             time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"


        font = QFont(self.time_font_family, int(self.time_font_size * (side / 300))) # Scale font size
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(self.text_color)
        painter.drawText(draw_rect, Qt.AlignmentFlag.AlignCenter, time_str)

        super().paintEvent(event)

if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication, QVBoxLayout
    from PyQt6.QtCore import QTimer

    app = QApplication(sys.argv)
    window = QWidget()
    window.setWindowTitle("Circular Timer Test")
    window.setGeometry(100, 100, 300, 350)

    layout = QVBoxLayout(window)

    circular_timer = CircularTimerDisplay()
    # circular_timer.set_time_font_size(30) # Font size is now scaled in paintEvent
    layout.addWidget(circular_timer)

    # Test data
    total_secs_test_main = 60 # Renamed to avoid conflict if this file is imported
    current_secs_test_main = 60
    circular_timer.update_time(current_secs_test_main, total_secs_test_main)

    timer_test_main = QTimer() # Renamed

    def test_update_main(): # Renamed
        global current_secs_test_main, total_secs_test_main, timer_test_main # Added timer_test_main
        if current_secs_test_main > 0:
            current_secs_test_main -= 1
            circular_timer.update_time(current_secs_test_main, total_secs_test_main)
        else:
            timer_test_main.stop()
            circular_timer.update_time(0, total_secs_test_main)

    timer_test_main.timeout.connect(test_update_main)
    # timer_test_main.start(1000) # Uncomment to test live update

    def on_timer_click_main(): # Renamed
        print("Timer clicked! Setting new time.")
        global current_secs_test_main, total_secs_test_main, timer_test_main # Added timer_test_main
        current_secs_test_main = 30
        total_secs_test_main = 30
        circular_timer.update_time(current_secs_test_main, total_secs_test_main)
        if not timer_test_main.isActive() and current_secs_test_main > 0: # Check if time > 0
             # timer_test_main.start(1000) # Restart if stopped and time is set
             pass

    circular_timer.clicked.connect(on_timer_click_main)

    window.show()
    sys.exit(app.exec())
