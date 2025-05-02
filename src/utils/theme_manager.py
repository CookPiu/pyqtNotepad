import os
from PyQt6.QtCore import QFile, QTextStream, QSettings


class ThemeManager:
    """主题管理类，用于管理应用程序的主题样式"""
    
    LIGHT_THEME = "light"
    DARK_THEME = "dark"
    
    def __init__(self):
        self.current_theme = self.LIGHT_THEME
        self.settings = QSettings("PythonProject", "TextEditor")
        self.load_saved_theme()
        
    def load_saved_theme(self):
        """从设置中加载保存的主题"""
        saved_theme = self.settings.value("theme", self.LIGHT_THEME)
        self.current_theme = saved_theme
    
    def save_theme(self, theme):
        """保存主题设置"""
        self.settings.setValue("theme", theme)
        self.current_theme = theme
    
    def get_current_theme(self):
        """获取当前主题"""
        return self.current_theme
    
    def toggle_theme(self):
        """切换主题"""
        if self.current_theme == self.LIGHT_THEME:
            self.current_theme = self.DARK_THEME
        else:
            self.current_theme = self.LIGHT_THEME
        self.save_theme(self.current_theme)
        return self.current_theme
    
    def apply_theme(self, app):
        """应用主题到应用程序"""
        if self.current_theme == self.LIGHT_THEME:
            stylesheet = self.load_light_theme()
        else:
            stylesheet = self.load_dark_theme()
        # Apply the loaded stylesheet
        app.setStyleSheet(stylesheet)

    def load_light_theme(self):
        """加载浅色主题样式表"""
        # Point to the new light theme file
        return self._load_stylesheet("style_light.qss")

    def load_dark_theme(self):
        """加载深色主题样式表"""
        return self._load_stylesheet("style_dark.qss")

    def _load_stylesheet(self, filename):
        """加载样式表文件"""
        # Corrected path calculation: Go up two directories from src/utils to project root, then into assets
        assets_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets"))
        file_path = os.path.join(assets_dir, filename)
        qss_file = QFile(file_path)

        if qss_file.exists() and qss_file.open(QFile.OpenModeFlag.ReadOnly | QFile.OpenModeFlag.Text):
            stream = QTextStream(qss_file)
            stylesheet = stream.readAll()
            qss_file.close()
            return stylesheet
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
