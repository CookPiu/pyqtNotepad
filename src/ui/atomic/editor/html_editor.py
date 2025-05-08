import os
from PyQt6.QtWidgets import (QWidget, QPlainTextEdit, QVBoxLayout, QHBoxLayout, 
                             QStackedWidget, QFrame) # QWebEngineView imported below
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QUrl, QRect, QSize
from PyQt6.QtGui import QColor, QPainter, QTextCharFormat, QFont, QPalette, QTextCursor, QPaintEvent # Added QPaintEvent

# Re-using LineNumberArea similar to MarkdownEditorWidget
class LineNumberArea(QWidget):
    def __init__(self, editor: QPlainTextEdit):
        super().__init__(editor)
        self.editor = editor
        self._width = 40
        self.setFixedWidth(self._width)
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
        top_y_viewport = self.editor.blockBoundingGeometry(block).translated(self.editor.contentOffset()).top()
        bottom_y_viewport = top_y_viewport + self.editor.blockBoundingRect(block).height()
        font_metrics_height = self.editor.fontMetrics().height()

        while block.isValid() and top_y_viewport <= event.rect().bottom():
            if block.isVisible() and bottom_y_viewport >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(self._text_color)
                paint_rect = QRect(0, int(top_y_viewport), self.width() - 6, font_metrics_height)
                painter.drawText(paint_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, number)
            block = block.next()
            if not block.isValid(): break
            block_geom = self.editor.blockBoundingGeometry(block)
            top_y_viewport = block_geom.translated(self.editor.contentOffset()).top()
            bottom_y_viewport = top_y_viewport + block_geom.height()
            block_number += 1

