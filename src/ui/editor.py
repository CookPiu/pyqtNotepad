import sys
# Change base class import but keep QTextEdit for ExtraSelection
# Import QFrame for setFrameStyle
from PyQt6.QtWidgets import QWidget, QPlainTextEdit, QTextEdit, QFrame
from PyQt6.QtGui import QPainter, QTextCursor, QColor, QPalette, QFontMetrics
from PyQt6.QtCore import Qt, QRect, QPointF, pyqtSignal, QPoint


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor # editor is TextEditWithLineNumbers (a QPlainTextEdit)
        self.setFixedWidth(40)  # Initial width, adjusted later
        self._background_color = QColor(Qt.GlobalColor.lightGray)
        self._text_color = QColor(Qt.GlobalColor.black)

    def set_colors(self, background: QColor, text: QColor):
        """Set background and text colors for the line number area."""
        self._background_color = background
        self._text_color = text
        self.update() # Trigger repaint

    def paintEvent(self, event):
        """Paints the line number area, adapted for QPlainTextEdit."""
        painter = QPainter(self)
        painter.fillRect(event.rect(), self._background_color)

        block = self.editor.firstVisibleBlock()
        block_number = block.blockNumber()
        # Use contentOffset provided by QPlainTextEdit for correct vertical positioning
        offset_y = self.editor.contentOffset().y()
        block_top = self.editor.blockBoundingGeometry(block).translated(0, offset_y).top()

        font_metrics = self.editor.fontMetrics()
        font_height = font_metrics.height()

        # Iterate through visible blocks
        while block.isValid() and block_top <= event.rect().bottom():
            if block.isVisible() and block_top + self.editor.blockBoundingRect(block).height() >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(self._text_color)
                # Draw text vertically centered within the block's height
                paint_rect = QRect(0, int(block_top), self.width() - 6, font_height) # Use 6 for padding consistency
                painter.drawText(paint_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, number)

            block = block.next()
            if block.isValid():
                 block_top = self.editor.blockBoundingGeometry(block).translated(0, offset_y).top()
            block_number += 1


