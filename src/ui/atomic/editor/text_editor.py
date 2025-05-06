# src/ui/atomic/editor/text_editor.py
import sys
# Change QPlainTextEdit to QTextEdit, Add QMainWindow, QTextDocument
from PyQt6.QtWidgets import QWidget, QTextEdit, QFrame, QHBoxLayout, QVBoxLayout, QMenu, QApplication, QMainWindow
from PyQt6.QtGui import QPainter, QTextCursor, QColor, QPalette, QFontMetrics, QTextFormat, QContextMenuEvent, QTextBlock, QTextDocument
from PyQt6.QtCore import Qt, QRect, QPointF, pyqtSignal, QPoint, QEvent, QTimer # Added QEvent, QTimer

# Correct relative import from atomic/editor to core
from ...core.base_widget import BaseWidget
# Import the custom ResizableImageTextEdit
from .resizable_image_text_edit import ResizableImageTextEdit
# Assuming ThemeManager might be needed later, e.g., for direct access
# from ...core.theme_manager import ThemeManager # Or get_theme_manager()

# --- LineNumberArea - Might need adjustments for QTextEdit ---
class LineNumberArea(QWidget):
    """Widget to display line numbers for the text editor."""
    def __init__(self, editor): # editor will be _InternalTextEdit
        super().__init__(editor)
        self.editor = editor
        self._width = 40
        self.setFixedWidth(self._width)
        self._background_color = QColor(Qt.GlobalColor.lightGray)
        self._text_color = QColor(Qt.GlobalColor.black)
        self._border_color = QColor(Qt.GlobalColor.darkGray)

    def set_colors(self, background: QColor, text: QColor, border: QColor):
        self._background_color = background
        self._text_color = text
        self._border_color = border
        self.setStyleSheet(f"border-right: 1px solid {self._border_color.name()};")
        self.update()

    def update_width(self, width):
        if self._width != width:
            self._width = width
            self.setFixedWidth(width)
            self.update()

    def paintEvent(self, event):
        """Paints the line number area. Adjusted for QTextEdit."""
        painter = QPainter(self)
        painter.fillRect(event.rect(), self._background_color)

        # --- Logic adjusted for QTextEdit ---
        first_visible_block = self.editor.firstVisibleBlock()
        block_number = first_visible_block.blockNumber()
        # Use cursor to find top of viewport
        cursor = QTextCursor(first_visible_block)
        # Get the document layout
        layout = self.editor.document().documentLayout()
        if not layout: return # Exit if layout is not available

        # Calculate the top position relative to the viewport
        block_rect = layout.blockBoundingRect(first_visible_block)
        viewport_offset_y = self.editor.verticalScrollBar().value() # Get scrollbar position
        block_top = int(block_rect.translated(0, -viewport_offset_y).top())


        font_metrics = self.editor.fontMetrics()
        font_height = font_metrics.height()
        block = first_visible_block

        while block.isValid() and block_top <= event.rect().bottom():
            if block.isVisible() and block_top + int(layout.blockBoundingRect(block).height()) >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(self._text_color)
                paint_rect = QRect(0, block_top, self.width() - 6, font_height)
                painter.drawText(paint_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, number)

            block = block.next()
            if block.isValid():
                 block_rect = layout.blockBoundingRect(block)
                 block_top = int(block_rect.translated(0, -viewport_offset_y).top())
            block_number += 1
        # --- End adjustment ---


