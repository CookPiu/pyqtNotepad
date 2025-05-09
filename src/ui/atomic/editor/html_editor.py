import os
from PyQt6.QtWidgets import (QWidget, QPlainTextEdit, QVBoxLayout, QHBoxLayout, 
                             QStackedWidget, QFrame, QTextEdit, QToolBar) # Added QTextEdit, QToolBar
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QUrl, QRect, QSize
from PyQt6.QtGui import QColor, QPainter, QTextCharFormat, QFont, QPalette, QTextCursor, QPaintEvent, QIcon, QAction, QTextListFormat # Added QPaintEvent, QIcon, QAction, QTextListFormat

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

class RichTextEditor(QTextEdit):
    """富文本编辑器组件，用于所见即所得的HTML编辑"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptRichText(True)
        # 设置默认字体和样式
        font = QFont("Arial", 10)
        self.setFont(font)
        # 启用HTML支持
        self.document().setDefaultStyleSheet("body { font-family: Arial; font-size: 10pt; }")

    def insertFromMimeData(self, source):
        # 重写此方法以支持粘贴图片和富文本
        super().insertFromMimeData(source)

class HtmlEditor(QWidget):
    document_modified = pyqtSignal(bool)
    view_mode_changed = pyqtSignal(int) # 0: 源码, 1: 预览, 2: 富文本编辑

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_base_url = QUrl.fromLocalFile(os.getcwd() + os.path.sep) # Default base URL, ensure trailing slash

        # 源码编辑器部分，带行号
        self.editor_area_widget = QWidget(self)
        editor_area_layout = QHBoxLayout(self.editor_area_widget)
        editor_area_layout.setContentsMargins(0,0,0,0)
        editor_area_layout.setSpacing(0)

        self.source_editor = QPlainTextEdit(self.editor_area_widget) # For HTML source
        self.source_editor.setAcceptDrops(False) # Disable drops to let MainWindow handle file drops
        self.line_numbers = LineNumberArea(self.source_editor)
        
        editor_area_layout.addWidget(self.line_numbers)
        editor_area_layout.addWidget(self.source_editor)
        self.editor_area_widget.setLayout(editor_area_layout)

        # 预览部分
        self.preview = QWebEngineView(self)
        settings = self.preview.page().settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        
        # 富文本编辑器部分
        self.rich_text_container = QWidget(self)
        rich_text_layout = QVBoxLayout(self.rich_text_container)
        rich_text_layout.setContentsMargins(0,0,0,0)
        
        # 添加富文本编辑工具栏
        self.rich_text_toolbar = QToolBar("富文本编辑工具栏")
        self.rich_text_toolbar.setIconSize(QSize(16, 16))
        
        # 创建富文本编辑器
        self.rich_text_editor = RichTextEditor(self)
        self.rich_text_editor.textChanged.connect(self._on_rich_text_changed)
        
        # 添加常用格式化操作
        self._setup_rich_text_toolbar()
        
        rich_text_layout.addWidget(self.rich_text_toolbar)
        rich_text_layout.addWidget(self.rich_text_editor)
        
        # 使用堆叠小部件在三种模式之间切换
        self.stacked_widget = QStackedWidget(self)
        self.SOURCE_MODE = 0
        self.PREVIEW_MODE = 1
        self.RICH_TEXT_MODE = 2
        
        self.editor_page_index = self.stacked_widget.addWidget(self.editor_area_widget)  # 索引 0
        self.preview_page_index = self.stacked_widget.addWidget(self.preview)            # 索引 1
        self.rich_text_page_index = self.stacked_widget.addWidget(self.rich_text_container) # 索引 2

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.addWidget(self.stacked_widget)
        self.setLayout(main_layout)

        self._render_timer = QTimer(self, interval=250, singleShot=True) # Timer for preview update
        self._render_timer.timeout.connect(self._update_preview_from_source)
        self._rich_to_source_timer = QTimer(self, interval=500, singleShot=True) # 富文本到源码的更新定时器
        self._rich_to_source_timer.timeout.connect(self._update_source_from_rich_text)

        # Connect signals for line number area updates
        self.source_editor.blockCountChanged.connect(self._update_line_number_area_width)
        self.source_editor.updateRequest.connect(self._update_line_number_area_on_request)
        # self.source_editor.cursorPositionChanged.connect(self._highlight_current_line_in_editor) # Optional

        self.source_editor.textChanged.connect(self._on_source_editor_text_changed)
        self.source_editor.document().modificationChanged.connect(self.document_modified)

        self.current_mode = self.SOURCE_MODE # 默认从源码模式开始
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

    def _setup_rich_text_toolbar(self):
        """设置富文本编辑器工具栏"""
        # 文本格式化操作
        bold_action = QAction("粗体", self)
        bold_action.setShortcut("Ctrl+B")
        bold_action.triggered.connect(lambda: self.rich_text_editor.setFontWeight(
            QFont.Weight.Bold if self.rich_text_editor.fontWeight() < QFont.Weight.Bold else QFont.Weight.Normal))
        self.rich_text_toolbar.addAction(bold_action)
        
        italic_action = QAction("斜体", self)
        italic_action.setShortcut("Ctrl+I")
        italic_action.triggered.connect(self.rich_text_editor.setFontItalic)
        self.rich_text_toolbar.addAction(italic_action)
        
        underline_action = QAction("下划线", self)
        underline_action.setShortcut("Ctrl+U")
        underline_action.triggered.connect(self.rich_text_editor.setFontUnderline)
        self.rich_text_toolbar.addAction(underline_action)
        
        self.rich_text_toolbar.addSeparator()
        
        # 对齐方式
        align_left_action = QAction("左对齐", self)
        align_left_action.triggered.connect(lambda: self.rich_text_editor.setAlignment(Qt.AlignmentFlag.AlignLeft))
        self.rich_text_toolbar.addAction(align_left_action)
        
        align_center_action = QAction("居中", self)
        align_center_action.triggered.connect(lambda: self.rich_text_editor.setAlignment(Qt.AlignmentFlag.AlignCenter))
        self.rich_text_toolbar.addAction(align_center_action)
        
        align_right_action = QAction("右对齐", self)
        align_right_action.triggered.connect(lambda: self.rich_text_editor.setAlignment(Qt.AlignmentFlag.AlignRight))
        self.rich_text_toolbar.addAction(align_right_action)
        
        self.rich_text_toolbar.addSeparator()
        
        # 列表
        bullet_list_action = QAction("项目符号", self)
        bullet_list_action.triggered.connect(self._toggle_bullet_list)
        self.rich_text_toolbar.addAction(bullet_list_action)
        
        # 插入图片
        insert_image_action = QAction("插入图片", self)
        insert_image_action.triggered.connect(self._insert_image_to_rich_text)
        self.rich_text_toolbar.addAction(insert_image_action)
    
    def _toggle_bullet_list(self):
        """切换项目符号列表"""
        cursor = self.rich_text_editor.textCursor()
        list_format = cursor.blockFormat()
        
        if list_format.indent() == 0:
            list_format.setIndent(1)
            cursor.setBlockFormat(list_format)
            list_style = QTextListFormat()
            list_style.setStyle(QTextListFormat.Style.ListDisc)
            cursor.createList(list_style)
        else:
            list_format.setIndent(0)
            cursor.setBlockFormat(list_format)
        
    def _insert_image_to_rich_text(self):
        """在富文本编辑器中插入图片"""
        from PyQt6.QtWidgets import QFileDialog
        file_name, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if file_name:
            self.rich_text_editor.insertHtml(f'<img src="{file_name}" />')
    
    def _on_source_editor_text_changed(self):
        self.document_modified.emit(True) # 源码已更改
        if self.current_mode == self.PREVIEW_MODE: # 如果预览处于活动状态，则更新它
            self._render_timer.start()
        elif self.current_mode == self.RICH_TEXT_MODE: # 如果富文本编辑器处于活动状态，也需要更新
            # 这里我们需要小心，避免循环更新
            # 只有当源码编辑器的内容变化不是由富文本编辑器引起的时才更新富文本编辑器
            if not self._rich_to_source_timer.isActive():
                self._update_rich_text_from_source()
    
    def _on_rich_text_changed(self):
        """富文本编辑器内容变化时的处理"""
        self.document_modified.emit(True) # 内容已更改
        # 启动定时器，延迟更新源码，避免频繁更新
        self._rich_to_source_timer.start()
    
    def _update_preview_from_source(self): # 使用 self._current_base_url
        html_source = self.source_editor.toPlainText()
        if self.preview.page():
            self.preview.page().setHtml(html_source, self._current_base_url)
        else: # 如果页面不可用，应该不会发生
            self.preview.setHtml(html_source, self._current_base_url)
    
    def _update_rich_text_from_source(self):
        """从源码更新富文本编辑器"""
        html_source = self.source_editor.toPlainText()
        self.rich_text_editor.setHtml(html_source)
    
    def _update_source_from_rich_text(self):
        """从富文本编辑器更新源码"""
        rich_html = self.rich_text_editor.toHtml()
        # 阻止源码编辑器的textChanged信号触发_on_source_editor_text_changed
        # 这样可以避免循环更新
        self.source_editor.blockSignals(True)
        self.source_editor.setPlainText(rich_html)
        self.source_editor.blockSignals(False)
        # 如果预览模式是活动的，也更新预览
        if self.current_mode == self.PREVIEW_MODE:
            self._update_preview_from_source()


    def set_edit_mode(self, mode: int):
        """设置编辑模式: 0=源码, 1=预览, 2=富文本编辑"""
        if mode < 0 or mode > 2:
            return
            
        if mode == self.current_mode:
            return
            
        old_mode = self.current_mode
        self.current_mode = mode
        
        # 在切换模式前同步内容
        if old_mode == self.SOURCE_MODE:
            # 从源码模式切换出来，需要更新预览和富文本
            if mode == self.PREVIEW_MODE:
                self._update_preview_from_source()
            elif mode == self.RICH_TEXT_MODE:
                self._update_rich_text_from_source()
                
        elif old_mode == self.RICH_TEXT_MODE:
            # 从富文本模式切换出来，需要更新源码和预览
            self._update_source_from_rich_text()
            if mode == self.PREVIEW_MODE:
                self._update_preview_from_source()
        
        # 切换到目标模式
        if mode == self.SOURCE_MODE:
            self.stacked_widget.setCurrentIndex(self.editor_page_index)
            self.source_editor.setFocus()
        elif mode == self.PREVIEW_MODE:
            self.stacked_widget.setCurrentIndex(self.preview_page_index)
            self.preview.setFocus()
        elif mode == self.RICH_TEXT_MODE:
            self.stacked_widget.setCurrentIndex(self.rich_text_page_index)
            self.rich_text_editor.setFocus()
            
        # 发出模式变化信号
        self.view_mode_changed.emit(mode)
    
    def set_preview_visible(self, show_preview: bool):
        """在源码编辑器和预览之间切换（向后兼容）"""
        if show_preview:
            self.set_edit_mode(self.PREVIEW_MODE)
        else:
            self.set_edit_mode(self.SOURCE_MODE)

    # --- 内容访问方法 ---
    def setHtml(self, html_source: str, baseUrl: QUrl = QUrl()):
        self.source_editor.setPlainText(html_source)
        if baseUrl.isValid() and not baseUrl.isEmpty(): # 检查是否提供了有效的非空baseUrl
            self._current_base_url = baseUrl
        
        # 更新预览和富文本编辑器
        self._update_preview_from_source() 
        self._update_rich_text_from_source()
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

    # --- 焦点和其他QWidget方法 ---
    def setFocus(self):
        if self.current_mode == self.PREVIEW_MODE:
            self.preview.setFocus()
        elif self.current_mode == self.RICH_TEXT_MODE:
            self.rich_text_editor.setFocus()
        else:
            self.source_editor.setFocus()

if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QButtonGroup, QRadioButton
    class TestHtmlEditorWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("HTML Editor Test")
            self.editor = HtmlEditor(self)
            self.setCentralWidget(self.editor)
            
            toolbar = QToolBar("HTML Tools")
            self.addToolBar(toolbar)
            
            # 创建模式切换按钮组
            self.mode_group = QButtonGroup(self)
            
            self.source_btn = QRadioButton("源码", self)
            self.source_btn.setChecked(True) # 默认选中源码模式
            self.mode_group.addButton(self.source_btn, 0)
            toolbar.addWidget(self.source_btn)
            
            self.preview_btn = QRadioButton("预览", self)
            self.mode_group.addButton(self.preview_btn, 1)
            toolbar.addWidget(self.preview_btn)
            
            self.rich_text_btn = QRadioButton("富文本编辑", self)
            self.mode_group.addButton(self.rich_text_btn, 2)
            toolbar.addWidget(self.rich_text_btn)
            
            # 连接模式切换信号
            self.mode_group.idClicked.connect(self.editor.set_edit_mode)
            self.editor.view_mode_changed.connect(self._on_mode_changed)

            self.editor.setHtml("<h1>Hello World</h1><p>This is a test HTML document.</p><p>Try editing in <b>rich text mode</b>!</p>")
            self.setGeometry(100, 100, 900, 600)
        
        def _on_mode_changed(self, mode):
            # 更新按钮状态
            if mode == 0:
                self.source_btn.setChecked(True)
            elif mode == 1:
                self.preview_btn.setChecked(True)
            elif mode == 2:
                self.rich_text_btn.setChecked(True)

    app = QApplication(sys.argv)
    win = TestHtmlEditorWindow()
    win.show()
    sys.exit(app.exec())
