# src/ui/dialogs/pdf_action_dialog.py
import os
import sys
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QMessageBox, QSizePolicy, QDialogButtonBox, QApplication)
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt, QSize

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

# Assuming BaseDialog is in src/ui/core
# If BaseDialog is not strictly necessary, QDialog can be used directly.
# For now, let's use QDialog as a base for simplicity unless BaseDialog provides essential common features.
from ..core.base_dialog import BaseDialog # Let's assume BaseDialog exists and is QDialog based

class PdfActionChoiceDialog(BaseDialog): # Or QDialog if BaseDialog is not suitable/available
    # Define constants for dialog results for clarity
    PREVIEW_AS_PDF_IN_TAB = 1
    CONVERT_TO_HTML_SOURCE = 2
    ACTION_CANCELLED = 0

    def __init__(self, pdf_path, parent=None):
        self.pdf_path = pdf_path
        self.action_choice = self.ACTION_CANCELLED # Default to cancelled
        super().__init__(parent)
        # _init_dialog_ui is called by BaseDialog's constructor

    def _init_dialog_ui(self):
        self.setWindowTitle("PDF 操作选择")
        self.setMinimumSize(400, 300) # Adjust as needed

        # Main layout is self.main_layout from BaseDialog (QVBoxLayout)
        
        # Image Preview Label
        self.preview_image_label = QLabel("正在加载预览...")
        self.preview_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_image_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.preview_image_label.setScaledContents(False) # We will scale pixmap manually
        self.preview_image_label.setMinimumHeight(200) # Ensure some space for preview
        self.main_layout.addWidget(self.preview_image_label)

        self._load_first_page_preview()

        # Buttons
        self.btn_preview_pdf_in_tab = QPushButton("在标签页中预览 PDF")
        self.btn_convert_to_html = QPushButton("转换为 HTML 源码")
        
        # Using QDialogButtonBox for standard button layout and roles
        self.button_box = QDialogButtonBox()
        self.button_box.addButton(self.btn_preview_pdf_in_tab, QDialogButtonBox.ButtonRole.AcceptRole)
        self.button_box.addButton(self.btn_convert_to_html, QDialogButtonBox.ButtonRole.ActionRole)
        self.button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        
        self.main_layout.addWidget(self.button_box)

    def _connect_dialog_signals(self):
        self.btn_preview_pdf_in_tab.clicked.connect(self._on_preview_pdf_in_tab)
        self.btn_convert_to_html.clicked.connect(self._on_convert_to_html)
        self.button_box.rejected.connect(self.reject) # For Cancel button

    def _apply_dialog_theme(self):
        # Placeholder for theme application if BaseDialog doesn't handle it
        # or if specific styling is needed.
        pass

    def _load_first_page_preview(self):
        if not PYMUPDF_AVAILABLE:
            self.preview_image_label.setText("错误: PyMuPDF (fitz) 模块未安装。\n无法显示预览。")
            QMessageBox.critical(self, "依赖缺失", "PyMuPDF (fitz) 模块未安装，无法生成 PDF 页面预览。")
            return

        if not self.pdf_path or not os.path.exists(self.pdf_path):
            self.preview_image_label.setText("错误: PDF 文件无效。")
            return

        try:
            doc = fitz.open(self.pdf_path)
            if len(doc) > 0:
                page = doc.load_page(0) # Load first page
                
                # Render pixmap - adjust zoom for dialog preview size
                # Let's aim for a preview image width of around 300-350px
                target_width = 350 
                zoom_x = target_width / page.rect.width if page.rect.width > 0 else 1
                zoom_y = zoom_x # Maintain aspect ratio
                mat = fitz.Matrix(zoom_x, zoom_y)
                
                pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB, alpha=False)
                img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
                if not img.isNull():
                    pixmap = QPixmap.fromImage(img)
                    # Scale it to fit the label while maintaining aspect ratio
                    # self.preview_image_label.setPixmap(pixmap.scaled(
                    #     self.preview_image_label.size(), # Use label's current size as hint
                    #     Qt.AspectRatioMode.KeepAspectRatio,
                    #     Qt.TransformationMode.SmoothTransformation
                    # ))
                    self.preview_image_label.setPixmap(pixmap) # Let label handle scaling if setScaledContents(True)
                                                              # Or set fixed size for label and scale pixmap to fit
                else:
                    self.preview_image_label.setText("无法渲染 PDF 预览图像。")
            else:
                self.preview_image_label.setText("PDF 文件为空，无页面可预览。")
            doc.close()
        except Exception as e:
            self.preview_image_label.setText(f"加载 PDF 预览时出错:\n{e}")
            print(f"Error loading PDF preview for dialog: {e}")

    def _on_preview_pdf_in_tab(self):
        self.action_choice = self.PREVIEW_AS_PDF_IN_TAB
        self.accept() # Close dialog and signal acceptance

    def _on_convert_to_html(self):
        self.action_choice = self.CONVERT_TO_HTML_SOURCE
        self.accept()

    # Override exec() to return the custom choice enum
    def exec(self) -> int: # Changed from exec_ to exec to match QDialog
        super().exec() # Call QDialog.exec()
        return self.action_choice

if __name__ == '__main__':
    # Test for PdfActionChoiceDialog
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    # Create a dummy PDF for testing if it doesn't exist
    dummy_pdf_for_dialog_test = "dummy_dialog_test.pdf"
    if not os.path.exists(dummy_pdf_for_dialog_test):
        if PYMUPDF_AVAILABLE:
            try:
                doc = fitz.open()
                page = doc.new_page()
                page.insert_text((50, 72), "Test PDF for Action Choice Dialog")
                doc.save(dummy_pdf_for_dialog_test)
                doc.close()
            except Exception as e:
                print(f"Could not create dummy PDF for dialog test: {e}")
        else:
            print("PyMuPDF not available, cannot create dummy PDF for dialog test.")
            
    if os.path.exists(dummy_pdf_for_dialog_test):
        dialog = PdfActionChoiceDialog(dummy_pdf_for_dialog_test)
        choice = dialog.exec()

        if choice == PdfActionChoiceDialog.PREVIEW_AS_PDF_IN_TAB:
            print("User chose: Preview PDF in Tab")
        elif choice == PdfActionChoiceDialog.CONVERT_TO_HTML_SOURCE:
            print("User chose: Convert to HTML Source")
        else: # ACTION_CANCELLED or dialog closed
            print("User cancelled or closed the dialog.")
    else:
        QMessageBox.critical(None, "Test Error", f"Dummy PDF '{dummy_pdf_for_dialog_test}' not found or could not be created.")

    # sys.exit(app.exec()) # Not needed if just testing dialog logic
