import os
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import (
    QWebEnginePage, 
    QWebEngineSettings, 
    QWebEngineUrlRequestInterceptor,
    QWebEngineProfile,
    QWebEnginePage # Added
)
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWidgets import QSizePolicy, QMenu, QApplication, QMainWindow # Added QMenu, QApplication, QMainWindow
from PyQt6.QtGui import QAction # Added QAction

class HtmlBridge(QObject):
    htmlChanged = pyqtSignal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_html = ""
    @pyqtSlot(str)
    def receiveHtmlFromJs(self, html_content: str):
        self._current_html = html_content
        self.htmlChanged.emit(html_content)
    def getCurrentHtml(self) -> str:
        return self._current_html

class MubuResourceInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, parent=None):
        super().__init__(parent)

    def interceptRequest(self, info):
        url_str = info.requestUrl().toString()
        if "api2.mubu.com" in url_str:
            print(f"MubuResourceInterceptor: Blocking request to {url_str}")
            info.block(True)
        # else:
            # print(f"MubuResourceInterceptor: Allowing request to {url_str}")

class EditableHtmlPreviewWidget(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        page_obj = self.page()
        # It's important to get the profile from the page_obj, not a new default one,
        # if we want settings to apply to this specific page's loading.
        profile = page_obj.profile() 

        # Install the interceptor
        # Ensure the interceptor has a parent or is stored as an instance member
        # to prevent premature garbage collection if profile.setUrlRequestInterceptor
        # doesn't take ownership strongly. Assigning to self should be safe.
        self._mubu_interceptor = MubuResourceInterceptor(self) # Parent it to the widget
        profile.setUrlRequestInterceptor(self._mubu_interceptor)
        
        settings = page_obj.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True) 
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True) # Enable plugins
        settings.setAttribute(QWebEngineSettings.WebAttribute.XSSAuditingEnabled, False) # Try disabling XSS auditing
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True) # Enable WebGL
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True) # Enable 2D Canvas

        self._bridge = HtmlBridge(self)
        self._channel = QWebChannel(page_obj) 
        page_obj.setWebChannel(self._channel)
        self._channel.registerObject("pyBridge", self._bridge)

        self._is_editing_enabled = False 
        self._page_fully_loaded = False # Flag to track if loadFinished has occurred
        self.main_window_ref = parent.main_window if hasattr(parent, 'main_window') else None # Store main_window_ref if parent (HtmlViewContainer) has it

        self.loadStarted.connect(self._on_load_started)
        self.loadProgress.connect(self._on_load_progress)
        self.loadFinished.connect(self._on_load_finished)
        
        # Temporarily comment out the problematic line to allow HTML files to open
        # page_obj.javaScriptConsoleMessage.connect(self._handle_js_console_message)
        print("DEBUG EditableHtmlPreviewWidget: Skipped connecting page_obj.javaScriptConsoleMessage for now.")
        page_obj.certificateError.connect(self._handle_certificate_error)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        # Try to get MainWindow instance from stored ref or by traversing parent
        main_window = self.main_window_ref 
        if not isinstance(main_window, QMainWindow):
            parent_widget = self.parent()
            while parent_widget:
                if isinstance(parent_widget, QMainWindow):
                    main_window = parent_widget
                    break
                # Check if parent_widget has a main_window attribute (like HtmlViewContainer might)
                if hasattr(parent_widget, 'main_window') and isinstance(parent_widget.main_window, QMainWindow):
                    main_window = parent_widget.main_window
                    break
                parent_widget = parent_widget.parent()

        # Standard Web Actions
        action_undo = self.page().action(QWebEnginePage.WebAction.Undo)
        action_undo.setText("撤销")
        menu.addAction(action_undo)

        action_redo = self.page().action(QWebEnginePage.WebAction.Redo)
        action_redo.setText("重做")
        menu.addAction(action_redo)
        
        menu.addSeparator()
        
        action_cut = self.page().action(QWebEnginePage.WebAction.Cut)
        action_cut.setText("剪切")
        menu.addAction(action_cut)
        
        action_copy = self.page().action(QWebEnginePage.WebAction.Copy)
        action_copy.setText("复制")
        menu.addAction(action_copy)
        
        action_paste = self.page().action(QWebEnginePage.WebAction.Paste)
        action_paste.setText("粘贴")
        menu.addAction(action_paste)
        
        menu.addSeparator()
        
        action_select_all = self.page().action(QWebEnginePage.WebAction.SelectAll)
        action_select_all.setText("全选")
        menu.addAction(action_select_all)

        has_selection = self.hasSelection()
        if has_selection:
            menu.addSeparator()
            
            translate_action = menu.addAction("翻译选中内容")
            if main_window and hasattr(main_window, 'translate_selection_wrapper'):
                translate_action.triggered.connect(main_window.translate_selection_wrapper)
            else:
                translate_action.setEnabled(False)
                print("EditableHtmlPreviewWidget: Warning - Could not connect translate to MainWindow wrapper.")

            calc_action = menu.addAction("计算选中内容")
            if main_window and hasattr(main_window, 'calculate_selection_wrapper'):
                calc_action.triggered.connect(main_window.calculate_selection_wrapper)
            else:
                calc_action.setEnabled(False)
                print("EditableHtmlPreviewWidget: Warning - Could not connect calculate to MainWindow wrapper.")

            ai_action = menu.addAction("将选中内容复制到 AI 助手")
            if main_window and hasattr(main_window, 'copy_to_ai_wrapper'):
                ai_action.triggered.connect(main_window.copy_to_ai_wrapper)
            else:
                ai_action.setEnabled(False)
                print("EditableHtmlPreviewWidget: Warning - Could not connect copy_to_ai to MainWindow wrapper.")

            # Add "Fetch URL Source" action
            selected_text_for_url = self.selectedText().strip()
            if selected_text_for_url:
                is_potential_url = selected_text_for_url.startswith("http://") or selected_text_for_url.startswith("https://")
                if is_potential_url:
                    menu.addSeparator()
                    fetch_action = menu.addAction("打开并抓取源码(Web视图)")
                    if main_window and hasattr(main_window, 'fetch_url_source_wrapper'):
                        fetch_action.triggered.connect(main_window.fetch_url_source_wrapper)
                    else:
                        fetch_action.setEnabled(False)
                        print("EditableHtmlPreviewWidget: Warning - Could not connect fetch_url_source to MainWindow wrapper.")

        menu.exec(event.globalPos())

    def _on_load_started(self):
        print("EditableHtmlPreviewWidget: Load started.")
        self._page_fully_loaded = False # Reset on new load start

    def _on_load_progress(self, progress: int):
        print(f"EditableHtmlPreviewWidget: Load progress: {progress}%")

    def _handle_certificate_error(self, error_info):
        print(f"EditableHtmlPreviewWidget: Certificate error for URL {error_info.url().toString()}. Error: {error_info.errorDescription()}")
        error_info.ignoreCertificateError()
        print("EditableHtmlPreviewWidget: Ignored certificate error.")

    def _handle_js_console_message(self, level, message, lineNumber, sourceID):
        level_str = "INFO"
        if level == QWebEnginePage.JavaScriptConsoleMessageLevel.WarningMessageLevel:
            level_str = "WARNING"
        elif level == QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel:
            level_str = "ERROR"
        print(f"JS CONSOLE [{level_str}] ({sourceID}:{lineNumber}): {message}")

    def _on_load_finished(self, success: bool):
        print(f"DEBUG EditableHtmlPreviewWidget: _on_load_finished SIGNAL EMITTED. Success: {success}") # Added explicit signal log
        print(f"EditableHtmlPreviewWidget: _on_load_finished called. Success: {success}")
        
        if not success:
            print("EditableHtmlPreviewWidget: Page load failed. Attempting to enable editing anyway as per user request.")
            # Even if the page technically failed to load (e.g., missing resources),
            # we'll still try to make it editable if that's the desired state.
            # The DOM might be partially available.
            self._page_fully_loaded = True # Consider it "loaded enough" for an edit attempt.
                                         # This might be optimistic but aligns with user wanting to edit despite errors.
        else:
            print("EditableHtmlPreviewWidget: Page load successful.")
            self._page_fully_loaded = True # Mark page as fully loaded
        
        minimal_init_script = r"""
            console.log('EditableHtmlPreviewWidget: Minimal init_script executed in _on_load_finished.');
        """
        # Try to run init script regardless of load success, as basic JS environment might be up.
        self.page().runJavaScript(minimal_init_script)
        
        # Apply editing state regardless of 'success' status, as per trying to edit even with failed resources.
        if self._is_editing_enabled:
            self._execute_enable_editing_js()
        else: 
            # If not explicitly enabled, ensure it's disabled, especially if default is non-editable.
            self._execute_disable_editing_js()

    def _execute_enable_editing_js(self):
        print("DEBUG EditableHtmlPreviewWidget: Attempting to execute JS to enable editing...")
        js_code = r"""
            if (document && document.body) {
                document.body.contentEditable = 'true';
                // document.designMode = 'on'; // Removed designMode
                console.log('document.body.contentEditable set to true via _execute_enable_editing_js.');
            } else {
                console.error('_execute_enable_editing_js: document or document.body not ready for contentEditable.');
            }
        """
        self.page().runJavaScript(js_code)
        print("DEBUG EditableHtmlPreviewWidget: JS to enable editing executed.")

    def _execute_disable_editing_js(self):
        print("DEBUG EditableHtmlPreviewWidget: Attempting to execute JS to disable editing...")
        js_code = r"""
            if (document && document.body) {
                document.body.contentEditable = 'false';
                // document.designMode = 'off'; // Removed designMode
                console.log('document.body.contentEditable set to false via _execute_disable_editing_js.');
            } else {
                console.error('_execute_disable_editing_js: document or document.body not ready for contentEditable.');
            }
        """
        self.page().runJavaScript(js_code)
        print("DEBUG EditableHtmlPreviewWidget: JS to disable editing executed.")

    def setHtml(self, html_content: str, base_url: QUrl = QUrl()):
        effective_base_url = base_url
        if not base_url or base_url.isEmpty() or not base_url.isValid():
            # Try to set a default valid base URL, e.g., project root or a known safe directory
            # Assuming this file is in src/ui/views/
            project_root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
            effective_base_url = QUrl.fromLocalFile(project_root_path)
            print(f"DEBUG EditableHtmlPreviewWidget.setHtml: Original base_url was empty/invalid, using default: {effective_base_url.toString()}")
        
        print(f"DEBUG EditableHtmlPreviewWidget.setHtml: effective_base_url='{effective_base_url.toString()}', content (first 150): {html_content[:150]}")
        self._page_fully_loaded = False 
        super().setHtml(html_content, effective_base_url)

    def getHtml(self, callback=None):
        if callback:
            self.page().toHtml(callback)
        else:
            return self._bridge.getCurrentHtml() 

    def enableEditing(self):
        print(f"DEBUG EditableHtmlPreviewWidget: enableEditing() called. Current _is_editing_enabled: {self._is_editing_enabled}, _page_fully_loaded: {self._page_fully_loaded}")
        self._is_editing_enabled = True
        if self._page_fully_loaded:
            print("DEBUG EditableHtmlPreviewWidget: enableEditing(): page is fully loaded, calling _execute_enable_editing_js now.")
            self._execute_enable_editing_js()
        else:
            print("DEBUG EditableHtmlPreviewWidget: enableEditing(): page not fully loaded yet, _on_load_finished will handle JS execution.")

    def disableEditing(self):
        self._is_editing_enabled = False
        if self._page_fully_loaded:
            self._execute_disable_editing_js()

    def toggleEditing(self):
        if self._is_editing_enabled:
            self.disableEditing()
        else:
            self.enableEditing()
        return self._is_editing_enabled

    def isEditingEnabled(self) -> bool:
        return self._is_editing_enabled

