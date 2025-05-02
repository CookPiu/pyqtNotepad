import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSplitter, QToolBar, QFileDialog
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QFile, QIODevice, QTextStream, QSize
from PyQt6.QtGui import QColor, QPalette, QAction
from src.ui.editor import TextEditWithLineNumbers

class HtmlEditor(QWidget):
    """增强的HTML编辑器组件，提供编辑和预览功能"""
    
    # 定义信号
    document_modified = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self._is_modified = False
        self._file_path = None
        self._is_new = True
        self._is_pdf_converted = False
        self._pdf_temp_dir = None
        self._untitled_name = None
        
    def setup_ui(self):
        """设置UI组件"""
        # 创建主布局
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建工具栏
        self.toolbar = QToolBar("HTML编辑工具栏")
        self.toolbar.setIconSize(QSize(16, 16))
        
        # 添加编辑/预览切换按钮
        self.toggle_view_action = QAction("预览", self)
        self.toggle_view_action.setCheckable(True)
        self.toggle_view_action.toggled.connect(self.toggle_view)
        self.toolbar.addAction(self.toggle_view_action)
        
        # 添加工具栏到布局
        self.layout.addWidget(self.toolbar)
        
        # 创建分割器
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 创建编辑器（使用现有的TextEditWithLineNumbers）
        self.editor = TextEditWithLineNumbers()
        # 使用QPlainTextEdit兼容的方式设置字体大小
        font = self.editor.font()
        font.setPointSize(12)
        self.editor.setFont(font)
        self.editor.textChanged.connect(self.on_text_changed)
        
        # 创建预览视图
        self.preview = QWebEngineView()
        self.preview.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)  # 禁用右键菜单
        
        # 添加组件到分割器
        self.splitter.addWidget(self.editor)
        self.splitter.addWidget(self.preview)
        self.splitter.setSizes([400, 200])  # 默认分配大小
        
        # 初始状态：隐藏预览
        self.preview.hide()
        
        # 添加分割器到布局
        self.layout.addWidget(self.splitter)
    
    def toggle_view(self, checked):
        """切换编辑/预览视图"""
        if checked:  # 预览模式
            self.toggle_view_action.setText("编辑")
            self.update_preview()
            self.preview.show()
        else:  # 编辑模式
            self.toggle_view_action.setText("预览")
            self.preview.hide()
    
    def on_text_changed(self):
        """处理文本变更"""
        if not self._is_modified:
            self._is_modified = True
            self.document_modified.emit(True)
        
        # 如果预览可见，则更新预览
        if self.preview.isVisible():
            self.update_preview()
    
    def update_preview(self):
        """更新HTML预览"""
        # 使用document().toHtml()获取HTML内容，QPlainTextEdit没有直接的toHtml方法
        html_content = self.editor.document().toHtml()
        self.preview.setHtml(html_content)
    
    def set_html(self, html):
        """设置HTML内容"""
        # 使用document().setHtml()设置HTML内容，QPlainTextEdit没有直接的setHtml方法
        self.editor.document().setHtml(html)
        self._is_modified = False
        self.document_modified.emit(False)
    
    def set_plain_text(self, text):
        """设置纯文本内容"""
        self.editor.setPlainText(text)
        self._is_modified = False
        self.document_modified.emit(False)
    
    def to_html(self):
        """获取HTML内容"""
        # 使用document().toHtml()获取HTML内容，QPlainTextEdit没有直接的toHtml方法
        return self.editor.document().toHtml()
    
    def to_plain_text(self):
        """获取纯文本内容"""
        return self.editor.toPlainText()
    
    def update_highlight_colors(self, is_dark):
        """更新编辑器和预览的颜色"""
        # 更新编辑器颜色
        self.editor.update_highlight_colors(is_dark)
        
        # 更新预览背景色
        palette = self.preview.palette()
        bg_color = QColor("#1E1E1E") if is_dark else QColor(Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Base, bg_color)
        self.preview.setPalette(palette)
    
    # 属性访问方法，与TextEditWithLineNumbers兼容
    def get_property(self, name):
        """获取属性值"""
        if name == "file_path":
            return self._file_path
        elif name == "is_new":
            return self._is_new
        elif name == "is_pdf_converted":
            return self._is_pdf_converted
        elif name == "pdf_temp_dir":
            return self._pdf_temp_dir
        elif name == "untitled_name":
            return self._untitled_name
        return None
    
    # 重写QObject的property方法，使其与我们的get_property兼容
    def property(self, name):
        return self.get_property(name)
    
    def setProperty(self, name, value):
        """设置属性值"""
        if name == "file_path":
            self._file_path = value
        elif name == "is_new":
            self._is_new = value
        elif name == "is_pdf_converted":
            self._is_pdf_converted = value
        elif name == "pdf_temp_dir":
            self._pdf_temp_dir = value
        elif name == "untitled_name":
            self._untitled_name = value
    
    # 文档修改状态方法
    def document(self):
        """返回一个与QTextDocument兼容的对象"""
        # 返回编辑器的document对象，而不是self
        return self.editor.document()
    
    def isModified(self):
        """返回文档是否被修改"""
        return self._is_modified
    
    def setModified(self, modified):
        """设置文档修改状态"""
        if self._is_modified != modified:
            self._is_modified = modified
            self.document_modified.emit(modified)
    
    # 光标和选择相关方法
    def textCursor(self):
        """获取文本光标"""
        return self.editor.textCursor()
    
    # 转发编辑器的信号和方法
    def setFontPointSize(self, size):
        """设置字体大小"""
        # 使用QPlainTextEdit兼容的方式设置字体大小
        font = self.editor.font()
        font.setPointSize(size)
        self.editor.setFont(font)
    
    # 添加与TextEditWithLineNumbers兼容的方法
    def copyAvailable(self):
        """获取copyAvailable信号"""
        return self.editor.copyAvailable
    
    def cut(self):
        """剪切选中内容"""
        self.editor.cut()
    
    def copy(self):
        """复制选中内容"""
        self.editor.copy()
    
    def paste(self):
        """粘贴内容"""
        self.editor.paste()
    
    def selectAll(self):
        """全选内容"""
        self.editor.selectAll()
    
    def insertHtml(self, html):
        """插入HTML内容"""
        # QPlainTextEdit没有直接的insertHtml方法，需要使用textCursor
        cursor = self.editor.textCursor()
        cursor.insertHtml(html)
        self.editor.setTextCursor(cursor)
    
    def insertPlainText(self, text):
        """插入纯文本内容"""
        self.editor.insertPlainText(text)