from PyQt6.QtCore import QUrl, pyqtSignal, QObject, pyqtSlot, QUrlQuery
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QStackedWidget # Added QTextEdit, QStackedWidget
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView
import os
import sys


class PyQtBridge(QObject):
    """用于JavaScript和PyQt之间的通信桥接"""
    contentChangedSignal = pyqtSignal(str) 
    editorReadySignal = pyqtSignal()      # Renamed signal
    fileImportedSignal = pyqtSignal(str)  # Renamed signal
    exportFileSignal = pyqtSignal(str)    # Renamed signal
    
    @pyqtSlot(str)
    def contentChanged(self, html): # Slot name for JS
        self.contentChangedSignal.emit(html)
    
    @pyqtSlot()
    def editorReady(self): # Slot name for JS
        self.editorReadySignal.emit()
        
    @pyqtSlot(str)
    def fileImported(self, filename): # Slot name for JS
        self.fileImportedSignal.emit(filename)
        
    @pyqtSlot(str)
    def exportFile(self, content): # Slot name for JS
        self.exportFileSignal.emit(content)


class WangEditor(QWidget):
    document_modified = pyqtSignal(bool)
    view_mode_changed = pyqtSignal(int)  # 保持与原HtmlEditor相同的信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_modified = False
        self._current_editor_mode = 1  # 0 for source, 1 for rich text (wangEditor)
        self._editor_is_ready = False
        self._pending_html_to_set = None
        self._setup_ui()
        
    def _setup_ui(self):
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建WebEngineView来加载wangEditor (富文本视图)
        self.web_view = QWebEngineView(self)
        
        # 创建QTextEdit用于源码编辑 (源码视图)
        self.source_code_editor = QTextEdit(self)
        self.source_code_editor.setAcceptRichText(False) # Ensure plain text editing
        self.source_code_editor.setVisible(False) # Initially hidden

        # 创建QStackedWidget来管理视图切换
        self.stacked_widget = QStackedWidget(self)
        self.stacked_widget.addWidget(self.web_view) # Index 0 for rich text (wangEditor)
        self.stacked_widget.addWidget(self.source_code_editor) # Index 1 for source code

        # 配置WebEngineView设置
        settings = self.web_view.page().settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        
        # 创建通信桥接
        self.bridge = PyQtBridge(self)
        self.bridge.contentChangedSignal.connect(self._on_content_changed)
        self.bridge.editorReadySignal.connect(self._on_editor_ready)     # Connect to renamed signal
        self.bridge.fileImportedSignal.connect(self._on_file_imported) # Connect to renamed signal
        self.bridge.exportFileSignal.connect(self._on_export_file)     # Connect to renamed signal
        
        # 将桥接对象添加到JavaScript环境
        self.web_view.page().setWebChannel(self._create_web_channel())
        
        # 添加StackedWidget到布局
        layout.addWidget(self.stacked_widget)
        self.setLayout(layout)

        # 连接loadFinished信号
        self.web_view.loadFinished.connect(self._on_load_finished)
        
        # 加载wangEditor HTML文件
        self._load_editor()
    
    def _create_web_channel(self):
        from PyQt6.QtWebChannel import QWebChannel
        # Try setting the parent of QWebChannel to self (the WangEditor widget)
        # instead of self.web_view.page() to see if it affects lifecycle or availability.
        channel = QWebChannel(self) 
        channel.registerObject("pyqtBridge", self.bridge)
        return channel
    
    def _on_load_finished(self, success):
        print(f"Page load finished. Success: {success}")
        if not success:
            # 可以根据需要添加更详细的错误处理或日志记录
            page = self.web_view.page()
            print(f"Page load error: {page.loadErrorCode()}, URL: {page.url().toString()}") # Qt 6.2+
            # For older Qt versions, error information might be harder to get directly here.

    def _load_editor(self):
        # 尝试禁用缓存 - HttpCacheEnabled 属性在当前PyQt版本可能不存在，暂时注释掉
        # settings = self.web_view.page().settings()
        # settings.setAttribute(QWebEngineSettings.WebAttribute.HttpCacheEnabled, False) 

        # 获取wangEditor的HTML文件路径
        editor_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))), 
                                 "wangEditor", "editor.html") # Restore to original editor.html
        
        # 确保文件存在
        if not os.path.exists(editor_path):
            print(f"错误：找不到wangEditor HTML文件: {editor_path}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"找不到wangEditor HTML文件: {editor_path}")
            return
        
        # 为URL附加时间戳以尝试绕过缓存
        import time
        url = QUrl.fromLocalFile(editor_path)
        query = QUrlQuery()
        query.addQueryItem("timestamp", str(int(time.time())))
        url.setQuery(query)
        
        # 加载编辑器
        self.web_view.load(url)
        print(f"正在加载编辑器 (尝试禁用缓存): {url.toString()}")
    
    def _on_content_changed(self, html):
        # 当编辑器内容变化时触发
        # print(f"Editor content changed (Python side): {html[:100]}...") # Debugging line
        if not self._is_modified:
            self._is_modified = True
            self.document_modified.emit(True)
    
    def _on_editor_ready(self):
        # 编辑器加载完成时触发
        print("编辑器已准备就绪 (Python _on_editor_ready)")
        self._editor_is_ready = True
        if self._pending_html_to_set is not None:
            print(f"DEBUG: Editor is ready, setting pending HTML: {self._pending_html_to_set[:100]}...")
            self._execute_set_html_js(self._pending_html_to_set)
            self._pending_html_to_set = None
        
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
        """设置编辑模式: 0=源码, 1=富文本编辑 (wangEditor)"""
        if mode == self._current_editor_mode:
            return

        if mode == 0: # Switch to source code view
            # Get HTML from wangEditor and display in source_code_editor
            self.toHtml(self._display_source_code)
        elif mode == 1: # Switch to rich text view (wangEditor)
            # Get HTML from source_code_editor and set to wangEditor
            source_html = self.source_code_editor.toPlainText()
            self.setHtml(source_html) # This will also make web_view visible via _display_rich_text
            self._display_rich_text() # Ensure correct view is shown
        else:
            print(f"Unsupported edit mode: {mode}")
            return
            
        self._current_editor_mode = mode
        self.view_mode_changed.emit(mode)

    def _display_source_code(self, html_from_editor):
        """Callback for toHtml, sets content to source editor and shows it."""
        self.source_code_editor.setPlainText(html_from_editor)
        self.stacked_widget.setCurrentWidget(self.source_code_editor)

    def _display_rich_text(self):
        """Shows the wangEditor (rich text) view."""
        self.stacked_widget.setCurrentWidget(self.web_view)

    def set_preview_visible(self, show_preview: bool):
        """
        兼容接口: True for rich text (wangEditor), False for source code.
        wangEditor is always 'preview' in the old sense.
        """
        if show_preview:
            self.set_edit_mode(1)  # Rich text mode
        else:
            self.set_edit_mode(0)  # Source code mode
    
    def setHtml(self, html_source: str, baseUrl=None):
        """设置HTML内容"""
        print(f"DEBUG: WangEditor.setHtml called with html_source (first 100 chars): {html_source[:100]}") # 调试打印
        # 使用JavaScript接口设置内容
        # 使用json.dumps确保HTML内容被正确转义为JavaScript字符串
        import json
        if self._editor_is_ready:
            self._execute_set_html_js(html_source)
        else:
            print("DEBUG: WangEditor.setHtml - Editor not ready, queuing HTML.")
            self._pending_html_to_set = html_source
        
        # Modification status should be set after content is actually applied or if it's a new load
        # self._is_modified = False 
        # self.document_modified.emit(False) 
        # Let on_editor_content_changed in MainWindow handle this via signals if needed,
        # or after _execute_set_html_js if it's a direct set.
        # For now, let's assume a setHtml implies the content is "clean" from the source.
        if self._editor_is_ready: # Only if we actually set it now
            self._is_modified = False
            self.document_modified.emit(False)


    def _execute_set_html_js(self, html_to_set: str):
        import json
        js_code = f"if(window.setHtmlContent) window.setHtmlContent({json.dumps(html_to_set)}); else console.error('window.setHtmlContent not defined when trying to execute');"
        self.web_view.page().runJavaScript(js_code)
        # After successfully executing, mark as not modified
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
