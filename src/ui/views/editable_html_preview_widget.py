import os
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWidgets import QSizePolicy

class HtmlBridge(QObject):
    """
    Bridge object for communication between Python and JavaScript in QWebEngineView.
    It receives HTML content from JavaScript when changes occur in contentEditable mode
    and emits a signal to notify Python components.
    """
    # Signal emitted when HTML content is changed in the JS side
    htmlChanged = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_html = ""

    @pyqtSlot(str)
    def receiveHtmlFromJs(self, html_content: str):
        """
        Slot to receive HTML content from JavaScript.
        Stores the HTML and emits the htmlChanged signal.
        """
        # print(f"Python Bridge received HTML: {html_content[:100]}...") # For debugging
        self._current_html = html_content
        self.htmlChanged.emit(html_content)

    def getCurrentHtml(self) -> str:
        """Returns the latest HTML content received from JS."""
        return self._current_html


class EditableHtmlPreviewWidget(QWebEngineView):
    """
    A QWebEngineView subclass that allows for direct editing of displayed HTML
    content (contentEditable=true) and communicates changes back to Python via QWebChannel.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._bridge = HtmlBridge(self)
        self._channel = QWebChannel(self.page())
        self.page().setWebChannel(self._channel)
        self._channel.registerObject("pyBridge", self._bridge)

        self._is_editing_enabled = False # Track editing state
        self.loadFinished.connect(self._on_load_finished)

    def _on_load_finished(self, success: bool):
        """
        Called when the page has finished loading.
        Injects necessary JavaScript for QWebChannel and editing.
        """
        if not success:
            print("EditableHtmlPreviewWidget: Page load failed.")
            return

        # Inject qwebchannel.js. This path is standard for Qt.
        # Ensure qrc:///qtwebchannel/qwebchannel.js is available.
        # Typically, this is handled by Qt's resource system if QtWebChannel is properly installed.
        # If it's not found, you might need to manually add it to your resources or deploy it.
        init_script = """
            if (typeof QWebChannel === 'undefined') {
                var script = document.createElement('script');
                script.src = 'qrc:///qtwebchannel/qwebchannel.js';
                script.onload = function() { console.log('qwebchannel.js loaded.'); setupChannel(); };
                script.onerror = function() { console.error('Failed to load qwebchannel.js'); };
                document.head.appendChild(script);
            } else {
                setupChannel();
            }

            function setupChannel() {
                if (window.qt && window.qt.webChannelTransport) {
                    new QWebChannel(qt.webChannelTransport, function(channel) {
                        window.pyBridge = channel.objects.pyBridge;
                        console.log('Python bridge (pyBridge) initialized in JS.');
                        // Optionally, enable editing by default or based on a flag
                        // window.enableEditingInternal();
                    });
                } else {
                    console.error('qt.webChannelTransport is not available. QWebChannel setup failed.');
                }
            }

            function enableEditingInternal() {
                document.body.contentEditable = 'true';
                document.designMode = 'on'; // Some browsers/versions might prefer this
                console.log('Content editable enabled.');
                // Send initial content back if needed, or wait for changes
                // pyBridge.receiveHtmlFromJs(document.documentElement.outerHTML);

                // Listen for changes. 'input' is common for contentEditable.
                // Using a debounce function is highly recommended for performance.
                let debounceTimer;
                document.body.addEventListener('input', function() {
                    clearTimeout(debounceTimer);
                    debounceTimer = setTimeout(function() {
                        if (window.pyBridge) {
                            // console.log('Sending HTML to Python...'); // For debugging
                            window.pyBridge.receiveHtmlFromJs(document.documentElement.outerHTML);
                        }
                    }, 500); // Adjust debounce delay as needed (e.g., 300-1000ms)
                });
            }

            function disableEditingInternal() {
                document.body.contentEditable = 'false';
                document.designMode = 'off';
                console.log('Content editable disabled.');
                // Consider removing the event listener if it was added specifically for editing
            }
        """
        self.page().runJavaScript(init_script)
        if self._is_editing_enabled: # Re-apply editing if it was enabled before reload
            self.enableEditing()


    def setHtml(self, html_content: str, base_url: QUrl = QUrl()):
        """
        Sets the HTML content of the web view.
        The base_url is crucial for resolving relative paths (CSS, JS, images).
        """
        print(f"DEBUG EditableHtmlPreviewWidget.setHtml: base_url='{base_url.toString()}', content (first 150): {html_content[:150]}")
        super().setHtml(html_content, base_url)
        # Editing state might need to be reapplied after content is set,
        # handled by _on_load_finished and self._is_editing_enabled

    def getHtml(self, callback=None):
        """
        Asynchronously retrieves the current HTML content from the web page.
        The result is passed to the callback function.
        If no callback is provided, it attempts to return the cached version from HtmlBridge.
        """
        if callback:
            self.page().toHtml(callback) # QWebEnginePage.toHtml is asynchronous
        else:
            # This returns the HTML last sent by JS, might not be perfectly up-to-date
            # if there were very recent changes not yet sent by the debounced input listener.
            return self._bridge.getCurrentHtml()


    def enableEditing(self):
        """Enables contentEditable mode on the loaded HTML page."""
        self._is_editing_enabled = True
        self.page().runJavaScript("if (typeof enableEditingInternal === 'function') { enableEditingInternal(); } else { console.error('enableEditingInternal not defined'); }")

    def disableEditing(self):
        """Disables contentEditable mode on the loaded HTML page."""
        self._is_editing_enabled = False
        self.page().runJavaScript("if (typeof disableEditingInternal === 'function') { disableEditingInternal(); } else { console.error('disableEditingInternal not defined'); }")

    def toggleEditing(self):
        """Toggles the contentEditable mode."""
        if self._is_editing_enabled:
            self.disableEditing()
        else:
            self.enableEditing()
        return self._is_editing_enabled

    def isEditingEnabled(self) -> bool:
        return self._is_editing_enabled

if __name__ == '__main__':
    # Example Usage (requires a QApplication)
    import sys
    from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget, QPushButton

    class TestApp(QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Editable HTML Preview Test")
            self.setGeometry(100, 100, 800, 600)
            layout = QVBoxLayout(self)

            self.editor_view = EditableHtmlPreviewWidget()
            layout.addWidget(self.editor_view)

            # Example HTML content
            example_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Test Page</title>
                <style>
                    body { font-family: sans-serif; background-color: #f0f0f0; padding: 20px; }
                    h1 { color: navy; }
                    p { line-height: 1.6; }
                    .note { background-color: yellow; padding: 10px; border-radius: 5px;}
                </style>
            </head>
            <body>
                <h1>Hello, World!</h1>
                <p>This is an <strong>editable</strong> HTML page. Try changing this text.</p>
                <div class="note">
                    <p>This is a note. You can edit this too!</p>
                    <ul>
                        <li>Item 1</li>
                        <li>Item 2</li>
                    </ul>
                </div>
                <p>Another paragraph here.</p>
            </body>
            </html>
            """
            # For local file base URL (e.g., if HTML references local images/css)
            # current_dir = os.path.dirname(os.path.abspath(__file__))
            # base_url = QUrl.fromLocalFile(current_dir + os.path.sep)
            # self.editor_view.setHtml(example_html, base_url)
            self.editor_view.setHtml(example_html) # No base URL needed for this simple example

            self.editor_view._bridge.htmlChanged.connect(self.on_html_changed)

            self.toggle_button = QPushButton("Toggle Editing (Currently: OFF)")
            self.toggle_button.clicked.connect(self.do_toggle_editing)
            layout.addWidget(self.toggle_button)

            self.get_html_button = QPushButton("Get Current HTML (Print to Console)")
            self.get_html_button.clicked.connect(self.print_current_html)
            layout.addWidget(self.get_html_button)

            # Enable editing by default for testing
            self.editor_view.enableEditing()
            self.update_toggle_button_text()


        def do_toggle_editing(self):
            self.editor_view.toggleEditing()
            self.update_toggle_button_text()

        def update_toggle_button_text(self):
            state = "ON" if self.editor_view.isEditingEnabled() else "OFF"
            self.toggle_button.setText(f"Toggle Editing (Currently: {state})")

        def on_html_changed(self, html):
            print(f"Python App: HTML changed (first 100 chars): {html[:100]}...")

        def print_current_html(self):
            # Using the callback version of getHtml
            # self.editor_view.getHtml(lambda html_content: print(f"Current HTML (async):\n{html_content}"))

            # Using the cached version from bridge
            print(f"Current HTML (cached from bridge):\n{self.editor_view.getHtml()}")


    app = QApplication(sys.argv)
    main_window = TestApp()
    main_window.show()
    sys.exit(app.exec())
