from PyQt6.QtWidgets import (QWidget, QToolBar, QPlainTextEdit, QStackedWidget, 
                             QVBoxLayout, QHBoxLayout, QFrame, QTextEdit) # Added QTextEdit for ExtraSelection
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRegularExpression, QSignalBlocker, QRect, QSize
from PyQt6.QtGui import (QColor, QAction, QSyntaxHighlighter, QTextCharFormat, 
                         QFont, QPainter, QTextCursor, QPalette, QPaintEvent) # Added QPaintEvent
from markdown_it import MarkdownIt
from markdown_it.token import Token
from markdownify import markdownify

# --- LineNumberArea for QPlainTextEdit ---
class LineNumberArea(QWidget):
    def __init__(self, editor: QPlainTextEdit):
        super().__init__(editor)
        self.editor = editor
        self._width = 40
        self.setFixedWidth(self._width)
        # Default colors, can be updated by theme
        self._background_color = QColor(Qt.GlobalColor.lightGray)
        self._text_color = QColor(Qt.GlobalColor.black)
        self._border_color = QColor(Qt.GlobalColor.darkGray)
        self.setStyleSheet(f"border-right: 1px solid {self._border_color.name()};")

    def sizeHint(self) -> QSize:
        return QSize(self._width, 0)

    def set_colors(self, background: QColor, text: QColor, border: QColor):
        self._background_color = background
        self._text_color = text
        self._border_color = border
        self.setStyleSheet(f"border-right: 1px solid {self._border_color.name()};")
        self.update()
    
    def update_width(self, width: int):
        if self._width != width:
            self._width = width
            self.setFixedWidth(width)
            self.update()

    def paintEvent(self, event: QPaintEvent): # type: ignore
        painter = QPainter(self)
        painter.fillRect(event.rect(), self._background_color)

        block = self.editor.firstVisibleBlock()
        block_number = block.blockNumber()
        # Get the top of the first visible block in viewport coordinates
        top_y_viewport = self.editor.blockBoundingGeometry(block).translated(self.editor.contentOffset()).top()
        bottom_y_viewport = top_y_viewport + self.editor.blockBoundingRect(block).height()
        
        font_metrics_height = self.editor.fontMetrics().height()

        while block.isValid() and top_y_viewport <= event.rect().bottom():
            if block.isVisible() and bottom_y_viewport >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(self._text_color)
                # Draw text aligned to the right, vertically centered within the line number area for that block
                paint_rect = QRect(0, int(top_y_viewport), self.width() - 6, font_metrics_height)
                painter.drawText(paint_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, number)

            block = block.next()
            if not block.isValid():
                break
            
            block_geom = self.editor.blockBoundingGeometry(block)
            top_y_viewport = block_geom.translated(self.editor.contentOffset()).top()
            bottom_y_viewport = top_y_viewport + block_geom.height()
            block_number += 1

# --- Markdown-it plugin ---
def source_line_plugin(md_instance: MarkdownIt):
    def add_line_attributes_rule(state):
        for token in state.tokens:
            if token.map and token.type not in ["list_item_close", "paragraph_close", "heading_close"]:
                if token.nesting >= 0: 
                    line_start = token.map[0]
                    token.attrSet('data-source-line', str(line_start))
    md_instance.core.ruler.push('source_line_attributes', add_line_attributes_rule)

md = MarkdownIt().use(source_line_plugin)

