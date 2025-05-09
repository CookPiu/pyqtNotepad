# src/ui/views/image_viewer_view.py
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QMessageBox, 
                             QScrollArea, QSizePolicy)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, QSize

class ImageViewWidget(QWidget):
    """
    图片查看器 Widget。
    使用 QLabel 和 QPixmap 在可滚动区域中显示图片。
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_path = None
        self.pixmap = None

        self._image_label = QLabel(self)
        self._image_label.setBackgroundRole(self.backgroundRole()) # Match theme
        self._image_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._scroll_area = QScrollArea(self)
        self._scroll_area.setBackgroundRole(self.backgroundRole())
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setWidget(self._image_label)
        self._scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout(self)
        layout.addWidget(self._scroll_area)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def load_image(self, file_path: str) -> bool:
        """
        加载指定的图片文件。
        """
        self.file_path = file_path
        if not self.file_path or not os.path.exists(self.file_path):
            QMessageBox.critical(self, "错误", f"图片文件路径无效或文件不存在:\n{self.file_path}")
            return False
        
        self.pixmap = QPixmap(self.file_path)
        if self.pixmap.isNull():
            QMessageBox.critical(self, "错误", f"无法加载图片:\n{self.file_path}\n文件可能已损坏或格式不受支持。")
            self.pixmap = None # Ensure pixmap is None if loading failed
            return False
        
        self._image_label.setPixmap(self.pixmap)
        # Adjust label size to pixmap size for scroll area to work correctly
        self._image_label.adjustSize() 
        return True

    def get_file_path(self) -> str | None:
        return self.file_path

    def cleanup(self):
        """清理资源。"""
        if self.pixmap:
            self.pixmap = QPixmap() # Clear the pixmap
            self._image_label.setPixmap(self.pixmap)
        self.file_path = None

    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)

if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication, QFileDialog

    app = QApplication.instance() 
    if app is None:
        app = QApplication(sys.argv)
    
    main_win = QWidget()
    main_win.setWindowTitle("Image Viewer Widget Test")
    main_win.setGeometry(100, 100, 800, 600)
    
    viewer_widget = ImageViewWidget(main_win)
    
    from PyQt6.QtWidgets import QPushButton
    btn = QPushButton("Open Image File", main_win)
    
    vbox = QVBoxLayout(main_win)
    vbox.addWidget(btn)
    vbox.addWidget(viewer_widget)
    main_win.setLayout(vbox)

    def open_test_image():
        file_path, _ = QFileDialog.getOpenFileName(main_win, "Select Image File", "", 
                                                   "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)")
        if file_path:
            if not viewer_widget.load_image(file_path):
                print(f"Failed to load image: {file_path}")
    
    btn.clicked.connect(open_test_image)
    
    main_win.show()
    sys.exit(app.exec())