if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget, QPushButton
    # QTimer is needed for the original test code's delayed call, ensure it's imported if used.
    # from PyQt6.QtCore import QTimer 

    class TestApp(QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Editable HTML Preview Test")
            self.setGeometry(100, 100, 800, 600)
            layout = QVBoxLayout(self)
            self.editor_view = EditableHtmlPreviewWidget()
            layout.addWidget(self.editor_view)
            example_html = """<!DOCTYPE html><html><head><title>Test Page</title>
                <style> body { font-family: sans-serif; } h1 { color: navy; } </style></head>
                <body><h1>Hello, World!</h1><p>This is an editable HTML page.</p></body></html>"""
            
            # Set the intention to be editable
            self.editor_view.enableEditing() 
            # Now set HTML, _on_load_finished will apply the editing state
            self.editor_view.setHtml(example_html)
            
            self.toggle_button = QPushButton("Toggle Editing (Python Flag)")
            self.toggle_button.clicked.connect(self.do_toggle_editing)
            layout.addWidget(self.toggle_button)
            self.update_toggle_button_text()

        def do_toggle_editing(self):
            self.editor_view.toggleEditing()
            self.update_toggle_button_text()
            
        def update_toggle_button_text(self):
            state = "ON" if self.editor_view.isEditingEnabled() else "OFF"
            self.toggle_button.setText(f"Toggle Editing (Python Flag: {state})")
            
        # def on_html_changed(self, html): # QWebChannel likely not working
        #     print(f"Python App: HTML changed (first 100 chars): {html[:100]}...")

    app = QApplication(sys.argv)
    main_window = TestApp()
    main_window.show()
    sys.exit(app.exec())