# Change base class to QPlainTextEdit
class TextEditWithLineNumbers(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        # —— 去掉 QPlainTextEdit 默认 1px frame，使用正确的 Shape 枚举
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.line_number_area = LineNumberArea(self)
        self._current_line_color = QColor(Qt.GlobalColor.yellow).lighter(160)
        self._setup_highlight()

        # Connect signals for QPlainTextEdit
        self.blockCountChanged.connect(self.update_line_number_area_width) # Width update
        self.cursorPositionChanged.connect(self._highlight_current_line)   # Highlight update
        self.updateRequest.connect(self._update_line_number_area)         # Scroll/repaint update

        # Initial setup
        self.update_line_number_area_width() # Set initial width and margins

    def _setup_highlight(self):
        """Initializes the extra selection for current line highlighting."""
        self.extra_selections = [] # Ensure it's a list
        # Instantiate ExtraSelection from QTextEdit, even if base class is QPlainTextEdit
        self._current_line_selection = QTextEdit.ExtraSelection()
        fmt = self._current_line_selection.format
        fmt.setBackground(self._current_line_color)
        # Use the correct enum member for FullWidthSelection
        try:
             full_width_prop = QTextCursor.FormatProperty.FullWidthSelection
        except AttributeError:
             full_width_prop = 1 # Fallback

        fmt.setProperty(full_width_prop, True)
        self._current_line_selection.cursor = self.textCursor() # Assign initial cursor
        self._current_line_selection.cursor.clearSelection()
        self.extra_selections.append(self._current_line_selection) # Add to list
        self.setExtraSelections(self.extra_selections)

    def _highlight_current_line(self):
        """Updates the position of the current line highlight."""
        if not hasattr(self, 'extra_selections') or not self.extra_selections: # Safety check
             self._setup_highlight() # Reinitialize if list is missing or empty
             if not self.extra_selections: # If setup failed, exit
                 return

        current_selection = self.extra_selections[0] # Assume it's the first
        current_selection.format.setBackground(self._current_line_color) # Ensure color is up-to-date
        current_selection.cursor = self.textCursor()
        current_selection.cursor.clearSelection()
        self.setExtraSelections(self.extra_selections) # Re-apply the list

    def update_highlight_colors(self, is_dark: bool):
        """Updates colors for line number area and current line highlight based on theme."""
        if is_dark:
            # 行号列背景 = 编辑区背景 (深色 #1E1E1E)
            line_num_bg = QColor("#1E1E1E")
            line_num_text = QColor("#CCCCCC")
            current_line_highlight = QColor("#3A3D41") # Dark theme highlight
            editor_bg = QColor("#1E1E1E")
            editor_text = QColor("#D4D4D4")
            selection_bg = "#264F78" # Dark theme selection
            highlighted_text_color = editor_text # Usually same as base text on dark
        else:
            # 行号列背景 = 编辑区背景 (浅色 #FFFFFF)
            line_num_bg = QColor(Qt.GlobalColor.white) # Light theme line number background
            line_num_text = QColor(Qt.GlobalColor.black)       # Light theme line number text
            current_line_highlight = QColor(Qt.GlobalColor.yellow).lighter(160) # Light theme highlight
            editor_bg = QColor(Qt.GlobalColor.white)    # Light theme editor background
            editor_text = QColor(Qt.GlobalColor.black)       # Light theme editor text
            selection_bg = "#ADD6FF" # Light theme selection
            highlighted_text_color = editor_text # Usually same as base text on light
        # 定义边框颜色
        border_col = "#2B2B2B" if is_dark else "#E5E5E5"   # 跟全局 splitter 配色一致

        # Update Line Number Area colors
        self.line_number_area.set_colors(line_num_bg, line_num_text)

        # Update Current Line Highlight color
        self._current_line_color = current_line_highlight
        self._highlight_current_line() # Re-apply highlight with new color

        # Update base editor colors using Palette (more reliable for QPlainTextEdit)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Base, editor_bg)
        palette.setColor(QPalette.ColorRole.Text, editor_text)
        # Set selection color via palette
        palette.setColor(QPalette.ColorRole.Highlight, QColor(selection_bg))
        palette.setColor(QPalette.ColorRole.HighlightedText, highlighted_text_color)
        self.setPalette(palette)

        # Apply gutter styling via QSS (still okay for the separate widget)
        gutter_bg_hex = line_num_bg.name()
        gutter_fg_hex = line_num_text.name()
        # 应用 gutter 样式并添加右边框
        self.line_number_area.setStyleSheet(
            f"background:{gutter_bg_hex};"
            f"color:{gutter_fg_hex};"
            f"border-right:1px solid {border_col};"      # ← 关键：右侧 1 px 分界线
            "font:10pt 'Consolas';"
        )

        # Force repaint of editor viewport
        self.viewport().update()
        # Update gutter width when colors change (e.g., on tab switch)
        self.update_line_number_area_width()


    def line_number_area_width(self):
        """Calculate the width needed for the line number area."""
        digits = len(str(max(1, self.blockCount())))
        # VS Code style: ~4-6 chars + padding
        space = self.fontMetrics().horizontalAdvance('9') * digits + 6 # +6 pixel padding
        return space

    def update_line_number_area_width(self, _=0): # Parameter often unused, kept for signal compatibility
        """Sets the width of the line number area and updates viewport margins."""
        width = self.line_number_area_width()
        # Check if width actually changed to avoid unnecessary updates
        if self.line_number_area.width() != width:
            self.line_number_area.setFixedWidth(width)
            # Update viewport margins when width changes
            self.setViewportMargins(width, 0, 0, 0)

    # New slot connected to updateRequest
    def _update_line_number_area(self, rect, dy):
        """Slot connected to updateRequest signal. Handles scrolling and repainting."""
        if dy:
            # Vertical scroll: scroll the line number area
            self.line_number_area.scroll(0, dy)
        else:
            # Other updates (like resize, text changes): repaint the necessary part
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())

        # Update width if the viewport rect was entirely contained in the update rect
        # (This logic might need refinement depending on exact updateRequest behavior)
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width()

    def resizeEvent(self, event):
        """Handles editor resize events."""
        super().resizeEvent(event)
        cr = self.contentsRect()
        # Update the geometry of the line number area
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))
        # Ensure margins are correct after resize - update_line_number_area_width handles this now
        # self.update_line_number_area_width() # Call width update on resize


    # blockBoundingGeometry and blockBoundingRect are provided by QPlainTextEdit
    # firstVisibleBlock is also provided by QPlainTextEdit