# --- Internal QTextEdit class ---
# Change base class from QTextEdit to ResizableImageTextEdit
class _InternalTextEdit(ResizableImageTextEdit):
    """The actual QTextEdit implementation with line numbers and highlighting, now with image resizing."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.line_number_area = LineNumberArea(self)
        self._current_line_color = QColor(Qt.GlobalColor.yellow).lighter(160)
        # Accept rich text for pasting etc.
        self.setAcceptRichText(True)
        self._setup_highlight()

        # Connect signals
        self.document().blockCountChanged.connect(self.update_line_number_area_width) # Connect to document's signal
        self.cursorPositionChanged.connect(self._highlight_current_line)
        # QTextEdit doesn't have updateRequest, use verticalScrollBar valueChanged? Or viewport repaint?
        # Let's try connecting to scrollbar changes and viewport updates.
        self.verticalScrollBar().valueChanged.connect(self._update_line_number_area_on_scroll)
        self.viewport().installEventFilter(self) # To catch paint events on viewport

        # Initial setup
        self.update_line_number_area_width()

    # --- Event Filter for Viewport Painting ---
    def eventFilter(self, source, event):
        if source is self.viewport() and event.type() == QEvent.Type.Paint:
            # Schedule the update instead of calling directly to avoid potential recursion
            QTimer.singleShot(0, self._update_line_number_area)
        return super().eventFilter(source, event)

    def _setup_highlight(self):
        """Initializes the extra selection for current line highlighting."""
        self.extra_selections = []
        self._current_line_selection = QTextEdit.ExtraSelection()
        fmt = self._current_line_selection.format
        fmt.setBackground(self._current_line_color)
        try:
             full_width_prop = QTextFormat.Property.FullWidthSelection
        except AttributeError:
             full_width_prop = 1
        fmt.setProperty(full_width_prop, True)
        self._current_line_selection.cursor = self.textCursor()
        self._current_line_selection.cursor.clearSelection()
        self.extra_selections.append(self._current_line_selection)
        self.setExtraSelections(self.extra_selections)

    def _highlight_current_line(self):
        """Updates the position of the current line highlight."""
        if not hasattr(self, 'extra_selections') or not self.extra_selections:
             self._setup_highlight()
             if not self.extra_selections: return

        current_selection = self.extra_selections[0]
        current_selection.format.setBackground(self._current_line_color)
        current_selection.cursor = self.textCursor()
        current_selection.cursor.clearSelection()
        self.setExtraSelections(self.extra_selections)

    def update_highlight_colors(self, is_dark: bool):
        """Updates colors for line number area and current line highlight based on theme."""
        if is_dark:
            line_num_bg = QColor("#1E1E1E")
            line_num_text = QColor("#CCCCCC")
            current_line_highlight = QColor("#3A3D41")
            editor_bg = QColor("#1E1E1E")
            editor_text = QColor("#D4D4D4")
            selection_bg = QColor("#264F78")
            highlighted_text_color = editor_text
            border_col = QColor("#2B2B2B")
        else:
            line_num_bg = QColor(Qt.GlobalColor.white)
            line_num_text = QColor(Qt.GlobalColor.black)
            current_line_highlight = QColor(Qt.GlobalColor.yellow).lighter(160)
            editor_bg = QColor(Qt.GlobalColor.white)
            editor_text = QColor(Qt.GlobalColor.black)
            selection_bg = QColor("#ADD6FF")
            highlighted_text_color = editor_text
            border_col = QColor("#E5E5E5")

        self.line_number_area.set_colors(line_num_bg, line_num_text, border_col)
        self._current_line_color = current_line_highlight
        self._highlight_current_line()

        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Base, editor_bg)
        palette.setColor(QPalette.ColorRole.Text, editor_text)
        palette.setColor(QPalette.ColorRole.Highlight, selection_bg)
        palette.setColor(QPalette.ColorRole.HighlightedText, highlighted_text_color)
        self.setPalette(palette)

        self.viewport().update()
        self.update_line_number_area_width()

    def line_number_area_width(self):
        """Calculate the width needed for the line number area."""
        digits = len(str(max(1, self.document().blockCount()))) # Use document().blockCount()
        space = self.fontMetrics().horizontalAdvance('9') * digits + 12
        return max(40, space)

    def update_line_number_area_width(self, newBlockCount=0): # Parameter name changed for clarity
        """Sets the width of the line number area and updates viewport margins."""
        width = self.line_number_area_width()
        self.setViewportMargins(width, 0, 0, 0)
        self.line_number_area.update_width(width)

    # Slot for scrollbar changes
    def _update_line_number_area_on_scroll(self, value):
         # Use QTimer.singleShot to avoid potential direct repaint issues during scroll
         QTimer.singleShot(0, self.line_number_area.update)

    # Slot for viewport paint events (called via event filter)
    def _update_line_number_area(self):
         self.line_number_area.update()


    def resizeEvent(self, event):
        """Handles editor resize events."""
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def contextMenuEvent(self, event: QContextMenuEvent):
        """Creates and shows a custom context menu."""
        menu = QMenu(self)
        parent = self.parent()
        main_window = None
        while parent:
            if isinstance(parent, QMainWindow):
                main_window = parent
                break
            parent = parent.parent()

        undo_action = menu.addAction("撤销")
        undo_action.setEnabled(self.document().isUndoAvailable())
        undo_action.triggered.connect(self.undo)

        redo_action = menu.addAction("重做")
        redo_action.setEnabled(self.document().isRedoAvailable())
        redo_action.triggered.connect(self.redo)

        menu.addSeparator()

        cut_action = menu.addAction("剪切")
        cut_action.setEnabled(self.textCursor().hasSelection())
        cut_action.triggered.connect(self.cut)

        copy_action = menu.addAction("复制")
        copy_action.setEnabled(self.textCursor().hasSelection())
        copy_action.triggered.connect(self.copy)

        paste_action = menu.addAction("粘贴")
        clipboard = QApplication.clipboard()
        mime = clipboard.mimeData()
        can_paste_content = mime.hasText() or mime.hasImage()
        paste_action.setEnabled(can_paste_content)

        if main_window and hasattr(main_window, 'paste_action_wrapper'):
            paste_action.triggered.connect(main_window.paste_action_wrapper)
        else:
            paste_action.triggered.connect(self.paste) # Fallback to QTextEdit's paste
            print("Warning: Could not connect context menu paste to MainWindow's logic. Falling back to standard paste.")

        menu.addSeparator()

        select_all_action = menu.addAction("全选")
        select_all_action.setEnabled(True)
        select_all_action.triggered.connect(self.selectAll)

        menu.exec(event.globalPos())

    # --- Add methods to match QPlainTextEdit if needed by external code ---
    # Example: firstVisibleBlock (might behave differently)
    def firstVisibleBlock(self) -> QTextBlock:
         # QTextEdit doesn't have a direct equivalent.
         # This is an approximation, might not be perfect.
         cursor = self.cursorForPosition(QPoint(0, 0))
         return cursor.block()

    # Add other compatibility methods if required


# --- The main Atomic Widget: TextEditor ---
class TextEditor(BaseWidget):
    """
    An atomic text editor widget with line numbers, inheriting from BaseWidget.
    It contains an internal QTextEdit for the actual editing functionality.
    """
    # Forward signals from the internal editor
    textChanged = pyqtSignal()
    cursorPositionChanged = pyqtSignal()
    modificationChanged = pyqtSignal(bool) # Forward modification state

    def __init__(self, parent=None):
        super().__init__(parent)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._editor = _InternalTextEdit(self)
        layout.addWidget(self._editor)
        self.setLayout(layout)

    def _connect_signals(self):
        self._editor.textChanged.connect(self.textChanged)
        self._editor.cursorPositionChanged.connect(self.cursorPositionChanged)
        self._editor.document().modificationChanged.connect(self.modificationChanged) # Connect to document's signal

    def _apply_theme(self):
        self.update_colors(is_dark=False)

    def update_colors(self, is_dark: bool):
        if hasattr(self, '_editor'):
            self._editor.update_highlight_colors(is_dark)

    # --- Expose necessary methods from the internal editor ---
    # Changed setPlainText to setHtml to allow image insertion via HTML
    def setPlainText(self, text: str, clear_undo_stack=True):
        """Sets the editor's content as plain text (will be interpreted by QTextEdit)."""
        # Use setPlainText for initial loading if strict plain text is desired
        # Or use setHtml if the input might contain simple HTML/images
        self._editor.setPlainText(text)
        if clear_undo_stack:
             self._editor.document().clearUndoRedoStacks()
             self._editor.document().setModified(False)

    # Add setHtml if needed
    def setHtml(self, html: str, clear_undo_stack=True):
        """Sets the editor's content using HTML."""
        self._editor.setHtml(html)
        if clear_undo_stack:
             self._editor.document().clearUndoRedoStacks()
             self._editor.document().setModified(False)

    def toPlainText(self) -> str:
        """Gets the editor's content as plain text."""
        return self._editor.toPlainText()

    # Add toHtml if needed
    def toHtml(self) -> str:
        """Gets the editor's content as HTML."""
        return self._editor.toHtml()

    def textCursor(self) -> QTextCursor:
        return self._editor.textCursor()

    def moveCursor(self, operation: QTextCursor.MoveOperation, mode: QTextCursor.MoveMode = QTextCursor.MoveMode.MoveAnchor):
         self._editor.moveCursor(operation, mode)

    def setReadOnly(self, readOnly: bool):
        self._editor.setReadOnly(readOnly)

    def isReadOnly(self) -> bool:
        return self._editor.isReadOnly()

    def document(self):
         return self._editor.document()

    def isModified(self) -> bool:
        return self._editor.document().isModified()

    def setModified(self, modified: bool):
        self._editor.document().setModified(modified)

    def clear(self):
        self._editor.clear()

    def setFocus(self):
        self._editor.setFocus()

    # --- Add methods specific to QTextEdit if needed ---
    def insertHtml(self, html: str):
         self._editor.insertHtml(html)

    def insertPlainText(self, text: str):
         self._editor.insertPlainText(text)

    # Forward other relevant QTextEdit methods...
    def paste(self):
         self._editor.paste()
    def copy(self):
         self._editor.copy()
    def cut(self):
         self._editor.cut()
    def undo(self):
         self._editor.undo()
    def redo(self):
         self._editor.redo()
    def selectAll(self):
         self._editor.selectAll()
    def find(self, text: str, options: QTextDocument.FindFlag = 0) -> bool:
         return self._editor.find(text, options)
