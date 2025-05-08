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
        self.temp_html_content_path = None # For storing path to a temp HTML file if setHtml with base URL is problematic

    def loadFile(self, office_file_path: str, preview_format: str = 'pdf') -> bool: # Added preview_format
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

            # Create a temporary file for the PDF (still needed as intermediate for HTML conversion)
            # Suffix is important. delete=False because Office writes to it.
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmpfile_pdf:
                self.temp_pdf_path = tmpfile_pdf.name
            
            abs_office_file_path = os.path.abspath(office_file_path)

            # Step 1: Convert Office to PDF
            if file_extension == ".docx" or file_extension == ".doc":
                app_dispatch_name = "Word.Application"
                save_format_const = WD_FORMAT_PDF
                office_app = win32com.client.Dispatch(app_dispatch_name)
                office_app.Visible = False
                doc = office_app.Documents.Open(abs_office_file_path, ReadOnly=True)
                doc.SaveAs(self.temp_pdf_path, FileFormat=save_format_const)
            elif file_extension == ".xlsx" or file_extension == ".xls":
                app_dispatch_name = "Excel.Application"
                # save_format_const is not used for Excel's ExportAsFixedFormat's Type argument
                office_app = win32com.client.Dispatch(app_dispatch_name)
                office_app.Visible = False
                doc = office_app.Workbooks.Open(abs_office_file_path, ReadOnly=True)
                doc.ExportAsFixedFormat(Type=XL_TYPE_PDF, Filename=self.temp_pdf_path)
            elif file_extension == ".pptx" or file_extension == ".ppt":
                app_dispatch_name = "PowerPoint.Application"
                save_format_const = PPT_SAVE_AS_PDF
                office_app = win32com.client.Dispatch(app_dispatch_name)
                doc = office_app.Presentations.Open(abs_office_file_path, ReadOnly=True, WithWindow=False)
                doc.SaveAs(self.temp_pdf_path, FileFormat=save_format_const)
            else:
                QMessageBox.warning(self, "不支持的文件", f"不支持的文件类型: {file_extension} 进行转换。")
                self._cleanup_temp_files()
                return False

            # Step 2: Display based on preview_format
            if preview_format == 'pdf':
                self.web_view.setUrl(QUrl.fromLocalFile(self.temp_pdf_path))
            elif preview_format == 'html':
                # Import necessary functions from pdf_utils
                from ...utils.pdf_utils import extract_pdf_content, APPLICATION_ROOT as PDF_UTILS_APP_ROOT
                
                html_content_string = extract_pdf_content(self.temp_pdf_path)
                
                # Option 1: Set HTML directly (preferred if truly self-contained)
                # The APPLICATION_ROOT from pdf_utils might be different if pdf_utils is in a different
                # relative location to the project root than this file.
                # For simplicity, let's assume APPLICATION_ROOT from pdf_utils is suitable.
                # A more robust way might be to pass the project root to setHtml.
                # For now, using a generic local file base URL.
                base_url = QUrl.fromLocalFile(os.path.dirname(abs_office_file_path)) # Base URL of original file's dir
                self.web_view.setHtml(html_content_string, baseUrl=base_url)

                # Option 2: Save HTML to a temp file and load that (if setHtml has issues with complex content/base URLs)
                # with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode='w', encoding='utf-8') as tmpfile_html:
                #     self.temp_html_content_path = tmpfile_html.name
                #     tmpfile_html.write(html_content_string)
                # self.web_view.setUrl(QUrl.fromLocalFile(self.temp_html_content_path))
            else:
                QMessageBox.warning(self, "未知预览格式", f"未知的预览格式: {preview_format}")
                self._cleanup_temp_files()
                return False
            
            return True

        except pythoncom.com_error as e:
            QMessageBox.critical(self, "COM 错误", f"与 Microsoft Office 交互时发生错误 (COM Error):\n{str(e)}\n请确保已安装 Microsoft Office 并且文件未损坏。")
            self._cleanup_temp_files()
            return False
        except ImportError as e_imp: # Catch import error for pdf_utils if it occurs
            QMessageBox.critical(self, "导入错误", f"无法加载必要的预览组件: {e_imp}")
            self._cleanup_temp_files()
            return False
        except Exception as e:
            QMessageBox.critical(self, "转换/加载错误", f"处理文件 '{os.path.basename(office_file_path)}' 时发生错误:\n{str(e)}")
            self._cleanup_temp_files()
            return False
        finally:
            # Close Office doc and Quit app for Office to PDF conversion
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
            # Release COM objects
            doc = None # Ensure they are released
            office_app = None


    def _cleanup_temp_files(self): # Renamed to reflect it might clean more than one
        if self.temp_pdf_path and os.path.exists(self.temp_pdf_path):
            try:
                os.remove(self.temp_pdf_path)
                self.temp_pdf_path = None
            except OSError as e:
                print(f"Error deleting temporary PDF file '{self.temp_pdf_path}': {e}")
        elif self.temp_pdf_path: 
             self.temp_pdf_path = None

        if self.temp_html_content_path and os.path.exists(self.temp_html_content_path):
            try:
                os.remove(self.temp_html_content_path)
                self.temp_html_content_path = None
            except OSError as e:
                print(f"Error deleting temporary HTML file '{self.temp_html_content_path}': {e}")
        elif self.temp_html_content_path:
            self.temp_html_content_path = None


    def cleanup(self):
        """Called when the tab/widget is being closed."""
        self.web_view.stop() 
        self.web_view.setUrl(QUrl("")) 
        self._cleanup_temp_files() # Call the new cleanup method

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
