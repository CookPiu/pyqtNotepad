from PyQt6.QtWidgets import QMessageBox, QDockWidget, QWidget # Add QDockWidget and QWidget
from PyQt6.QtCore import QSize, Qt # Add Qt

# Assuming UIManager is accessible via main_window or passed separately
# from .ui_manager import UIManager

class ViewOperations:
    """处理MainWindow的视图操作功能 (Refactored)"""
    
    def __init__(self, main_window, ui_manager): # Accept ui_manager
        self.main_window = main_window
        self.ui_manager = ui_manager # Store ui_manager
        self._pre_zen_state = {} # Store visibility state for Zen mode

    def toggle_theme(self):
        """切换亮色/暗色主题 (Delegates to UIManager)"""
        # UIManager now handles theme toggling and application
        self.ui_manager.toggle_theme()
        # Status message update might also be handled by UIManager or MainWindow
        current_theme = "暗色" if self.ui_manager.theme_manager.is_dark_theme() else "亮色"
        if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar:
             self.main_window.statusBar.showMessage(f"已切换到{current_theme}主题")
    
    def toggle_zen_mode(self, checked: bool):
        """切换 Zen 模式"""
        if checked:  # 进入 Zen 模式
            self._pre_zen_state = {
                'sidebar_visible': self.main_window.sidebar_dock.isVisible(),
                'activity_bar_visible': self.main_window.activity_bar_dock.isVisible(),
                'toolbar_visible': self.main_window.toolbar.isVisible(),
                'statusbar_visible': self.main_window.statusBar.isVisible(),
                'ai_chat_visible': self.main_window.ai_chat_dock.isVisible() if hasattr(self.main_window, 'ai_chat_dock') else False,
                'window_state': self.main_window.windowState() # Save normal/maximized state
            }
            # Hide docks and bars
            self.main_window.sidebar_dock.hide()
            self.main_window.activity_bar_dock.hide()
            self.main_window.toolbar.hide()
            self.main_window.statusBar.hide()
            # Hide AI chat dock if it exists
            if hasattr(self.main_window, 'ai_chat_dock'):
                self.main_window.ai_chat_dock.hide()
            # Hide menu bar if it exists and is visible
            if self.main_window.menuBar(): self.main_window.menuBar().hide()

            # Hide other docks managed by UIManager? (Optional)
            # for dock in self.ui_manager.view_docks.values(): dock.hide()

            self.main_window.showFullScreen()
            if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar:
                 # Status bar is hidden, maybe show temporary message elsewhere or log
                 print("已进入Zen模式 (F11退出)")
        else:  # 退出 Zen 模式
            # Restore visibility based on saved state
            if self._pre_zen_state.get('sidebar_visible', True): self.main_window.sidebar_dock.show()
            if self._pre_zen_state.get('activity_bar_visible', True): self.main_window.activity_bar_dock.show()
            if self._pre_zen_state.get('toolbar_visible', True): self.main_window.toolbar.show()
            if self._pre_zen_state.get('statusbar_visible', True): self.main_window.statusBar.show()
            # Restore AI chat dock if it exists
            if hasattr(self.main_window, 'ai_chat_dock') and self._pre_zen_state.get('ai_chat_visible', False):
                self.main_window.ai_chat_dock.show()
                if hasattr(self.main_window, 'toggle_ai_chat_action'):
                    self.main_window.toggle_ai_chat_action.setChecked(True)
            if self.main_window.menuBar(): self.main_window.menuBar().setVisible(False) # Keep menu hidden by default

            # Restore previous window state (Normal or Maximized)
            previous_state = self._pre_zen_state.get('window_state', Qt.WindowState.WindowNoState)
            if previous_state == Qt.WindowState.WindowMaximized:
                 self.main_window.showMaximized()
            else:
                 self.main_window.showNormal()

            if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar:
                 self.main_window.statusBar.showMessage("已退出Zen模式")
            self._pre_zen_state = {} # Clear saved state
    
    def toggle_sidebar(self, show: bool | None = None):
        """切换侧边栏 Dock 的可见性"""
        if not hasattr(self.main_window, 'sidebar_dock'): return

        if show is None:
            show = not self.main_window.sidebar_dock.isVisible()

        self.main_window.sidebar_dock.setVisible(show)
        # Status message update might be redundant if visibilityChanged signal handles it
        # if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar:
        #      status = "显示" if show else "隐藏"
        #      self.main_window.statusBar.showMessage(f"侧边栏已{status}")
    # --- Browser Pane Handling (Removed/Commented - Depends on Final Layout) ---
    # def _collapse_global_browser(self):
    #     """折叠全局浏览器区域 (If applicable)"""
    #     # Check if the relevant splitter exists and adjust sizes
    #     # Example: if hasattr(self.main_window, 'editor_browser_splitter'): ...
    #     print("Note: Global browser collapse logic needs review based on final layout.")
    #
    # def _restore_global_browser(self):
    #     """恢复全局浏览器区域 (If applicable)"""
    #     # Check if the relevant splitter exists and adjust sizes
    #     print("Note: Global browser restore logic needs review based on final layout.")

    def handle_tab_change(self, current_widget: QWidget | None):
         """根据当前标签页调整UI（例如，浏览器面板）"""
         # This logic might be simplified or removed if the browser pane isn't used globally
         # Example: Check if current_widget is NoteDownloaderView and collapse browser
         # from ..views.note_downloader_view import NoteDownloaderView # Import locally if needed
         # if isinstance(current_widget, NoteDownloaderView):
         #      self._collapse_global_browser()
         # else:
         #      self._restore_global_browser()
         pass # Placeholder - review based on final layout needs

    def show_about(self):
        """显示关于信息"""
        QMessageBox.about(self.main_window, "关于 Pynote Refactored",
                         "<h3>Pynote Refactored</h3>"
                         "<p>版本 1.1 (重构版)</p>"
                         "<p>一个基于 PyQt6 的多功能记事本应用。</p>"
                         "<p>包含文本/HTML 编辑、文件浏览、PDF 预览、工具集等。</p>")
