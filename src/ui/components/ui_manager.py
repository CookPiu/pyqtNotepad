import os
from PyQt6.QtWidgets import QDockWidget, QMessageBox, QWidget, QTabWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon # **Import QIcon**

# --- Corrected Relative Imports ---
from ..composite.combined_tools import CombinedTools
from ..atomic.mini_tools.calculator_widget import CalculatorWidget
from ..atomic.mini_tools.timer_widget import TimerWidget # Added TimerWidget
from ..atomic.mini_tools.speech_recognition_widget import SpeechRecognitionWidget
from ..views.note_downloader_view import NoteDownloaderView
from ..views.pdf_viewer_view import PdfViewerView
# Import BaseWidget for type checking if needed
from ..core.base_widget import BaseWidget
# Import editor types for checking
from ..atomic.editor.text_editor import TextEditor
from ..atomic.editor.html_editor import HtmlEditor
# Import ThemeManager if needed directly (though likely handled by MainWindow now)
from ..core.theme_manager import ThemeManager


class UIManager:
    """处理MainWindow的UI管理功能，包括主题应用、视图/编辑器管理和工具窗口管理"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.tab_widget = None # Explicitly initialize tab_widget
        self.theme_manager = ThemeManager() # Create ThemeManager instance here
        self.registered_views = {} # Initialize view registry
        self.view_instances = {} # Initialize instance cache
        self.view_docks = {} # Initialize dock cache
        
        # 注册核心视图和组件
        self.register_speech_recognition()
        self.register_view(NoteDownloaderView, "NoteDownloader") # 注册笔记下载器
        self.register_view(CalculatorWidget, "计算器")
        self.register_view(TimerWidget, "计时器")
    
    def apply_current_theme(self):
        """应用当前主题到UI组件"""
        # Theme application might be more complex now, involving child widgets
        # This method might need access to the ThemeManager instance
        # theme_manager is now initialized in __init__
        style_sheet = self.theme_manager.get_current_style_sheet()
        if style_sheet: # Check if stylesheet loaded correctly
            self.main_window.setStyleSheet(style_sheet) # Apply base style to main window
        else:
            print("警告: 未能加载样式表，无法应用主题。")

        # Propagate theme update to all relevant children managed by UIManager
        is_dark = self.theme_manager.is_dark_theme()
        # Update docks, tabs, etc.
        if hasattr(self.main_window, 'sidebar_dock') and hasattr(self.main_window.sidebar_dock.widget(), 'update_styles'):
            self.main_window.sidebar_dock.widget().update_styles(is_dark)
        # Update open tabs/views
        if self.tab_widget: # Check if tab_widget exists
            for i in range(self.tab_widget.count()):
                widget = self.tab_widget.widget(i)
                if hasattr(widget, 'update_styles'):
                    widget.update_styles(is_dark)
                elif hasattr(widget, 'update_colors'): # Handle editors specifically
                    widget.update_colors(is_dark)

        current_theme = "暗色" if is_dark else "亮色"
        if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar:
            self.main_window.statusBar.showMessage(f"已应用{current_theme}主题")

    def toggle_theme(self):
        """Toggles the theme and applies it."""
        print("UIManager: Toggling theme...")
        self.theme_manager.toggle_theme()
        self.apply_current_theme()
        # Emit signal from main_window if needed for external listeners
        if hasattr(self.main_window, 'theme_changed'):
             self.main_window.theme_changed.emit(self.theme_manager.is_dark_theme())
        print(f"UIManager: Theme toggled to {'dark' if self.theme_manager.is_dark_theme() else 'light'}")

    def open_note_downloader_tab(self):
        """打开笔记下载器标签页"""
        # Use the new open_view method
        self.open_view(view_name="NoteDownloader") # Assuming registered name is 'NoteDownloader'
    
    def open_pdf_preview(self, pdf_path: str):
        """打开PDF预览对话框"""
        # PdfViewerView is now imported at the top
        try:
            pdf_viewer = PdfViewerView(pdf_path, self.main_window)
            # Connect signal using the wrapper method in MainWindow
            pdf_viewer.convert_to_html_signal.connect(self.convert_pdf_to_html_wrapper)
            pdf_viewer.exec()
        except Exception as e:
            QMessageBox.critical(self.main_window, "错误", f"无法打开 PDF 预览: {e}")
    
    def sidebar_item_clicked(self, item):
        """处理侧边栏项目点击事件"""
        item_text = item.text()
        is_combined_tool = item_text in ("计时器", "便签与待办", "日历")
        combined_dock_key = "CombinedTools"
        # 确定要查找或存储的dock的key
        dock_key = combined_dock_key if is_combined_tool else item_text

        # TODO: Refactor sidebar item handling.
        # This logic should likely use UIManager.open_view to open registered views
        # in appropriate locations (docks or tabs) instead of manually creating docks here.
        # For now, just map names to potential view names.
        view_map = {
            "计时器": "Timer",
            "便签与待办": "CombinedNotes", # Or StickyNotes/TodoList individually?
            "计算器": "Calculator",
            "日历": "Calendar",
            "笔记下载": "NoteDownloader",
            "语音识别": "SpeechRecognition",
        }
        view_name_to_open = view_map.get(item_text)

        if view_name_to_open:
             print(f"Sidebar clicked: {item_text} -> Opening view: {view_name_to_open}")
             self.open_view(view_name=view_name_to_open, open_in_dock=True) # Try opening in a dock
             # Update status bar if open_view doesn't handle it
             if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar:
                  self.main_window.statusBar.showMessage(f"已打开/切换到 {item_text}")
        else:
             QMessageBox.information(self.main_window, "功能占位符", f"'{item_text}' 功能尚未实现或注册。")

    # Wrapper for signal connection from PdfViewerView
    def convert_pdf_to_html_wrapper(self, pdf_path: str):
         self.convert_pdf_to_html(pdf_path)
    
    def convert_pdf_to_html(self, pdf_path: str):
        """将PDF转换为HTML并在新的HTML编辑器标签页中打开"""
        # Correct import path for pdf_utils
        try:
            from ...utils.pdf_utils import extract_pdf_content
        except ImportError:
            QMessageBox.critical(self.main_window, "错误", "无法导入 PDF 处理工具 (pdf_utils)。")
            return

        try:
            html_content, temp_dir = extract_pdf_content(pdf_path)
            if not html_content:
                QMessageBox.warning(self.main_window, "警告", "无法从 PDF 提取内容。")
                return

            # Create and open a new HTML editor tab using FileOperations
            # Pass content directly instead of creating editor here
            file_name = os.path.basename(pdf_path) + ".html"
            self.main_window.file_operations.add_editor_tab(
                content=html_content,
                file_path=None, # It's unsaved initially
                file_type='html',
                set_current=True,
                untitled_name=f"{os.path.splitext(file_name)[0]} (转换)"
            )

            # Get the newly created editor to set properties
            new_editor = self.main_window.get_current_editor_widget()
            if self.is_widget_html_editor(new_editor):
                 # Store temporary directory path if needed for cleanup later
                 # This might be better handled elsewhere or by saving images inline
                 new_editor.setProperty("pdf_temp_dir", temp_dir)
                 new_editor.setProperty("is_pdf_converted", True)
                 # Ensure it starts as unmodified
                 new_editor.setModified(False)

            if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar:
                 self.main_window.statusBar.showMessage(f"已将 PDF 转换为 HTML: {file_name}")

        except Exception as e:
            QMessageBox.critical(self.main_window, "转换错误", f"转换 PDF 时出错: {e}")
            import traceback
            traceback.print_exc()

    # --- New Methods for View Management ---

    def create_tab_widget(self):
         """Creates the central tab widget."""
         print("UIManager: Attempting to create QTabWidget (simplified)...") # Debug print
         try:
             # Create without parent first, assign later if needed by layout
             new_tab_widget = QTabWidget()
             if new_tab_widget:
                 print("UIManager: QTabWidget instance created successfully.") # Debug print
                 self.tab_widget = new_tab_widget # Assign to the instance variable
                 # Set properties after successful creation
                 self.tab_widget.setDocumentMode(True)
                 self.tab_widget.setTabsClosable(True)
                 self.tab_widget.setMovable(True)
                 # Connect signal - ensure file_operations exists
                 if hasattr(self.main_window, 'file_operations'):
                      self.tab_widget.tabCloseRequested.connect(self.main_window.file_operations.close_tab)
                 else:
                      print("UIManager: WARNING - main_window.file_operations not found for tabCloseRequested connection.")
                 # Store reference in MainWindow
                 self.main_window.tab_widget = self.tab_widget
                 print(f"UIManager: tab_widget assigned to self.tab_widget: {self.tab_widget is not None}") # Debug print
             else:
                 # This case should ideally not happen if the constructor doesn't raise an exception
                 print("UIManager: ERROR - QTabWidget creation returned None/False!") # Debug print
                 self.tab_widget = None # Ensure it's None if creation failed
                 self.main_window.tab_widget = None
         except Exception as e:
             print(f"UIManager: EXCEPTION during QTabWidget creation: {e}") # Catch potential exceptions
             import traceback
             traceback.print_exc()
             self.tab_widget = None # Ensure it's None if creation failed
             self.main_window.tab_widget = None

    def register_view(self, view_class: type[BaseWidget], view_name: str, icon_name: str | None = None):
         """Registers a view class for later instantiation."""
         # Dictionaries are initialized in __init__ now
         if view_name in self.registered_views:
             print(f"警告: 视图 '{view_name}' 已注册。将被覆盖。")

         self.registered_views[view_name] = {
             "class": view_class,
             "icon": icon_name
         }
         print(f"视图已注册: {view_name} (Class: {view_class.__name__})")
         # Add button to activity bar dynamically? Or assume fixed buttons map to names.
         # For now, assume fixed buttons or menu items trigger open_view(view_name)

    def open_view(self, view_name: str, open_in_dock: bool = False, bring_to_front: bool = True):
        """Opens or focuses a registered view, either in a tab or a dock."""
        if not hasattr(self, 'registered_views') or view_name not in self.registered_views:
            QMessageBox.warning(self.main_window, "视图未注册", f"视图 '{view_name}' 未找到或未注册。")
            return

        view_info = self.registered_views[view_name]
        view_class = view_info["class"]
        icon = QIcon.fromTheme(view_info["icon"]) if view_info["icon"] else QIcon()

        # --- Handle Docked Views ---
        if open_in_dock:
            dock = self.view_docks.get(view_name)
            if dock and dock.widget(): # Check if dock and widget exist
                 if bring_to_front:
                      dock.show()
                      dock.raise_()
                 return dock.widget() # Return existing instance
            elif dock and not dock.widget(): # Dock exists but widget was deleted?
                 print(f"警告: 视图 '{view_name}' 的 Dock 存在但无 Widget，将重新创建。")
                 del self.view_docks[view_name] # Remove bad dock reference

            # Create new dock and instance
            try:
                 instance = view_class(self.main_window)
                 dock = QDockWidget(view_name, self.main_window)
                 dock.setObjectName(f"{view_name}Dock")
                 dock.setWidget(instance)
                 # Allow docking anywhere
                 dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
                 # Decide initial dock area (e.g., Right)
                 self.main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
                 self.view_docks[view_name] = dock # Store dock reference
                 self.view_instances[view_name] = instance # Store instance reference

                 # Attempt to tabify with existing docks in the same area
                 for existing_dock in self.view_docks.values():
                      if existing_dock != dock and self.main_window.dockWidgetArea(existing_dock) == self.main_window.dockWidgetArea(dock):
                           self.main_window.tabifyDockWidget(existing_dock, dock)
                           break # Tabify with the first one found

                 if bring_to_front:
                      dock.show()
                      dock.raise_()
                 return instance
            except Exception as e:
                 QMessageBox.critical(self.main_window, "打开视图错误", f"创建视图 '{view_name}' 时出错: {e}")
                 return None

        # --- Handle Tabbed Views (Default) ---
        else:
            # Check if already open in a tab
            for i in range(self.tab_widget.count()):
                 widget = self.tab_widget.widget(i)
                 if isinstance(widget, view_class):
                      if bring_to_front:
                           self.tab_widget.setCurrentIndex(i)
                      return widget # Return existing instance

            # Create new instance and add tab
            try:
                 instance = view_class(self.main_window)
                 index = self.tab_widget.addTab(instance, icon, view_name)
                 if bring_to_front:
                      self.tab_widget.setCurrentIndex(index)
                 # Store instance if needed for single-instance views
                 # self.view_instances[view_name] = instance
                 return instance
            except Exception as e:
                 QMessageBox.critical(self.main_window, "打开视图错误", f"创建视图 '{view_name}' 时出错: {e}")
                 return None

    # --- Utility Methods ---
    def is_widget_editor(self, widget: QWidget | None) -> bool:
         """Checks if a widget is one of the known editor types."""
         if widget is None:
             return False
         # Add other editor types here if needed
         return isinstance(widget, (TextEditor, HtmlEditor))

    def is_widget_html_editor(self, widget: QWidget | None) -> bool:
         """Checks specifically if a widget is an HtmlEditor."""
         if widget is None:
             return False
         return isinstance(widget, HtmlEditor)

    def get_widget_base_name(self, widget: QWidget | None) -> str | None:
         """Gets the base name (filename or untitled name) for a widget."""
         if not widget: return None
         # Check for file_path property first
         file_path = widget.property("file_path")
         if file_path:
             return os.path.basename(file_path)
         # Check for untitled_name property
         untitled_name = widget.property("untitled_name")
         if untitled_name:
             return untitled_name
         # Fallback for non-editor views or if properties aren't set
         if hasattr(widget, 'windowTitle') and callable(widget.windowTitle):
              return widget.windowTitle() # Use window title if available
         # Last resort: Use class name
         return widget.__class__.__name__

    def is_file_open(self, file_path: str) -> bool:
        """Checks if a file is already open in a tab."""
        if not self.tab_widget:
            return False
        abs_file_path = os.path.abspath(file_path)
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if self.is_widget_editor(widget):
                editor_path = widget.property("file_path")
                if editor_path and os.path.abspath(editor_path) == abs_file_path:
                    return True
        return False

    def focus_tab_by_filepath(self, file_path: str):
        """Sets the current tab to the one containing the specified file."""
        if not self.tab_widget:
            return
        abs_file_path = os.path.abspath(file_path)
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if self.is_widget_editor(widget):
                editor_path = widget.property("file_path")
                if editor_path and os.path.abspath(editor_path) == abs_file_path:
                    self.tab_widget.setCurrentIndex(i)
                    break
                    
    def register_speech_recognition(self):
        """注册语音识别组件"""
        self.register_view(SpeechRecognitionWidget, "SpeechRecognition", "microphone")
