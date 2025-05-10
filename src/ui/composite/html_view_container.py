import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QStackedWidget
from PyQt6.QtCore import QUrl, pyqtSignal

from ..atomic.editor.text_editor import TextEditor
from ..views.editable_html_preview_widget import EditableHtmlPreviewWidget

HTML_SKELETON = """<!DOCTYPE html>
<html>
<head>
    <title>New Page</title>
</head>
<body>
    
</body>
</html>"""

class HtmlViewContainer(QWidget):
    internalModificationChanged = pyqtSignal(bool) 

    def __init__(self, parent=None, file_path=None, initial_content=None, is_new_file=True, main_window_ref=None):
        super().__init__(parent)
        self.main_window = main_window_ref
        self.file_path = file_path
        self.is_new_file = is_new_file
        self._current_mode = "source" if self.is_new_file else "preview"

        self.text_editor_widget = TextEditor(self)
        self.preview_widget = EditableHtmlPreviewWidget(self)

        self.stacked_widget = QStackedWidget(self)
        self.stacked_widget.addWidget(self.text_editor_widget)
        self.stacked_widget.addWidget(self.preview_widget)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stacked_widget)
        self.setLayout(layout)

        self._raw_html_content_for_preview = "" 

        if self.is_new_file:
            final_initial_content = initial_content if initial_content is not None else HTML_SKELETON
            self.text_editor_widget.setPlainText(final_initial_content)
            self._raw_html_content_for_preview = final_initial_content 
            self.stacked_widget.setCurrentWidget(self.text_editor_widget)
            if self.text_editor_widget._editor.document():
                 self.text_editor_widget._editor.document().setModified(False)
        else: 
            if initial_content is None:
                initial_content = ""
                print(f"Warning: HtmlViewContainer opened existing file '{file_path}' but no initial_content provided.")

            self.text_editor_widget.setPlainText(initial_content)
            if self.text_editor_widget._editor.document():
                 self.text_editor_widget._editor.document().setModified(False)

            self._raw_html_content_for_preview = initial_content # Keep for saving logic

            if self.file_path:
                print(f"HtmlViewContainer: Loading preview from file: {self.file_path}")
                self.preview_widget.load(QUrl.fromLocalFile(self.file_path))
            else:
                # Fallback or error if no file_path for an existing file (should not happen in normal flow)
                print("HtmlViewContainer Error: Existing file mode but no file_path provided.")
                self.preview_widget.setHtml("<html><body>Error: No file path provided for existing file.</body></html>")

            # The bridge connection might still be relevant if JS within the loaded page calls pyBridge
            print(f"DEBUG HtmlViewContainer: Attempting to connect preview_widget._bridge.htmlChanged. Type: {type(self.preview_widget._bridge.htmlChanged)}")
            self.preview_widget._bridge.htmlChanged.connect(self._on_preview_html_changed)
            print(f"DEBUG HtmlViewContainer: Connected preview_widget._bridge.htmlChanged.")
            
            if self.main_window: 
                self.main_window.on_editor_content_changed(self.preview_widget, initially_modified=False)
            
            self.preview_widget.enableEditing() # Enable editing by default when opening in preview
            self.stacked_widget.setCurrentWidget(self.preview_widget)
            self.preview_widget.setFocus() # Ensure preview widget gets focus
        
        if self.text_editor_widget._editor.document():
            print(f"DEBUG HtmlViewContainer: Attempting to connect text_editor_widget._editor.document().modificationChanged. Type: {type(self.text_editor_widget._editor.document().modificationChanged)}")
            self.text_editor_widget._editor.document().modificationChanged.connect(self._on_text_editor_modification_changed)
            print(f"DEBUG HtmlViewContainer: Connected text_editor_widget._editor.document().modificationChanged.")

    def _on_text_editor_modification_changed(self, modified: bool):
        print(f"DEBUG HtmlViewContainer: _on_text_editor_modification_changed called with modified={modified}") # Added debug print
        if self.stacked_widget.currentWidget() == self.text_editor_widget:
            self.internalModificationChanged.emit(modified)
            if self.main_window:
                 self.main_window.on_editor_content_changed(self.text_editor_widget, initially_modified=modified)

    def _on_preview_html_changed(self, html_content: str):
        if self.stacked_widget.currentWidget() == self.preview_widget:
            self.internalModificationChanged.emit(True) 

    def switch_view(self):
        if self._current_mode == "source": # Switching from Source to Preview
            current_text_content = self.text_editor_widget.toPlainText()
            self._raw_html_content_for_preview = current_text_content # Update cache for saving

            source_editor_modified = True # Default to modified if document is not available
            if self.text_editor_widget._editor.document():
                source_editor_modified = self.text_editor_widget._editor.document().isModified()

            if self.file_path and not self.is_new_file and not source_editor_modified:
                print(f"HtmlViewContainer.switch_view (source->preview): Loading from file: {self.file_path}")
                self.preview_widget.load(QUrl.fromLocalFile(self.file_path))
            else:
                print(f"HtmlViewContainer.switch_view (source->preview): Setting HTML from editor content. NewFile:{self.is_new_file}/Modified:{source_editor_modified}")
                base_url = QUrl()
                # Ensure base_url is set correctly if file_path exists, even for new/modified content being set via setHtml
                if self.file_path: # Check if self.file_path is not None or empty
                     # For existing files (is_new_file is False) or new files that have been named (file_path is set)
                    if os.path.exists(os.path.dirname(self.file_path)): # Ensure directory exists
                        base_url = QUrl.fromLocalFile(os.path.dirname(self.file_path) + os.path.sep)
                    else: # Fallback if path is somehow invalid, though less likely if file_path is set
                        print(f"Warning: Base directory for {self.file_path} does not exist. Using empty base_url.")
                
                self.preview_widget.setHtml(current_text_content, base_url)
            
            # Pass the source editor's modified state to the preview
            if self.main_window:
                self.main_window.on_editor_content_changed(self.preview_widget, initially_modified=source_editor_modified)

            self.preview_widget.enableEditing() # Ensure preview is editable when switched to
            self.stacked_widget.setCurrentWidget(self.preview_widget)
            self._current_mode = "preview"
            self.preview_widget.setFocus()

        elif self._current_mode == "preview":
            self.stacked_widget.setCurrentWidget(self.text_editor_widget)
            self._current_mode = "source"
            self.text_editor_widget.setFocus()
            
            if self.main_window and self.text_editor_widget._editor.document():
                is_modified = self.text_editor_widget._editor.document().isModified()
                self.main_window.on_editor_content_changed(self.text_editor_widget, initially_modified=is_modified)
                self.internalModificationChanged.emit(is_modified)

    def _update_text_editor_and_switch_to_source(self, html_content_from_preview: str):
        # This callback is still connected to preview_widget.getHtml for async nature,
        # but switch_view for preview->source now directly switches without calling getHtml.
        # If getHtml were used, this would be its handler.
        print(f"DEBUG HtmlViewContainer (CALLBACK): _update_text_editor_and_switch_to_source received HTML (first 200 chars):\n{html_content_from_preview[:200]}")
        # self.text_editor_widget.setPlainText(html_content_from_preview) # Avoid this if QWebChannel is broken
        
        # preview_was_modified = self.preview_widget.property("is_modified_custom_flag") or False
        # if self.text_editor_widget._editor.document():
        #     self.text_editor_widget._editor.document().setModified(preview_was_modified)

    def get_current_actual_editor(self):
        if self.stacked_widget.currentWidget() == self.text_editor_widget:
            return self.text_editor_widget._editor
        elif self.stacked_widget.currentWidget() == self.preview_widget:
            return self.preview_widget
        return None

    def get_content_for_saving(self) -> str:
        if self._current_mode == "source":
            return self.text_editor_widget.toPlainText()
        elif self._current_mode == "preview":
            # Always save from the source-of-truth, which is _raw_html_content_for_preview
            # as it was the content last sent TO the preview.
            return self._raw_html_content_for_preview 
        return ""

    def is_modified(self) -> bool:
        if self.stacked_widget.currentWidget() == self.text_editor_widget:
            doc = self.text_editor_widget._editor.document()
            return doc.isModified() if doc else False
        elif self.stacked_widget.currentWidget() == self.preview_widget:
            # If QWebChannel worked, we'd check preview_widget's custom flag.
            # Since it doesn't, "modified" in preview mode means the underlying
            # source (_raw_html_content_for_preview) is different from what's in text_editor_widget
            # OR text_editor_widget itself is marked modified.
            # This is tricky. For simplicity, let's tie it to text_editor's state.
            doc = self.text_editor_widget._editor.document() # Check underlying source editor
            return doc.isModified() if doc else False
        return False

    def set_file_path_and_name(self, file_path: str, is_new: bool):
        self.file_path = file_path
        self.is_new_file = is_new
        self.setProperty("file_path", file_path)
        self.setProperty("is_new", is_new)
        if is_new:
            self.setProperty("untitled_name", os.path.basename(file_path) if file_path else "未命名.html")
        else:
            self.setProperty("untitled_name", None)

    def set_modified_status_on_current_editor(self, modified: bool):
        current_editor_widget = self.stacked_widget.currentWidget()
        if current_editor_widget == self.text_editor_widget:
            if self.text_editor_widget._editor.document():
                self.text_editor_widget._editor.document().setModified(modified)
        elif current_editor_widget == self.preview_widget:
            if self.main_window: # This will set the custom flag on preview_widget
                self.main_window.on_editor_content_changed(self.preview_widget, initially_modified=modified)
            # Also ensure the underlying text_editor_widget reflects this if QWebChannel was working
            # For now, this means if preview is marked modified, the source is considered modified too.
            if self.text_editor_widget._editor.document():
                 self.text_editor_widget._editor.document().setModified(modified)

        self.internalModificationChanged.emit(modified)

    def setFocus(self): 
        current_internal_widget = self.get_current_actual_editor()
        if current_internal_widget:
            current_internal_widget.setFocus()
        else:
            super().setFocus()

    def cleanup(self):
        if self.text_editor_widget and self.text_editor_widget._editor.document():
            try:
                self.text_editor_widget._editor.document().modificationChanged.disconnect(self._on_text_editor_modification_changed)
            except TypeError: pass 
        if self.preview_widget and hasattr(self.preview_widget, '_bridge'):
            try:
                self.preview_widget._bridge.htmlChanged.disconnect(self._on_preview_html_changed)
            except TypeError: pass
        print(f"HtmlViewContainer for {self.file_path or 'untitled'} cleaned up.")
