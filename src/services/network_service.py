import traceback
from PyQt6.QtCore import QObject, pyqtSignal, QUrl
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply, QNetworkRequest # Added QNetworkRequest again for RedirectPolicy

class NetworkService(QObject):
    html_fetched = pyqtSignal(str, str) # url, html_content
    fetch_error = pyqtSignal(str, str)  # url, error_message

    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = QNetworkAccessManager(self)
        self.manager.finished.connect(self._handle_finished)
        self._active_requests = {} # To store QNetworkReply objects by URL

    def fetch_html(self, url_string: str):
        if not url_string:
            self.fetch_error.emit(url_string, "URL为空。")
            return

        q_url = QUrl(url_string)
        if not q_url.isValid():
            self.fetch_error.emit(url_string, f"无效的URL格式: {url_string}")
            return

        try:
            print(f"NetworkService: Fetching HTML from {url_string}")
            request = QNetworkRequest(q_url)
            # Set a user-agent to mimic a browser, some sites might block default Qt agent
            request.setHeader(QNetworkRequest.KnownHeaders.UserAgentHeader, 
                              "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36")
            # Corrected FollowRedirects attribute again based on new feedback
            request.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute, QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy)
            
            reply = self.manager.get(request)
            self._active_requests[url_string] = reply # Store reply to identify it later
        except Exception as e:
            error_msg = f"发起网络请求时出错: {url_string}\n{traceback.format_exc()}"
            print(error_msg)
            self.fetch_error.emit(url_string, str(e))


    def _handle_finished(self, reply: QNetworkReply):
        original_url = reply.request().url().toString()
        
        # Remove the reply from active requests now that it's finished
        if original_url in self._active_requests:
            del self._active_requests[original_url]
        else:
            # This might happen if the URL changed due to redirects and we didn't track the original
            # For now, we'll try to use the final URL from the reply
            print(f"Warning: Reply URL {original_url} not found in active requests. This might be due to a redirect not tracked by original key.")


        if reply.error() == QNetworkReply.NetworkError.NoError:
            try:
                # Try to decode with UTF-8 first, then with a common fallback like ISO-8859-1 or windows-1252
                # More robust charset detection might be needed for a wider range of sites
                html_bytes = reply.readAll()
                try:
                    html_content = str(html_bytes, 'utf-8')
                except UnicodeDecodeError:
                    try:
                        html_content = str(html_bytes, 'iso-8859-1') # Common fallback
                    except UnicodeDecodeError:
                        html_content = str(html_bytes, 'windows-1252') # Another common fallback
                
                print(f"NetworkService: Successfully fetched HTML from {original_url} (length: {len(html_content)})")
                self.html_fetched.emit(original_url, html_content)
            except Exception as e:
                error_msg = f"读取或解码响应内容时出错: {original_url}\n{traceback.format_exc()}"
                print(error_msg)
                self.fetch_error.emit(original_url, f"读取响应内容错误: {e}")
        else:
            error_string = reply.errorString()
            status_code_attribute = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
            status_code = status_code_attribute if status_code_attribute is not None else "N/A"
            
            error_msg = f"网络错误 (状态码: {status_code}): {error_string} - URL: {original_url}"
            print(error_msg)
            self.fetch_error.emit(original_url, error_msg)
        
        reply.deleteLater()

    def __del__(self):
        # Clean up any pending requests if the service is deleted
        for url_str, reply_obj in list(self._active_requests.items()): # Iterate over a copy
            if reply_obj and not reply_obj.isFinished():
                print(f"NetworkService: Aborting pending request for {url_str} during deletion.")
                reply_obj.abort()
        self._active_requests.clear()

if __name__ == '__main__':
    from PyQt6.QtWidgets import QApplication, QTextEdit, QVBoxLayout, QWidget, QPushButton, QLineEdit
    from PyQt6.QtCore import QCoreApplication # Use QCoreApplication for non-GUI test if possible

    # Minimal app to test the service
    # app = QCoreApplication(sys.argv) # Use QCoreApplication if no GUI elements are shown directly
    app = QApplication([]) # Use QApplication if any widget will be shown or for full event loop

    class TestWidget(QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("NetworkService Test")
            layout = QVBoxLayout(self)
            self.url_input = QLineEdit("https://www.example.com")
            self.fetch_button = QPushButton("Fetch HTML")
            self.result_display = QTextEdit()
            self.result_display.setReadOnly(True)
            
            layout.addWidget(QLabel("Enter URL:"))
            layout.addWidget(self.url_input)
            layout.addWidget(self.fetch_button)
            layout.addWidget(self.result_display)
            self.setLayout(layout)

            self.network_service = NetworkService()
            self.fetch_button.clicked.connect(self.do_fetch)
            self.network_service.html_fetched.connect(self.on_html_ready)
            self.network_service.fetch_error.connect(self.on_fetch_error)

        def do_fetch(self):
            url = self.url_input.text()
            self.result_display.setPlainText(f"Fetching {url}...")
            self.network_service.fetch_html(url)

        def on_html_ready(self, url, html):
            self.result_display.setPlainText(f"Fetched from {url}:\n\n{html[:1000]}...") # Display first 1000 chars

        def on_fetch_error(self, url, error_msg):
            self.result_display.setPlainText(f"Error fetching {url}:\n{error_msg}")

    widget = TestWidget()
    widget.show()
    
    # For non-GUI test with QCoreApplication, use QTimer to exit after some time
    # QTimer.singleShot(10000, app.quit) # Exit after 10 seconds
    
    app.exec() # Use app.exec() for QApplication
