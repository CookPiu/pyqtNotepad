# src/ui/atomic/editor/html_editor.py
import os
from PyQt6.QtWebEngineWidgets import QWebEngineView # QWebEnginePage is in Core
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings # Correct module for QWebEnginePage and QWebEngineSettings
# Removed incorrect import: from PyQt6.QtWebEngineCore.backends.web_engine_settings import QWebEngineSettings
from PyQt6.QtCore import QUrl, pyqtSignal, QObject, Qt, QTimer # Import QTimer for delayed execution
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QColor, QFocusEvent # Import QFocusEvent

# No longer need BaseWidget or TextEditor imports here

class HtmlEditor(QWebEngineView):
    """
    HTML editor component based on QWebEngineView with JavaScript enabled.
    """
    # Signal emitted when modification state changes (potentially triggered via JS)
    document_modified = pyqtSignal(bool)
    # Signal to potentially emit HTML content when retrieved asynchronously
    html_content_ready = pyqtSignal(str)
    plain_text_ready = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus) # Set focus policy
        self.setAttribute(Qt.WidgetAttribute.WA_InputMethodEnabled, True) # Enable input method handling

        # --- Enable JavaScript ---
        settings = self.page().settings() # Get settings from the page
        # Correct the enum name to WebAttribute
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        # Optional: Enable other features if needed, e.g., local content access
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)

        # --- Internal State ---
        self._is_modified = False
        self._file_path = None
        self._is_new = True
        self._untitled_name = None
        # PDF related state removed, should be managed elsewhere if needed

        # Set initial blank page or content (removed contenteditable)
        self.setHtml("<!DOCTYPE html><html><head></head><body></body></html>")
        self.setModified(False) # Start unmodified

        # Connect load finished signal to potentially run setup JS
        self.page().loadFinished.connect(self._on_load_finished)

    def _on_load_finished(self, ok):
        """Run JavaScript after the page finishes loading."""
        if ok:
            # Example: Inject CSS for basic theme handling (can be expanded)
            # self.apply_theme_js(is_dark=False) # Apply default theme
            # Enable designMode and try focusing body
            self.run_js("document.designMode = 'on'; document.body.focus();")
            # print("HtmlEditor _on_load_finished: Enabled designMode and attempted focus.") # Debug

    def run_js(self, script: str, callback=None):
        """Executes JavaScript code in the context of the page."""
        if callback:
            self.page().runJavaScript(script, callback)
        else:
            self.page().runJavaScript(script)

    # --- Content Access Methods ---
    def setHtml(self, html: str, baseUrl: QUrl = QUrl()):
        """Sets the HTML content of the page."""
        super().setHtml(html, baseUrl)
        # Reset modification state after programmatic change
        self.setModified(False)

    def toHtml(self, callback=None):
        """
        Asynchronously retrieves the HTML content of the page.
        The result is passed to the callback function.
        Placeholder: For synchronous calls, this won't work directly.
        """
        effective_callback = callback if callback else self.html_content_ready.emit
        self.page().toHtml(effective_callback)
        # Synchronous placeholder (will likely cause issues with saving):
        # print("Warning: toHtml is asynchronous. Returning placeholder.")
        # return "" # Or raise NotImplementedError

    def setPlainText(self, text: str):
        """Sets plain text content (interpreted as HTML)."""
        # QWebEngineView interprets plain text as HTML source
        self.setHtml(text)

    def toPlainText(self, callback=None):
        """
        Asynchronously retrieves the plain text content of the page.
        The result is passed to the callback function.
        Placeholder: For synchronous calls, this won't work directly.
        """
        effective_callback = callback if callback else self.plain_text_ready.emit
        self.page().toPlainText(effective_callback)
        # Synchronous placeholder:
        # print("Warning: toPlainText is asynchronous. Returning placeholder.")
        # return "" # Or raise NotImplementedError

    # --- State Management ---
    def setFilePath(self, path: str | None):
        self._file_path = path
        self._is_new = (path is None)

    def filePath(self) -> str | None:
        return self._file_path

    def isNewFile(self) -> bool:
        return self._is_new

    def setUntitledName(self, name: str):
        self._untitled_name = name

    def untitledName(self) -> str | None:
        return self._untitled_name

    # --- Modification Status ---
    def isModified(self) -> bool:
        """Returns the modification state."""
        # QWebEnginePage.isModified() might not be reliable for JS changes.
        # Rely on our internal flag, which should be set via setModified.
        return self._is_modified

    def setModified(self, modified: bool):
        """
        Sets the modification state and emits the document_modified signal.
        This should be called explicitly when changes are made (e.g., via JS).
        """
        if self._is_modified != modified:
            self._is_modified = modified
            self.document_modified.emit(modified)

    # --- Theme/Color Handling (Example via JS) ---
    def apply_theme_js(self, is_dark: bool):
        """Injects CSS via JS to apply basic dark/light theme."""
        bg_color_str = "#1E1E1E" if is_dark else "#FFFFFF"
        text_color_str = "#D4D4D4" if is_dark else "#000000"
        script = f"""
        (function() {{
            var styleId = 'theme-style-override';
            var existingStyle = document.getElementById(styleId);
            if (!existingStyle) {{
                existingStyle = document.createElement('style');
                existingStyle.id = styleId;
                document.head.appendChild(existingStyle);
            }}
            existingStyle.innerHTML = 'body {{ background-color: {bg_color_str} !important; color: {text_color_str} !important; }}';
        }})();
        """
        self.run_js(script)

    # --- Methods not applicable to QWebEngineView (removed or need JS implementation) ---
    # textCursor, document, currentFont, setCurrentFont, textColor, setTextColor
    # cut, copy, paste, selectAll, find, undo, redo
    # These would need to be implemented by executing corresponding JavaScript commands.
    # Example for paste (very basic):
    # def paste(self):
    #     self.run_js("document.execCommand('paste');")

    def setFocus(self):
        """Override setFocus to try focusing the internal web view child."""
        # Find the actual child widget that handles rendering/input
        # This might be implementation-dependent, but often it's the first QWidget child
        view_child = self.findChild(QWebEngineView) # Or maybe just QWidget? Let's try QWidget first.
        actual_focus_target = None
        children = self.findChildren(QWidget)
        if children:
            # The actual web rendering widget might be one of the children
            # Let's try focusing the first one that isn't the HtmlEditor itself
            for child in children:
                 if child != self: # Ensure it's not the main widget itself
                      actual_focus_target = child
                      break # Focus the first likely candidate

        if actual_focus_target:
            # print(f"HtmlEditor setFocus: Attempting focus on child: {actual_focus_target}") # Debug
            actual_focus_target.setFocus()
        else:
            # print("HtmlEditor setFocus: No suitable child found, calling super().setFocus()") # Debug
            super().setFocus() # Fallback to default behavior

        # Still try JS focus as a backup, maybe with a tiny delay
        QTimer.singleShot(0, lambda: self.run_js("document.body.focus();"))
        # print("HtmlEditor setFocus: Scheduled JS focus.") # Debug


    # Removed focusInEvent override as it didn't solve the input issue
    # def focusInEvent(self, event: QFocusEvent):
    #     """Override focusInEvent."""
    #     # Let the base class handle the event, which should manage internal focus.
    #     super().focusInEvent(event)
    #     # Removed JS focus call: self.run_js("document.body.focus();")
    #     # print("HtmlEditor focusInEvent: Base event handled.") # Debug print (optional)
