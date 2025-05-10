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
        self.pdf_conversion_temp_dir = None # To store the path of the directory containing HTML and its resources

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
                from ...utils.pdf_utils import extract_pdf_content
                
                # extract_pdf_content now returns (full_html_path_to_load, resource_base_dir_path)
                full_html_path_to_load, resource_base_dir_path = extract_pdf_content(self.temp_pdf_path)
                self.pdf_conversion_temp_dir = resource_base_dir_path # Store for cleanup

                if full_html_path_to_load and os.path.exists(full_html_path_to_load):
                    print(f"DEBUG OfficeViewerWidget: Loading HTML from file: {full_html_path_to_load}")
                    self.web_view.load(QUrl.fromLocalFile(full_html_path_to_load))
                else:
                    error_msg = f"生成HTML文件失败或未找到: {full_html_path_to_load}"
                    print(f"ERROR OfficeViewerWidget: {error_msg}")
                    QMessageBox.critical(self, "HTML预览错误", error_msg)
                    # Clean up the potentially empty or problematic resource_base_dir_path
                    if resource_base_dir_path and os.path.isdir(resource_base_dir_path):
                        try:
                            shutil.rmtree(resource_base_dir_path)
                        except Exception as e_shutil:
                            print(f"Error cleaning up resource_base_dir_path on load failure: {e_shutil}")
                    self.pdf_conversion_temp_dir = None # Nullify as it's cleaned or invalid
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
            if doc:
                try:
                    doc.Close(SaveChanges=0) 
                except Exception as e_close:
                    print(f"Error closing Office document: {e_close}")
            if office_app:
                try:
                    office_app.Quit()
                except Exception as e_quit:
                    print(f"Error quitting Office application: {e_quit}")
            pythoncom.CoUninitialize()
            doc = None 
            office_app = None

    def _cleanup_temp_files(self): 
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
        
        # Cleanup the directory holding PDF conversion HTML and resources
        if self.pdf_conversion_temp_dir and os.path.exists(self.pdf_conversion_temp_dir):
            try:
                # shutil.rmtree is needed for directories
                import shutil 
                shutil.rmtree(self.pdf_conversion_temp_dir)
                print(f"DEBUG OfficeViewerWidget: Cleaned up PDF conversion temp dir: {self.pdf_conversion_temp_dir}")
                self.pdf_conversion_temp_dir = None
            except Exception as e:
                print(f"Error deleting PDF conversion temp dir '{self.pdf_conversion_temp_dir}': {e}")
        elif self.pdf_conversion_temp_dir:
            self.pdf_conversion_temp_dir = None


    def cleanup(self):
        self.web_view.stop() 
        self.web_view.setUrl(QUrl("")) 
        self._cleanup_temp_files() 

    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)

if __name__ == '__main__':
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
                # Test HTML preview
                if not viewer.loadFile(file_path, preview_format='html'):
                    print(f"Failed to load and convert {file_path} to HTML")
        
        btn.clicked.connect(open_test_file)
        
        main_win.show()
        sys.exit(app.exec())
    else:
        if sys.platform != 'win32':
            print("This test is Windows-specific because it uses COM automation.")
        elif not WIN32_AVAILABLE:
            print("pywin32 module is not available. Cannot run the test.")
