import sys
import os
from PyQt6.QtWidgets import (QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QTextEdit, QListWidget, QListWidgetItem, QToolBar, QMenuBar, QMenu,
                             QStatusBar, QFileDialog, QFontDialog, QColorDialog, QMessageBox,
                             QInputDialog, QSplitter)
from PyQt6.QtGui import QAction, QFont, QColor, QTextCursor, QIcon, QImage, QTextDocument, QPainter
from PyQt6.QtCore import Qt, QSize, QUrl, QRect, QEvent, pyqtSignal, QPointF, QFile, QTextStream
from theme_manager import ThemeManager
from file_explorer import FileExplorer
import fitz  # PyMuPDF库
from pdf_utils import extract_pdf_content, cleanup_temp_images
from pdf_viewer import PDFViewer


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self.setFixedWidth(40)  # 初始宽度，会根据行号数量自动调整

    def paintEvent(self, event):
        # 绘制行号区域
        painter = QPainter(self)
        painter.fillRect(event.rect(), Qt.GlobalColor.lightGray)
        
        # 获取可见区域的第一个块
        block = self.editor.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.editor.blockBoundingGeometry(block).translated(self.editor.contentOffset()).top()
        bottom = top + self.editor.blockBoundingRect(block).height()
        
        # 绘制行号
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(Qt.GlobalColor.black)
                # 创建一个矩形区域来绘制文本
                rect = QRect(0, int(top), self.width() - 5, self.editor.fontMetrics().height())
                painter.drawText(rect, Qt.AlignmentFlag.AlignRight, number)
            
            block = block.next()
            top = bottom
            bottom = top + self.editor.blockBoundingRect(block).height()
            block_number += 1


