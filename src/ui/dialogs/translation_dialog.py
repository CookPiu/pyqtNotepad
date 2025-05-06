from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
                           QTextEdit, QPushButton, QLineEdit, QMessageBox, QGroupBox,
                           QFormLayout, QDialogButtonBox, QTabWidget, QWidget, QApplication,
                           QGridLayout, QSplitter)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QColor, QPalette
from src.services.translation_service import TranslationService


class TranslationDialog(QDialog):
    """翻译对话框，用于文本翻译和API设置"""
    
    def __init__(self, parent=None, selected_text=""):
        super().__init__(parent)
        self.setWindowTitle("文本翻译")
        self.resize(600, 400)
        
        # 创建翻译服务
        self.translation_service = TranslationService()
        # 从设置中加载API凭据
        self.load_credentials()
        
        # 初始文本
        self.selected_text = selected_text
        
        # 初始化界面
        self._init_ui()
        self._apply_styles()
        
    def _init_ui(self):
        """初始化用户界面"""
        # 使用垂直布局作为主布局
        main_layout = QVBoxLayout(self)
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
        
        main_layout.addLayout(button_layout)
        
        # 如果有选定文本，填充并激活
        if self.selected_text:
            self.source_text.setPlainText(self.selected_text)
            self.translate_text()
    
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
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            api_settings = dialog.get_api_settings()
            self.translation_service.set_credentials(
                api_settings["app_id"], 
                api_settings["app_secret"]
            )
            
            # 保存到设置
            settings = QSettings("PyQtNotepad", "TranslationService")
            settings.setValue("baidu_app_id", api_settings["app_id"])
            settings.setValue("baidu_app_secret", api_settings["app_secret"])
            
            QMessageBox.information(self, "API设置", "API凭据已保存")
        
    def populate_language_combos(self):
        """填充语言下拉列表"""
        languages = self.translation_service.get_language_list()
        
        for name in languages.keys():
            self.from_lang_combo.addItem(name, languages[name])
            self.to_lang_combo.addItem(name, languages[name])
        
        # 设置默认值
        auto_index = self.from_lang_combo.findText("自动检测")
        if auto_index >= 0:
            self.from_lang_combo.setCurrentIndex(auto_index)
        
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
                "请点击'API设置'按钮配置您的API凭据"
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
                self.accept()  # 关闭对话框
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
        """从设置加载API凭据"""
        settings = QSettings("PyQtNotepad", "TranslationService")
        app_id = settings.value("baidu_app_id", "")
        app_secret = settings.value("baidu_app_secret", "")
        
        if app_id and app_secret:
            self.translation_service.set_credentials(app_id, app_secret)
            
class APIConfigDialog(QDialog):
    """API配置对话框"""
    
    def __init__(self, parent=None, app_id="", app_secret=""):
        super().__init__(parent)
        self.setWindowTitle("API配置")
        self.setMinimumWidth(400)
        
        self.app_id = app_id
        self.app_secret = app_secret
        
        self.init_ui()
        self._apply_styles()
        
    def init_ui(self):
        layout = QGridLayout()
        
        # APP ID输入
        self.app_id_label = QLabel("APP ID:")
        self.app_id_input = QLineEdit()
        self.app_id_input.setPlaceholderText("输入百度翻译API的APP ID")
        self.app_id_input.setText(self.app_id)
        layout.addWidget(self.app_id_label, 0, 0)
        layout.addWidget(self.app_id_input, 0, 1)
        
        # API密钥输入
        self.app_secret_label = QLabel("API密钥:")
        self.app_secret_input = QLineEdit()
        self.app_secret_input.setPlaceholderText("输入百度翻译API的密钥")
        self.app_secret_input.setText(self.app_secret)
        self.app_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.app_secret_label, 1, 0)
        layout.addWidget(self.app_secret_input, 1, 1)
        
        # 说明文本
        info_label = QLabel(
            "请输入您的API凭据。\n"
            "如果您还没有，请前往开放平台申请：\n"
        )
        info_label.setTextFormat(Qt.TextFormat.RichText)
        info_label.setOpenExternalLinks(True)
        layout.addWidget(info_label, 2, 0, 1, 2)
        
        # 按钮
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout, 3, 0, 1, 2)
        
        self.setLayout(layout)
        
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
        """
        
        self.save_btn.setStyleSheet(button_style)
        
        cancel_style = """
        QPushButton {
            background-color: #e0e0e0;
            color: #424242;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #eeeeee;
        }
        QPushButton:pressed {
            background-color: #bdbdbd;
        }
        """
        self.cancel_btn.setStyleSheet(cancel_style)
        
        # 输入框样式
        input_style = """
        QLineEdit {
            border: 1px solid #bdbdbd;
            border-radius: 4px;
            padding: 6px;
            background-color: white;
        }
        QLineEdit:focus {
            border: 1px solid #2979ff;
        }
        """
        self.app_id_input.setStyleSheet(input_style)
        self.app_secret_input.setStyleSheet(input_style)
    
    def get_api_settings(self):
        return {
            "app_id": self.app_id_input.text().strip(),
            "app_secret": self.app_secret_input.text().strip()
        } 