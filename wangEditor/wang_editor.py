import os
import base64
import uuid
from PyQt6.QtCore import QObject, pyqtSlot, QUrl, QDir
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtNetwork import QSslSocket
from PyQt6.QtWidgets import QMenu, QApplication, QMainWindow # Added
from PyQt6.QtGui import QAction # Added
from PyQt6.QtCore import Qt # Added


class CustomWebPage(QWebEnginePage):
    """自定义WebPage类，用于处理SSL证书错误"""
    
    def __init__(self, profile, parent=None):
        super().__init__(profile, parent)
        print(f"SSL支持状态: {QSslSocket.supportsSsl()}")
        print(f"SSL库版本: {QSslSocket.sslLibraryVersionString()}")
    
    def certificateError(self, error):
        # 记录详细的SSL错误信息
        error_code = error.error()
        url = error.url().toString()
        description = error.errorDescription()
        print(f"SSL证书错误: {description}")
        print(f"错误码: {error_code}, URL: {url}")
        print(f"错误类型: {self._get_ssl_error_type(error_code)}")
        
        # 忽略所有SSL证书错误
        error.ignoreCertificateError()
        return True
    
    def _get_ssl_error_type(self, error_code):
        """根据错误码返回更详细的SSL错误类型描述"""
        ssl_errors = {
            1: "证书未被信任的机构签名",
            2: "证书已过期",
            3: "证书尚未生效",
            4: "证书已被吊销",
            5: "证书主机名不匹配",
            6: "证书无法验证",
            7: "证书包含无效签名",
            8: "证书使用了不安全的算法",
            9: "证书包含无效数据"
        }
        return ssl_errors.get(error_code, f"未知SSL错误 ({error_code})")


class PyQtBridge(QObject):
    """与wangEditor通信的桥接类"""
    
    def __init__(self, parent=None, upload_dir=None):
        super().__init__(parent)
        # 设置图片上传目录，默认为当前目录下的uploads文件夹
        self.upload_dir = upload_dir or os.path.join(QDir.currentPath(), "uploads")
        # 确保上传目录存在
        if not os.path.exists(self.upload_dir):
            os.makedirs(self.upload_dir)
    
    @pyqtSlot()
    def editorReady(self):
        """编辑器准备就绪时调用"""
        print("编辑器已准备就绪")
    
    @pyqtSlot(str)
    def contentChanged(self, html):
        """内容变化时调用"""
        # 可以在这里处理内容变化事件
        pass
    
    @pyqtSlot(str)
    def fileImported(self, filename):
        """文件导入时调用"""
        print(f"文件已导入: {filename}")
    
    @pyqtSlot(str)
    def exportFile(self, content):
        """导出文件时调用"""
        # 可以在这里处理文件导出逻辑
        pass
    
    @pyqtSlot(str, str, 'QJSValue')
    def uploadImage(self, base64data, filename, callback):
        """处理图片上传
        
        Args:
            base64data: 图片的base64编码数据
            filename: 原始文件名
            callback: JavaScript回调函数，用于返回图片URL
        """
        try:
            # 从base64数据中提取实际的图片数据（去除前缀）
            if "," in base64data:
                base64data = base64data.split(",", 1)[1]
            
            # 解码base64数据
            image_data = base64.b64decode(base64data)
            
            # 检查上传目录是否存在，不存在则创建
            if not os.path.exists(self.upload_dir):
                os.makedirs(self.upload_dir)
                print(f"创建上传目录: {self.upload_dir}")
            
            # 生成唯一文件名
            file_ext = os.path.splitext(filename)[1].lower()
            # 如果没有扩展名，根据文件头判断类型
            if not file_ext:
                # 简单的文件类型检测
                if image_data.startswith(b'\xff\xd8\xff'):
                    file_ext = '.jpg'
                elif image_data.startswith(b'\x89PNG\r\n'):
                    file_ext = '.png'
                elif image_data.startswith(b'GIF87a') or image_data.startswith(b'GIF89a'):
                    file_ext = '.gif'
                elif image_data.startswith(b'RIFF') and image_data[8:12] == b'WEBP':
                    file_ext = '.webp'
                else:
                    file_ext = '.jpg'  # 默认使用jpg
            
            unique_filename = f"{uuid.uuid4().hex}{file_ext}"
            file_path = os.path.join(self.upload_dir, unique_filename)
            
            # 保存图片
            with open(file_path, "wb") as f:
                f.write(image_data)
            
            # 构建图片URL（使用file://协议）
            # 确保使用正确的协议，避免混合内容警告
            image_url = QUrl.fromLocalFile(file_path).toString(QUrl.UrlFormattingOption.None_)
            
            # 调用JavaScript回调函数，返回图片URL
            callback.call([image_url])
            
            print(f"图片已上传: {file_path}")
            return True
            
        except Exception as e:
            print(f"图片上传失败: {str(e)}")
            callback.call([None])  # 返回None表示上传失败
            return False


