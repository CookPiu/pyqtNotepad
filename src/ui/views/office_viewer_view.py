import sys
import os
import tempfile
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QMessageBox, QApplication
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl, Qt, QLoggingCategory

# Suppress QWebEngineView context menu INFO messages if they are noisy
# QLoggingCategory.setFilterRules("qt.webenginecontextmenu.info=false")

if sys.platform == 'win32':
    try:
        import win32com.client
        import pythoncom
        WIN32_AVAILABLE = True
    except ImportError:
        WIN32_AVAILABLE = False
else:
    WIN32_AVAILABLE = False

# Office SaveAs PDF constants
WD_FORMAT_PDF = 17
XL_TYPE_PDF = 0
PPT_SAVE_AS_PDF = 32

class OfficeViewerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.web_view = QWebEngineView(self)
        self.temp_pdf_path = None

        layout = QVBoxLayout(self)
        layout.addWidget(self.web_view)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # Basic PDF viewer settings (optional)
        self.web_view.settings().setAttribute(self.web_view.settings().WebAttribute.PluginsEnabled, True)
        self.web_view.settings().setAttribute(self.web_view.settings().WebAttribute.PdfViewerEnabled, True)

    def loadFile(self, office_file_path: str) -> bool:
        if not WIN32_AVAILABLE:
            QMessageBox.critical(self, "错误", "pywin32 模块未找到，无法执行 Office 文件转换。")
            return False

        if not os.path.exists(office_file_path):
            QMessageBox.critical(self, "错误", f"文件不存在: {office_file_path}")
            return False

        file_extension = os.path.splitext(office_file_path)[1].lower()
        app_dispatch_name = None
        save_format_const = None
        office_app = None
        doc = None

        try:
            # Initialize COM for this thread
            pythoncom.CoInitialize()

            # Create a temporary file for the PDF
            # Suffix is important for QWebEngineView to recognize it as PDF
            # delete=False because Office will write to this path, we delete it manually in cleanup.
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmpfile:
                self.temp_pdf_path = tmpfile.name
            
            abs_office_file_path = os.path.abspath(office_file_path)

            if file_extension == ".docx" or file_extension == ".doc":
                app_dispatch_name = "Word.Application"
                save_format_const = WD_FORMAT_PDF
                office_app = win32com.client.Dispatch(app_dispatch_name)
                office_app.Visible = False # Run in background
                doc = office_app.Documents.Open(abs_office_file_path, ReadOnly=True)
                doc.SaveAs(self.temp_pdf_path, FileFormat=save_format_const)

            elif file_extension == ".xlsx" or file_extension == ".xls":
                app_dispatch_name = "Excel.Application"
                save_format_const = XL_TYPE_PDF # This is Type for ExportAsFixedFormat
                office_app = win32com.client.Dispatch(app_dispatch_name)
                office_app.Visible = False # Run in background
                doc = office_app.Workbooks.Open(abs_office_file_path, ReadOnly=True)
                doc.ExportAsFixedFormat(Type=save_format_const, Filename=self.temp_pdf_path)
                
            elif file_extension == ".pptx" or file_extension == ".ppt":
                app_dispatch_name = "PowerPoint.Application"
                save_format_const = PPT_SAVE_AS_PDF
                office_app = win32com.client.Dispatch(app_dispatch_name)
                # PowerPoint might not have a simple Visible=False, or it might behave differently.
                # office_app.Visible = False # May or may not work as expected
                doc = office_app.Presentations.Open(abs_office_file_path, ReadOnly=True, WithWindow=False)
                doc.SaveAs(self.temp_pdf_path, FileFormat=save_format_const)

            else:
                QMessageBox.warning(self, "不支持的文件", f"不支持的文件类型: {file_extension} 进行PDF转换。")
                self._cleanup_temp_file() # Clean up if temp file was created but not used
                return False

            self.web_view.setUrl(QUrl.fromLocalFile(self.temp_pdf_path))
            return True

        except pythoncom.com_error as e:
            QMessageBox.critical(self, "COM 错误", f"与 Microsoft Office 交互时发生错误 (COM Error):\n{str(e)}\n请确保已安装 Microsoft Office 并且文件未损坏。")
            self._cleanup_temp_file()
            return False
        except Exception as e:
            QMessageBox.critical(self, "转换错误", f"将文件 '{os.path.basename(office_file_path)}' 转换为 PDF 时发生错误:\n{str(e)}")
            self._cleanup_temp_file()
            return False
        finally:
            if doc:
                try:
                    doc.Close(SaveChanges=0) # 0 for wdDoNotSaveChanges or equivalent
                except Exception as e_close:
                    print(f"Error closing Office document: {e_close}")
            if office_app:
                try:
                    office_app.Quit()
                except Exception as e_quit:
                    print(f"Error quitting Office application: {e_quit}")
            # Uninitialize COM
            pythoncom.CoUninitialize()
            # Release COM objects (good practice, though Python's GC + comtypes usually handles it)
            doc = None
            office_app = None


    def _cleanup_temp_file(self):
        if self.temp_pdf_path and os.path.exists(self.temp_pdf_path):
            try:
                os.remove(self.temp_pdf_path)
                # print(f"Temporary PDF file deleted: {self.temp_pdf_path}") # For debugging
                self.temp_pdf_path = None
            except OSError as e:
                print(f"Error deleting temporary PDF file '{self.temp_pdf_path}': {e}")
        elif self.temp_pdf_path: # Path exists but file doesn't, just clear path
             self.temp_pdf_path = None


    def cleanup(self):
        """Called when the tab/widget is being closed."""
        self.web_view.stop() # Stop any loading
        self.web_view.setUrl(QUrl("")) # Clear the view
        self._cleanup_temp_file()
        # print("OfficeViewerWidget cleanup called.") # For debugging

    def closeEvent(self, event):
        """Handle widget close event."""
        self.cleanup()
        super().closeEvent(event)

if __name__ == '__main__':
    # This is a simple test application for OfficeViewerWidget (PDF conversion)
    if sys.platform == 'win32' and WIN32_AVAILABLE:
        app = QApplication(sys.argv)
        
        main_win = QWidget()
        main_win.setWindowTitle("Office to PDF Viewer Test")
        main_win.setGeometry(100, 100, 800, 600)
        
        viewer = OfficeViewerWidget(main_win)
        
        from PyQt6.QtWidgets import QPushButton, QFileDialog
        btn = QPushButton("Open Office File for PDF Conversion", main_win)
        
        vbox = QVBoxLayout(main_win)
        vbox.addWidget(btn)
        vbox.addWidget(viewer)
        main_win.setLayout(vbox)

        def open_test_file():
            file_path, _ = QFileDialog.getOpenFileName(main_win, "Select Office File", "", 
                                                       "Office Files (*.docx *.doc *.xlsx *.xls *.pptx *.ppt)")
            if file_path:
                if not viewer.loadFile(file_path):
                    print(f"Failed to load and convert {file_path}")
        
        btn.clicked.connect(open_test_file)
        
        main_win.show()
        sys.exit(app.exec())
    else:
        if sys.platform != 'win32':
            print("This test is Windows-specific because it uses COM automation.")
        elif not WIN32_AVAILABLE:
            print("pywin32 module is not available. Cannot run the test.")
