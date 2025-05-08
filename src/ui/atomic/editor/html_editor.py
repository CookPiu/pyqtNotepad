# src/ui/atomic/editor/html_editor.py
import os
from PyQt6.QtWebEngineWidgets import QWebEngineView # QWebEnginePage is in Core
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings # Correct module for QWebEnginePage and QWebEngineSettings
# Removed incorrect import: from PyQt6.QtWebEngineCore.backends.web_engine_settings import QWebEngineSettings
from PyQt6.QtCore import QUrl, pyqtSignal, QObject, Qt, QTimer # Import QTimer for delayed execution
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QColor, QFocusEvent # Import QFocusEvent

# No longer need BaseWidget or TextEditor imports here

class HtmlEditor(QWebEngineView):
    """
    HTML editor component based on QWebEngineView with JavaScript enabled.
    """
    # Signal emitted when modification state changes (potentially triggered via JS)
    document_modified = pyqtSignal(bool)
    # Signal to potentially emit HTML content when retrieved asynchronously
    html_content_ready = pyqtSignal(str)
    plain_text_ready = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus) # Set focus policy
        self.setAttribute(Qt.WidgetAttribute.WA_InputMethodEnabled, True) # Enable input method handling

        # --- Enable JavaScript ---
        settings = self.page().settings() # Get settings from the page
        # Correct the enum name to WebAttribute
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        # Optional: Enable other features if needed, e.g., local content access
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)

        # --- Internal State ---
        self._is_modified = False
        self._file_path = None
        self._is_new = True
        self._untitled_name = None
        # PDF related state removed, should be managed elsewhere if needed

        # 设置JavaScript消息处理器
        self.page().javaScriptConsoleMessage = self._handle_js_console_message

        # Set initial blank page or content (removed contenteditable)
        self.setHtml("<!DOCTYPE html><html><head></head><body></body></html>")
        self.setModified(False) # Start unmodified

        # Connect load finished signal to potentially run setup JS
        self.page().loadFinished.connect(self._on_load_finished)

    def _handle_js_console_message(self, level, message, line, source_id):
        """处理JavaScript控制台消息"""
        # 日志级别：0=Info, 1=Warning, 2=Error
        if level > 0:  # 只记录警告和错误
            print(f"JS {['Info', 'Warning', 'Error'][level]} ({source_id}:{line}): {message}")
            
        # 检查是否为翻译事件相关消息
        if "translateText" in message:
            print(f"译事件触发: {message}")
            
    def _on_load_finished(self, ok):
        """Run JavaScript after the page finishes loading."""
        if ok:
            # Example: Inject CSS for basic theme handling (can be expanded)
            # self.apply_theme_js(is_dark=False) # Apply default theme
            # Enable designMode and try focusing body
            self.run_js("document.designMode = 'on'; document.body.focus();")
            # Inject the paste handler script
            self._inject_paste_handler()
            # Inject the context menu handler script
            self._inject_context_menu_handler()
            # 注入翻译事件监听器
            self._inject_translation_listener()
            # print("HtmlEditor _on_load_finished: Enabled designMode, attempted focus, and injected handlers.") # Debug

    def _inject_paste_handler(self):
        """Injects JavaScript to handle image pasting with resizing."""
        # Max width for pasted images
        max_width = 200
        
        # Escape curly braces for the f-string by doubling them {{ }}
        # Add console logs for debugging
        script = f"""
        (function() {{
            console.log("Attempting to inject paste handler for HTML editor.");
            document.body.addEventListener('paste', function(event) {{
                console.log("Paste event triggered in HTML editor.");
                const items = (event.clipboardData || window.clipboardData).items;
                let imageFound = false;

                if (!items) {{
                    console.log("Paste event: No clipboard items found.");
                    return; // Exit if no items
                }}
                console.log(`Paste event: Found ${{items.length}} clipboard items.`);

                for (let i = 0; i < items.length; i++) {{
                    console.log(`Item ${{i}}: kind=${{items[i].kind}}, type=${{items[i].type}}`);
                    if (items[i].kind === 'file' && items[i].type.startsWith('image/')) {{
                        console.log("Image file found in clipboard. Preventing default paste.");
                        event.preventDefault(); // Stop default paste
                        imageFound = true;
                        const file = items[i].getAsFile();
                        if (!file) {{
                            console.error("Could not get file from clipboard item.");
                            continue; // Try next item
                        }}
                        const reader = new FileReader();

                        reader.onload = function(e) {{
                            console.log("FileReader onload triggered.");
                            const dataUrl = e.target.result;
                            if (!dataUrl) {{
                                console.error("FileReader result (dataUrl) is empty.");
                                return;
                            }}
                            const tempImg = new Image();
                            tempImg.onload = function() {{
                                console.log("Temporary image loaded from dataUrl.");
                                const originalWidth = tempImg.naturalWidth;
                                const originalHeight = tempImg.naturalHeight;
                                console.log(`Original image size: ${{originalWidth}}x${{originalHeight}}`);
                                let targetWidth = originalWidth;
                                let targetHeight = originalHeight;
                                const maxWidth = {max_width}; // Use Python variable

                                if (originalWidth > maxWidth) {{
                                    const ratio = maxWidth / originalWidth;
                                    targetWidth = maxWidth;
                                    targetHeight = Math.round(originalHeight * ratio);
                                    console.log(`Resizing image to: ${{targetWidth}}x${{targetHeight}}`);
                                }} else {{
                                     console.log("Image width is within limit, using original size.");
                                }}

                                // Escape curly braces in the generated HTML string for the f-string
                                const imgHtml = `<img src="${{{{dataUrl}}}}" width="${{{{targetWidth}}}}" height="${{{{targetHeight}}}}">`;
                                console.log("Inserting HTML:", imgHtml);
                                // Use execCommand to insert HTML at cursor position
                                try {{
                                    const success = document.execCommand('insertHTML', false, imgHtml);
                                    console.log(`document.execCommand('insertHTML') success: ${{success}}`);
                                    // Optionally, try to signal modification back to Python if needed
                                    // window.qt_bridge.setModified(true); // If a bridge exists
                                }} catch (err) {{
                                     console.error("Error executing insertHTML:", err);
                                }}
                            }};
                            tempImg.onerror = function() {{
                                console.error("Error loading temporary image from dataUrl.");
                            }};
                            tempImg.src = dataUrl;
                        }};
                        reader.onerror = function() {{
                             console.error("FileReader error reading file.");
                        }};
                        reader.readAsDataURL(file);
                        break; // Handle only the first image found
                    }}
                }}
                if (!imageFound) {{
                    console.log("No image file found in paste event, allowing default paste.");
                }}
            }});
            console.log("Paste handler successfully injected for HTML editor.");
        }})();
        """
        self.run_js(script)

    def _inject_context_menu_handler(self):
        """Injects JavaScript to handle right-click context menu with custom options."""
        script = """
        (function() {
            document.addEventListener('contextmenu', function(event) {
                // 获取选中的文本
                const selectedText = window.getSelection().toString().trim();
                
                // 检查是否点击在图片上
                const target = event.target;
                const isImage = target.tagName === 'IMG';
                
                // 如果没有选中文本且不是图片，则使用默认上下文菜单
                if (!selectedText && !isImage) {
                    return;
                }
                
                // 阻止默认上下文菜单
                event.preventDefault();
                
                // 创建自定义菜单
                const customMenu = document.createElement('div');
                customMenu.className = 'html-editor-context-menu';
                customMenu.style.position = 'absolute';
                customMenu.style.top = event.clientY + 'px';
                customMenu.style.left = event.clientX + 'px';
                customMenu.style.backgroundColor = '#ffffff';
                customMenu.style.border = '1px solid #ccc';
                customMenu.style.boxShadow = '2px 2px 5px rgba(0,0,0,0.3)';
                customMenu.style.padding = '5px 0';
                customMenu.style.borderRadius = '4px';
                customMenu.style.zIndex = '1000';
                
                // 为图片添加调整大小选项
                if (isImage) {
                    const resizeOption = document.createElement('div');
                    resizeOption.className = 'menu-item';
                    resizeOption.textContent = '调整图片大小';
                    resizeOption.style.padding = '5px 15px';
                    resizeOption.style.cursor = 'pointer';
                    resizeOption.style.hover = 'background-color: #f0f0f0';
                    
                    resizeOption.addEventListener('click', function() {
                        customMenu.remove(); // 关闭菜单
                        
                        const currentWidth = target.width;
                        const originalWidth = target.naturalWidth;
                        const originalHeight = target.naturalHeight;
                        
                        const newWidthStr = prompt(`调整图片大小 - 输入新的宽度 (像素):\\n当前宽度: ${currentWidth}px`, currentWidth);
                        
                        if (newWidthStr !== null) {
                            const newWidth = parseInt(newWidthStr, 10);
                            if (!isNaN(newWidth) && newWidth > 0 && originalWidth > 0) {
                                const aspectRatio = originalHeight / originalWidth;
                                const newHeight = Math.round(newWidth * aspectRatio);
                                
                                if (newHeight > 0) {
                                    target.width = newWidth;
                                    target.height = newHeight;
                                } else {
                                    alert("错误: 计算出的高度无效。");
                                }
                            } else if (newWidth <= 0) {
                                alert("错误: 宽度必须大于 0。");
                            } else if (isNaN(newWidth)) {
                                alert("错误: 请输入有效的数字宽度。");
                            } else {
                                alert("错误: 无法获取原始图片尺寸。");
                            }
                        }
                    });
                    
                    customMenu.appendChild(resizeOption);
                }
                
                // 如果有选中文本，添加翻译选项
                if (selectedText) {
                    const translateOption = document.createElement('div');
                    translateOption.className = 'menu-item';
                    translateOption.textContent = '翻译选中内容';
                    translateOption.style.padding = '5px 15px';
                    translateOption.style.cursor = 'pointer';
                    translateOption.style.hover = 'background-color: #f0f0f0';
                    
                    translateOption.addEventListener('click', function() {
                        customMenu.remove(); // 关闭菜单
                        
                        // 通过QWebChannel调用Python中的翻译方法
                        # 使用异步方式安全地调用Python侧方法
                        const callbackFunction = function() {
                            if (window.qt && window.qt.webChannelTransport) {
                                // 触发全局事件，让Python端处理
                                const event = new CustomEvent('translateText', {
                                    detail: { text: selectedText }
                                });
                                document.dispatchEvent(event);
                            } else {
                                console.error("Qt WebChannel未设置，无法调用翻译方法");
                                alert("无法连接到翻译功能，请通过菜单栏使用翻译功能。");
                            }
                        };
                        
                        // 使用setTimeout确保UI先更新
                        setTimeout(callbackFunction, 10);
                    });
                    
                    customMenu.appendChild(translateOption);
                }
                
                // 添加剪切、复制、粘贴等通用选项
                if (selectedText) {
                    const copyOption = document.createElement('div');
                    copyOption.className = 'menu-item';
                    copyOption.textContent = '复制';
                    copyOption.style.padding = '5px 15px';
                    copyOption.style.cursor = 'pointer';
                    
                    copyOption.addEventListener('click', function() {
                        customMenu.remove(); // 关闭菜单
                        document.execCommand('copy');
                    });
                    
                    const cutOption = document.createElement('div');
                    cutOption.className = 'menu-item';
                    cutOption.textContent = '剪切';
                    cutOption.style.padding = '5px 15px';
                    cutOption.style.cursor = 'pointer';
                    
                    cutOption.addEventListener('click', function() {
                        customMenu.remove(); // 关闭菜单
                        document.execCommand('cut');
                    });
                    
                    if (customMenu.childElementCount > 0) {
                        customMenu.appendChild(document.createElement('hr'));
                    }
                    customMenu.appendChild(copyOption);
                    customMenu.appendChild(cutOption);
                }
                
                // 添加菜单项分隔线和样式
                const menuItems = customMenu.querySelectorAll('.menu-item');
                menuItems.forEach(item => {
                    item.addEventListener('mouseover', function() {
                        this.style.backgroundColor = '#f0f0f0';
                    });
                    item.addEventListener('mouseout', function() {
                        this.style.backgroundColor = 'transparent';
                    });
                });
                
                // 点击页面其他地方关闭菜单
                const closeMenu = function(e) {
                    if (!customMenu.contains(e.target)) {
                        customMenu.remove();
                        document.removeEventListener('click', closeMenu);
                    }
                };
                
                // 添加菜单到页面
                document.body.appendChild(customMenu);
                document.addEventListener('click', closeMenu);
            });
        })();
        """
        self.run_js(script)

    def _inject_translation_listener(self):
        """注入JavaScript代码监听翻译事件"""
        script = """
        (function() {
            document.addEventListener('translateText', function(event) {
                if (event.detail && event.detail.text) {
                    const text = event.detail.text;
                    console.log('translateText event received with text: ' + text);
                    
                    // 将翻译请求传递到Python
                    if (window.navigator) {
                        // 使用用户代理来触发Python端的检测
                        const originalUserAgent = window.navigator.userAgent;
                        window.navigator.userAgent = 'TRANSLATE_REQUEST:' + text;
                        setTimeout(function() {
                            window.navigator.userAgent = originalUserAgent;
                        }, 10);
                    }
                }
            });
            console.log('Translation event listener installed');
        })();
        """
        self.run_js(script)

    def userAgentForUrl(self, url):
        """重写userAgentForUrl方法来捕获JavaScript传递的翻译请求"""
        user_agent = super().userAgentForUrl(url)
        
        # 检查是否包含翻译请求标记
        if user_agent.startswith('TRANSLATE_REQUEST:'):
            text = user_agent[18:]  # 提取文本内容
            # 延迟调用以避免在事件处理期间修改UI
            QTimer.singleShot(0, lambda: self._handle_translation_request(text))
            
        return user_agent
    
    def _handle_translation_request(self, text):
        """处理来自JavaScript的翻译请求"""
        # 查找主窗口
        parent = self.parent()
        main_window = None
        while parent:
            if parent.__class__.__name__ == 'MainWindow':
                main_window = parent
                break
            parent = parent.parent()
            
        # 调用主窗口的翻译方法
        if main_window and hasattr(main_window, 'translate_selection_wrapper'):
            # 先设置选中文本到剪贴板
            from PyQt6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            
            # 调用翻译方法
            main_window.translate_selection_wrapper()
            
    def apply_translation_result(self, text):
        """应用翻译结果到HTML编辑器
        
        此方法由TranslationDialog或TranslationDockWidget调用，
        用于将翻译结果直接应用到HTML编辑器中。
        """
        try:
            # 对文本进行HTML转义，避免破坏HTML结构
            import html
            escaped_text = html.escape(text)
            
            # 使用JavaScript在编辑器中插入文本
            js_code = f"""
            (function() {{
                var selection = window.getSelection();
                if (selection.rangeCount > 0) {{
                    var range = selection.getRangeAt(0);
                    range.deleteContents();
                    
                    // 创建文本节点并插入
                    var textNode = document.createTextNode("{escaped_text}");
                    range.insertNode(textNode);
                    
                    // 重置选区
                    selection.removeAllRanges();
                    return true;
                }} else {{
                    // 如果没有选区，尝试在光标位置插入
                    document.execCommand('insertText', false, "{escaped_text}");
                    return true;
                }}
                return false;
            }})()
            """
            
            # 执行JavaScript代码
            self.page().runJavaScript(js_code)
            return True
        except Exception as e:
            print(f"在HTML编辑器中应用翻译结果时出错: {e}")
            return False

    def run_js(self, script: str, callback=None):
        """Executes JavaScript code in the context of the page."""
        if callback:
            self.page().runJavaScript(script, callback)
        else:
            self.page().runJavaScript(script)

    # --- Content Access Methods ---
    def setHtml(self, html: str, baseUrl: QUrl = QUrl()):
        """Sets the HTML content of the page."""
        super().setHtml(html, baseUrl)
        # Reset modification state after programmatic change
        self.setModified(False)

    def toHtml(self, callback=None):
        """
        Asynchronously retrieves the HTML content of the page.
        The result is passed to the callback function.
        Placeholder: For synchronous calls, this won't work directly.
        """
        effective_callback = callback if callback else self.html_content_ready.emit
        self.page().toHtml(effective_callback)
        # Synchronous placeholder (will likely cause issues with saving):
        # print("Warning: toHtml is asynchronous. Returning placeholder.")
        # return "" # Or raise NotImplementedError

    def setPlainText(self, text: str):
        """Sets plain text content (interpreted as HTML)."""
        # QWebEngineView interprets plain text as HTML source
        self.setHtml(text)

    def toPlainText(self, callback=None):
        """
        Asynchronously retrieves the plain text content of the page.
        The result is passed to the callback function.
        Placeholder: For synchronous calls, this won't work directly.
        """
        effective_callback = callback if callback else self.plain_text_ready.emit
        self.page().toPlainText(effective_callback)
        # Synchronous placeholder:
        # print("Warning: toPlainText is asynchronous. Returning placeholder.")
        # return "" # Or raise NotImplementedError

    # --- State Management ---
    def setFilePath(self, path: str | None):
        self._file_path = path
        self._is_new = (path is None)

    def filePath(self) -> str | None:
        return self._file_path

    def isNewFile(self) -> bool:
        return self._is_new

    def setUntitledName(self, name: str):
        self._untitled_name = name

    def untitledName(self) -> str | None:
        return self._untitled_name

    # --- Modification Status ---
    def isModified(self) -> bool:
        """Returns the modification state."""
        # QWebEnginePage.isModified() might not be reliable for JS changes.
        # Rely on our internal flag, which should be set via setModified.
        return self._is_modified

    def setModified(self, modified: bool):
        """
        Sets the modification state and emits the document_modified signal.
        This should be called explicitly when changes are made (e.g., via JS).
        """
        if self._is_modified != modified:
            self._is_modified = modified
            self.document_modified.emit(modified)

    # --- Theme/Color Handling (Example via JS) ---
    def apply_theme_js(self, is_dark: bool):
        """Injects CSS via JS to apply basic dark/light theme."""
        bg_color_str = "#1E1E1E" if is_dark else "#FFFFFF"
        text_color_str = "#D4D4D4" if is_dark else "#000000"
        script = f"""
        (function() {{
            var styleId = 'theme-style-override';
            var existingStyle = document.getElementById(styleId);
            if (!existingStyle) {{
                existingStyle = document.createElement('style');
                existingStyle.id = styleId;
                document.head.appendChild(existingStyle);
            }}
            existingStyle.innerHTML = 'body {{ background-color: {bg_color_str} !important; color: {text_color_str} !important; }}';
        }})();
        """
        self.run_js(script)

    # --- Methods not applicable to QWebEngineView (removed or need JS implementation) ---
    # textCursor, document, currentFont, setCurrentFont, textColor, setTextColor
    # cut, copy, paste, selectAll, find, undo, redo
    # These would need to be implemented by executing corresponding JavaScript commands.
    # Example for paste (very basic):
    # def paste(self):
    #     self.run_js("document.execCommand('paste');")

    def setFocus(self):
        """Override setFocus to try focusing the internal web view child."""
        # Find the actual child widget that handles rendering/input
        # This might be implementation-dependent, but often it's the first QWidget child
        view_child = self.findChild(QWebEngineView) # Or maybe just QWidget? Let's try QWidget first.
        actual_focus_target = None
        children = self.findChildren(QWidget)
        if children:
            # The actual web rendering widget might be one of the children
            # Let's try focusing the first one that isn't the HtmlEditor itself
            for child in children:
                 if child != self: # Ensure it's not the main widget itself
                      actual_focus_target = child
                      break # Focus the first likely candidate

        if actual_focus_target:
            # print(f"HtmlEditor setFocus: Attempting focus on child: {actual_focus_target}") # Debug
            actual_focus_target.setFocus()
        else:
            # print("HtmlEditor setFocus: No suitable child found, calling super().setFocus()") # Debug
            super().setFocus() # Fallback to default behavior

        # Still try JS focus as a backup, maybe with a tiny delay
        QTimer.singleShot(0, lambda: self.run_js("document.body.focus();"))
        # print("HtmlEditor setFocus: Scheduled JS focus.") # Debug


    # Removed focusInEvent override as it didn't solve the input issue
    # def focusInEvent(self, event: QFocusEvent):
    #     """Override focusInEvent."""
    #     # Let the base class handle the event, which should manage internal focus.
    #     super().focusInEvent(event)
    #     # Removed JS focus call: self.run_js("document.body.focus();")
    #     # print("HtmlEditor focusInEvent: Base event handled.") # Debug print (optional)
