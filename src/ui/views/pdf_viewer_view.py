# src/ui/views/pdf_viewer_view.py
import os
import fitz  # PyMuPDF
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QScrollArea, QMessageBox, QDialog, QSizePolicy)
from PyQt6.QtGui import QPixmap, QImage, QPalette, QColor
from PyQt6.QtCore import Qt, pyqtSignal

# Correct relative import from views to core
from ..core.base_dialog import BaseDialog

class PdfViewerView(BaseDialog):
    """
    PDF 查看器视图对话框。
    继承自 BaseDialog。
    """
    # Signal emitted when user requests conversion to HTML
    convert_to_html_signal = pyqtSignal(str)

    def __init__(self, pdf_path, parent=None):
        self.pdf_path = pdf_path
        self.pdf_document = None
        self.current_page = 0
        self.total_pages = 0
        # self.page_images = [] # Not currently used, can be removed or used for caching
        super().__init__(parent) # Calls _init_dialog_ui, _connect_dialog_signals, _apply_dialog_theme
        self.load_pdf() # Load PDF after UI is initialized

    def _init_dialog_ui(self):
        """初始化 PDF 查看器 UI"""
        self.setWindowTitle(f"PDF预览 - {os.path.basename(self.pdf_path)}")
        self.resize(800, 700) # Adjust initial size

        # Main layout is already created in BaseDialog (self.main_layout)
        self.main_layout.setSpacing(5)

        # Scroll Area for PDF pages
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("PdfScrollArea")
        self.scroll_content = QWidget() # Content widget for the scroll area
        self.scroll_layout = QVBoxLayout(self.scroll_content) # Layout for the content widget
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignCenter) # Center pages
        self.scroll_content.setLayout(self.scroll_layout)
        self.scroll_area.setWidget(self.scroll_content)
        self.scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Page display label (inside scroll area)
        self.image_display_label = QLabel("正在加载 PDF...") # Placeholder label
        self.image_display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_display_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored) # Allow scaling
        self.image_display_label.setScaledContents(True) # Scale pixmap
        self.scroll_layout.addWidget(self.image_display_label)

        # Navigation and Controls Layout
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)

        self.prev_button = QPushButton("上一页")
        self.page_label = QLabel("页码") # Placeholder
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.next_button = QPushButton("下一页")
        self.convert_button = QPushButton("转换为HTML")

        controls_layout.addWidget(self.prev_button)
        controls_layout.addStretch()
        controls_layout.addWidget(self.page_label)
        controls_layout.addStretch()
        controls_layout.addWidget(self.next_button)
        controls_layout.addStretch(2) # More space before convert button
        controls_layout.addWidget(self.convert_button)

        # Add components to the main layout provided by BaseDialog
        self.main_layout.addWidget(self.scroll_area, 1) # Scroll area takes most space
        self.main_layout.addLayout(controls_layout)

    def _connect_dialog_signals(self):
        """连接信号与槽"""
        self.prev_button.clicked.connect(self.prev_page)
        self.next_button.clicked.connect(self.next_page)
        self.convert_button.clicked.connect(self._emit_convert_signal)

    def _apply_dialog_theme(self):
        """应用主题样式"""
        self.update_styles(is_dark=False) # Default light

    def update_styles(self, is_dark: bool):
        """根据主题更新样式"""
        bg_color = "#1e1e1e" if is_dark else "#ffffff"
        text_color = "#f0f0f0" if is_dark else "#2c3e50"
        border_color = "#555555" if is_dark else "#cccccc"
        button_bg = "#555" if is_dark else "#f0f0f0"
        button_text = text_color
        scroll_bg = "#2d2d2d" if is_dark else "#f8f8f8" # Slightly different scroll bg

        # Apply to dialog background (might be handled by BaseDialog)
        # palette = self.palette()
        # palette.setColor(QPalette.ColorRole.Window, QColor(bg_color))
        # self.setPalette(palette)

        self.scroll_area.setStyleSheet(f"""
            QScrollArea#PdfScrollArea {{
                background-color: {scroll_bg};
                border: 1px solid {border_color};
                border-radius: 4px;
            }}
        """)
        # Style the content widget background if needed
        self.scroll_content.setStyleSheet(f"background-color: {scroll_bg};")
        self.page_label.setStyleSheet(f"color: {text_color}; background: transparent;")

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
            QPushButton:disabled {{
                background-color: {"#444" if is_dark else "#e0e0e0"};
                color: {"#888" if is_dark else "#a0a0a0"};
                border-color: {"#666" if is_dark else "#d0d0d0"};
            }}
        """
        self.prev_button.setStyleSheet(button_style)
        self.next_button.setStyleSheet(button_style)
        self.convert_button.setStyleSheet(button_style)


    # --- PDF Loading and Navigation ---
    def load_pdf(self):
        """Loads the PDF document."""
        if not self.pdf_path or not os.path.exists(self.pdf_path):
             QMessageBox.critical(self, "错误", f"PDF 文件路径无效或文件不存在:\n{self.pdf_path}")
             self.image_display_label.setText("无法加载 PDF")
             self._update_button_states() # Disable buttons
             return
        try:
            self.pdf_document = fitz.open(self.pdf_path)
            self.total_pages = len(self.pdf_document)
            if self.total_pages > 0:
                self.current_page = 0
                self.show_page(self.current_page)
            else:
                self.image_display_label.setText("PDF 文件为空")
                QMessageBox.warning(self, "警告", "PDF 文件没有页面。")
            self._update_button_states()
            self.update_page_label()
        except Exception as e:
            self.image_display_label.setText(f"加载 PDF 时出错:\n{e}")
            QMessageBox.critical(self, "错误", f"无法加载 PDF 文件:\n{e}")
            self.pdf_document = None
            self.total_pages = 0
            self._update_button_states()
            self.update_page_label()

    def show_page(self, page_num):
        """Renders and displays the specified PDF page."""
        if not self.pdf_document or not (0 <= page_num < self.total_pages):
            return

        try:
            page = self.pdf_document.load_page(page_num)
            # Adjust zoom factor as needed (e.g., based on window size or user control)
            zoom = 1.5
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False) # alpha=False for QImage format

            # Convert to QImage
            if pix.alpha: # Format_RGBA8888
                 img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGBA8888)
            else: # Format_RGB888
                 img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)

            if img.isNull():
                 self.image_display_label.setText(f"无法渲染第 {page_num + 1} 页")
                 return

            pixmap = QPixmap.fromImage(img)
            self.image_display_label.setPixmap(pixmap)

            self.current_page = page_num
            self.update_page_label()
            self._update_button_states()

            # Scroll to top after loading new page
            self.scroll_area.verticalScrollBar().setValue(0)

        except Exception as e:
            self.image_display_label.setText(f"渲染第 {page_num + 1} 页时出错:\n{e}")
            print(f"Error rendering page {page_num}: {e}")
            self._update_button_states() # Update buttons even on error

    def update_page_label(self):
        """Updates the page number display label."""
        if self.total_pages > 0:
            self.page_label.setText(f"第 {self.current_page + 1} / {self.total_pages} 页")
        else:
            self.page_label.setText("无页面")

    def _update_button_states(self):
        """Enables/disables navigation buttons based on current page."""
        has_doc = self.pdf_document is not None and self.total_pages > 0
        self.prev_button.setEnabled(has_doc and self.current_page > 0)
        self.next_button.setEnabled(has_doc and self.current_page < self.total_pages - 1)
        self.convert_button.setEnabled(has_doc) # Enable convert if document loaded

    def prev_page(self):
        """Shows the previous page."""
        if self.current_page > 0:
            self.show_page(self.current_page - 1)

    def next_page(self):
        """Shows the next page."""
        if self.current_page < self.total_pages - 1:
            self.show_page(self.current_page + 1)

    def _emit_convert_signal(self):
        """Emits the convert signal and closes the dialog."""
        if self.pdf_path:
            self.convert_to_html_signal.emit(self.pdf_path)
        self.accept() # Close the dialog after emitting

    def closeEvent(self, event):
        """Cleans up the PDF document when the dialog is closed."""
        if self.pdf_document:
            try:
                self.pdf_document.close()
                self.pdf_document = None
            except Exception as e:
                print(f"关闭 PDF 文档时出错: {e}")
        super().closeEvent(event)
