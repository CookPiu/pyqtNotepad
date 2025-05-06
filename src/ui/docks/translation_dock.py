from PyQt6.QtWidgets import (QDockWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
                           QTextEdit, QPushButton, QMessageBox, QApplication, QWidget,
                           QGridLayout, QSplitter)
from PyQt6.QtCore import Qt, QSettings, QTimer
from PyQt6.QtGui import QColor, QPalette, QKeyEvent
from src.services.translation_service import TranslationService
from ..dialogs.translation_dialog import APIConfigDialog
import os
import json


class TranslationDockWidget(QDockWidget):
    """可拖拽的翻译窗口，使用QDockWidget实现"""
    
    # 偏好设置文件路径
    PREFERENCES_DIR = "D:\\pyqtNotepad\\data\\API"
    PREFERENCES_FILE = "translation_preferences.json"
    
    def __init__(self, parent=None):
        super().__init__("翻译", parent)
        self.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | 
                         QDockWidget.DockWidgetFeature.DockWidgetFloatable |
                         QDockWidget.DockWidgetFeature.DockWidgetClosable)  # 添加关闭按钮
        
        # 创建必要的目录
        os.makedirs(self.PREFERENCES_DIR, exist_ok=True)
        
        # 默认值初始化
        self.default_from_lang = "自动检测"
        self.default_to_lang = "中文"
        self.live_selection = True  # 默认开启实时选择翻译
        
        # 创建翻译服务
        self.translation_service = TranslationService()
        # 从设置中加载API凭据
        self.load_credentials()
        
        # 实时获取选中文本的定时器
        self.selection_timer = QTimer(self)
        self.selection_timer.setInterval(500)  # 500毫秒检查一次
        self.selection_timer.timeout.connect(self.check_selection)
        
        # 初始化界面
        self._init_ui()
        self._apply_styles()
        
        # 默认启动实时选中功能
        if self.live_selection:
            self.selection_timer.start()
        
    def _init_ui(self):
        """初始化用户界面"""
        # 创建主容器
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(10)
        
        # 顶部控制区域
        top_layout = QHBoxLayout()
        
        # API设置按钮
        self.settings_btn = QPushButton("API设置")
        self.settings_btn.clicked.connect(self.show_api_settings)
        top_layout.addWidget(self.settings_btn)
        
        # 添加语言选择和交换按钮
        lang_layout = QHBoxLayout()
        
        # 源语言
        self.from_lang_label = QLabel("源语言:")
        self.from_lang_combo = QComboBox()
        lang_layout.addWidget(self.from_lang_label)
        lang_layout.addWidget(self.from_lang_combo)
        
        # 交换语言按钮
        self.swap_button = QPushButton("⇄")
        self.swap_button.setFixedWidth(40)
        self.swap_button.clicked.connect(self.swap_languages)
        lang_layout.addWidget(self.swap_button)
        
        # 目标语言
        self.to_lang_label = QLabel("目标语言:")
        self.to_lang_combo = QComboBox()
        lang_layout.addWidget(self.to_lang_label)
        lang_layout.addWidget(self.to_lang_combo)
        
        # 填充语言列表
        self.populate_language_combos()
        
        top_layout.addLayout(lang_layout)
        top_layout.addStretch(1)
        
        main_layout.addLayout(top_layout)
        
        # 使用分隔器来分开源文本和翻译结果
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)
        
        # 源文本区域
        source_widget = QWidget()
        source_layout = QVBoxLayout(source_widget)
        source_layout.setContentsMargins(0, 0, 0, 0)
        
        source_label = QLabel("源文本:")
        self.source_text = QTextEdit()
        source_layout.addWidget(source_label)
        source_layout.addWidget(self.source_text)
        
        splitter.addWidget(source_widget)
        
        # 结果文本区域
        result_widget = QWidget()
        result_layout = QVBoxLayout(result_widget)
        result_layout.setContentsMargins(0, 0, 0, 0)
        
        result_label = QLabel("翻译结果:")
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        result_layout.addWidget(result_label)
        result_layout.addWidget(self.result_text)
        
        splitter.addWidget(result_widget)
        
        # 设置初始分隔位置
        splitter.setSizes([200, 200])
        
        main_layout.addWidget(splitter, 1)  # 给予分隔器较大的拉伸因子
        
        # 底部按钮区域
        button_layout = QHBoxLayout()
        
        # 翻译按钮
        self.translate_button = QPushButton("翻译")
        self.translate_button.clicked.connect(self.translate_text)
        button_layout.addWidget(self.translate_button)
        
        button_layout.addStretch(1)
        
        # 操作按钮
        self.copy_button = QPushButton("复制结果")
        self.copy_button.clicked.connect(self.copy_result)
        button_layout.addWidget(self.copy_button)
        
        self.clear_button = QPushButton("清空")
        self.clear_button.clicked.connect(self.clear_text)
        button_layout.addWidget(self.clear_button)
        
        self.apply_button = QPushButton("应用到编辑器")
        self.apply_button.clicked.connect(self.apply_to_editor)
        button_layout.addWidget(self.apply_button)
        
        # 添加明显的关闭按钮
        self.close_button = QPushButton("关闭")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)
        
        main_layout.addLayout(button_layout)
        
        # 设置主窗口部件
        self.setWidget(main_widget)
    
    def _apply_styles(self):
        """应用样式"""
        # 设置按钮样式
        button_style = """
        QPushButton {
            background-color: #2979ff;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #448aff;
        }
        QPushButton:pressed {
            background-color: #2962ff;
        }
        QPushButton:disabled {
            background-color: #bbdefb;
            color: #e0e0e0;
        }
        """
        
        self.translate_button.setStyleSheet(button_style)
        self.copy_button.setStyleSheet(button_style)
        self.apply_button.setStyleSheet(button_style)
        self.clear_button.setStyleSheet(button_style)
        
        # 关闭按钮样式
        close_style = """
        QPushButton {
            background-color: #f44336;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #e57373;
        }
        QPushButton:pressed {
            background-color: #d32f2f;
        }
        """
        self.close_button.setStyleSheet(close_style)
        
        # 设置设置按钮样式
        settings_style = """
        QPushButton {
            background-color: #757575;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #9e9e9e;
        }
        QPushButton:pressed {
            background-color: #616161;
        }
        """
        self.settings_btn.setStyleSheet(settings_style)
        
        # 交换按钮样式
        swap_style = """
        QPushButton {
            background-color: #ff9800;
            color: white;
            border: none;
            padding: 2px;
            border-radius: 4px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #ffa726;
        }
        QPushButton:pressed {
            background-color: #fb8c00;
        }
        """
        self.swap_button.setStyleSheet(swap_style)
        
        # 下拉框样式
        combo_style = """
        QComboBox {
            border: 1px solid #bdbdbd;
            border-radius: 4px;
            padding: 4px;
            background: white;
        }
        QComboBox::drop-down {
            border: none;
            width: 24px;
        }
        """
        self.from_lang_combo.setStyleSheet(combo_style)
        self.to_lang_combo.setStyleSheet(combo_style)
        
        # 文本编辑区域样式
        textedit_style = """
        QTextEdit {
            border: 1px solid #bdbdbd;
            border-radius: 4px;
            padding: 4px;
            background-color: white;
        }
        """
        self.source_text.setStyleSheet(textedit_style)
        self.result_text.setStyleSheet(textedit_style)
        
    def show_api_settings(self):
        """显示API设置对话框"""
        dialog = APIConfigDialog(
            self, 
            self.translation_service.app_id, 
            self.translation_service.app_secret
        )
        
        if dialog.exec() == APIConfigDialog.DialogCode.Accepted:
            api_settings = dialog.get_api_settings()
            self.translation_service.set_credentials(
                api_settings["app_id"], 
                api_settings["app_secret"]
            )
            
            # 保存凭据到文件
            if self.translation_service.save_credentials_to_file():
                QMessageBox.information(self, "API设置", "API凭据已保存到文件")
            else:
                QMessageBox.warning(self, "API设置", "API凭据保存失败")
    
    def check_selection(self):
        """检查当前编辑器中的选中文本并更新到翻译窗口"""
        if not self.live_selection or not self.isVisible():
            return
            
        if not self.parent() or not hasattr(self.parent(), 'get_current_editor_widget'):
            return
            
        editor = self.parent().get_current_editor_widget()
        if not editor or not hasattr(editor, 'textCursor'):
            return
            
        cursor = editor.textCursor()
        if not cursor.hasSelection():
            return
            
        selected_text = cursor.selectedText()
        if selected_text and selected_text.strip():
            current_text = self.source_text.toPlainText()
            # 只有当选中文本和当前文本不同时才更新，避免重复翻译
            if selected_text != current_text:
                self.set_text(selected_text)
        
    def populate_language_combos(self):
        """填充语言下拉列表"""
        languages = self.translation_service.get_language_list()
        
        for name in languages.keys():
            self.from_lang_combo.addItem(name, languages[name])
            self.to_lang_combo.addItem(name, languages[name])
        
        # 设置默认值
        auto_index = self.from_lang_combo.findText(self.default_from_lang)
        if auto_index >= 0:
            self.from_lang_combo.setCurrentIndex(auto_index)
        else:
            # 如果找不到保存的设置，使用"自动检测"
            auto_index = self.from_lang_combo.findText("自动检测")
            if auto_index >= 0:
                self.from_lang_combo.setCurrentIndex(auto_index)
        
        zh_index = self.to_lang_combo.findText(self.default_to_lang)
        if zh_index >= 0:
            self.to_lang_combo.setCurrentIndex(zh_index)
        else:
            # 如果找不到保存的设置，使用"中文"
            zh_index = self.to_lang_combo.findText("中文")
            if zh_index >= 0:
                self.to_lang_combo.setCurrentIndex(zh_index)
        
    def swap_languages(self):
        """交换源语言和目标语言"""
        from_index = self.from_lang_combo.currentIndex()
        to_index = self.to_lang_combo.currentIndex()
        
        # 不允许将"自动检测"设为目标语言
        auto_text = "自动检测"
        if self.to_lang_combo.itemText(from_index) == auto_text:
            return
        
        self.from_lang_combo.setCurrentIndex(to_index)
        self.to_lang_combo.setCurrentIndex(from_index)
        
        # 同时交换文本
        source = self.source_text.toPlainText()
        result = self.result_text.toPlainText()
        
        if result:
            self.source_text.setPlainText(result)
            self.result_text.setPlainText(source)
    
    def translate_text(self):
        """执行翻译"""
        text = self.source_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "翻译", "请输入要翻译的文本")
            return
            
        if not self.translation_service.has_credentials():
            QMessageBox.warning(
                self, "API凭据缺失", 
                "请点击'API设置'按钮配置您的百度翻译API凭据"
            )
            self.show_api_settings()
            return
            
        # 获取语言代码
        from_lang = self.from_lang_combo.currentData()
        to_lang = self.to_lang_combo.currentData()
        
        # 执行翻译
        success, result, _ = self.translation_service.translate(
            text, from_lang, to_lang
        )
        
        if success:
            self.result_text.setPlainText(result)
        else:
            QMessageBox.warning(self, "翻译错误", result)
    
    def copy_result(self):
        """复制翻译结果到剪贴板"""
        result = self.result_text.toPlainText()
        if result:
            QApplication.clipboard().setText(result)
            QMessageBox.information(self, "复制成功", "已复制到剪贴板")
    
    def clear_text(self):
        """清空文本"""
        self.source_text.clear()
        self.result_text.clear()
        
    def apply_to_editor(self):
        """将翻译结果应用到编辑器"""
        result = self.result_text.toPlainText()
        if result and self.parent():
            # 尝试获取主窗口的当前编辑器
            editor = None
            if hasattr(self.parent(), 'get_current_editor_widget'):
                editor = self.parent().get_current_editor_widget()
                
            if editor and hasattr(editor, 'textCursor') and hasattr(editor, 'insertPlainText'):
                cursor = editor.textCursor()
                if cursor.hasSelection():
                    cursor.removeSelectedText()
                cursor.insertText(result)
            else:
                QMessageBox.warning(
                    self, "应用失败", 
                    "无法将翻译结果应用到编辑器，请手动复制"
                )
        else:
            QMessageBox.warning(
                self, "应用失败", 
                "没有翻译结果或编辑器不可用"
            )
    
    def load_credentials(self):
        """加载API凭据（现在由TranslationService负责）"""
        # 在创建TranslationService实例时已经会自动尝试加载凭据
        # 这里不需要再次加载API凭据
        
        # 加载翻译偏好
        self.load_preferences()
    
    def get_preferences_file_path(self) -> str:
        """获取偏好设置文件的完整路径"""
        return os.path.join(self.PREFERENCES_DIR, self.PREFERENCES_FILE)
    
    def load_preferences(self):
        """从文件加载用户翻译偏好"""
        try:
            # 确保目录存在
            os.makedirs(self.PREFERENCES_DIR, exist_ok=True)
            
            file_path = self.get_preferences_file_path()
            if not os.path.exists(file_path):
                # 如果文件不存在，使用默认值
                return
                
            with open(file_path, 'r', encoding='utf-8') as f:
                preferences = json.load(f)
            
            # 记录默认语言选择
            self.default_from_lang = preferences.get("default_from_lang", "自动检测")
            self.default_to_lang = preferences.get("default_to_lang", "中文")
        except Exception as e:
            print(f"加载翻译偏好失败: {e}")
            # 出错时使用默认值
    
    def save_preferences(self):
        """保存用户翻译偏好到文件"""
        try:
            # 确保目录存在
            os.makedirs(self.PREFERENCES_DIR, exist_ok=True)
            
            # 保存当前语言选择
            preferences = {
                "default_from_lang": self.from_lang_combo.currentText(),
                "default_to_lang": self.to_lang_combo.currentText()
            }
            
            with open(self.get_preferences_file_path(), 'w', encoding='utf-8') as f:
                json.dump(preferences, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存翻译偏好失败: {e}")
    
    def set_text(self, text):
        """设置源文本并自动进行翻译"""
        if text:
            self.source_text.setPlainText(text)
            # 如果有API凭据，自动进行翻译
            if self.translation_service.has_credentials():
                self.translate_text()
                
    def keyPressEvent(self, event: QKeyEvent):
        """处理按键事件"""
        # 当按下Escape键时关闭窗口
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)
            
    def closeEvent(self, event):
        """关闭窗口时停止定时器并保存偏好"""
        self.selection_timer.stop()
        self.save_preferences()
        super().closeEvent(event)
        
    def showEvent(self, event):
        """显示窗口时如果选中了实时功能，重新启动定时器"""
        if self.live_selection:
            self.selection_timer.start()
        super().showEvent(event) 