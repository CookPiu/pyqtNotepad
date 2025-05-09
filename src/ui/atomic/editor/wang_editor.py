from PyQt6.QtCore import QUrl, pyqtSignal, QObject, pyqtSlot
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView
import os
import sys


class PyQtBridge(QObject):
    """用于JavaScript和PyQt之间的通信桥接"""
    contentChanged = pyqtSignal(str)
    editorReady = pyqtSignal()
    fileImported = pyqtSignal(str)  # 文件导入信号，参数为文件名
    exportFile = pyqtSignal(str)   # 文件导出信号，参数为内容
    
    @pyqtSlot(str)
    def contentChanged(self, html):
        self.contentChanged.emit(html)
    
    @pyqtSlot()
    def editorReady(self):
        self.editorReady.emit()
        
    @pyqtSlot(str)
    def fileImported(self, filename):
        self.fileImported.emit(filename)
        
    @pyqtSlot(str)
    def exportFile(self, content):
        self.exportFile.emit(content)


class WangEditor(QWidget):
    document_modified = pyqtSignal(bool)
    view_mode_changed = pyqtSignal(int)  # 保持与原HtmlEditor相同的信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._is_modified = False
        self._current_mode = 1  # 默认为预览模式，因为wangEditor本身就是富文本编辑器
        
    def _setup_ui(self):
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建WebEngineView来加载wangEditor
        self.web_view = QWebEngineView(self)
        
        # 配置WebEngineView设置
        settings = self.web_view.page().settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        
        # 创建通信桥接
        self.bridge = PyQtBridge(self)
        self.bridge.contentChanged.connect(self._on_content_changed)
        self.bridge.editorReady.connect(self._on_editor_ready)
        self.bridge.fileImported.connect(self._on_file_imported)
        self.bridge.exportFile.connect(self._on_export_file)
        
        # 将桥接对象添加到JavaScript环境
        self.web_view.page().setWebChannel(self._create_web_channel())
        
        # 添加WebEngineView到布局
        layout.addWidget(self.web_view)
        self.setLayout(layout)
        
        # 加载wangEditor HTML文件
        self._load_editor()
    
    def _create_web_channel(self):
        from PyQt6.QtWebChannel import QWebChannel
        channel = QWebChannel(self.web_view.page())
        channel.registerObject("pyqtBridge", self.bridge)
        return channel
    
    def _load_editor(self):
        # 获取wangEditor的HTML文件路径
        editor_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))), 
                                 "wangEditor", "editor.html")
        
        # 确保文件存在
        if not os.path.exists(editor_path):
            print(f"错误：找不到wangEditor HTML文件: {editor_path}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"找不到wangEditor HTML文件: {editor_path}")
            return
        
        # 加载编辑器
        self.web_view.load(QUrl.fromLocalFile(editor_path))
        print(f"正在加载编辑器: {editor_path}")
    
    def _on_content_changed(self, html):
        # 当编辑器内容变化时触发
        if not self._is_modified:
            self._is_modified = True
            self.document_modified.emit(True)
    
    def _on_editor_ready(self):
        # 编辑器加载完成时触发
        print("编辑器已准备就绪")
        
    def _on_file_imported(self, filename):
        # 当从编辑器导入文件时触发
        print(f"已导入文件: {filename}")
        self._is_modified = True
        self.document_modified.emit(True)
        
    def _on_export_file(self, content):
        # 当从编辑器导出文件时触发
        from PyQt6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出文件",
            "",
            "HTML文件 (*.html);;文本文件 (*.txt);;所有文件 (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"文件已导出到: {file_path}")
            except Exception as e:
                print(f"导出文件时出错: {str(e)}")
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "导出错误", f"导出文件时出错: {str(e)}")

    
    # --- 兼容原HtmlEditor的API ---
    
    def set_edit_mode(self, mode: int):
        """设置编辑模式: 0=源码, 1=预览, 2=富文本编辑
        注意：wangEditor本身就是富文本编辑器，所以这里只是为了兼容原接口"""
        if mode != self._current_mode:
            self._current_mode = mode
            self.view_mode_changed.emit(mode)
    
    def set_preview_visible(self, show_preview: bool):
        """在源码编辑器和预览之间切换（向后兼容）"""
        if show_preview:
            self.set_edit_mode(1)  # 预览模式
        else:
            self.set_edit_mode(0)  # 源码模式
    
    def setHtml(self, html_source: str, baseUrl=None):
        """设置HTML内容"""
        # 使用JavaScript接口设置内容
        # 转义反引号和其他特殊字符，确保JavaScript代码正确执行
        escaped_html = html_source.replace('`', '\`').replace('\\', '\\\\')
        js_code = f"setHtmlContent(`{escaped_html}`);"
        self.web_view.page().runJavaScript(js_code)
        self._is_modified = False
        self.document_modified.emit(False)
        
    def import_file(self):
        """从文件导入内容"""
        from PyQt6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入文件",
            "",
            "HTML文件 (*.html);;文本文件 (*.txt);;Markdown文件 (*.md);;所有文件 (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.setHtml(content)
                print(f"已导入文件: {file_path}")
                return True
            except Exception as e:
                print(f"导入文件时出错: {str(e)}")
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "导入错误", f"导入文件时出错: {str(e)}")
                return False
        return False
    
    def toHtml(self, callback=None):
        """获取HTML内容"""
        def _handle_html(html):
            if callback:
                callback(html)
            else:
                return html
        
        self.web_view.page().runJavaScript("getHtmlContent();", _handle_html)
        
    def export_file(self):
        """导出内容到文件"""
        from PyQt6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出文件",
            "",
            "HTML文件 (*.html);;文本文件 (*.txt);;所有文件 (*)"
        )
        
        if file_path:
            def save_content(html):
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(html)
                    print(f"文件已导出到: {file_path}")
                    self._is_modified = False
                    self.document_modified.emit(False)
                    return True
                except Exception as e:
                    print(f"导出文件时出错: {str(e)}")
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.critical(self, "导出错误", f"导出文件时出错: {str(e)}")
                    return False
            
            # 获取HTML内容并保存
            self.toHtml(save_content)
            return True
        return False
    
    def setPlainText(self, text: str):
        """设置纯文本内容（兼容接口）"""
        self.setHtml(text)
    
    def toPlainText(self, callback=None):
        """获取纯文本内容（兼容接口）"""
        return self.toHtml(callback)
    
    def isModified(self) -> bool:
        """检查内容是否被修改"""
        return self._is_modified
    
    def setModified(self, modified: bool):
        """设置修改状态"""
        self._is_modified = modified
        self.document_modified.emit(modified)
    
    def get_text_edit_widget(self):
        """获取文本编辑控件（兼容接口）"""
        return self.web_view
    
    def update_editor_theme_colors(self, text_color, background_color, border_color, current_line_bg_color):
        """更新编辑器主题颜色（兼容接口）"""
        # 可以通过JavaScript注入CSS来实现主题切换
        pass
    
    def setFocus(self):
        """设置焦点"""
        self.web_view.setFocus()