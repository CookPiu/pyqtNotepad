import os
import base64
import uuid
from PyQt6.QtCore import QObject, pyqtSlot, QUrl, QDir, Qt, pyqtSignal # Added pyqtSignal
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtNetwork import QSslSocket
from PyQt6.QtWidgets import QMenu, QApplication, QMainWindow
from PyQt6.QtGui import QAction


class CustomWebPage(QWebEnginePage):
    """自定义WebPage类，用于处理SSL证书错误"""
    
    def __init__(self, profile, parent=None):
        super().__init__(profile, parent)
        # print(f"SSL支持状态: {QSslSocket.supportsSsl()}")
        # print(f"SSL库版本: {QSslSocket.sslLibraryVersionString()}")
    
    def certificateError(self, error):
        error_code = error.error()
        url = error.url().toString()
        description = error.errorDescription()
        # print(f"SSL证书错误: {description}")
        # print(f"错误码: {error_code}, URL: {url}")
        # print(f"错误类型: {self._get_ssl_error_type(error_code)}")
        error.ignoreCertificateError()
        return True
    
    def _get_ssl_error_type(self, error_code):
        ssl_errors = {
            1: "证书未被信任的机构签名", 2: "证书已过期", 3: "证书尚未生效",
            4: "证书已被吊销", 5: "证书主机名不匹配", 6: "证书无法验证",
            7: "证书包含无效签名", 8: "证书使用了不安全的算法", 9: "证书包含无效数据"
        }
        return ssl_errors.get(error_code, f"未知SSL错误 ({error_code})")


class PyQtBridge(QObject):
    """与wangEditor通信的桥接类"""
    # Signals for content changes and export requests (if needed from JS to Python)
    # contentChangedSignal = pyqtSignal(str) 
    # exportFileSignal = pyqtSignal(str, str)

    def __init__(self, parent=None, upload_dir=None):
        super().__init__(parent)
        self.upload_dir = upload_dir or os.path.join(QDir.currentPath(), "uploads")
        if not os.path.exists(self.upload_dir):
            os.makedirs(self.upload_dir)
        self._current_html_content = "" # Store current HTML content

    @pyqtSlot()
    def editorReady(self):
        print("WangEditor JS: Editor is ready.")
    
    @pyqtSlot(str)
    def onContentChange(self, html_content: str): # Renamed to match JS call
        self._current_html_content = html_content
        # If WangEditor (Python widget) needs to know about this change:
        if hasattr(self.parent(), 'document_modified'): # Assuming parent is WangEditor
             self.parent().document_modified.emit(True)
        # print(f"PyQtBridge: Content changed (first 100): {html_content[:100]}")

    def getCurrentHtml(self) -> str: # Method for Python side to get content
        return self._current_html_content

    @pyqtSlot(str)
    def fileImported(self, filename):
        print(f"WangEditor JS: File imported: {filename}")
    
    @pyqtSlot(str, str) # Changed from single 'content' to 'filename, content'
    def onExportFile(self, filename: str, content: str): # Renamed to match JS call
        # This is if JS initiates export. Python-side export will call getHtml.
        print(f"PyQtBridge: JS requested export. Filename: {filename}")
        # Potentially trigger a Python-side save dialog if needed
        # For now, this might not be used if export is Python-driven.
        if hasattr(self.parent(), '_on_export_file_from_js'): # Assuming parent is WangEditor
            self.parent()._on_export_file_from_js(filename, content)


    @pyqtSlot(str, str, result=bool) # Removed QJSValue, callback is implicitly handled
    def uploadImage(self, base64data, filename, callback): # Callback is still passed
        try:
            if "," in base64data:
                base64data = base64data.split(",", 1)[1]
            image_data = base64.b64decode(base64data)
            if not os.path.exists(self.upload_dir):
                os.makedirs(self.upload_dir)
            
            file_ext = os.path.splitext(filename)[1].lower()
            if not file_ext:
                if image_data.startswith(b'\xff\xd8\xff'): file_ext = '.jpg'
                elif image_data.startswith(b'\x89PNG\r\n'): file_ext = '.png'
                elif image_data.startswith(b'GIF87a') or image_data.startswith(b'GIF89a'): file_ext = '.gif'
                elif image_data.startswith(b'RIFF') and image_data[8:12] == b'WEBP': file_ext = '.webp'
                else: file_ext = '.jpg'
            
            unique_filename = f"{uuid.uuid4().hex}{file_ext}"
            file_path = os.path.join(self.upload_dir, unique_filename)
            
            with open(file_path, "wb") as f: f.write(image_data)
            image_url = QUrl.fromLocalFile(file_path).toString(QUrl.UrlFormattingOption.None_)
            callback.call([image_url])
            print(f"WangEditor: Image uploaded: {file_path}")
            return True
        except Exception as e:
            print(f"WangEditor: Image upload failed: {str(e)}")
            callback.call([None])
            return False


