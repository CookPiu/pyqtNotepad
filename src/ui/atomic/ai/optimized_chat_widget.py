from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
                             QComboBox, QLabel, QScrollArea, QFrame, QSizePolicy, QStackedWidget,
                             QSplitter, QListWidget, QListWidgetItem, QToolBar)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer, QUrl
from PyQt6.QtGui import QFont, QColor, QTextCursor, QAction, QPalette
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
import sys
import os
import json
import threading
import time
import re

try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False
    print("警告：未安装markdown库，Markdown渲染功能将不可用。请使用pip install markdown安装。")

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("警告：未安装openai库，AI聊天功能将不可用。请使用pip install openai安装。")

class OptimizedMessageWidget(QFrame):
    def __init__(self, text, is_user=True, parent=None):
        super().__init__(parent)
        self.text = text
        self.is_user = is_user
        self.is_markdown_view = False
        
        if is_user:
            self.setStyleSheet(
                "OptimizedMessageWidget { background-color: #2196F3; border-radius: 6px; margin: 4px; padding: 8px; }"
            )
            qtextedit_text_color = "white"
            label_text_color = "white"
            self.html_body_bg_color = "'#2196F3'"
            self.html_text_color = "white"
        else:
            self.setStyleSheet(
                "OptimizedMessageWidget { background-color: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 6px; margin: 4px; padding: 8px; }"
            )
            qtextedit_text_color = "#212121"
            label_text_color = "#424242"
            self.html_body_bg_color = "transparent"
            self.html_text_color = "#212121"
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(4)
        
        top_layout = QHBoxLayout()
        sender_label = QLabel("用户" if is_user else "AI", self)
        sender_label.setStyleSheet(f"font-weight: bold; color: {label_text_color}; font-size: 12px; background: transparent;")
        top_layout.addWidget(sender_label)
        top_layout.addStretch(1)

        if not is_user:
            button_layout = QHBoxLayout()
            button_layout.setSpacing(4)
            self.toggle_md_button = QPushButton("格式", self)
            self.toggle_md_button.setStyleSheet(
                f"QPushButton {{ background-color: transparent; color: #757575; border: none; font-size: 11px; padding: 2px 4px; }}"
                f"QPushButton:hover {{ color: #2196F3; }}"
            )
            self.toggle_md_button.setFixedSize(30, 20)
            self.toggle_md_button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.toggle_md_button.clicked.connect(self.toggle_markdown_view)
            self.toggle_md_button.setToolTip("切换Markdown/纯文本视图")
            button_layout.addWidget(self.toggle_md_button)
            
            self.copy_button = QPushButton("复制", self)
            self.copy_button.setStyleSheet(
                f"QPushButton {{ background-color: transparent; color: #757575; border: none; font-size: 11px; padding: 2px 4px; }}"
                f"QPushButton:hover {{ color: #2196F3; }}"
            )
            self.copy_button.setFixedSize(30, 20)
            self.copy_button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.copy_button.clicked.connect(self.copy_text)
            self.copy_button.setToolTip("复制消息内容")
            button_layout.addWidget(self.copy_button)
            top_layout.addLayout(button_layout)
        
        self.layout.addLayout(top_layout)
        
        self.stacked_widget = QStackedWidget(self)
        
        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setPlainText(text)
        if is_user:
            self.text_edit.setStyleSheet(f"QTextEdit {{ background-color: #2196F3; color: white; border: none; font-size: 13px; padding: 0px; margin: 0px; }}")
        else:
            self.text_edit.setStyleSheet(f"QTextEdit {{ background-color: transparent; color: {qtextedit_text_color}; border: none; font-size: 13px; padding: 0px; margin: 0px; }}")
        self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.text_edit.setMinimumHeight(20) 
        self.text_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        self.text_edit.document().setDocumentMargin(0)
        
        self.web_view = QWebEngineView(self)
        self.web_view.setStyleSheet("background-color: transparent; border: none;")
        self.web_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        # Potentially useful for debugging SSL issues with MathJax CDN:
        # settings.setAttribute(QWebEngineSettings.WebAttribute. cinquième, True) # This is a placeholder, actual attribute might differ or not exist
        # self.web_view.page().profile().setHttpAcceptLanguage("en-US,en;q=0.9") # Example of setting profile properties

        self.stacked_widget.addWidget(self.text_edit)
        self.stacked_widget.addWidget(self.web_view)
        self.layout.addWidget(self.stacked_widget)
        
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setLayout(self.layout)
        
        self.resize_timer = QTimer(self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.adjust_height_for_no_scroll)
        
        if not self.is_user:
            self.web_view.page().javaScriptConsoleMessage = self.handle_js_console_message
            self.web_view.loadFinished.connect(self._on_webview_load_finished)

        if not self.is_user and MARKDOWN_AVAILABLE:
            self.is_markdown_view = True
            self._render_and_switch_view()
        elif not self.is_user:
            self.stacked_widget.setCurrentWidget(self.text_edit)
            if hasattr(self, 'toggle_md_button'):
                self.toggle_md_button.setText("格式")
                self.toggle_md_button.setEnabled(MARKDOWN_AVAILABLE) 
        else: 
            self.stacked_widget.setCurrentWidget(self.text_edit)
            if not self.is_user and hasattr(self, 'toggle_md_button'):
                self.toggle_md_button.setText("格式")
                self.toggle_md_button.setEnabled(MARKDOWN_AVAILABLE)
        
        QTimer.singleShot(50, self.adjust_height_for_no_scroll)

    def handle_js_console_message(self, level, message, lineNumber, sourceID):
        log_level_str = ["Info", "Warning", "Error"]
        print(f"JS Console ({log_level_str[level]} - {sourceID}:{lineNumber}): {message}")

    def _render_and_switch_view(self):
        current_body_bg_color_css = self.html_body_bg_color
        current_text_color_css = self.html_text_color

        processed_text = self.text
        if not self.is_user:
            # Convert [latex_block] to \[latex_block\] for pymdownx.arithmatex (generic mode)
            # This regex aims to be non-greedy and handle simple cases.
            # It matches content within [ ] that does not itself contain [ or ].
            # This is a simplification and might fail for nested brackets not related to LaTeX.
            processed_text = re.sub(r'\[\s*([^\[\]]+?)\s*\]', r'\\\[\1\\\]', processed_text)
            
        if self.is_markdown_view and MARKDOWN_AVAILABLE:
            html_body = markdown.markdown(
                processed_text,
                extensions=[
                    'markdown.extensions.extra', 
                    'markdown.extensions.sane_lists', 
                    'markdown.extensions.md_in_html', 
                    'pymdownx.arithmatex' 
                ],
                extension_configs={
                    'pymdownx.arithmatex': {
                        'generic': True 
                    }
                }
            )
            if "math/tex" in html_body:
                 print("DEBUG: MathJax script tags were generated by pymdownx.arithmatex.")
            else:
                 print("DEBUG: MathJax script tags were NOT generated by pymdownx.arithmatex. Check processed_text and arithmatex config.")
                 print(f"DEBUG: Processed text for Markdown: {processed_text}")
            
            mathjax_script = """
              <script>
                window.MathJax = {
                  tex: {
                    inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
                    displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
                    processEscapes: true,
                    tags: 'ams' 
                  },
                  options: {
                    skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code'],
                    ignoreHtmlClass: 'tex2jax_ignore',
                    processHtmlClass: 'tex2jax_process'
                  },
                  svg: { fontCache: 'global' }
                };
              </script>
            """
            
            css_rules = f"""
                body {{ margin:0; padding: 0px; font-size:13px; font-family: "Microsoft YaHei", Arial, sans-serif; color: {current_text_color_css}; background-color: {current_body_bg_color_css}; line-height: 1.6; overflow-wrap: break-word; word-wrap: break-word; overflow-y: hidden; overflow-x: auto; }}
                pre {{ background-color: rgba(0,0,0,0.05); padding: 8px; border-radius: 4px; overflow-x: auto; white-space: pre-wrap; word-wrap: break-word; }}
                code {{ font-family: 'Courier New', monospace; padding: 2px 4px; border-radius: 2px; background-color: rgba(0,0,0,0.05);}}
                mjx-container {{ /* Allow horizontal scroll for single-line formulas */
                    overflow-x: auto;
                    overflow-y: hidden;
                    display: inline-block;
                    max-width: 100%;
                }}
                pre code {{ background-color: transparent; padding: 0; }} 
                blockquote {{ border-left: 4px solid #E0E0E0; margin-left: 0; padding-left: 16px; color: #757575; }}
                img {{ max-width: 100%; }} table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #E0E0E0; padding: 8px; text-align: left; }} th {{ background-color: #f5f5f5; }}
                ol, ul {{ padding-left:1.5em; }}
                p {{ margin-top: 0.5em; margin-bottom: 0.5em; }}
            """

            styled_html = f"""
            <!DOCTYPE html><html><head><meta charset="utf-8">
              {mathjax_script}
              <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js" async></script>
              <style>
              {css_rules}
              </style></head><body>{html_body}</body></html>"""

            self.web_view.setHtml(styled_html, QUrl("https://cdn.jsdelivr.net/"))
            self.stacked_widget.setCurrentWidget(self.web_view)
            if hasattr(self, 'toggle_md_button'):
                self.toggle_md_button.setText("文本")
                self.toggle_md_button.setEnabled(True)
        else: 
            self.text_edit.setPlainText(self.text)
            self.stacked_widget.setCurrentWidget(self.text_edit)
            if hasattr(self, 'toggle_md_button'):
                self.toggle_md_button.setText("格式")
                self.toggle_md_button.setEnabled(MARKDOWN_AVAILABLE)
        
        self.resize_timer.start(50)

    def toggle_markdown_view(self):
        if not MARKDOWN_AVAILABLE: return
        self.is_markdown_view = not self.is_markdown_view
        self._render_and_switch_view()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resize_timer.start(20)

    def adjust_height_for_no_scroll(self):
        current_content_widget = self.stacked_widget.currentWidget()
        if current_content_widget is self.text_edit:
            doc = self.text_edit.document()
            # Use contentsRect for available width for text layout
            available_width = self.text_edit.contentsRect().width() 
            if available_width <=0: # Fallback if contentsRect is not yet valid
                omw_padding = 8 
                available_width = max(10, self.width() - (2 * omw_padding))

            doc.setTextWidth(available_width)
            # doc.adjustSize() # This might not be needed if setTextWidth correctly triggers relayout for size
            content_height = int(doc.size().height())
            # Add a slightly larger buffer to be safe, especially if font metrics vary.
            if self.is_user:
                self.text_edit.setFixedHeight(content_height + 25)
            else:
                self.text_edit.setFixedHeight(content_height + 10) 
        elif current_content_widget is self.web_view:
            current_content_widget.setMinimumHeight(30)
            self._request_webview_height_update()
        self._update_total_widget_height()

    def _request_webview_height_update(self):
        if self.stacked_widget.currentWidget() is self.web_view and self.web_view.page().url().isValid():
            def set_h_from_js(h_str):
                try:
                    h = 0
                    if h_str is not None:
                        try: h = int(float(h_str))
                        except ValueError: print(f"Warning: Could not convert scrollHeight '{h_str}' to int during resize.")
                    # Add a more generous buffer for web view, as scrollHeight can sometimes be tricky
                    self.web_view.setFixedHeight(max(40, h + 20)) 
                except Exception as e:
                    print(f"Error in set_h_from_js (resize): {e}")
                    self.web_view.setFixedHeight(max(40, self.web_view.sizeHint().height() + 20))
                finally:
                    self._update_total_widget_height()
                    if self.parentWidget(): self.parentWidget().updateGeometry()
            js_script = "Math.max(document.body ? document.body.scrollHeight : 0, document.documentElement ? document.documentElement.scrollHeight : 0);"
            QTimer.singleShot(100, lambda: self.web_view.page().runJavaScript(js_script, 0, set_h_from_js)) # Increased delay

    def _on_webview_load_finished(self, success):
        if success: self._request_webview_height_update()
        else:
            print("WebView load failed.")
            self.web_view.setFixedHeight(max(40, self.web_view.sizeHint().height()))
            self._update_total_widget_height()

    def _update_total_widget_height(self):
        top_layout_h = self.layout.itemAt(0).layout().sizeHint().height()
        content_actual_h = self.stacked_widget.currentWidget().height()
        new_total_height = top_layout_h + self.layout.spacing() + content_actual_h
        if not self.is_user and self.layout.count() > 2: # AI messages might have a separator
            separator_item = self.layout.itemAt(2) # Assuming separator is at index 2 for AI
            if separator_item and separator_item.widget():
                 new_total_height += self.layout.spacing() + separator_item.widget().sizeHint().height() 
        self.setFixedHeight(max(30, new_total_height))

    def copy_text(self):
        from PyQt6.QtGui import QClipboard
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self.text)
        original_text = self.copy_button.text()
        self.copy_button.setText("✓")
        self.copy_button.setStyleSheet(
            f"QPushButton {{ background-color: transparent; color: {'#A5D6A7' if self.is_user else '#4CAF50'}; border: none; font-size: 11px; padding: 2px 4px; }}"
        )
        QTimer.singleShot(1500, lambda: self.copy_button.setText(original_text))
        QTimer.singleShot(1500, lambda: self.copy_button.setStyleSheet(
            f"QPushButton {{ background-color: transparent; color: #757575; border: none; font-size: 11px; padding: 2px 4px; }}"
            f"QPushButton:hover {{ color: {'#BBDEFB' if self.is_user else '#2196F3'}; }}"
        ))
    
    def set_text(self, text):
        self.text = text
        self.text_edit.setPlainText(text)
        if self.is_markdown_view and MARKDOWN_AVAILABLE:
            self._render_and_switch_view()
        else: 
            self.stacked_widget.setCurrentWidget(self.text_edit)
            # When text is set for a plain text view, ensure its height is also adjusted.
            QTimer.singleShot(10, self.adjust_height_for_no_scroll) 
        # self.resize_timer.start(10) # This might be redundant if adjust_height_for_no_scroll is called

