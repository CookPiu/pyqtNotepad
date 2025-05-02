from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QSize

class ViewOperations:
    """处理MainWindow的视图操作功能"""
    
    def __init__(self, main_window):
        self.main_window = main_window
    
    def toggle_theme(self):
        """切换亮色/暗色主题"""
        self.main_window.theme_manager.toggle_theme()
        self.main_window.apply_current_theme()
        current_theme = "暗色" if self.main_window.theme_manager.is_dark_theme() else "亮色"
        self.main_window.statusBar.showMessage(f"已切换到{current_theme}主题")
    
    def toggle_zen_mode(self, checked):
        """切换Zen模式"""
        if checked:  # 进入Zen模式
            # 保存当前分割器大小以便恢复
            self.main_window._pre_zen_sizes = {
                'v_splitter': self.main_window.v_splitter.sizes(),
                'editor_browser': self.main_window.editor_browser_splitter.sizes()
            }
            
            # 隐藏侧边栏、工具栏、菜单栏和状态栏
            self.main_window.sidebar.setVisible(False)
            self.main_window.toolbar.setVisible(False)
            self.main_window.activity_bar.setVisible(False)
            self.main_window.menuBar().setVisible(False)
            self.main_window.statusBar.setVisible(False)
            
            # 隐藏浏览器区域
            sizes = self.main_window.editor_browser_splitter.sizes()
            if len(sizes) == 2 and sizes[1] > 0:  # 如果浏览器可见
                self.main_window.editor_browser_splitter.setSizes([1, 0])  # 折叠浏览器
            
            # 设置窗口为全屏
            self.main_window.showFullScreen()
            self.main_window.statusBar.showMessage("已进入Zen模式 (F11退出)")
        else:  # 退出Zen模式
            # 恢复分割器大小
            if self.main_window._pre_zen_sizes:
                if 'v_splitter' in self.main_window._pre_zen_sizes:
                    self.main_window.v_splitter.setSizes(self.main_window._pre_zen_sizes['v_splitter'])
                if 'editor_browser' in self.main_window._pre_zen_sizes:
                    self.main_window.editor_browser_splitter.setSizes(self.main_window._pre_zen_sizes['editor_browser'])
            
            # 恢复UI元素可见性
            self.main_window.sidebar.setVisible(True)
            self.main_window.toolbar.setVisible(True)
            self.main_window.activity_bar.setVisible(True)
            self.main_window.statusBar.setVisible(True)
            
            # 退出全屏
            self.main_window.showNormal()
            self.main_window.statusBar.showMessage("已退出Zen模式")
    
    def toggle_sidebar(self, show=None):
        """切换侧边栏显示/隐藏"""
        # 获取当前侧边栏宽度
        current_sizes = self.main_window.v_splitter.sizes()
        
        # 如果show参数未指定，则根据当前状态切换
        if show is None:
            show = current_sizes[0] == 0  # 如果当前宽度为0，则显示
        
        if show:  # 显示侧边栏
            # 恢复保存的宽度，或使用默认宽度
            new_sizes = [self.main_window._saved_sidebar_width, current_sizes[1] - self.main_window._saved_sidebar_width]
            self.main_window.v_splitter.setSizes(new_sizes)
            self.main_window.statusBar.showMessage("已显示侧边栏")
        else:  # 隐藏侧边栏
            # 保存当前宽度以便恢复
            if current_sizes[0] > 0:
                self.main_window._saved_sidebar_width = current_sizes[0]
            # 设置宽度为0以隐藏
            self.main_window.v_splitter.setSizes([0, sum(current_sizes)])
            self.main_window.statusBar.showMessage("已隐藏侧边栏")
    
    def _collapse_global_browser(self):
        """折叠全局浏览器区域"""
        if len(self.main_window.editor_browser_splitter.sizes()) == 2:
            self.main_window.editor_browser_splitter.setSizes([1, 0])
    
    def _restore_global_browser(self):
        """恢复全局浏览器区域"""
        if len(self.main_window.editor_browser_splitter.sizes()) == 2:
            self.main_window.editor_browser_splitter.setSizes([2, 1])
    
    def show_about(self):
        """显示关于信息"""
        QMessageBox.about(self.main_window, "关于多功能记事本",
                         "<h3>多功能记事本</h3>"
                         "<p>版本 1.0</p>"
                         "<p>一个功能丰富的记事本应用程序，支持文本编辑、PDF预览、计算器、日历等功能。</p>"
                         "<p>© 2023 示例公司</p>")