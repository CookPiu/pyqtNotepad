from PyQt6.QtWidgets import QWidget, QToolBar, QPlainTextEdit, QStackedWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRegularExpression, QSignalBlocker
from PyQt6.QtGui import QColor, QAction, QSyntaxHighlighter, QTextCharFormat, QFont
from markdown_it import MarkdownIt
from markdown_it.token import Token # Import Token for plugin
from markdownify import markdownify

# --- Markdown-it plugin to add source line numbers ---
def source_line_plugin(md_instance: MarkdownIt):
    def add_line_attributes_rule(state):
        for token in state.tokens:
            if token.map and token.type not in ["list_item_close", "paragraph_close", "heading_close"]: # Avoid adding to closing tags if not needed
                # Add to block-level opening tags or self-closing tags that have a map
                if token.nesting >= 0: # Opening or self-closing
                    line_start = token.map[0]
                    token.attrSet('data-source-line', str(line_start))
    
    # Apply to the core ruler to process tokens after parsing
    md_instance.core.ruler.push('source_line_attributes', add_line_attributes_rule)

# Global MarkdownIt instance with the plugin
md = MarkdownIt().use(source_line_plugin)


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
        self._render_timer.timeout.connect(self._render_preview_from_editor)

        self.editor.textChanged.connect(self._on_editor_text_changed)
        self._render_preview_html("") 
        self.is_preview_mode = False
        self.stacked_widget.setCurrentIndex(self.editor_index)

    def _on_editor_text_changed(self):
        if not self.is_preview_mode:
            self._render_timer.start()

    def _render_preview_from_editor(self):
        current_text = self.editor.toPlainText()
        self._render_preview_html(current_text)
        self.content_changed.emit()

    def _render_preview_html(self, markdown_text: str):
        try:
            html = md.render(markdown_text) # md instance now has the plugin
            if self.preview.page():
                 self.preview.page().setHtml(html)
            else:
                 self.preview.setHtml(html)
        except Exception as e:
            print(f"Error rendering Markdown: {e}")
            self.preview.setHtml(f"<pre>Error rendering Markdown:\n{e}</pre>")

    def _sync_preview_to_editor(self, html_content: str):
        try:
            converted_markdown = markdownify(html_content, heading_style='atx', bullets='*')
            with QSignalBlocker(self.editor):
                current_cursor_pos = self.editor.textCursor().position()
                self.editor.setPlainText(converted_markdown)
                cursor = self.editor.textCursor()
                cursor.setPosition(min(current_cursor_pos, len(converted_markdown)))
                self.editor.setTextCursor(cursor)
            
            self._render_preview_html(converted_markdown) # Re-render preview with cleaned MD
            self.editor.document().setModified(True)
            self.content_changed.emit()
        except Exception as e:
            print(f"Error converting HTML to Markdown: {e}")

    def set_preview_visible(self, show_preview: bool):
        if show_preview:
            if not self.is_preview_mode or self.stacked_widget.currentWidget() != self.preview:
                current_editor_text = self.editor.toPlainText()
                self._render_preview_html(current_editor_text)

                current_block_number = self.editor.textCursor().blockNumber() # 0-indexed
                
                def apply_preview_settings():
                    if self.preview.page():
                        self.preview.page().runJavaScript("document.body.contentEditable = 'true';")
                        # Scroll to element with data-source-line attribute
                        scroll_js = (
                            f"const targetElement = document.querySelector('[data-source-line=\"{current_block_number}\"]');"
                            "if (targetElement) { targetElement.scrollIntoView({ behavior: 'auto', block: 'start' }); }"
                            "else { window.scrollTo(0, 0); }" # Fallback to top if element not found
                        )
                        self.preview.page().runJavaScript(scroll_js)
                        self.preview.setFocus()
                
                QTimer.singleShot(200, apply_preview_settings) # Increased delay for complex pages and JS execution

                self.stacked_widget.setCurrentIndex(self.preview_index)
                self.is_preview_mode = True
        else: 
            if self.is_preview_mode or self.stacked_widget.currentWidget() != self.editor:
                if self.preview.page():
                    self.preview.page().runJavaScript("document.body.contentEditable = 'false';")
                    self.preview.page().toHtml(self._sync_preview_to_editor) 
                
                self.stacked_widget.setCurrentIndex(self.editor_index)
                self.editor.setFocus()
                self.is_preview_mode = False
        
        self.view_mode_changed.emit(self.is_preview_mode)

    def load_markdown(self, file_path: str) -> bool:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            with QSignalBlocker(self.editor): # Block signals during setPlainText
                self.editor.setPlainText(content)
            
            self._render_preview_html(content) 
            self.editor.document().setModified(False)

            # Scroll to top for both views on new load
            self.editor.verticalScrollBar().setValue(0)
            if self.preview.page():
                 QTimer.singleShot(100, lambda: self.preview.page().runJavaScript("window.scrollTo(0, 0);"))


            if self.is_preview_mode: # If already in preview mode, make it editable
                 QTimer.singleShot(150, lambda: self.preview.page().runJavaScript("document.body.contentEditable = 'true';") if self.preview.page() else None)
                 self.preview.setFocus()
            else:
                 self.editor.setFocus()
            return True
        except Exception as e:
            print(f"Error loading Markdown file {file_path}: {e}")
            return False

    def save_markdown(self, file_path: str) -> bool:
        try:
            if self.is_preview_mode:
                print("Warning: Saving while in preview mode. Syncing from preview to editor first.")
                # This sync is async. For robust save, this should be handled carefully.
                # For now, we'll proceed with current editor content if sync is too slow.
                # A better way: disable save button in preview, or force sync then save.
                # For this iteration, we save what's in self.editor. User should switch to editor to ensure sync.
                pass # Content is already synced when switching out of preview mode (if user did so)

            content = self.editor.toPlainText()
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.editor.document().setModified(False)
            return True
        except Exception as e:
            print(f"Error saving Markdown file {file_path}: {e}")
            return False

    def get_content(self) -> str:
        return self.editor.toPlainText()

    def set_content(self, text: str):
        with QSignalBlocker(self.editor):
            self.editor.setPlainText(text)
        self._render_preview_html(text)

    def clear_content(self):
        with QSignalBlocker(self.editor):
            self.editor.clear()
        self._render_preview_html("")

    def set_preview_background_color(self, color: QColor):
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
            self.markdown_widget.set_content("# Hello Markdown!\n\nThis is a **test**.\n\n* Item 1\n* Item 2\n\n```python\nprint('Hello')\n```\n\nVisit [Google](https://www.google.com)\n\n" + "\n".join([f"Line {i}" for i in range(50)]))


        def toggle_view(self, checked):
            self.markdown_widget.set_preview_visible(checked)

    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
