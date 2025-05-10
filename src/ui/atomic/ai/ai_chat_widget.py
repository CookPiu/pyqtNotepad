from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
                             QComboBox, QLabel, QScrollArea, QFrame, QSizePolicy, QStackedWidget)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QFont, QColor, QTextCursor
from PyQt6.QtWebEngineWidgets import QWebEngineView
import sys
import os
import json
import threading
import time
import re

# 尝试导入Markdown相关库
try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False
    print("警告：未安装markdown库，Markdown渲染功能将不可用。请使用pip install markdown安装。")

# 尝试导入OpenAI库，如果不存在则显示提示信息
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("警告：未安装openai库，AI聊天功能将不可用。请使用pip install openai安装。")


class MessageWidget(QFrame):
    """单条消息显示组件 - 扁平化设计，支持Markdown渲染"""
    def __init__(self, text, is_user=True, parent=None):
        super().__init__(parent)
        self.text = text
        self.is_user = is_user
        self.is_markdown_view = False
        
        # 设置扁平化样式
        if is_user:
            self.setStyleSheet(
                "background-color: #E3F2FD; border-radius: 4px; margin: 4px; padding: 8px;"
            )
        else:
            self.setStyleSheet(
                "background-color: #F5F5F5; border-radius: 4px; margin: 4px; padding: 8px;"
            )
        
        # 创建布局
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(4)
        
        # 创建顶部布局（发送者标签和操作按钮）
        top_layout = QHBoxLayout()
        
        # 创建标签显示发送者
        sender_label = QLabel("用户" if is_user else "AI", self)
        sender_label.setStyleSheet("font-weight: bold; color: #424242; font-size: 12px;")
        top_layout.addWidget(sender_label)
        
        # 如果是AI消息，添加操作按钮
        if not is_user:
            # 添加切换Markdown视图按钮
            self.toggle_md_button = QPushButton("MD", self)
            self.toggle_md_button.setStyleSheet(
                "QPushButton { background-color: transparent; color: #757575; border: none; font-size: 11px; padding: 2px 4px; }"
                "QPushButton:hover { color: #2196F3; }"
            )
            self.toggle_md_button.setFixedSize(24, 20)
            self.toggle_md_button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.toggle_md_button.clicked.connect(self.toggle_markdown_view)
            self.toggle_md_button.setToolTip("切换Markdown视图")
            top_layout.addWidget(self.toggle_md_button)
        
        top_layout.addStretch(1)
        self.layout.addLayout(top_layout)
        
        # 创建堆叠小部件用于切换纯文本和Markdown视图
        self.stacked_widget = QStackedWidget(self)
        
        # 创建纯文本显示区域
        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setPlainText(text)
        self.text_edit.setStyleSheet("background-color: transparent; border: none; font-size: 13px; color: #212121;")
        self.text_edit.setMinimumHeight(40)
        self.text_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.text_edit.document().setDocumentMargin(0)
        
        # 创建Markdown视图
        self.web_view = QWebEngineView(self)
        self.web_view.setStyleSheet("background-color: transparent; border: none;")
        self.web_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        
        # 添加到堆叠小部件
        self.stacked_widget.addWidget(self.text_edit)
        self.stacked_widget.addWidget(self.web_view)
        self.layout.addWidget(self.stacked_widget)
        
        # 调整大小策略
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setLayout(self.layout)
        
        # 设置自动调整高度的计时器
        self.resize_timer = QTimer(self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.adjust_height)
        self.resize_timer.start(100)
    
    def toggle_markdown_view(self):
        """切换Markdown视图和纯文本视图"""
        if not MARKDOWN_AVAILABLE and not self.is_markdown_view:
            self.text_edit.setPlainText(self.text + "\n\n警告：未安装markdown库，无法渲染Markdown。")
            return
        
        self.is_markdown_view = not self.is_markdown_view
        
        if self.is_markdown_view:
            # 渲染Markdown
            html_content = markdown.markdown(self.text, extensions=['tables', 'fenced_code'])
            
            # 添加基本样式
            styled_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; font-size: 13px; color: #212121; margin: 0; padding: 0; }}
                    pre {{ background-color: #f5f5f5; padding: 8px; border-radius: 4px; overflow-x: auto; }}
                    code {{ font-family: 'Courier New', monospace; background-color: #f5f5f5; padding: 2px 4px; border-radius: 2px; }}
                    pre code {{ padding: 0; }}
                    blockquote {{ border-left: 4px solid #e0e0e0; margin-left: 0; padding-left: 16px; color: #757575; }}
                    img {{ max-width: 100%; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ border: 1px solid #e0e0e0; padding: 8px; text-align: left; }}
                    th {{ background-color: #f5f5f5; }}
                </style>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """
            
            self.web_view.setHtml(styled_html)
            self.stacked_widget.setCurrentWidget(self.web_view)
            self.toggle_md_button.setText("文本")
        else:
            self.stacked_widget.setCurrentWidget(self.text_edit)
            self.toggle_md_button.setText("MD")
        
        # 调整高度
        self.resize_timer.start(100)
    
    def adjust_height(self):
        """根据内容自动调整高度"""
        if self.is_markdown_view:
            # 对于Markdown视图，设置一个最小高度，然后让它自动扩展
            self.web_view.setMinimumHeight(100)
            # 可以通过JavaScript获取内容高度，但这里简化处理
        else:
            # 对于文本视图，根据文档高度调整
            document_height = self.text_edit.document().size().height()
            # 添加一些边距
            self.text_edit.setMinimumHeight(min(int(document_height + 20), 300))
            
            # 如果内容很长，启用滚动条
            if document_height > 300:
                self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            else:
                self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    
    def set_text(self, text):
        """更新消息文本"""
        self.text = text
        self.text_edit.setPlainText(text)
        
        # 如果当前是Markdown视图，更新Markdown渲染
        if self.is_markdown_view and MARKDOWN_AVAILABLE:
            self.toggle_markdown_view()  # 切换回文本视图
            self.toggle_markdown_view()  # 再切换到Markdown视图以刷新
        
        # 调整高度
        self.resize_timer.start(100)


class AIChatWidget(QWidget):
    """AI聊天组件 - 扁平化设计"""
    chat_completed = pyqtSignal(str, str)  # 聊天完成信号，参数为模型名称和回复内容
    message_updated = pyqtSignal(object, str)  # 消息更新信号，参数为消息组件和新文本
    regenerate_button_state = pyqtSignal(bool)  # 重新生成按钮状态信号，参数为是否启用
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.api_key = ""
        self.current_model = "deepseek-v3"
        self.current_conversation = []  # 存储当前对话历史
        self.last_user_message = ""  # 存储最后一条用户消息，用于重新生成
        self.last_ai_message_widget = None  # 存储最后一条AI消息组件，用于更新
        
        # 连接信号到槽函数
        self.message_updated.connect(self._on_message_updated)
        self.regenerate_button_state.connect(self._on_regenerate_button_state_changed)
        
        self.load_config()
    
    def setup_ui(self):
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        
        # 创建模型选择区域
        model_layout = QHBoxLayout()
        model_label = QLabel("AI模型：", self)
        model_label.setStyleSheet("color: #424242; font-size: 13px;")
        self.model_combo = QComboBox(self)
        self.model_combo.setStyleSheet(
            "QComboBox { border: 1px solid #BDBDBD; border-radius: 3px; padding: 3px; background-color: #FAFAFA; }"
            "QComboBox::drop-down { border: none; width: 20px; }"
            "QComboBox::down-arrow { image: url(:/icons/down_arrow.png); width: 12px; height: 12px; }"
        )
        self.model_combo.addItem("DeepSeek V3")
        self.model_combo.addItem("DeepSeek R1")
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_combo)
        
        # 添加重新生成按钮
        self.regenerate_button = QPushButton("重新生成", self)
        self.regenerate_button.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; border: none; border-radius: 4px; padding: 4px 8px; }"
            "QPushButton:hover { background-color: #43A047; }"
            "QPushButton:pressed { background-color: #388E3C; }"
            "QPushButton:disabled { background-color: #BDBDBD; }"
        )
        self.regenerate_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.regenerate_button.clicked.connect(self.regenerate_response)
        self.regenerate_button.setEnabled(False)  # 初始禁用
        model_layout.addWidget(self.regenerate_button)
        model_layout.addStretch(1)
        main_layout.addLayout(model_layout)
        
        # 创建消息显示区域
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet(
            "QScrollArea { border: 1px solid #E0E0E0; background-color: #FFFFFF; border-radius: 4px; }"
            "QScrollBar:vertical { border: none; background: #F5F5F5; width: 8px; margin: 0px; }"
            "QScrollBar::handle:vertical { background: #BDBDBD; border-radius: 4px; min-height: 20px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }"
        )
        
        # 创建消息容器
        self.message_container = QWidget()
        self.message_container.setStyleSheet("background-color: #FFFFFF;")
        self.message_layout = QVBoxLayout(self.message_container)
        self.message_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.message_layout.setSpacing(8)
        self.message_layout.setContentsMargins(8, 8, 8, 8)
        self.message_container.setLayout(self.message_layout)
        
        self.scroll_area.setWidget(self.message_container)
        main_layout.addWidget(self.scroll_area, 1)
        
        # 创建输入区域
        input_layout = QHBoxLayout()
        self.input_text = QTextEdit(self)
        self.input_text.setPlaceholderText("输入您的问题...")
        self.input_text.setMaximumHeight(80)
        self.input_text.setStyleSheet(
            "QTextEdit { border: 1px solid #E0E0E0; border-radius: 4px; padding: 6px; background-color: #FAFAFA; }"
            "QTextEdit:focus { border: 1px solid #2196F3; }"
        )
        self.send_button = QPushButton("发送", self)
        self.send_button.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: white; border: none; border-radius: 4px; padding: 6px 12px; }"
            "QPushButton:hover { background-color: #1E88E5; }"
            "QPushButton:pressed { background-color: #1976D2; }"
        )
        self.send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.input_text)
        input_layout.addWidget(self.send_button)
        main_layout.addLayout(input_layout)
        
        # 设置布局
        self.setLayout(main_layout)
        
        # 添加欢迎消息
        self.add_message("欢迎使用AI聊天助手！请输入您的问题。", is_user=False)
    
    def on_model_changed(self, model_name):
        """当模型选择改变时调用"""
        model_map = {
            "DeepSeek V3": "deepseek-v3",
            "DeepSeek R1": "deepseek-r1"
        }
        self.current_model = model_map.get(model_name, "deepseek-v3")
        self.save_config()
    
    def add_message(self, text, is_user=True):
        """添加一条消息到聊天界面"""
        message_widget = MessageWidget(text, is_user, self)
        self.message_layout.addWidget(message_widget)
        # 滚动到底部
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )
        return message_widget
    
    def send_message(self):
        """发送消息"""
        text = self.input_text.toPlainText().strip()
        if not text:
            return
        
        # 保存用户消息用于可能的重新生成
        self.last_user_message = text
        
        # 添加用户消息
        self.add_message(text, is_user=True)
        self.input_text.clear()
        
        # 检查API密钥
        if not self.api_key:
            self.add_message("错误：未设置API密钥。请在设置中配置您的API密钥。", is_user=False)
            return
        
        # 检查OpenAI库是否可用
        if not OPENAI_AVAILABLE:
            self.add_message("错误：未安装openai库。请使用pip install openai安装。", is_user=False)
            return
        
        # 显示正在思考的消息
        thinking_message = self.add_message("正在思考...", is_user=False)
        self.last_ai_message_widget = thinking_message
        
        # 禁用重新生成按钮，直到响应完成
        self.regenerate_button.setEnabled(False)
        
        # 在新线程中发送请求
        threading.Thread(target=self._send_request, args=(text, thinking_message)).start()
    
    def _send_request(self, text, thinking_message):
        """在后台线程发送API请求"""
        try:
            # 从配置中获取模型信息
            config = self.load_config()
            model_info = config.get("models", {}).get(self.current_model)
            
            if not model_info:
                self._update_thinking_message(thinking_message, "错误：未知的模型类型。")
                return
            
            # 配置OpenAI客户端
            client = openai.OpenAI(
                api_key=self.api_key,
                base_url=model_info["api_base"]
            )
            
            # 更新对话历史
            if not self.current_conversation:
                # 如果是新对话，添加系统消息
                self.current_conversation.append({"role": "system", "content": "你是一个有用的AI助手。"})
            
            # 添加用户消息到对话历史
            self.current_conversation.append({"role": "user", "content": text})
            
            # 发送请求
            response = client.chat.completions.create(
                model=model_info["model"],
                messages=self.current_conversation,
                temperature=0.7,
                max_tokens=2000
            )
            
            # 获取回复
            reply = response.choices[0].message.content
            
            # 添加AI回复到对话历史
            self.current_conversation.append({"role": "assistant", "content": reply})
            
            # 更新消息（通过信号）
            self.message_updated.emit(thinking_message, reply)
            
            # 发出聊天完成信号
            self.chat_completed.emit(model_info["name"], reply)
            
            # 启用重新生成按钮（通过信号）
            self.regenerate_button_state.emit(True)
            
        except Exception as e:
            error_message = f"错误：{str(e)}"
            self.message_updated.emit(thinking_message, error_message)
    
    def _on_message_updated(self, message_widget, new_text):
        """响应消息更新信号的槽函数，在主线程中安全地更新UI"""
        if message_widget and hasattr(message_widget, 'set_text'):
            message_widget.set_text(new_text)
    
    def _on_regenerate_button_state_changed(self, enabled):
        """响应重新生成按钮状态变化信号的槽函数"""
        if hasattr(self, 'regenerate_button'):
            self.regenerate_button.setEnabled(enabled)
    
    def get_config_path(self):
        """获取配置文件路径"""
        # 使用项目根目录下的data文件夹
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
        data_dir = os.path.join(base_dir, "data")
        # 确保目录存在
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        return os.path.join(data_dir, "ai_config.json")
    
    def regenerate_response(self):
        """重新生成AI回复"""
        if not self.last_user_message or not self.last_ai_message_widget:
            return
        
        # 移除最后一条AI回复
        if len(self.current_conversation) >= 2 and self.current_conversation[-1]["role"] == "assistant":
            self.current_conversation.pop()
        
        # 更新UI显示（通过信号）
        self.message_updated.emit(self.last_ai_message_widget, "正在重新生成...")
        
        # 禁用重新生成按钮，直到响应完成
        self.regenerate_button.setEnabled(False)
        
        # 在新线程中发送请求
        threading.Thread(target=self._send_request, args=(self.last_user_message, self.last_ai_message_widget)).start()
    
    def load_config(self):
        """从配置文件加载设置"""
        config_path = self.get_config_path()
        default_config = {
            "api_key": "",
            "selected_model": "deepseek-v3",
            "models": {
                "deepseek-v3": {
                    "name": "DeepSeek V3",
                    "api_base": "https://api.deepseek.com/v1",
                    "model": "deepseek-chat"
                },
                "deepseek-r1": {
                    "name": "DeepSeek R1",
                    "api_base": "https://api.deepseek.com/v1",
                    "model": "deepseek-r1"
                }
            }
        }
        
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.api_key = config.get("api_key", "")
                    self.current_model = config.get("selected_model", "deepseek-v3")
                    
                    # 更新下拉框选择
                    model_display = {
                        "deepseek-v3": "DeepSeek V3",
                        "deepseek-r1": "DeepSeek R1"
                    }
                    current_display = model_display.get(self.current_model)
                    if current_display:
                        index = self.model_combo.findText(current_display)
                        if index >= 0:
                            self.model_combo.setCurrentIndex(index)
                    
                    return config
            except Exception as e:
                print(f"加载配置时出错：{e}")
                return default_config
        else:
            # 如果配置文件不存在，创建默认配置
            try:
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(default_config, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"创建默认配置时出错：{e}")
            return default_config
    
    def save_config(self):
        """保存配置到文件"""
        config_path = self.get_config_path()
        try:
            # 先读取现有配置
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            else:
                config = self.load_config()  # 获取默认配置
            
            # 更新配置
            config["api_key"] = self.api_key
            config["selected_model"] = self.current_model
            
            # 保存配置
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"保存配置时出错：{e}")
    
    def set_api_key(self, api_key):
        """设置API密钥"""
        self.api_key = api_key
        self.save_config()
        
        # 添加确认消息
        if api_key:
            self.add_message("API密钥已设置成功！", is_user=False)
        else:
            self.add_message("警告：API密钥已清除。", is_user=False)