class MarkdownHighlighter(QSyntaxHighlighter):
    def __init__(self, parent):
        super().__init__(parent)
        self.rules = []
        h1_format = QTextCharFormat(); h1_format.setForeground(QColor("#1a1a8c")); h1_format.setFontWeight(QFont.Weight.Bold); h1_format.setFontPointSize(parent.defaultFont().pointSize()*1.5); self.rules.append((QRegularExpression(r"^#\s+.*$"),h1_format))
        h2_format = QTextCharFormat(); h2_format.setForeground(QColor("#1a5c8c")); h2_format.setFontWeight(QFont.Weight.Bold); h2_format.setFontPointSize(parent.defaultFont().pointSize()*1.3); self.rules.append((QRegularExpression(r"^##\s+.*$"),h2_format))
        h3_format = QTextCharFormat(); h3_format.setForeground(QColor("#1a8c5c")); h3_format.setFontWeight(QFont.Weight.Bold); h3_format.setFontPointSize(parent.defaultFont().pointSize()*1.15); self.rules.append((QRegularExpression(r"^###\s+.*$"),h3_format))
        bold_format = QTextCharFormat(); bold_format.setFontWeight(QFont.Weight.Bold); self.rules.append((QRegularExpression(r"\*\*(.+?)\*\*"),bold_format)); self.rules.append((QRegularExpression(r"__(.+?)__"),bold_format))
        italic_format = QTextCharFormat(); italic_format.setFontItalic(True); self.rules.append((QRegularExpression(r"\*(?!\s)(.+?)(?<!\s)\*"),italic_format)); self.rules.append((QRegularExpression(r"_(?!\s)(.+?)(?<!\s)_"),italic_format))
        inline_code_format = QTextCharFormat(); inline_code_format.setFontFamily("Consolas, Courier New, monospace"); inline_code_format.setBackground(QColor("#f0f0f0")); inline_code_format.setForeground(QColor("#c7254e")); self.rules.append((QRegularExpression(r"`([^`\n]+)`"),inline_code_format))
        self.code_block_format = QTextCharFormat(); self.code_block_format.setFontFamily("Consolas, Courier New, monospace"); self.code_block_format.setBackground(QColor("#f5f5f5"))
        self.code_block_start_expression = QRegularExpression(r"^```.*$"); self.code_block_end_expression = QRegularExpression(r"^```$")
        link_format = QTextCharFormat(); link_format.setForeground(QColor("blue")); link_format.setFontUnderline(True); self.rules.append((QRegularExpression(r"\[([^\]]+)\]\(([^\)]+)\)"),link_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            iterator = pattern.globalMatch(text);
            while iterator.hasNext():
                match = iterator.next(); self.setFormat(match.capturedStart(), match.capturedLength(), fmt)
        self.setCurrentBlockState(0) 
        if self.previousBlockState() == 1:
            if self.code_block_end_expression.match(text).hasMatch(): self.setCurrentBlockState(0) 
            else: self.setCurrentBlockState(1) 
            self.setFormat(0, len(text), self.code_block_format)
        else: 
            if self.code_block_start_expression.match(text).hasMatch():
                if self.code_block_end_expression.match(text).hasMatch() and len(text.strip())==3: self.setCurrentBlockState(0) 
                else: self.setCurrentBlockState(1) 
                self.setFormat(0, len(text), self.code_block_format)

class MarkdownEditorWidget(QWidget):
    content_changed = pyqtSignal()
    view_mode_changed = pyqtSignal(bool) 

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Editor part with line numbers
        self.editor_area_widget = QWidget(self) # Container for editor + line numbers
        editor_area_layout = QHBoxLayout(self.editor_area_widget)
        editor_area_layout.setContentsMargins(0,0,0,0)
        editor_area_layout.setSpacing(0)

        self.editor = QPlainTextEdit(self.editor_area_widget)
        self.line_numbers = LineNumberArea(self.editor) # Pass editor to LineNumberArea
        self.highlighter = MarkdownHighlighter(self.editor.document())
        
        editor_area_layout.addWidget(self.line_numbers)
        editor_area_layout.addWidget(self.editor)
        self.editor_area_widget.setLayout(editor_area_layout)

        self.preview = QWebEngineView(self)
        
        self.stacked_widget = QStackedWidget(self)
        self.editor_page_index = self.stacked_widget.addWidget(self.editor_area_widget) # Add container
        self.preview_page_index = self.stacked_widget.addWidget(self.preview)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.addWidget(self.stacked_widget)
        self.setLayout(main_layout)

        self._render_timer = QTimer(self, interval=100, singleShot=True)
        self._render_timer.timeout.connect(self._render_preview_from_editor)

        # Connect signals for line number area updates
        self.editor.blockCountChanged.connect(self.update_line_number_area_width)
        self.editor.updateRequest.connect(self.update_line_number_area)
        self.editor.cursorPositionChanged.connect(self._highlight_current_line_in_editor) # Optional: current line highlight

        self.editor.textChanged.connect(self._on_editor_text_changed)
        self._render_preview_html("") 
        self.is_preview_mode = False
        self.stacked_widget.setCurrentIndex(self.editor_page_index)
        self.update_line_number_area_width() # Initial width update

        # For current line highlight in editor (optional, similar to TextEditor)
        self._editor_current_line_selection = QTextEdit.ExtraSelection() # Use QTextEdit.ExtraSelection


    def update_line_number_area_width(self):
        width = self.line_number_area_width_calculator()
        self.line_numbers.update_width(width)

    def line_number_area_width_calculator(self) -> int:
        digits = len(str(max(1, self.editor.document().blockCount())))
        space = self.editor.fontMetrics().horizontalAdvance('9') * digits + 12 # Adjust padding
        return max(40, space)

    def update_line_number_area(self, rect: QRect, dy: int):
        if dy:
            self.line_numbers.scroll(0, dy)
        else:
            self.line_numbers.update(0, rect.y(), self.line_numbers.width(), rect.height())
        if rect.contains(self.editor.viewport().rect()):
            self.update_line_number_area_width()
            
    def _highlight_current_line_in_editor(self): # Optional
        # This is a simplified version. TextEditor has more robust theming for this.
        selections = []
        if not self.editor.isReadOnly(): # Check read-only status on the editor instance
            selection = QTextEdit.ExtraSelection() # Use QTextEdit.ExtraSelection
            line_color = QColor(Qt.GlobalColor.yellow).lighter(160) # Example color
            # Theme manager should provide this color
            # For now, using a default. It can be updated by update_editor_theme_colors
            if hasattr(self, '_current_line_highlight_color_editor'):
                line_color = self._current_line_highlight_color_editor

            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.editor.textCursor()
            selection.cursor.clearSelection()
            selections.append(selection)
        self.editor.setExtraSelections(selections)


    def _on_editor_text_changed(self):
        if not self.is_preview_mode:
            self._render_timer.start()

    def _render_preview_from_editor(self):
        current_text = self.editor.toPlainText()
        self._render_preview_html(current_text)
        self.content_changed.emit()

    def _render_preview_html(self, markdown_text: str):
        try:
            html = md.render(markdown_text)
            if self.preview.page(): self.preview.page().setHtml(html)
            else: self.preview.setHtml(html)
        except Exception as e:
            print(f"Error rendering Markdown: {e}"); self.preview.setHtml(f"<pre>Error rendering Markdown:\n{e}</pre>")

    def _sync_preview_to_editor(self, html_content: str, scroll_percentage: float | None = 0.0):
        try:
            converted_markdown = markdownify(html_content, heading_style='atx', bullets='*')
            with QSignalBlocker(self.editor): self.editor.setPlainText(converted_markdown)
            self._render_preview_html(converted_markdown) 
            self.editor.document().setModified(True); self.content_changed.emit()
            if scroll_percentage is not None:
                scrollbar = self.editor.verticalScrollBar()
                QTimer.singleShot(0, lambda: scrollbar.setValue(int(scroll_percentage * scrollbar.maximum())) if scrollbar.maximum() > 0 else scrollbar.setValue(0))
        except Exception as e: print(f"Error converting HTML to Markdown or scrolling: {e}")

    def _handle_preview_scroll_and_initiate_sync(self, scroll_data):
        scroll_percentage = 0.0
        if isinstance(scroll_data, list) and len(scroll_data) == 2 and all(isinstance(item, (int, float)) for item in scroll_data):
            scroll_y, scroll_height = scroll_data
            if scroll_height > 0: scroll_percentage = scroll_y / scroll_height
        if self.preview.page(): self.preview.page().toHtml(lambda html_content: self._sync_preview_to_editor(html_content, scroll_percentage))
        else: self._sync_preview_to_editor("", 0.0)

    def set_preview_visible(self, show_preview: bool):
        mode_actually_changed = False
        if show_preview:
            if not self.is_preview_mode or self.stacked_widget.currentWidget() != self.preview:
                current_editor_text = self.editor.toPlainText()
                self._render_preview_html(current_editor_text)
                current_block_number = self.editor.textCursor().blockNumber()
                def apply_preview_settings():
                    if self.preview.page():
                        self.preview.page().runJavaScript("document.body.contentEditable = 'true';")
                        scroll_js = (f"const targetElement = document.querySelector('[data-source-line=\"{current_block_number}\"]');"
                                     "if (targetElement) { targetElement.scrollIntoView({ behavior: 'auto', block: 'start' }); }"
                                     "else { window.scrollTo(0, 0); }")
                        self.preview.page().runJavaScript(scroll_js)
                        self.preview.setFocus()
                QTimer.singleShot(200, apply_preview_settings)
                self.stacked_widget.setCurrentIndex(self.preview_page_index)
                self.is_preview_mode = True; mode_actually_changed = True
        else: 
            if self.is_preview_mode or self.stacked_widget.currentWidget() != self.editor_area_widget: # Check against editor_area_widget
                if self.preview.page():
                    self.preview.page().runJavaScript("document.body.contentEditable = 'false';")
                    self.preview.page().runJavaScript("[window.scrollY, document.documentElement.scrollHeight];", self._handle_preview_scroll_and_initiate_sync)
                self.stacked_widget.setCurrentIndex(self.editor_page_index) # Switch to editor_area_widget
                self.editor.setFocus(); self.is_preview_mode = False; mode_actually_changed = True
        if mode_actually_changed: self.view_mode_changed.emit(self.is_preview_mode)

    def load_markdown(self, file_path: str) -> bool:
        try:
            with open(file_path, 'r', encoding='utf-8') as f: content = f.read()
            with QSignalBlocker(self.editor): self.editor.setPlainText(content)
            self._render_preview_html(content); self.editor.document().setModified(False)
            self.editor.verticalScrollBar().setValue(0)
            if self.preview.page(): QTimer.singleShot(100, lambda: self.preview.page().runJavaScript("window.scrollTo(0, 0);"))
            if self.is_preview_mode:
                 QTimer.singleShot(150, lambda: self.preview.page().runJavaScript("document.body.contentEditable = 'true';") if self.preview.page() else None)
                 self.preview.setFocus()
            else: self.editor.setFocus()
            return True
        except Exception as e: print(f"Error loading Markdown file {file_path}: {e}"); return False

    def save_markdown(self, file_path: str) -> bool:
        try:
            if self.is_preview_mode: print("Warning: Saving while in preview mode. Content from source editor will be saved.")
            content = self.editor.toPlainText()
            with open(file_path, 'w', encoding='utf-8') as f: f.write(content)
            self.editor.document().setModified(False); return True
        except Exception as e: print(f"Error saving Markdown file {file_path}: {e}"); return False

    def get_content(self) -> str: return self.editor.toPlainText()
    def set_content(self, text: str):
        with QSignalBlocker(self.editor): self.editor.setPlainText(text)
        self._render_preview_html(text)
    def clear_content(self):
        with QSignalBlocker(self.editor): self.editor.clear()
        self._render_preview_html("")

    def set_preview_background_color(self, color: QColor):
        js_script = (f"if(document.body) {{ document.body.style.backgroundColor = '{color.name()}'; }} "
                     f"else if(document.documentElement) {{ document.documentElement.style.backgroundColor = '{color.name()}'; }}")
        if self.preview.page(): self.preview.page().runJavaScript(js_script)

    def get_text_edit_widget(self) -> QPlainTextEdit: return self.editor

    # Method to update line number colors from theme manager
    def update_editor_theme_colors(self, text_color: QColor, background_color: QColor, border_color: QColor, current_line_bg_color: QColor):
        self.line_numbers.set_colors(background_color, text_color, border_color)
        
        palette = self.editor.palette()
        palette.setColor(QPalette.ColorRole.Base, background_color)
        palette.setColor(QPalette.ColorRole.Text, text_color)
        # TODO: Set selection colors from theme if needed
        # palette.setColor(QPalette.ColorRole.Highlight, QColor("#ADD6FF")) 
        # palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#000000"))
        self.editor.setPalette(palette)
        
        # Store and apply current line highlight color
        self._current_line_highlight_color_editor = current_line_bg_color
        self._highlight_current_line_in_editor() # Re-apply to make it visible


if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow
    class TestWindow(QMainWindow):
        def __init__(self):
            super().__init__(); self.setWindowTitle("Markdown Editor Widget Test")
            self.markdown_widget = MarkdownEditorWidget(self)
            self.setCentralWidget(self.markdown_widget)
            self.setGeometry(100,100,800,600); toolbar = QToolBar("Test"); self.addToolBar(toolbar)
            self.preview_action = QAction("Toggle Preview",self,checkable=True); self.preview_action.setChecked(False) 
            self.preview_action.triggered.connect(self.toggle_view); toolbar.addAction(self.preview_action)
            self.markdown_widget.view_mode_changed.connect(self.preview_action.setChecked)
            self.markdown_widget.set_content("# Hello Markdown!\n\nThis is a **test**.\n\n* Item 1\n* Item 2\n\n```python\nprint('Hello')\n```\n\nVisit [Google](https://www.google.com)\n\n" + "\n".join([f"Line {i}" for i in range(50)]))
        def toggle_view(self,checked): self.markdown_widget.set_preview_visible(checked)
    app = QApplication(sys.argv); window = TestWindow(); window.show(); sys.exit(app.exec())
