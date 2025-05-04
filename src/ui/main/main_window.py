# src/ui/main/main_window.py
import sys
import os
from PyQt6.QtWidgets import (QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QTextEdit, QListWidget, QListWidgetItem, QToolBar, QMenuBar, QMenu,
                             QStatusBar, QFileDialog, QFontDialog, QColorDialog, QMessageBox,
                              QInputDialog, QSplitter, QTabWidget, QToolButton, QDockWidget, QMenu, QSizePolicy)
from PyQt6.QtGui import QAction, QFont, QColor, QTextCursor, QIcon, QImage, QTextDocument, QPainter # Removed leading space
from PyQt6.QtCore import Qt, QSize, QUrl, QRect, QEvent, pyqtSignal, QPointF, QFile, QTextStream, QPoint, QSignalBlocker, QDateTime, QTimer # Import QTimer

# --- Corrected Relative Imports ---
# Core
from ..core.base_widget import BaseWidget # May not be directly needed here, but good practice # Corrected indentation

# Utils (ThemeManager might be accessed via UIManager or passed)
# from ...utils.theme_manager import ThemeManager # Old path, likely not needed directly

# Components (Operations and Initializer) - Adjust relative path
from .ui_initializer import UIInitializer # Updated import path
from ..components.file_operations import FileOperations
from ..components.edit_operations import EditOperations
from ..components.view_operations import ViewOperations
from ..components.ui_manager import UIManager

# Atomic/Composite/Views (UIManager or UIInitializer will handle these)
# No direct imports of specific widgets like TextEditor, HtmlEditor, CalendarWidget etc. needed here anymore.


