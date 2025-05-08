from PyQt6.QtWidgets import QWidget, QToolBar, QPlainTextEdit, QStackedWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRegularExpression, QSignalBlocker
from PyQt6.QtGui import QColor, QAction, QSyntaxHighlighter, QTextCharFormat, QFont
from markdown_it import MarkdownIt
from markdownify import markdownify # Import markdownify

# 全局解析器实例
md = MarkdownIt()

class MarkdownHighlighter(QSyntaxHighlighter):
    def __init__(self, parent): # parent is QPlainTextEdit.document()
        super().__init__(parent)
        self.rules = []
        # ... (highlighter rules remain the same) ...
        h1_format = QTextCharFormat()
        h1_format.setForeground(QColor("#1a1a8c")) 
        h1_format.setFontWeight(QFont.Weight.Bold)
        h1_format.setFontPointSize(parent.defaultFont().pointSize() * 1.5) 
        self.rules.append((QRegularExpression(r"^#\s+.*$"), h1_format))
        h2_format = QTextCharFormat()
        h2_format.setForeground(QColor("#1a5c8c")) 
        h2_format.setFontWeight(QFont.Weight.Bold)
        h2_format.setFontPointSize(parent.defaultFont().pointSize() * 1.3)
        self.rules.append((QRegularExpression(r"^##\s+.*$"), h2_format))
        h3_format = QTextCharFormat()
        h3_format.setForeground(QColor("#1a8c5c")) 
        h3_format.setFontWeight(QFont.Weight.Bold)
        h3_format.setFontPointSize(parent.defaultFont().pointSize() * 1.15)
        self.rules.append((QRegularExpression(r"^###\s+.*$"), h3_format))
        bold_format = QTextCharFormat()
        bold_format.setFontWeight(QFont.Weight.Bold)
        self.rules.append((QRegularExpression(r"\*\*(.+?)\*\*"), bold_format))
        self.rules.append((QRegularExpression(r"__(.+?)__"), bold_format))
        italic_format = QTextCharFormat()
        italic_format.setFontItalic(True)
        self.rules.append((QRegularExpression(r"\*(?!\s)(.+?)(?<!\s)\*"), italic_format))
        self.rules.append((QRegularExpression(r"_(?!\s)(.+?)(?<!\s)_"), italic_format))
        inline_code_format = QTextCharFormat()
        inline_code_format.setFontFamily("Consolas, Courier New, monospace")
        inline_code_format.setBackground(QColor("#f0f0f0")) 
        inline_code_format.setForeground(QColor("#c7254e")) 
        self.rules.append((QRegularExpression(r"`([^`\n]+)`"), inline_code_format))
        self.code_block_format = QTextCharFormat()
        self.code_block_format.setFontFamily("Consolas, Courier New, monospace")
        self.code_block_format.setBackground(QColor("#f5f5f5")) 
        self.code_block_start_expression = QRegularExpression(r"^```.*$")
        self.code_block_end_expression = QRegularExpression(r"^```$")
        link_format = QTextCharFormat()
        link_format.setForeground(QColor("blue"))
        link_format.setFontUnderline(True)
        self.rules.append((QRegularExpression(r"\[([^\]]+)\]\(([^\)]+)\)"), link_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            iterator = pattern.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)
        self.setCurrentBlockState(0) 
        if self.previousBlockState() == 1:
            if self.code_block_end_expression.match(text).hasMatch():
                self.setCurrentBlockState(0) 
            else:
                self.setCurrentBlockState(1) 
            self.setFormat(0, len(text), self.code_block_format)
        else: 
            if self.code_block_start_expression.match(text).hasMatch():
                if self.code_block_end_expression.match(text).hasMatch() and len(text.strip()) == 3 :
                     self.setCurrentBlockState(0) 
                else:
                    self.setCurrentBlockState(1) 
                self.setFormat(0, len(text), self.code_block_format)

class MarkdownEditorWidget(QWidget):
    content_changed = pyqtSignal()
    view_mode_changed = pyqtSignal(bool) 

    def __init__(self, parent=None):
        super().__init__(parent)
        self.editor = QPlainTextEdit(self)
        self.highlighter = MarkdownHighlighter(self.editor.document())
        self.preview = QWebEngineView(self)
        
        self.stacked_widget = QStackedWidget(self)
        self.editor_index = self.stacked_widget.addWidget(self.editor)
        self.preview_index = self.stacked_widget.addWidget(self.preview)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.addWidget(self.stacked_widget)
        self.setLayout(main_layout)

        self._render_timer = QTimer(self, interval=100, singleShot=True)
        self._render_timer.timeout.connect(self._render_preview_from_editor) # Renamed for clarity

        self.editor.textChanged.connect(self._on_editor_text_changed)
        self._render_preview_html("") 
        self.is_preview_mode = False
        self.stacked_widget.setCurrentIndex(self.editor_index) # Start with editor

    def _on_editor_text_changed(self):
        # If we are in editor mode, start the timer to update the preview (which is hidden but needs to be current)
        # If we are in preview mode, edits are happening in preview, not here.
        if not self.is_preview_mode:
            self._render_timer.start()

    def _render_preview_from_editor(self):
        """Renders HTML from editor's content to the preview pane."""
        current_text = self.editor.toPlainText()
        self._render_preview_html(current_text)
        self.content_changed.emit() # Emit content_changed, might be used for modified status

    def _render_preview_html(self, markdown_text: str):
        try:
            html = md.render(markdown_text)
            # It's important that setHtml is called on the correct page object
            if self.preview.page():
                 self.preview.page().setHtml(html)
            else: # Page might not be ready immediately
                 self.preview.setHtml(html) # Fallback
        except Exception as e:
            print(f"Error rendering Markdown: {e}")
            self.preview.setHtml(f"<pre>Error rendering Markdown:\n{e}</pre>")

    def _sync_preview_to_editor(self, html_content: str):
        """Converts HTML from preview to Markdown and updates editor."""
        try:
            # Whitelist common block tags, otherwise markdownify might add too many newlines
            # Adjust based on typical content and desired Markdown output
            converted_markdown = markdownify(html_content, heading_style='atx', bullets='*')
            
            blocker = QSignalBlocker(self.editor) # Block signals during programmatic change
            current_cursor_pos = self.editor.textCursor().position()
            self.editor.setPlainText(converted_markdown)
            # Try to restore cursor position, might not be perfect after content change
            cursor = self.editor.textCursor()
            cursor.setPosition(min(current_cursor_pos, len(converted_markdown)))
            self.editor.setTextCursor(cursor)
            blocker.unblock() # Manually unblock, or rely on __exit__ if 'with' was used

            # After syncing, the editor's content has changed, so the preview needs to be re-rendered
            # from this new Markdown source to ensure consistency if user switches back to preview.
            self._render_preview_html(converted_markdown)
            self.editor.document().setModified(True) # Content was changed
            self.content_changed.emit()

        except Exception as e:
            print(f"Error converting HTML to Markdown: {e}")


    def set_preview_visible(self, show_preview: bool):
        current_editor_text = self.editor.toPlainText()

        if show_preview: # Switching to Preview Mode
            if not self.is_preview_mode: # Only if changing mode
                self._render_preview_html(current_editor_text) # Ensure preview is up-to-date
                if self.preview.page():
                    self.preview.page().runJavaScript("document.documentElement.contentEditable = 'true';") # Use documentElement for whole page
                self.stacked_widget.setCurrentIndex(self.preview_index)
                self.preview.setFocus()
                self.is_preview_mode = True
        else: # Switching to Editor Mode
            if self.is_preview_mode: # Only if changing mode
                if self.preview.page():
                    self.preview.page().runJavaScript("document.documentElement.contentEditable = 'false';")
                    # Asynchronously get HTML and then sync
                    self.preview.page().toHtml(self._sync_preview_to_editor) 
                self.stacked_widget.setCurrentIndex(self.editor_index)
                self.editor.setFocus()
                self.is_preview_mode = False
        
        self.view_mode_changed.emit(self.is_preview_mode)


    def load_markdown(self, file_path: str) -> bool:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.editor.setPlainText(content)
            self._render_preview_html(content) # Update preview regardless of current mode
            self.editor.document().setModified(False)
            return True
        except Exception as e:
            print(f"Error loading Markdown file {file_path}: {e}")
            return False

    def save_markdown(self, file_path: str) -> bool:
        try:
            # If in preview mode, first sync preview changes back to editor
            if self.is_preview_mode and self.preview.page():
                # This is tricky because toHtml is async. Saving should ideally wait.
                # For simplicity now, we save the editor's current content.
                # A more robust solution would force sync before save or save from preview's HTML.
                # Let's assume for now that if user hits save, they want the source editor's content.
                # Or, we can attempt a synchronous-like fetch if possible, but QWebEnginePage.toHtml is async.
                print("Warning: Saving while in preview mode. Content from source editor will be saved.")
                # To make it save what's in preview, we'd need to call toHtml and do the save in its callback.
                # This complicates the save_markdown signature.

            content = self.editor.toPlainText()
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.editor.document().setModified(False)
            return True
        except Exception as e:
            print(f"Error saving Markdown file {file_path}: {e}")
            return False

    def get_content(self) -> str:
        # If in preview mode, ideally we should get the (potentially edited) preview content,
        # convert to MD, and return that. But toHtml is async.
        # For now, always return from the source editor.
        return self.editor.toPlainText()

    def set_content(self, text: str):
        self.editor.setPlainText(text)
        self._render_preview_html(text) # Update preview

    def clear_content(self):
        self.editor.clear()
        self._render_preview_html("")

    def set_preview_background_color(self, color: QColor):
        # More robust script to set background color
        js_script = (
            f"if(document.body) {{ document.body.style.backgroundColor = '{color.name()}'; }} "
            f"else if(document.documentElement) {{ document.documentElement.style.backgroundColor = '{color.name()}'; }}"
        )
        if self.preview.page(): 
            self.preview.page().runJavaScript(js_script)

    def get_text_edit_widget(self) -> QPlainTextEdit:
        return self.editor

if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow

    class TestWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Markdown Editor Widget Test")
            self.markdown_widget = MarkdownEditorWidget(self)
            self.setCentralWidget(self.markdown_widget)
            self.setGeometry(100, 100, 800, 600)
            toolbar = QToolBar("Test")
            self.addToolBar(toolbar)
            self.preview_action = QAction("Toggle Preview", self, checkable=True)
            self.preview_action.setChecked(False) 
            self.preview_action.triggered.connect(self.toggle_view)
            toolbar.addAction(self.preview_action)
            self.markdown_widget.view_mode_changed.connect(self.preview_action.setChecked)
            self.markdown_widget.set_content("# Hello Markdown!\n\nThis is a **test**.\n\n* Item 1\n* Item 2\n\n```python\nprint('Hello')\n```\n\nVisit [Google](https://www.google.com)")

        def toggle_view(self, checked):
            self.markdown_widget.set_preview_visible(checked)

    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
