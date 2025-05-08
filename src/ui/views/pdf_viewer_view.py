# src/ui/views/pdf_viewer_view.py
import os
import sys
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QMessageBox, QApplication
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl, Qt, pyqtSignal

# Correct relative import from views to core or utils if needed
# from ..core.base_widget import BaseWidget # Assuming BaseWidget is a QWidget suitable for tabs

class PdfViewerView(QWidget): # Changed from BaseDialog to QWidget
    """
    PDF 查看器视图。
    使用 QWebEngineView 在标签页中嵌入显示 PDF 文件。
    """
    # htmlGenerated signal is removed as this view now focuses on direct PDF display.
    # If PDF-to-HTML source is still needed, it should be a separate action/utility.

    def __init__(self, parent=None): # pdf_path removed from constructor, will be passed to load_pdf
        super().__init__(parent)
        self.pdf_path = None
        
        self.web_view = QWebEngineView(self)
        
        layout = QVBoxLayout(self)
        layout.addWidget(self.web_view)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # Enable PDF viewer plugin in QWebEngineView
        self.web_view.settings().setAttribute(self.web_view.settings().WebAttribute.PluginsEnabled, True)
        self.web_view.settings().setAttribute(self.web_view.settings().WebAttribute.PdfViewerEnabled, True)
        
        # print(f"PdfViewerView (QWebEngineView based) initialized. Instance: {id(self)}")

    def load_pdf(self, pdf_path: str) -> bool:
        """
        加载指定的 PDF 文件到 QWebEngineView 中。
        """
        self.pdf_path = pdf_path
        if not self.pdf_path or not os.path.exists(self.pdf_path):
            QMessageBox.critical(self, "错误", f"PDF 文件路径无效或文件不存在:\n{self.pdf_path}")
            # print(f"Error: PDF file path invalid or not found: {self.pdf_path}")
            return False
        
        try:
            pdf_url = QUrl.fromLocalFile(self.pdf_path)
            self.web_view.setUrl(pdf_url)
            # print(f"PdfViewerView: Loading PDF {self.pdf_path} into QWebEngineView. URL: {pdf_url.toString()}")
            return True
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载 PDF 文件时出错:\n{e}")
            # print(f"Error loading PDF into QWebEngineView: {e}")
            return False

    def cleanup(self):
        """清理资源（如果需要）。"""
        self.web_view.stop()
        self.web_view.setUrl(QUrl("")) # Clear the view
        # print(f"PdfViewerView cleanup for {self.pdf_path}. Instance: {id(self)}")

    def closeEvent(self, event):
        """处理关闭事件（如果作为独立窗口，但现在是QWidget）。"""
        self.cleanup()
        super().closeEvent(event)

# Minimal __main__ for testing this QWidget if needed
if __name__ == '__main__':
    app = QApplication.instance() 
    if app is None:
        app = QApplication(sys.argv)
    
    # Create a dummy window to host the PdfViewerView widget
    main_win = QWidget()
    main_win.setWindowTitle("PDF Viewer Widget Test")
    main_win.setGeometry(100, 100, 800, 600)
    
    viewer_widget = PdfViewerView(main_win) # Create instance
    
    # Example: Load a test PDF. Replace with an actual PDF path for testing.
    # test_pdf = "path/to/your/test.pdf"
    # if os.path.exists(test_pdf):
    #    viewer_widget.load_pdf(test_pdf)
    # else:
    #    QMessageBox.information(main_win, "Test File Missing", f"Test PDF not found: {test_pdf}")

    # Add a button to test loading
    from PyQt6.QtWidgets import QPushButton, QFileDialog
    btn = QPushButton("Open PDF File", main_win)
    
    vbox = QVBoxLayout(main_win)
    vbox.addWidget(btn)
    vbox.addWidget(viewer_widget) # Add viewer widget to layout
    main_win.setLayout(vbox)

    def open_test_pdf():
        file_path, _ = QFileDialog.getOpenFileName(main_win, "Select PDF File", "", "PDF Files (*.pdf)")
        if file_path:
            if not viewer_widget.load_pdf(file_path):
                print(f"Failed to load PDF: {file_path}")
    
    btn.clicked.connect(open_test_pdf)
    
    main_win.show()
    sys.exit(app.exec())