class WangEditor(QWebEngineView):
    """wangEditor编辑器组件"""
    document_modified = pyqtSignal(bool) # For MainWindow to track changes

    def __init__(self, parent=None, upload_dir=None, main_window_ref=None):
        super().__init__(parent)
        self.main_window_ref = main_window_ref 
        self._is_modified_internal = False
        
        self.profile = QWebEngineProfile.defaultProfile()
        self.profile.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        self.profile.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        self.profile.settings().setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True) # Corrected attribute
        
        self.custom_page = CustomWebPage(self.profile, self)
        self.setPage(self.custom_page)
        
        self.channel = QWebChannel(self.page())
        # Pass self (WangEditor instance) as parent to bridge
        self.bridge = PyQtBridge(self, upload_dir) 
        self.channel.registerObject("pyBridge", self.bridge) # Changed from pyqtBridge to pyBridge to match editor.html
        self.page().setWebChannel(self.channel)
        
        self.page().loadFinished.connect(self._on_load_finished)
        
        editor_html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "editor.html")
        self.load(QUrl.fromLocalFile(editor_html_path))

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        main_window = self.main_window_ref 
        if not isinstance(main_window, QMainWindow):
            parent_widget = self.parent()
            while parent_widget:
                if isinstance(parent_widget, QMainWindow):
                    main_window = parent_widget
                    break
                parent_widget = parent_widget.parent()
        
        action_undo = self.page().action(QWebEnginePage.WebAction.Undo); action_undo.setText("撤销"); menu.addAction(action_undo)
        action_redo = self.page().action(QWebEnginePage.WebAction.Redo); action_redo.setText("重做"); menu.addAction(action_redo)
        menu.addSeparator()
        action_cut = self.page().action(QWebEnginePage.WebAction.Cut); action_cut.setText("剪切"); menu.addAction(action_cut)
        action_copy = self.page().action(QWebEnginePage.WebAction.Copy); action_copy.setText("复制"); menu.addAction(action_copy)
        action_paste = self.page().action(QWebEnginePage.WebAction.Paste); action_paste.setText("粘贴"); menu.addAction(action_paste)
        menu.addSeparator()
        action_select_all = self.page().action(QWebEnginePage.WebAction.SelectAll); action_select_all.setText("全选"); menu.addAction(action_select_all)

        has_selection = self.hasSelection()
        if has_selection:
            menu.addSeparator()
            translate_action = menu.addAction("翻译选中内容")
            if main_window and hasattr(main_window, 'translate_selection_wrapper'):
                translate_action.triggered.connect(main_window.translate_selection_wrapper)
            else: translate_action.setEnabled(False)
            
            calc_action = menu.addAction("计算选中内容")
            if main_window and hasattr(main_window, 'calculate_selection_wrapper'):
                calc_action.triggered.connect(main_window.calculate_selection_wrapper)
            else: calc_action.setEnabled(False)
            
            ai_action = menu.addAction("将选中内容复制到 AI 助手")
            if main_window and hasattr(main_window, 'copy_to_ai_wrapper'):
                ai_action.triggered.connect(main_window.copy_to_ai_wrapper)
            else: ai_action.setEnabled(False)

            selected_text_for_url = self.selectedText().strip()
            if selected_text_for_url and (selected_text_for_url.startswith("http://") or selected_text_for_url.startswith("https://")):
                menu.addSeparator()
                fetch_action = menu.addAction("打开并抓取源码(Web视图)")
                if main_window and hasattr(main_window, 'fetch_url_source_wrapper'):
                    fetch_action.triggered.connect(main_window.fetch_url_source_wrapper)
                else: fetch_action.setEnabled(False)
                        
        menu.exec(event.globalPos())
    
    def _on_load_finished(self, success):
        if not success:
            print("WangEditor: HTML load failed.")
            return
        # Ensure WebChannel is initialized from JS side
        # The editor.html should call: new QWebChannel(qt.webChannelTransport, function(channel) { window.pyBridge = channel.objects.pyBridge; ... });
        print("WangEditor: HTML loaded successfully.")
        if hasattr(self, '_pending_initial_html'):
            self.setHtml(self._pending_initial_html)
            del self._pending_initial_html
        self.setModified(False) # Initial content is not a modification

    def setHtml(self, html_content: str):
        if not self.page().url().isValid() or self.page().url().isEmpty(): # Check if page is loaded
            self._pending_initial_html = html_content
            print("WangEditor: Page not loaded, queuing setHtml.")
            return
        # 使用 json.dumps 来更安全地转义文本以注入到 JavaScript 字符串中
        import json
        js_escaped_html = json.dumps(html_content)
        
        # 改为调用 editor.html 中定义的 window.setHtmlContent
        js_code = f"if (window.setHtmlContent) {{ window.setHtmlContent({js_escaped_html}); }} else {{ console.error('JS function setHtmlContent not found.'); }}"
        
        self.page().runJavaScript(js_code)
        # Content change should be signaled by JS via pyBridge.onContentChange -> self.setModified(True)

    def getHtml(self) -> str: # Made synchronous for easier use in FileOperations
        # This relies on pyBridge.onContentChange keeping _current_html_content updated.
        return self.bridge.getCurrentHtml()
    
    def toHtml(self, callback=None): # Kept for compatibility if some old code uses it with callback
        if callback:
            # To make it truly async for callback, we'd need JS to get content and call back.
            # For now, if callback is provided, call it immediately with sync content.
            callback(self.bridge.getCurrentHtml())
        else:
            return self.bridge.getCurrentHtml()

    def isModified(self) -> bool:
        return self._is_modified_internal

    def setModified(self, modified: bool):
        if self._is_modified_internal != modified:
            self._is_modified_internal = modified
            self.document_modified.emit(modified)
            # print(f"WangEditor: Modified state set to {modified}")

    def setUploadDir(self, directory):
        if os.path.exists(directory) and os.path.isdir(directory):
            self.bridge.upload_dir = directory
        else:
            try:
                os.makedirs(directory)
                self.bridge.upload_dir = directory
            except Exception as e:
                print(f"WangEditor: Failed to set upload directory: {str(e)}")

    def _on_export_file_from_js(self, filename_suggestion: str, html_content_to_export: str):
        # This handles export initiated from JS (e.g., an internal button in WangEditor)
        # This is different from MainWindow's File->Export
        from PyQt6.QtWidgets import QFileDialog, QMessageBox # Local import
        from PyQt6.QtCore import QStandardPaths
        from PyQt6.QtGui import QTextDocument

        default_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation) or os.getcwd()
        if not os.path.splitext(filename_suggestion)[1]:
            filename_suggestion += ".html"
        
        save_path_suggestion = os.path.join(default_dir, filename_suggestion)
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, "从编辑器导出文件", save_path_suggestion,
            "HTML 文件 (*.html);;文本文件 (*.txt);;所有文件 (*.*)"
        )

        if file_path:
            content_to_write = html_content_to_export
            if selected_filter == "文本文件 (*.txt)" or file_path.lower().endswith(".txt"):
                doc = QTextDocument()
                doc.setHtml(html_content_to_export)
                content_to_write = doc.toPlainText()
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content_to_write)
                QMessageBox.information(self, "导出成功", f"文件已导出到:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"无法导出文件到 '{file_path}':\n{str(e)}")