class OptimizedChatWidget(QWidget):
    chat_completed = pyqtSignal(str, str)
    message_updated = pyqtSignal(object, str)
    regenerate_button_state = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_conversation = []
        self.last_user_message = ""
        self.last_ai_message_widget = None
        config = self.load_config()
        self.api_key = config.get("api_key", "")
        self.current_model_id = config.get("current_model", "deepseek-v3")
        self.setup_ui()
        self.message_updated.connect(self._on_message_updated)
        self.regenerate_button_state.connect(self._on_regenerate_button_state_changed)
    
    def setup_ui(self):
        main_chat_layout = QVBoxLayout(self)
        main_chat_layout.setContentsMargins(0,0,0,0)
        main_chat_layout.setSpacing(0)
        content_pane = QWidget() 
        content_pane_layout = QVBoxLayout(content_pane) 
        content_pane_layout.setContentsMargins(0,0,0,0)
        content_pane_layout.setSpacing(0)
        toolbar = QToolBar()
        toolbar.setStyleSheet("""
            QToolBar { background: white; border-bottom:1px solid #E0E0E0; padding: 2px 8px; }
            QToolButton { border: none; margin: 0 2px; padding: 8px; background-color: transparent; color: #424242; }
            QToolButton:hover { background: #F0F0F0; }
            QToolButton:pressed { background: #E0E0E0; }
        """)
        toolbar_actions_text = ["新建", "列表", "刷新", "导出", "用户", "设置"]
        self.example_actions = [] 
        for text in toolbar_actions_text:
            action = QAction(text, self)
            toolbar.addAction(action)
            self.example_actions.append(action)
        content_pane_layout.addWidget(toolbar)
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet(
            "QScrollArea { border: none; background-color: #FFFFFF; }"
            "QScrollBar:vertical { border: none; background: #F5F5F5; width: 6px; margin: 0px; border-radius: 3px; }"
            "QScrollBar::handle:vertical { background: #BDBDBD; border-radius: 3px; min-height: 20px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }"
        )
        self.message_container = QWidget()
        self.message_container.setStyleSheet("background-color: #FFFFFF;") 
        self.message_layout = QVBoxLayout(self.message_container)
        self.message_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.message_layout.setSpacing(0) 
        self.message_layout.setContentsMargins(8, 4, 8, 4) 
        self.message_container.setLayout(self.message_layout)
        self.scroll_area.setWidget(self.message_container)
        content_pane_layout.addWidget(self.scroll_area, 1)
        # Input Area
        input_area_widget = QWidget()
        input_area_widget.setStyleSheet("background-color: white; border-top: 1px solid #E0E0E0;")
        input_layout = QHBoxLayout(input_area_widget)
        input_layout.setContentsMargins(8,8,8,8)
        input_layout.setSpacing(8)
        self.input_text = QTextEdit(self)
        self.input_text.setPlaceholderText("输入您的问题...")
        self.input_text.setFixedHeight(40) 
        self.input_text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.input_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                padding: 8px;
                background: #FFFFFF;
                color: #212121;
                font-size:13px;
            }
            QTextEdit:focus { 
                outline:none; 
                border: 1px solid #2196F3;
            }
        """)
        pal = self.input_text.palette()
        pal.setColor(QPalette.ColorRole.PlaceholderText, QColor(158,158,158))
        self.input_text.setPalette(pal)
        self.send_button = QPushButton("发送", self)
        self.send_button.setFixedSize(QSize(70, 38))
        self.send_button.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: white; border: none; border-radius: 6px; padding: 8px 12px; font-size: 13px; font-weight: bold;}"
            "QPushButton:hover { background-color: #1E88E5; }"
            "QPushButton:pressed { background-color: #1976D2; }"
        )
        self.send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.input_text, 1)
        input_layout.addWidget(self.send_button)
        content_pane_layout.addWidget(input_area_widget)
        main_chat_layout.addWidget(content_pane)
        self.setLayout(main_chat_layout)
        self.add_message("欢迎使用AI聊天助手！请输入您的问题。", is_user=False)
    
    def on_model_changed(self, model_name):
        model_map = {"DeepSeek V3": "deepseek-v3", "DeepSeek R1": "deepseek-r1"}
        self.current_model_id = model_map.get(model_name, "deepseek-v3")
        self.save_config()
    
    def add_message(self, text, is_user=True):
        message_widget = OptimizedMessageWidget(text, is_user, self.message_container)
        self.message_layout.addWidget(message_widget)
        QTimer.singleShot(50, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))
        return message_widget
    
    def send_message(self):
        text = self.input_text.toPlainText().strip()
        if not text: return
        self.last_user_message = text
        self.add_message(text, is_user=True)
        self.input_text.clear()
        if not self.api_key:
            self.add_message("错误：未设置API密钥。", is_user=False)
            return
        if not OPENAI_AVAILABLE:
            self.add_message("错误：未安装openai库。", is_user=False)
            return
        thinking_message = self.add_message("正在思考...", is_user=False)
        self.last_ai_message_widget = thinking_message
        self.regenerate_button_state.emit(False)
        threading.Thread(target=self._send_request, args=(text, thinking_message), daemon=True).start()
    
    def _send_request(self, text, thinking_message):
        try:
            config = self.load_config()
            model_info = config.get("models", {}).get(self.current_model_id)
            if not model_info:
                self.message_updated.emit(thinking_message, "错误：未知的模型类型。")
                return
            client = openai.OpenAI(api_key=self.api_key, base_url=model_info["api_base"])
            if not self.current_conversation or self.current_conversation[0].get("role") != "system":
                 self.current_conversation.insert(0, {"role": "system", "content": "你是一个有用的AI助手。"})
            self.current_conversation.append({"role": "user", "content": text})
            response = client.chat.completions.create(
                model=model_info["model"], messages=self.current_conversation, temperature=0.7, max_tokens=2000
            )
            reply = response.choices[0].message.content
            self.current_conversation.append({"role": "assistant", "content": reply})
            self.message_updated.emit(thinking_message, reply)
            self.chat_completed.emit(model_info["name"], reply)
            self.regenerate_button_state.emit(True)
        except Exception as e:
            error_message = f"错误：{str(e)}"
            self.message_updated.emit(thinking_message, error_message)
    
    def _on_message_updated(self, message_widget, new_text):
        if message_widget and hasattr(message_widget, 'set_text'):
             message_widget.set_text(new_text)
    
    def _on_regenerate_button_state_changed(self, enabled):
        pass
    
    def regenerate_response(self):
        if not self.last_user_message or not self.last_ai_message_widget: return
        if len(self.current_conversation) >= 2 and self.current_conversation[-1]["role"] == "assistant":
            self.current_conversation.pop()
        self.message_updated.emit(self.last_ai_message_widget, "正在重新生成...")
        self.regenerate_button_state.emit(False)
        threading.Thread(target=self._send_request, args=(self.last_user_message, self.last_ai_message_widget), daemon=True).start()
    
    def set_api_key(self, api_key):
        self.api_key = api_key
        self.save_config()
    
    def load_config(self):
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_config.json")
        default_config = {
            "api_key": "", "current_model": "deepseek-v3",
            "models": {
                "deepseek-v3": {"name": "DeepSeek V3", "model": "deepseek-chat", "api_base": "https://api.deepseek.com/v1"},
                "deepseek-r1": {"name": "DeepSeek R1", "model": "deepseek-chat", "api_base": "https://api.deepseek.com/v1"}
            }}
        try:
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f: config = json.load(f)
                for key, value in default_config.items():
                    if key not in config: config[key] = value
                return config
        except Exception as e: print(f"加载配置时出错: {e}")
        return default_config
    
    def save_config(self):
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_config.json")
        config = self.load_config()
        config["api_key"] = self.api_key
        config["current_model"] = self.current_model_id
        try:
            with open(config_path, "w", encoding="utf-8") as f: json.dump(config, f, ensure_ascii=False, indent=4)
        except Exception as e: print(f"保存配置时出错: {e}")
    
    def clear_conversation(self):
        self.current_conversation = []
        for i in reversed(range(self.message_layout.count())):
            item = self.message_layout.itemAt(i)
            if item and item.widget(): item.widget().deleteLater()
        self.add_message("对话已清空。请输入新的问题。", is_user=False)
        self.regenerate_button_state.emit(False)
        self.last_user_message = ""
        self.last_ai_message_widget = None

if __name__ == '__main__':
    from PyQt6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    main_chat_window = OptimizedChatWidget()
    main_chat_window.setWindowTitle("CLINE Style Chat Interface Test")
    main_chat_window.resize(1000, 700)
    main_chat_window.show()
    sys.exit(app.exec())