class HtmlEditor(QWidget): # Changed base class from QWebEngineView
    document_modified = pyqtSignal(bool)
    view_mode_changed = pyqtSignal(bool) # True for preview, False for editor

    def __init__(self, parent=None):
        super().__init__(parent)

        # Editor part with line numbers for HTML source
        self.editor_area_widget = QWidget(self)
        editor_area_layout = QHBoxLayout(self.editor_area_widget)
        editor_area_layout.setContentsMargins(0,0,0,0)
        editor_area_layout.setSpacing(0)

        self.source_editor = QPlainTextEdit(self.editor_area_widget) # For HTML source
        self.line_numbers = LineNumberArea(self.source_editor)
        
        editor_area_layout.addWidget(self.line_numbers)
        editor_area_layout.addWidget(self.source_editor)
        self.editor_area_widget.setLayout(editor_area_layout)

        # Preview part
        self.preview = QWebEngineView(self)
        settings = self.preview.page().settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        
        # Stacked widget to switch between editor and preview
        self.stacked_widget = QStackedWidget(self)
        self.editor_page_index = self.stacked_widget.addWidget(self.editor_area_widget)
        self.preview_page_index = self.stacked_widget.addWidget(self.preview)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.addWidget(self.stacked_widget)
        self.setLayout(main_layout)

        self._render_timer = QTimer(self, interval=250, singleShot=True) # Timer for preview update
        self._render_timer.timeout.connect(self._update_preview_from_source)

        # Connect signals for line number area updates
        self.source_editor.blockCountChanged.connect(self._update_line_number_area_width)
        self.source_editor.updateRequest.connect(self._update_line_number_area_on_request)
        # self.source_editor.cursorPositionChanged.connect(self._highlight_current_line_in_editor) # Optional

        self.source_editor.textChanged.connect(self._on_source_editor_text_changed)
        self.source_editor.document().modificationChanged.connect(self.document_modified)

        self.is_preview_mode = False # Start in editor mode
        self.stacked_widget.setCurrentIndex(self.editor_page_index)
        self._update_line_number_area_width()
        self.setHtml("<!DOCTYPE html>\n<html>\n<head>\n    <title>New HTML Page</title>\n</head>\n<body>\n    <h1>Hello, HTML!</h1>\n</body>\n</html>")
        self.source_editor.document().setModified(False)


    def _update_line_number_area_width(self):
        width = self._calculate_line_number_area_width()
        self.line_numbers.update_width(width)

    def _calculate_line_number_area_width(self) -> int:
        digits = len(str(max(1, self.source_editor.document().blockCount())))
        space = self.source_editor.fontMetrics().horizontalAdvance('9') * digits + 12
        return max(40, space)

    def _update_line_number_area_on_request(self, rect: QRect, dy: int):
        if dy:
            self.line_numbers.scroll(0, dy)
        else:
            self.line_numbers.update(0, rect.y(), self.line_numbers.width(), rect.height())
        if rect.contains(self.source_editor.viewport().rect()):
            self._update_line_number_area_width()

    def _on_source_editor_text_changed(self):
        self.document_modified.emit(True) # Source has changed
        if self.is_preview_mode: # If preview is active, update it
            self._render_timer.start() 

    def _update_preview_from_source(self):
        html_source = self.source_editor.toPlainText()
        if self.preview.page():
            self.preview.page().setHtml(html_source, QUrl.fromLocalFile(os.getcwd() + "/")) # Provide base URL for local resources
        else:
            self.preview.setHtml(html_source, QUrl.fromLocalFile(os.getcwd() + "/"))


    def set_preview_visible(self, show_preview: bool):
        """Switches between HTML source editor and preview."""
        mode_actually_changed = False
        if show_preview:
            if not self.is_preview_mode or self.stacked_widget.currentWidget() != self.preview:
                self._update_preview_from_source() # Update preview before showing
                self.stacked_widget.setCurrentIndex(self.preview_page_index)
                self.is_preview_mode = True
                mode_actually_changed = True
        else: 
            if self.is_preview_mode or self.stacked_widget.currentWidget() != self.editor_area_widget:
                self.stacked_widget.setCurrentIndex(self.editor_page_index)
                self.source_editor.setFocus()
                self.is_preview_mode = False
                mode_actually_changed = True
        
        if mode_actually_changed:
            self.view_mode_changed.emit(self.is_preview_mode)

    # --- Content Access Methods ---
    def setHtml(self, html_source: str, baseUrl: QUrl = QUrl()): # Renamed from setHtml to avoid conflict
        self.source_editor.setPlainText(html_source)
        self._update_preview_from_source() # Update preview
        self.source_editor.document().setModified(False)


    def toHtml(self, callback=None): # This now returns source HTML
        # For consistency with QWebEngineView's async toHtml, but here it's sync
        source_html = self.source_editor.toPlainText()
        if callback:
            callback(source_html)
        else: # If no callback, for direct calls (though FileOperations might expect async)
            return source_html 

    def setPlainText(self, text: str): # For compatibility if used as a generic editor
        self.setHtml(text)

    def toPlainText(self, callback=None): # Returns source HTML as plain text
        return self.toHtml(callback)

    # --- State Management ---
    def isModified(self) -> bool:
        return self.source_editor.document().isModified()

    def setModified(self, modified: bool):
        self.source_editor.document().setModified(modified)
        # self.document_modified.emit(modified) # Already emitted by textChanged connection

    def get_text_edit_widget(self) -> QPlainTextEdit: # To be used by MainWindow for focus/actions
        return self.source_editor

    def update_editor_theme_colors(self, text_color: QColor, background_color: QColor, border_color: QColor, current_line_bg_color: QColor):
        self.line_numbers.set_colors(background_color, text_color, border_color)
        palette = self.source_editor.palette()
        palette.setColor(QPalette.ColorRole.Base, background_color)
        palette.setColor(QPalette.ColorRole.Text, text_color)
        self.source_editor.setPalette(palette)
        # Current line highlight for QPlainTextEdit can be added if needed, similar to MarkdownEditorWidget

    # --- Focus and other QWidget methods ---
    def setFocus(self):
        if self.is_preview_mode:
            self.preview.setFocus()
        else:
            self.source_editor.setFocus()

if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton
    class TestHtmlEditorWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("HTML Editor Test")
            self.editor = HtmlEditor(self)
            self.setCentralWidget(self.editor)
            
            toolbar = QToolBar("HTML Tools")
            self.addToolBar(toolbar)
            
            self.toggle_action = QAction("Toggle Preview", self, checkable=True)
            self.toggle_action.setChecked(False) # Start in editor mode
            self.toggle_action.triggered.connect(self.editor.set_preview_visible)
            toolbar.addAction(self.toggle_action)
            self.editor.view_mode_changed.connect(self.toggle_action.setChecked)

            self.editor.setHtml("<h1>Hello World</h1><p>This is a test HTML document.</p><img src='https://www.google.com/images/branding/googlelogo/1x/googlelogo_color_272x92dp.png'>")
            self.setGeometry(100, 100, 900, 600)

    app = QApplication(sys.argv)
    win = TestHtmlEditorWindow()
    win.show()
    sys.exit(app.exec())