class TextEditWithLineNumbers(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)
        
        # 连接信号以更新行号区域
        self.document().blockCountChanged.connect(self.update_line_number_area_width)
        self.verticalScrollBar().valueChanged.connect(self.update_line_number_area)
        self.textChanged.connect(self.update_line_number_area)
        self.document().documentLayoutChanged.connect(self.update_line_number_area)
        self.textChanged.connect(self.document_modified)
        
        # 初始化行号区域宽度
        self.update_line_number_area_width(0)
        
        # 设置文档修改状态标志
        self.document().setModified(False)
    
    def firstVisibleBlock(self):
        # 获取可见区域的第一个文本块
        cursor = QTextCursor(self.document())
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        for i in range(self.document().blockCount()):
            block = self.document().findBlockByNumber(i)
            rect = self.document().documentLayout().blockBoundingRect(block)
            if rect.translated(0, -self.verticalScrollBar().value()).top() >= 0:
                return block
            cursor.movePosition(QTextCursor.MoveOperation.NextBlock)
        return self.document().firstBlock()
    
    def blockBoundingGeometry(self, block):
        # 获取块的几何信息
        return self.document().documentLayout().blockBoundingRect(block)
    
    def blockBoundingRect(self, block):
        # 获取块的边界矩形
        return self.document().documentLayout().blockBoundingRect(block)
    
    def contentOffset(self):
        # 获取内容偏移
        return QPointF(0, -self.verticalScrollBar().value())
    
    def update_line_number_area_width(self, _):
        # 更新行号区域宽度
        digits = len(str(max(1, self.document().blockCount())))
        width = 10 + self.fontMetrics().horizontalAdvance('9') * digits
        if self.line_number_area.width() != width:
            self.line_number_area.setFixedWidth(width)
            self.setViewportMargins(width, 0, 0, 0)
    
    def update_line_number_area(self):
        # 更新行号区域
        self.line_number_area.update(0, 0, self.line_number_area.width(), self.height())
        if self.verticalScrollBar().value() != self.verticalScrollBar().maximum():
            self.setViewportMargins(self.line_number_area.width(), 0, 0, 0)
    
    def resizeEvent(self, event):
        # 调整大小时更新行号区域
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area.width(), cr.height()))
    
    def paintEvent(self, event):
        # 绘制间隔行的半阴影效果
        painter = QPainter(self.viewport())
        painter.fillRect(event.rect(), self.palette().base())
        
        # 获取可见区域的第一个块
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        
        # 绘制间隔行背景
        while block.isValid():
            # 获取当前块的位置和高度
            rect = self.blockBoundingGeometry(block).translated(self.contentOffset())
            top = rect.top()
            
            # 如果已经超出可见区域，退出循环
            if top > event.rect().bottom():
                break
                
            if block.isVisible():
                # 为偶数行添加半阴影效果
                if block_number % 2 == 1:
                    # 使用块的实际几何信息创建矩形
                    rect = QRect(0, int(top), self.viewport().width(), int(rect.height()))
                    
                    # 根据当前主题选择合适的阴影颜色
                    if self.palette().base().color().lightness() < 128:  # 深色主题
                        # 使用更深的颜色作为深色主题的间隔行背景色
                        painter.fillRect(rect, QColor(45, 45, 45, 150))
                    else:  # 浅色主题
                        # 使用浅灰色作为浅色主题的间隔行背景色
                        painter.fillRect(rect, QColor(240, 240, 240, 100))
            
            block = block.next()
            block_number += 1
        
        # 调用父类的绘制事件以绘制文本
        painter.end()
        super().paintEvent(event)
    
    def document_modified(self):
        # 标记文档为已修改状态
        self.document().setModified(True)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 初始化主题管理器
        self.theme_manager = ThemeManager()
        
        # 初始化PDF临时目录变量
        self.current_pdf_temp_dir = None
        
        self.initUI()
        
        # 应用当前主题
        self.apply_current_theme()
        
    def initUI(self):
        # 设置窗口标题和大小
        self.setWindowTitle("多功能记事本")
        self.setGeometry(100, 100, 800, 600)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建工具栏
        self.toolbar = QToolBar("主工具栏")
        self.toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(self.toolbar)
        
        # 添加工具栏按钮
        toolbar_items = [
            {"name": "新建", "icon": "document-new", "action": self.new_file},
            {"name": "打开", "icon": "document-open", "action": self.open_file},
            {"name": "保存", "icon": "document-save", "action": self.save_file},
            {"name": "格式", "icon": "format-text-bold", "action": self.change_font},
            {"name": "查找", "icon": "edit-find", "action": self.find_text},
            {"name": "替换", "icon": "edit-find-replace", "action": self.replace_text},
            {"name": "插入图片", "icon": "insert-image", "action": self.insert_image}
        ]
        
        for item in toolbar_items:
            action = QAction(item["name"], self)
            action.triggered.connect(item["action"])
            self.toolbar.addAction(action)
        
        # 创建侧边栏容器（使用QSplitter分割上下两部分）
        self.sidebar_splitter = QSplitter(Qt.Orientation.Vertical)
        self.sidebar_splitter.setMaximumWidth(200)
        self.sidebar_splitter.setMinimumWidth(150)
        
        # 创建上半部分功能列表
        self.sidebar = QListWidget()
        
        # 添加侧边栏功能占位符
        sidebar_items = [
            {"name": "计时器", "icon": "clock"},
            {"name": "待办事项", "icon": "task-list"},
            {"name": "便签", "icon": "note"},
            {"name": "计算器", "icon": "calculator"},
            {"name": "日历", "icon": "calendar"}
        ]
        
        for item in sidebar_items:
            list_item = QListWidgetItem(item["name"])
            # 设置工具提示
            list_item.setToolTip(f"{item['name']}功能（占位符）")
            self.sidebar.addItem(list_item)
        
        # 连接点击事件（目前只显示消息）
        self.sidebar.itemClicked.connect(self.sidebar_item_clicked)
        
        # 创建下半部分文件浏览器
        self.file_explorer = FileExplorer()
        self.file_explorer.file_double_clicked.connect(self.open_file_from_explorer)
        
        # 将两部分添加到分割器中
        self.sidebar_splitter.addWidget(self.sidebar)
        self.sidebar_splitter.addWidget(self.file_explorer)
        
        # 设置初始分割比例（上半部分占40%，下半部分占60%）
        self.sidebar_splitter.setSizes([200, 300])
        
        # 创建带行号的富文本编辑区
        self.text_edit = TextEditWithLineNumbers()
        self.text_edit.setFontPointSize(12)
        
        # 创建编辑区布局
        edit_layout = QHBoxLayout()
        edit_layout.addWidget(self.sidebar_splitter)
        edit_layout.addWidget(self.text_edit)
        
        # 将编辑区布局添加到主布局
        main_layout.addLayout(edit_layout)
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建状态栏
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("就绪")
        
        # 初始化文件路径
        self.current_file = None
    
    def create_menu_bar(self):
        # 创建菜单栏
        menu_bar = self.menuBar()
        
        # 文件菜单
        file_menu = menu_bar.addMenu("文件")
        
        new_action = QAction("新建", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)
        
        open_action = QAction("打开", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        save_action = QAction("保存", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("另存为", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = menu_bar.addMenu("编辑")
        
        undo_action = QAction("撤销", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self.text_edit.undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("重做", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(self.text_edit.redo)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        cut_action = QAction("剪切", self)
        cut_action.setShortcut("Ctrl+X")
        cut_action.triggered.connect(self.text_edit.cut)
        edit_menu.addAction(cut_action)
        
        copy_action = QAction("复制", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self.text_edit.copy)
        edit_menu.addAction(copy_action)
        
        paste_action = QAction("粘贴", self)
        paste_action.setShortcut("Ctrl+V")
        paste_action.triggered.connect(self.text_edit.paste)
        edit_menu.addAction(paste_action)
        
        edit_menu.addSeparator()
        
        select_all_action = QAction("全选", self)
        select_all_action.setShortcut("Ctrl+A")
        select_all_action.triggered.connect(self.text_edit.selectAll)
        edit_menu.addAction(select_all_action)
        
        # 格式菜单
        format_menu = menu_bar.addMenu("格式")
        
        font_action = QAction("字体", self)
        font_action.triggered.connect(self.change_font)
        format_menu.addAction(font_action)
        
        color_action = QAction("颜色", self)
        color_action.triggered.connect(self.change_color)
        format_menu.addAction(color_action)
        
        format_menu.addSeparator()
        
        insert_image_action = QAction("插入图片", self)
        insert_image_action.triggered.connect(self.insert_image)
        format_menu.addAction(insert_image_action)
        
        format_menu.addSeparator()
        
        # 主题切换菜单项
        theme_action = QAction("切换主题", self)
        theme_action.setShortcut("Ctrl+T")
        theme_action.triggered.connect(self.toggle_theme)
        format_menu.addAction(theme_action)
        
        # 帮助菜单
        help_menu = menu_bar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    # 侧边栏功能点击事件
    def sidebar_item_clicked(self, item):
        if item.text() == "计时器":
            # 打开计时器窗口
            from timer import TimerWindow
            self.timer_window = TimerWindow(self)
            self.timer_window.show()
            self.statusBar.showMessage(f"已打开{item.text()}功能")
        else:
            # 其他功能仍然显示占位符消息
            self.statusBar.showMessage(f"'{item.text()}'是功能占位符，尚未实现实际功能")
            QMessageBox.information(self, "功能占位符", f"'{item.text()}'功能尚未实现，这只是一个UI占位符。")
    
    def new_file(self):
        if self.maybe_save():
            # 清理之前PDF文件的临时图片
            if self.current_pdf_temp_dir:
                cleanup_temp_images(self.current_pdf_temp_dir)
                self.current_pdf_temp_dir = None
                
            self.text_edit.clear()
            self.current_file = None
            self.statusBar.showMessage("新建文件")
    
    def open_file(self):
        if self.maybe_save():
            file_name, _ = QFileDialog.getOpenFileName(self, "打开文件", "", "HTML文件 (*.html);;文本文件 (*.txt);;PDF文件 (*.pdf);;所有文件 (*)")
            if file_name:
                # 根据文件扩展名决定如何打开
                _, ext = os.path.splitext(file_name)
                if ext.lower() == '.html':
                    with open(file_name, 'r', encoding='utf-8') as f:
                        html = f.read()
                    self.text_edit.setHtml(html)
                elif ext.lower() == '.pdf':
                    try:
                        # 打开PDF预览窗口
                        self.open_pdf_preview(file_name)
                    except Exception as e:
                        QMessageBox.critical(self, "错误", f"无法打开PDF文件: {str(e)}")
                        return
                else:
                    try:
                        with open(file_name, 'r', encoding='utf-8') as f:
                            text = f.read()
                        self.text_edit.setPlainText(text)
                    except UnicodeDecodeError:
                        # 尝试使用其他编码
                        try:
                            with open(file_name, 'r', encoding='gbk') as f:
                                text = f.read()
                            self.text_edit.setPlainText(text)
                        except Exception as e:
                            QMessageBox.critical(self, "错误", f"无法打开文件: {str(e)}")
                            return
                self.current_file = file_name
                self.statusBar.showMessage(f"已打开: {file_name}")
    
    def save_file(self):
        if self.current_file:
            # 根据文件扩展名决定如何保存
            _, ext = os.path.splitext(self.current_file)
            with open(self.current_file, 'w', encoding='utf-8') as f:
                if ext.lower() == '.html':
                    f.write(self.text_edit.toHtml())
                else:
                    f.write(self.text_edit.toPlainText())
            self.statusBar.showMessage(f"已保存: {self.current_file}")
            return True
        else:
            return self.save_file_as()
    
    def save_file_as(self):
        # 如果当前文件是PDF，默认保存为文本格式
        default_filter = "文本文件 (*.txt)"
        if self.current_file and self.current_file.lower().endswith('.pdf'):
            default_filter = "文本文件 (*.txt)"
            
        file_name, selected_filter = QFileDialog.getSaveFileName(self, "保存文件", "", "HTML文件 (*.html);;文本文件 (*.txt);;所有文件 (*)", default_filter)
        if file_name:
            # 确保文件有正确的扩展名
            _, ext = os.path.splitext(file_name)
            if not ext:
                if "HTML" in selected_filter:
                    file_name += ".html"
                elif "文本" in selected_filter:
                    file_name += ".txt"
            
            # 根据扩展名决定保存格式
            _, ext = os.path.splitext(file_name)
            with open(file_name, 'w', encoding='utf-8') as f:
                if ext.lower() == '.html':
                    f.write(self.text_edit.toHtml())
                else:
                    f.write(self.text_edit.toPlainText())
            self.current_file = file_name
            self.statusBar.showMessage(f"已保存: {file_name}")
            return True
        return False
    
    def maybe_save(self):
        if not self.text_edit.document().isModified():
            return True
        
        ret = QMessageBox.warning(self, "多功能记事本",
                                "文档已被修改。\n是否保存更改？",
                                QMessageBox.StandardButton.Save | 
                                QMessageBox.StandardButton.Discard | 
                                QMessageBox.StandardButton.Cancel)
        
        if ret == QMessageBox.StandardButton.Save:
            return self.save_file()
        elif ret == QMessageBox.StandardButton.Cancel:
            return False
        return True
        
    def open_pdf_preview(self, pdf_path):
        """打开PDF预览窗口"""
        # 清理之前PDF文件的临时图片
        if self.current_pdf_temp_dir:
            cleanup_temp_images(self.current_pdf_temp_dir)
            self.current_pdf_temp_dir = None
            
        # 创建PDF预览窗口
        pdf_viewer = PDFViewer(pdf_path, self)
        
        # 连接转换信号
        pdf_viewer.convert_to_html_signal.connect(self.convert_pdf_to_html)
        
        # 显示PDF预览窗口
        pdf_viewer.exec()
        
    def convert_pdf_to_html(self, pdf_path):
        """将PDF转换为HTML并显示"""
        try:
            # 使用pdf_utils模块处理PDF文件
            html_content, temp_dir = extract_pdf_content(pdf_path, self)
            if html_content:
                # 保存临时目录路径，以便后续清理
                self.current_pdf_temp_dir = temp_dir
                # 显示HTML内容
                self.text_edit.setHtml(html_content)
                self.statusBar.showMessage(f"已转换为HTML: {pdf_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法转换PDF文件: {str(e)}")
            return
    
    def change_font(self):
        current = self.text_edit.currentFont()
        font, ok = QFontDialog.getFont(current, self, "选择字体")
        if ok:
            self.text_edit.setCurrentFont(font)
    
    def change_color(self):
        color = QColorDialog.getColor(self.text_edit.textColor(), self, "选择颜色")
        if color.isValid():
            self.text_edit.setTextColor(color)
    
    def find_text(self):
        # 简单实现，实际应用中可以添加一个查找对话框
        text, ok = QInputDialog.getText(self, "查找", "输入要查找的文本:")
        if ok and text:
            cursor = self.text_edit.textCursor()
            # 保存原始位置
            original_position = cursor.position()
            # 从头开始查找
            cursor.movePosition(QTextCursor.Start)
            self.text_edit.setTextCursor(cursor)
            if not self.text_edit.find(text):
                # 如果没找到，恢复原始位置
                cursor.setPosition(original_position)
                self.text_edit.setTextCursor(cursor)
                QMessageBox.information(self, "查找", f"未找到 '{text}'")
    
    def replace_text(self):
        # 简单实现，实际应用中可以添加一个替换对话框
        find_text, ok = QInputDialog.getText(self, "查找", "输入要查找的文本:")
        if ok and find_text:
            replace_text, ok = QInputDialog.getText(self, "替换", "输入要替换的文本:")
            if ok:  # 即使替换文本为空也执行替换
                cursor = self.text_edit.textCursor()
                # 保存原始位置
                original_position = cursor.position()
                # 从头开始查找
                cursor.movePosition(QTextCursor.Start)
                self.text_edit.setTextCursor(cursor)
                
                # 查找并替换所有匹配项
                count = 0
                while self.text_edit.find(find_text):
                    # 获取当前选择
                    cursor = self.text_edit.textCursor()
                    # 替换选中的文本
                    cursor.insertText(replace_text)
                    count += 1
                
                if count > 0:
                    self.statusBar.showMessage(f"已替换 {count} 处匹配项")
                else:
                    # 如果没有找到匹配项，恢复原始光标位置
                    cursor = self.text_edit.textCursor()
                    cursor.setPosition(original_position)
                    self.text_edit.setTextCursor(cursor)
                    self.statusBar.showMessage("未找到匹配项")
    
    def open_file_from_explorer(self, file_path):
        """从文件浏览器打开文件"""
        if self.maybe_save():
            try:
                # 根据文件扩展名决定如何打开
                _, ext = os.path.splitext(file_path)
                # 图片和二进制文件类型
                binary_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.exe', '.dll']
                
                if ext.lower() == '.html':
                    with open(file_path, 'r', encoding='utf-8') as f:
                        html = f.read()
                    self.text_edit.setHtml(html)
                elif ext.lower() == '.pdf':
                    try:
                        # 打开PDF预览窗口
                        self.open_pdf_preview(file_path)
                    except Exception as e:
                        QMessageBox.critical(self, "错误", f"无法打开PDF文件: {str(e)}")
                        return
                elif ext.lower() in binary_extensions:
                    QMessageBox.information(self, "不支持的文件类型", f"无法打开二进制文件: {ext}")
                    return
                else:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            text = f.read()
                        self.text_edit.setPlainText(text)
                    except UnicodeDecodeError:
                        # 尝试使用其他编码
                        try:
                            with open(file_path, 'r', encoding='gbk') as f:
                                text = f.read()
                            self.text_edit.setPlainText(text)
                        except Exception as e:
                            QMessageBox.critical(self, "错误", f"无法打开文件: {str(e)}")
                            return
                
                self.current_file = file_path
                # 重置文档修改状态
                self.text_edit.document().setModified(False)
                self.statusBar.showMessage(f"已打开: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"打开文件时出错: {str(e)}")
                return
    
    def insert_image(self):
        # 打开文件对话框选择图片
        file_name, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif)")
        if file_name:
            # 获取当前光标位置
            cursor = self.text_edit.textCursor()
            
            # 创建图片对象
            image = QImage(file_name)
            if image.isNull():
                QMessageBox.warning(self, "插入图片", "无法加载图片！")
                return
            
            # 如果图片太大，调整大小
            if image.width() > 800:
                image = image.scaledToWidth(800, Qt.TransformationMode.SmoothTransformation)
            
            # 将图片转换为Base64编码
            import base64
            from PyQt6.QtCore import QByteArray, QBuffer
            from PyQt6.QtGui import QImageWriter
            
            # 确定图片格式
            _, ext = os.path.splitext(file_name)
            img_format = ext[1:].upper()  # 去掉点号，转为大写
            if img_format.lower() == 'jpg':
                img_format = 'JPEG'
            
            # 将图片转换为字节数组
            byte_array = QByteArray()
            buffer = QBuffer(byte_array)
            buffer.open(QBuffer.OpenModeFlag.WriteOnly)
            image_writer = QImageWriter(buffer, img_format.encode())
            image_writer.write(image)
            buffer.close()
            
            # 转换为Base64编码
            img_data = byte_array.data()
            base64_data = base64.b64encode(img_data).decode('utf-8')
            
            # 创建内联图片URL
            img_url = f"data:image/{img_format.lower()};base64,{base64_data}"
            
            # 将图片插入到文档中
            document = self.text_edit.document()
            document.addResource(QTextDocument.ResourceType.ImageResource, QUrl(img_url), image)
            cursor.insertImage(img_url)
            
            self.statusBar.showMessage(f"已插入图片: {os.path.basename(file_name)}")
    
    def show_about(self):
        QMessageBox.about(self, "关于多功能记事本", 
                         "多功能记事本 v1.1\n\n一个基于PyQt6的简单记事本应用，支持HTML格式和图片插入。支持计时器功能")
    
    def apply_current_theme(self):
        """应用当前主题样式表"""
        try:
            # 获取当前应用程序实例
            app = QApplication.instance()
            # 应用主题
            self.theme_manager.apply_theme(app)
            # 更新文件浏览器主题
            if hasattr(self, 'file_explorer'):
                self.file_explorer.update_theme(self.theme_manager.get_current_theme())
            # 更新状态栏消息
            theme_name = "白色" if self.theme_manager.get_current_theme() == ThemeManager.LIGHT_THEME else "黑色"
            self.statusBar.showMessage(f"已应用{theme_name}主题", 3000)
        except Exception as e:
            print(f"应用主题时出错: {str(e)}")
    
    def toggle_theme(self):
        """切换主题"""
        # 切换主题
        self.theme_manager.toggle_theme()
        # 应用新主题
        self.apply_current_theme()
        # 显示主题切换消息
        theme_name = "白色" if self.theme_manager.get_current_theme() == ThemeManager.LIGHT_THEME else "黑色"
        QMessageBox.information(self, "主题切换", f"已切换到{theme_name}主题")
    
    def closeEvent(self, event):
        """重写关闭事件，在关闭窗口前检查是否需要保存文件"""
        if self.maybe_save():
            # 清理临时图片文件
            if self.current_pdf_temp_dir:
                cleanup_temp_images(self.current_pdf_temp_dir)
            event.accept()
        else:
            event.ignore()


# 这里不需要main函数，因为主程序在Serial.py中