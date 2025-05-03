# src/ui/core/theme_manager.py
import os
from PyQt6.QtCore import QFile, QTextStream, QSettings, QStringConverter # Added QStringConverter


class ThemeManager:
    """主题管理类，用于管理应用程序的主题样式 (位于 src/ui/core)"""

    LIGHT_THEME = "light"
    DARK_THEME = "dark"

    def __init__(self):
        self.current_theme = self.LIGHT_THEME
        # 使用统一的组织和应用名称
        self.settings = QSettings("PynoteOrg", "PynoteApp") # 建议使用更具体的名称
        self.load_saved_theme()

    def load_saved_theme(self):
        """从设置中加载保存的主题"""
        saved_theme = self.settings.value("theme", self.LIGHT_THEME)
        # 基本验证，确保加载的值是有效的
        if saved_theme in [self.LIGHT_THEME, self.DARK_THEME]:
             self.current_theme = saved_theme
        else:
             self.current_theme = self.LIGHT_THEME # 默认值

    def save_theme(self, theme):
        """保存主题设置"""
        if theme in [self.LIGHT_THEME, self.DARK_THEME]:
            self.settings.setValue("theme", theme)
            self.current_theme = theme

    def get_current_theme(self):
        """获取当前主题"""
        return self.current_theme

    def toggle_theme(self):
        """切换主题"""
        if self.current_theme == self.LIGHT_THEME:
            new_theme = self.DARK_THEME
        else:
            new_theme = self.LIGHT_THEME
        self.save_theme(new_theme)
        return new_theme

    def apply_theme(self, app):
        """应用主题到应用程序"""
        stylesheet = self.get_current_style_sheet()
        if stylesheet:
            app.setStyleSheet(stylesheet)
        # TODO: 可能还需要通知所有 BaseWidget/BaseDialog 更新其样式

    def load_light_theme(self):
        """加载浅色主题样式表"""
        return self._load_stylesheet("style_light.qss")

    def load_dark_theme(self):
        """加载深色主题样式表"""
        return self._load_stylesheet("style_dark.qss")

    def _load_stylesheet(self, filename):
        """加载样式表文件"""
        # 新路径计算：从 src/ui/core 出发，向上三级到项目根目录，再进入 assets
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
            assets_dir = os.path.join(project_root, "assets")
            file_path = os.path.join(assets_dir, filename)
        except Exception as e:
            print(f"Error calculating stylesheet path: {e}")
            return ""

        qss_file = QFile(file_path)

        if not qss_file.exists():
            print(f"Stylesheet file not found at: {file_path}")
            return ""

        if qss_file.open(QFile.OpenModeFlag.ReadOnly | QFile.OpenModeFlag.Text):
            stream = QTextStream(qss_file)
            stream.setEncoding(QStringConverter.Encoding.Utf8) # 确保使用 UTF-8 读取
            stylesheet = stream.readAll()
            qss_file.close()
            return stylesheet
        else:
            print(f"Could not open stylesheet file: {file_path}, Error: {qss_file.errorString()}")
            return ""

    def get_current_style_sheet(self):
        """获取当前主题的样式表"""
        if self.current_theme == self.LIGHT_THEME:
            return self.load_light_theme()
        else:
            return self.load_dark_theme()

    def is_dark_theme(self):
        """检查当前主题是否为深色主题"""
        return self.current_theme == self.DARK_THEME

# 单例模式或全局实例管理 (可选)
# _instance = None
# def get_theme_manager():
#     global _instance
#     if _instance is None:
#         _instance = ThemeManager()
#     return _instance