class MainWindow(QMainWindow):
    """主应用程序窗口"""
    current_editor_changed = pyqtSignal(object) # Use object to allow QWidget or None
    theme_changed = pyqtSignal(bool) # Signal emitted when theme changes (True for dark, False for light)

    def __init__(self):
        print("▶ MainWindow.__init__ (Refactored)")
        super().__init__()

        # --- Initialize Core Components ---
        # UIManager now likely handles theme_manager access
        self.ui_manager = UIManager(self)
        # Operations classes need a reference to the main window and potentially the UIManager
        self.file_operations = FileOperations(self, self.ui_manager)
        self.edit_operations = EditOperations(self, self.ui_manager)
        self.view_operations = ViewOperations(self, self.ui_manager)

        # --- Create TabWidget directly in MainWindow ---
        print("MainWindow: Attempting to create QTabWidget...")
        try:
            self.tab_widget = QTabWidget(self) # Create with parent
            # print("DEBUG: tab_widget =", self.tab_widget) # REMOVED DEBUG PRINT
            # Use 'is not None' for explicit check against None, as Qt objects might evaluate differently in boolean context
            # Apply user patch: Change check to 'is None' for the error case
            if self.tab_widget is None:
                 # 只在 None 时报错
                 print("MainWindow: ERROR - QTabWidget creation returned None!")
                 # Keep None assignments here as it indicates a genuine failure
                 self.tab_widget = None
                 self.ui_manager.tab_widget = None
            else:
                 # This block now executes if tab_widget is NOT None
                 print("MainWindow: QTabWidget created successfully.")
                 self.tab_widget.setDocumentMode(True)
                 # Corrected indentation for the following lines:
                 self.tab_widget.setTabsClosable(True)
                 self.tab_widget.setMovable(True)
                 # Connect signal - ensure file_operations exists
                 # Connection moved to after file_operations is guaranteed to exist
                 # Assign to UIManager as well
                 self.ui_manager.tab_widget = self.tab_widget
            # Removed the stray 'else:' block that was here
        except Exception as e:
            print(f"MainWindow: EXCEPTION during QTabWidget creation: {e}")
            import traceback
            traceback.print_exc()
            # If an exception occurs, tab_widget might be partially initialized or invalid.
            # Setting to None might still be appropriate here, but let's follow instructions for now.
            # self.tab_widget = None # REMOVED
            # self.ui_manager.tab_widget = None # REMOVED

        # UIInitializer sets up the basic structure, now receives the tab_widget
        self.ui_initializer = UIInitializer(self, self.ui_manager, self.tab_widget) # Pass tab_widget

        # --- State Variables (Keep relevant ones) ---
        self.previous_editor = None # Still needed for signal management
        # Zen mode state might be managed by ViewOperations now
        # Sidebar state might be managed by ViewOperations now

        # --- Dock Options ---
        self.setDockOptions(
            QMainWindow.DockOption.AllowTabbedDocks
            | QMainWindow.DockOption.AnimatedDocks
        )

        # --- Create Actions ---
        # Actions connect to the wrapper methods which delegate to operation classes
        self.create_actions()

        # --- Setup UI via Initializer ---
        # UIInitializer will create central widget (splitter, tabs), docks, status bar etc.
        # It needs access to operations or UIManager to connect things like file_explorer signals
        self.ui_initializer.setup_ui() # This now builds the main structure

        # --- Create Menus and Toolbars (Using created actions) ---
        self.create_menu_bar()
        self.create_toolbar()

        # --- Apply Initial Theme (via UIManager) ---
        self.ui_manager.apply_current_theme()

        # --- Initial State ---
        # Connect signals managed by MainWindow itself
        # Use the directly created tab_widget
        if self.tab_widget is not None:
             # Connect signals now that file_operations definitely exists
             self.tab_widget.tabCloseRequested.connect(self.file_operations.close_tab)
             self.tab_widget.currentChanged.connect(self.on_current_tab_changed)
             # Ensure initial state update for actions
             self.on_current_tab_changed(self.tab_widget.currentIndex())
             # Create initial file if no tabs were restored/opened by initializer
             if self.tab_widget.count() == 0:
                 # Check if file_operations exists before calling (should always exist here)
                 if hasattr(self, 'file_operations'):
                      self.file_operations.new_file() # Use operation class
                 else:
                      print("MainWindow: ERROR - file_operations not available to create initial file.")
        else:
             # This message should now reflect MainWindow's attempt
             # This message should now reflect MainWindow's attempt
             print("错误：MainWindow 未能创建 tab_widget。")

        # Connect clipboard change signal to potentially update actions (optional but good practice)
        # Although paste is always enabled, this might be useful for other actions later.
        QApplication.clipboard().dataChanged.connect(
            lambda: self.update_edit_actions_state(self.get_current_editor_widget())
        )

        self.update_window_title() # Set initial window title

    # --- Action Creation (Remains largely the same) ---
    def create_actions(self):
        # Actions trigger the wrapper methods below
        self.new_action = QAction("新建文本", self, shortcut="Ctrl+N", toolTip="创建新文本文件 (Ctrl+N)", triggered=self.new_file_wrapper)
        self.new_html_action = QAction("新建HTML", self, shortcut="Ctrl+Shift+N", toolTip="创建新HTML文件 (Ctrl+Shift+N)", triggered=self.new_html_file_wrapper)
        self.open_action = QAction("打开...", self, shortcut="Ctrl+O", toolTip="打开现有文件 (Ctrl+O)", triggered=self.open_file_dialog_wrapper)
        self.save_action = QAction("保存", self, shortcut="Ctrl+S", toolTip="保存当前文件 (Ctrl+S)", triggered=self.save_file_wrapper, enabled=False)
        self.save_as_action = QAction("另存为...", self, shortcut="Ctrl+Shift+S", toolTip="将当前文件另存为... (Ctrl+Shift+S)", triggered=self.save_file_as_wrapper, enabled=False)
        self.close_tab_action = QAction("关闭标签页", self, shortcut="Ctrl+W", toolTip="关闭当前标签页 (Ctrl+W)", triggered=self.close_current_tab_wrapper, enabled=False)
        self.exit_action = QAction("退出", self, shortcut="Ctrl+Q", toolTip="退出应用程序 (Ctrl+Q)", triggered=self.close) # close is QMainWindow method

        self.undo_action = QAction("撤销", self, shortcut="Ctrl+Z", toolTip="撤销上一步操作 (Ctrl+Z)", triggered=self.undo_action_wrapper, enabled=False)
        self.redo_action = QAction("重做", self, shortcut="Ctrl+Y", toolTip="重做上一步操作 (Ctrl+Y)", triggered=self.redo_action_wrapper, enabled=False)
        self.cut_action = QAction("剪切", self, shortcut="Ctrl+X", toolTip="剪切选中内容 (Ctrl+X)", triggered=self.cut_action_wrapper, enabled=False)
        self.copy_action = QAction("复制", self, shortcut="Ctrl+C", toolTip="复制选中内容 (Ctrl+C)", triggered=self.copy_action_wrapper, enabled=False)
        # Keep paste action always enabled, logic handled in EditOperations.paste
        self.paste_action = QAction("粘贴", self, shortcut="Ctrl+V", toolTip="粘贴剪贴板内容 (Ctrl+V)", triggered=self.paste_action_wrapper, enabled=True)
        self.select_all_action = QAction("全选", self, shortcut="Ctrl+A", toolTip="全选文档内容 (Ctrl+A)", triggered=self.select_all_action_wrapper, enabled=False)

        self.font_action = QAction("字体...", self, toolTip="更改字体设置", triggered=self.change_font_wrapper, enabled=False)
        self.color_action = QAction("颜色...", self, toolTip="更改文本颜色", triggered=self.change_color_wrapper, enabled=False)
        self.insert_image_action = QAction("插入图片...", self, toolTip="在光标处插入图片", triggered=self.insert_image_wrapper, enabled=False) # Depends on editor type
        self.find_action = QAction("查找", self, shortcut="Ctrl+F", toolTip="在当前文件中查找文本 (Ctrl+F)", triggered=self.find_text_wrapper, enabled=False)
        self.replace_action = QAction("替换", self, shortcut="Ctrl+H", toolTip="在当前文件中查找并替换文本 (Ctrl+H)", triggered=self.replace_text_wrapper, enabled=False)

        self.toggle_theme_action = QAction("切换主题", self, shortcut="Ctrl+T", toolTip="切换亮色/暗色主题 (Ctrl+T)", triggered=self.toggle_theme_wrapper)
        self.zen_action = QAction("Zen Mode", self, checkable=True, shortcut="F11", triggered=self.toggle_zen_mode_wrapper, toolTip="进入/退出 Zen 模式 (F11)")
        # Sidebar toggle might be a direct button or menu item handled by ViewOperations/UIManager
        # self.toggle_sidebar_action = QAction("切换侧边栏", self, triggered=self.toggle_sidebar_wrapper)

        self.about_action = QAction("关于", self, toolTip="显示关于信息", triggered=self.show_about_wrapper)

    # --- Menu/Toolbar Creation (Remains largely the same, uses created actions) ---
    def create_menu_bar(self):
        menu_bar = self.menuBar()
        # ... (Add menus and actions as before) ...
        file_menu = menu_bar.addMenu("文件")
        file_menu.addActions([self.new_action, self.new_html_action, self.open_action, self.save_action, self.save_as_action])
        file_menu.addSeparator()
        file_menu.addAction(self.close_tab_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        edit_menu = menu_bar.addMenu("编辑")
        edit_menu.addActions([self.undo_action, self.redo_action])
        edit_menu.addSeparator()
        edit_menu.addActions([self.cut_action, self.copy_action, self.paste_action])
        edit_menu.addSeparator()
        edit_menu.addAction(self.select_all_action)
        edit_menu.addSeparator()
        edit_menu.addActions([self.find_action, self.replace_action])

        format_menu = menu_bar.addMenu("格式")
        format_menu.addActions([self.font_action, self.color_action])
        format_menu.addSeparator()
        format_menu.addAction(self.insert_image_action)
        format_menu.addSeparator()
        format_menu.addAction(self.toggle_theme_action)

        view_menu = menu_bar.addMenu("视图")
        view_menu.addAction(self.zen_action)
        # Add toggle sidebar action if needed
        # view_menu.addAction(self.toggle_sidebar_action)

        help_menu = menu_bar.addMenu("帮助")
        help_menu.addAction(self.about_action)

        menu_bar.setVisible(False) # Keep hidden by default

    def create_toolbar(self):
        # Toolbar is likely created by UIInitializer now, just add actions to it
        if not hasattr(self, 'toolbar'):
             print("警告: UIInitializer 未创建 toolbar。")
             self.toolbar = self.addToolBar("MainToolBar") # Create fallback
        else:
             self.toolbar.clear() # Clear any defaults added by initializer

        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(20, 20))

        self.toolbar.addActions([self.new_action, self.new_html_action, self.open_action, self.save_action])
        self.toolbar.addSeparator()
        self.toolbar.addActions([self.undo_action, self.redo_action])
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.find_action)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.toolbar.addWidget(spacer)

        menu_btn = QToolButton()
        menu_btn.setText("...")
        menu_btn.setToolTip("更多选项")
        menu_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        more_menu = QMenu(menu_btn)
        # ... (Add submenus and actions as before) ...
        file_submenu = more_menu.addMenu("文件")
        file_submenu.addActions([self.save_as_action, self.close_tab_action])
        file_submenu.addSeparator()
        file_submenu.addAction(self.exit_action)
        edit_submenu = more_menu.addMenu("编辑")
        edit_submenu.addActions([self.cut_action, self.copy_action, self.paste_action, self.select_all_action])
        edit_submenu.addSeparator()
        edit_submenu.addAction(self.replace_action)
        format_submenu = more_menu.addMenu("格式")
        format_submenu.addActions([self.font_action, self.color_action, self.insert_image_action])
        view_submenu = more_menu.addMenu("视图")
        view_submenu.addAction(self.toggle_theme_action)
        view_submenu.addSeparator()
        view_submenu.addAction(self.zen_action)
        help_submenu = more_menu.addMenu("帮助")
        help_submenu.addAction(self.about_action)
        menu_btn.setMenu(more_menu)
        self.toolbar.addWidget(menu_btn)

        self.addAction(self.zen_action) # Ensure global shortcut works

    # --- Wrapper Methods Delegating to Operation Classes ---
    # These wrappers keep the action connections simple in create_actions
    def new_file_wrapper(self): self.file_operations.new_file()
    def new_html_file_wrapper(self): self.file_operations.new_file(file_type="html")
    def open_file_dialog_wrapper(self): self.file_operations.open_file_dialog()
    def save_file_wrapper(self): self.file_operations.save_file()
    def save_file_as_wrapper(self): self.file_operations.save_file_as()
    def close_current_tab_wrapper(self):
        if self.ui_manager.tab_widget:
             self.file_operations.close_tab(self.ui_manager.tab_widget.currentIndex())
    def undo_action_wrapper(self): self.edit_operations.undo_action_handler()
    def redo_action_wrapper(self): self.edit_operations.redo_action_handler()
    def cut_action_wrapper(self): self.edit_operations.cut_action_handler()
    def copy_action_wrapper(self): self.edit_operations.copy_action_handler()
    # Corrected to call the renamed 'paste' method in EditOperations
    def paste_action_wrapper(self): self.edit_operations.paste()
    def select_all_action_wrapper(self): self.edit_operations.select_all_action_handler()
    def change_font_wrapper(self): self.edit_operations.change_font()
    def change_color_wrapper(self): self.edit_operations.change_color()
    def insert_image_wrapper(self): self.edit_operations.insert_image()
    def find_text_wrapper(self): self.edit_operations.find_text()
    def replace_text_wrapper(self): self.edit_operations.replace_text()
    def toggle_theme_wrapper(self): self.view_operations.toggle_theme()
    def toggle_zen_mode_wrapper(self, checked): self.view_operations.toggle_zen_mode(checked)
    # def toggle_sidebar_wrapper(self): self.view_operations.toggle_sidebar() # If action exists
    def show_about_wrapper(self): self.view_operations.show_about()

    # --- Core MainWindow Logic ---
    def get_current_editor_widget(self) -> QWidget | None:
        """
        Gets the actual underlying editor widget (_InternalTextEdit or HtmlEditor)
        from the current central tab, handling potential wrappers.
        """
        if not (self.ui_manager and self.ui_manager.tab_widget):
            return None
        current_tab_content = self.ui_manager.tab_widget.currentWidget()
        if not current_tab_content:
            return None

        # Import necessary types locally to avoid potential top-level circular imports
        from ..atomic.editor.html_editor import HtmlEditor
        from ..atomic.editor.text_editor import TextEditor, _InternalTextEdit

        # Case 1: The widget in the tab IS the TextEditor wrapper
        if isinstance(current_tab_content, TextEditor):
            if hasattr(current_tab_content, '_editor'):
                # print("DEBUG: get_current_editor_widget: Returning _editor from TextEditor wrapper")
                return current_tab_content._editor # Return the internal _InternalTextEdit
            else:
                print("Warning: get_current_editor_widget: TextEditor wrapper has no _editor attribute.")
                return current_tab_content # Fallback to wrapper

        # Case 2: The widget in the tab IS the HtmlEditor (which is the actual editor)
        if isinstance(current_tab_content, HtmlEditor):
             # print("DEBUG: get_current_editor_widget: Returning HtmlEditor directly")
             return current_tab_content

        # Case 3: The widget in the tab IS the _InternalTextEdit (less likely but possible)
        if isinstance(current_tab_content, _InternalTextEdit):
             # print("DEBUG: get_current_editor_widget: Returning _InternalTextEdit directly")
             return current_tab_content

        # Case 4: Check for nested editors as a fallback (e.g., if editor is inside another container)
        html_editor = current_tab_content.findChild(HtmlEditor)
        if html_editor:
            # print("DEBUG: get_current_editor_widget: Found nested HtmlEditor")
            return html_editor

        text_editor_wrapper = current_tab_content.findChild(TextEditor)
        if text_editor_wrapper:
            if hasattr(text_editor_wrapper, '_editor'):
                # print("DEBUG: get_current_editor_widget: Found nested TextEditor wrapper, returning _editor")
                return text_editor_wrapper._editor
            else:
                print("Warning: get_current_editor_widget: Found nested TextEditor wrapper but no _editor attribute.")
                return text_editor_wrapper

        # Case 5: It's not an editor we know how to handle
        # print(f"DEBUG: get_current_editor_widget: Returning non-editor widget: {type(current_tab_content)}")
        return current_tab_content # Return the original widget (e.g., a view)

    def get_current_editor(self):
        """获取当前编辑器的别名方法，用于兼容性"""
        return self.get_current_editor_widget()

    def on_current_tab_changed(self, index):
        """Updates UI elements when the current tab changes."""
        current_widget = self.get_current_editor_widget()
        self.update_edit_actions_state(current_widget)
        self.update_window_title()
        self.current_editor_changed.emit(current_widget) # Emit signal with current widget

        # Handle special view logic (like collapsing browser for downloader)
        self.view_operations.handle_tab_change(current_widget)

        # Explicitly set focus if the current widget is an editor
        if self.ui_manager.is_widget_editor(current_widget):
             current_widget.setFocus() # Ensure the Qt widget gets focus first
             # For HtmlEditor, try focusing its child widget after the main widget gets focus
             from ..atomic.editor.html_editor import HtmlEditor # Need import for isinstance
             if isinstance(current_widget, HtmlEditor):
                 # QWebEngineView often has a child QWidget that handles rendering/input
                 child_widget = current_widget.findChild(QWidget)
                 if child_widget:
                     # Use a timer to ensure the focus change happens after the current event processing
                     QTimer.singleShot(0, child_widget.setFocus)
                     # print("MainWindow.on_current_tab_changed: Scheduled focus for HtmlEditor child.") # Debug
                 # else:
                     # print("MainWindow.on_current_tab_changed: No child QWidget found for HtmlEditor.") # Debug


    def _update_copy_cut_state(self, available: bool):
        """Slot to update copy/cut action states."""
        self.copy_action.setEnabled(available)
        self.cut_action.setEnabled(available)

    def update_edit_actions_state(self, current_widget: QWidget | None):
        """Updates the enabled state of edit actions based on the current widget."""
        # --- 1. Disconnect previous editor signals ---
        if self.previous_editor and hasattr(self.previous_editor, 'document'):
            prev_doc = self.previous_editor.document()
            prev_copy_signal = None
            if hasattr(self.previous_editor, 'copyAvailable'):
                 prev_copy_signal = self.previous_editor.copyAvailable
                 if callable(prev_copy_signal): prev_copy_signal = prev_copy_signal()
            try: prev_doc.undoAvailable.disconnect(self.undo_action.setEnabled)
            except TypeError: pass
            try: prev_doc.redoAvailable.disconnect(self.redo_action.setEnabled)
            except TypeError: pass
            if prev_copy_signal:
                 try: prev_copy_signal.disconnect(self._update_copy_cut_state)
                 except TypeError: pass
            try: prev_doc.modificationChanged.disconnect(self.update_tab_title)
            except TypeError: pass
        self.previous_editor = None # Reset previous editor reference

        # --- 2. Determine states based on current_widget ---
        is_editor = self.ui_manager.is_widget_editor(current_widget)
        is_html_editor = self.ui_manager.is_widget_html_editor(current_widget)
        is_undoable = False
        is_redoable = False
        has_selection = False
        # Qt6: 通过 mimeData().hasText() 判断剪贴板中是否有文本 (Applying user patch)
        can_paste = QApplication.clipboard().mimeData().hasText()

        # 只有当 widget 真正支持 document() 和 textCursor() 时，才当作纯文本编辑器处理 (Applying user patch)
        if is_editor and hasattr(current_widget, "document") and hasattr(current_widget, "textCursor"):
            # We know current_widget is not None here and is an editor
            editor_doc = current_widget.document()
            editor_cursor = current_widget.textCursor()
            copy_available_signal = None
            if hasattr(current_widget, 'copyAvailable'):
                copy_available_signal = current_widget.copyAvailable
                if callable(copy_available_signal): copy_available_signal = copy_available_signal()

            # … 以下保持原逻辑，计算 undo/redo/选区状态、连接信号等 …
            # Determine editor-specific states
            has_selection = editor_cursor is not None and editor_cursor.hasSelection()
            is_undoable = editor_doc is not None and editor_doc.isUndoAvailable()
            is_redoable = editor_doc is not None and editor_doc.isRedoAvailable()

            # --- 3. Connect signals for the new editor ---
            try: editor_doc.undoAvailable.connect(self.undo_action.setEnabled)
            except TypeError: pass
            try: editor_doc.redoAvailable.connect(self.redo_action.setEnabled)
            except TypeError: pass
            if copy_available_signal:
                 try: copy_available_signal.connect(self._update_copy_cut_state)
                 except TypeError: pass
            try: editor_doc.modificationChanged.connect(self.update_tab_title)
            except TypeError: pass
            self.previous_editor = current_widget # Set the new previous editor
        else:
            # 非文本编辑器（比如 HtmlEditor），不执行 document/cursor 相关操作
            # is_editor     = False # REMOVE THIS LINE - Don't override is_editor here
            editor_doc    = None
            editor_cursor = None
            # has_selection, is_undoable, is_redoable 均保持 False
            # 后面会根据 is_editor = False 自动关闭这些动作

        # --- 4. Update action states ---
        self.undo_action.setEnabled(is_undoable)
        self.redo_action.setEnabled(is_redoable)
        self.cut_action.setEnabled(has_selection)
        self.copy_action.setEnabled(has_selection)
        # 粘贴操作由 EditOperations.paste 内部判断图片/文本，菜单始终可用
        self.paste_action.setEnabled(True)
        self.select_all_action.setEnabled(is_editor)
        self.font_action.setEnabled(is_editor)
        self.color_action.setEnabled(is_editor)
        # 只有当前标签是真正的 HtmlEditor 时，才启用“插入图片”
        is_html = self.ui_manager.is_widget_html_editor(current_widget)
        self.insert_image_action.setEnabled(is_html)
        self.save_action.setEnabled(is_editor)
        self.save_as_action.setEnabled(is_editor)
        # Close tab action depends only on whether tabs exist
        self.close_tab_action.setEnabled(self.ui_manager.tab_widget.count() > 0 if self.ui_manager.tab_widget else False)
        self.find_action.setEnabled(is_editor)
        self.replace_action.setEnabled(is_editor)


    def update_window_title(self):
        """Updates the main window title based on the current tab."""
        title_prefix = "Pynote Refactored" # New app name
        current_widget = self.get_current_editor_widget()
        if current_widget and self.ui_manager.tab_widget and (index := self.ui_manager.tab_widget.currentIndex()) != -1:
            tab_text = self.ui_manager.tab_widget.tabText(index)
            if tab_text:
                base_tab_text = tab_text[:-1].strip() if tab_text.endswith("*") else tab_text
                title_prefix = f"{base_tab_text} - {title_prefix}"
        self.setWindowTitle(title_prefix)

    def update_tab_title(self, modified: bool | None = None):
        """Updates the current tab's text to indicate modification status."""
        if self.ui_manager and self.ui_manager.tab_widget:
             index = self.ui_manager.tab_widget.currentIndex()
             if index == -1: return
             current_widget = self.ui_manager.tab_widget.widget(index)

             # If modified status not passed, get it from the widget
             if modified is None:
                 if self.ui_manager.is_widget_editor(current_widget) and hasattr(current_widget, 'isModified'):
                     modified = current_widget.isModified()
                 else:
                     return # Cannot determine modification status

             # Get base name (filename or untitled name)
             base_name = self.ui_manager.get_widget_base_name(current_widget)
             if not base_name: # Fallback if name cannot be determined
                  base_name = f"标签 {index + 1}"

             new_tab_text = f"{base_name}{'*' if modified else ''}"
             self.ui_manager.tab_widget.setTabText(index, new_tab_text)
             self.update_window_title() # Update window title as well

    def closeEvent(self, event):
        """Handles the main window close event, checks for unsaved changes."""
        if self.file_operations.close_all_tabs():
            # Save geometry or other settings if needed
            # settings = QSettings("YourOrg", "YourApp")
            # settings.setValue("geometry", self.saveGeometry())
            event.accept()
        else:
            event.ignore() # User cancelled closing

# Application entry point should be in main.py now
# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     # Ensure QWebEngine is initialized if used
#     # QWebEngineProfile.defaultProfile() # Example initialization
#     window = MainWindow()
#     window.show()
#     sys.exit(app.exec())