class WangEditor(QWebEngineView):
    """wangEditor编辑器组件"""
    
    def __init__(self, parent=None, upload_dir=None):
        super().__init__(parent)
        
        # 配置WebEngine设置
        self.profile = QWebEngineProfile.defaultProfile()
        self.profile.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        self.profile.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        self.profile.settings().setAttribute(QWebEngineSettings.WebAttribute.AllowInsecureContent, True)
        
        # 创建自定义页面以处理SSL错误
        self.custom_page = CustomWebPage(self.profile, self)
        self.setPage(self.custom_page)
        
        # 创建WebChannel和桥接对象
        self.channel = QWebChannel(self.page())
        self.bridge = PyQtBridge(self, upload_dir)
        self.channel.registerObject("pyqtBridge", self.bridge)
        self.page().setWebChannel(self.channel)
        
        # 设置页面加载错误处理
        self.page().loadFinished.connect(self._on_load_finished)
        
        # 加载编辑器HTML文件
        editor_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "editor.html")
        self.load(QUrl.fromLocalFile(editor_path))

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        main_window = None
        # Try to find MainWindow by traversing up the parent hierarchy
        parent_widget = self.parent()
        while parent_widget:
            if isinstance(parent_widget, QMainWindow):
                main_window = parent_widget
                break
            parent_widget = parent_widget.parent()
        
        # Standard Web Actions
        action_undo = self.page().action(QWebEnginePage.WebAction.Undo)
        action_undo.setText("撤销")
        menu.addAction(action_undo)

        action_redo = self.page().action(QWebEnginePage.WebAction.Redo)
        action_redo.setText("重做")
        menu.addAction(action_redo)
        
        menu.addSeparator()
        
        action_cut = self.page().action(QWebEnginePage.WebAction.Cut)
        action_cut.setText("剪切")
        menu.addAction(action_cut)
        
        action_copy = self.page().action(QWebEnginePage.WebAction.Copy)
        action_copy.setText("复制")
        menu.addAction(action_copy)
        
        action_paste = self.page().action(QWebEnginePage.WebAction.Paste)
        action_paste.setText("粘贴")
        menu.addAction(action_paste)
        
        menu.addSeparator()
        
        action_select_all = self.page().action(QWebEnginePage.WebAction.SelectAll)
        action_select_all.setText("全选")
        menu.addAction(action_select_all)

        has_selection = self.hasSelection()
        if has_selection:
            menu.addSeparator()
            
            translate_action = menu.addAction("翻译选中内容")
            if main_window and hasattr(main_window, 'translate_selection_wrapper'):
                translate_action.triggered.connect(main_window.translate_selection_wrapper)
            else:
                translate_action.setEnabled(False)
                print("WangEditor: Warning - Could not connect translate to MainWindow wrapper.")

            calc_action = menu.addAction("计算选中内容")
            if main_window and hasattr(main_window, 'calculate_selection_wrapper'):
                calc_action.triggered.connect(main_window.calculate_selection_wrapper)
            else:
                calc_action.setEnabled(False)
                print("WangEditor: Warning - Could not connect calculate to MainWindow wrapper.")

            ai_action = menu.addAction("将选中内容复制到 AI 助手")
            if main_window and hasattr(main_window, 'copy_to_ai_wrapper'):
                ai_action.triggered.connect(main_window.copy_to_ai_wrapper)
            else:
                ai_action.setEnabled(False)
                print("WangEditor: Warning - Could not connect copy_to_ai to MainWindow wrapper.")

        menu.exec(event.globalPos())
    
    def _on_load_finished(self, success):
        """页面加载完成后的处理"""
        if not success:
            print("编辑器HTML加载失败")
            return
        
        # 确保WebChannel正确初始化
        self.page().runJavaScript("""
            if (typeof window.initWebChannel === 'function') {
                window.initWebChannel();
                console.log('WebChannel初始化已触发');
            } else {
                console.error('initWebChannel函数未定义');
            }
        """)
        
        print("编辑器HTML加载完成")
    
    def setHtml(self, html):
        """设置编辑器内容"""
        self.page().runJavaScript(f"window.setHtmlContent(`{html}`);")
    
    def getHtml(self, callback):
        """获取编辑器内容
        
        Args:
            callback: 回调函数，接收HTML内容作为参数
        """
        self.page().runJavaScript("window.getHtmlContent();", callback)
    
    def toHtml(self, callback=None):
        """获取HTML内容（兼容接口）
        
        Args:
            callback: 回调函数，接收HTML内容作为参数
        """
        self.getHtml(callback)
    
    def setUploadDir(self, directory):
        """设置图片上传目录
        
        Args:
            directory: 图片上传目录的路径
        """
        if os.path.exists(directory) and os.path.isdir(directory):
            self.bridge.upload_dir = directory
        else:
            # 如果目录不存在，尝试创建
            try:
                os.makedirs(directory)
                self.bridge.upload_dir = directory
            except Exception as e:
                print(f"设置上传目录失败: {str(e)}")
