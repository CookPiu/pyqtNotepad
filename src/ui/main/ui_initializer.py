# src/ui/main/ui_initializer.py
import os
import importlib
import inspect
from pathlib import Path
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QToolBar, QMenuBar, QMenu,
                             QStatusBar, QSplitter, QTabWidget, QToolButton, QListWidget,
                             QListWidgetItem, QSizePolicy, QDockWidget, QMainWindow) # Added QMainWindow
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import Qt, QSize, QUrl

# Corrected Relative Imports
# Assuming UIManager and BaseWidget are correctly located relative to this file
from ..components.ui_manager import UIManager
from ..core.base_widget import BaseWidget
from ..core.base_dialog import BaseDialog # Needed for type checking
# FileExplorer is now atomic
from ..atomic.file_explorer import FileExplorer

# Conditional import for QWebEngineView
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    WEB_OK = True
except ImportError:
    WEB_OK = False
    QWebEngineView = None


class UIInitializer:
    """负责初始化 MainWindow 的核心 UI 结构和动态视图注册"""

    def __init__(self, main_window: QMainWindow, ui_manager: UIManager, tab_widget: QTabWidget | None): # Receive tab_widget
        self.main_window = main_window
        self.ui_manager = ui_manager # UIManager is now passed in
        self.tab_widget = tab_widget # Store the tab_widget passed from MainWindow

    def setup_ui(self):
        """设置主窗口UI结构"""
        self.main_window.setWindowTitle("Pynote Refactored")
        self.main_window.setGeometry(100, 100, 1100, 750) # Adjusted size
        central_widget = QWidget()
        self.main_window.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Initialize Core UI Elements ---
        self._setup_toolbar()       # Toolbar structure
        self._setup_status_bar()    # Status bar

        # --- Setup Central Area (Splitter with Docks/Tabs) ---
        # UIManager now likely owns the tab_widget and manages docks
        # We set up the main splitter layout here
        self._setup_main_layout(main_layout)

        # --- Register Views Dynamically ---
        self._register_views()

        # --- Setup Activity Bar and Sidebar Dock ---
        # These are created as dock widgets now
        self._setup_activity_bar_dock() # Activity bar triggers dock visibility
        self._setup_sidebar_dock()      # Sidebar contains File Explorer etc.

        # --- Connect Signals Handled by MainWindow ---
        # Connection moved to MainWindow.__init__ after UIManager creates tab_widget

        print("▶ UIInitializer.setup_ui 完成")

    def _setup_toolbar(self):
        """设置顶部工具栏框架"""
        # MainWindow creates the toolbar actions, UIInitializer just adds the toolbar itself
        self.main_window.toolbar = QToolBar("主工具栏")
        self.main_window.toolbar.setObjectName("MainToolBar")
        # Icons and style set in MainWindow.create_toolbar
        self.main_window.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.main_window.toolbar)

    def _setup_status_bar(self):
        """设置状态栏"""
        self.main_window.statusBar = QStatusBar()
        self.main_window.setStatusBar(self.main_window.statusBar)
        self.main_window.statusBar.showMessage("就绪")

    def _setup_main_layout(self, parent_layout: QVBoxLayout):
        """设置主内容区域的分割器布局"""
        # Use the tab_widget created in MainWindow and passed to __init__
        # Apply user patch: Change check to 'is None'
        if self.tab_widget is None:
             # 只在 None 时才报错，空的 QTabWidget 也会被 Python 视为 False
             print("错误: MainWindow 未能创建 tab_widget，无法设置主布局!")
             # Optionally create a placeholder or return
             # return # Don't return, let the rest of the UI setup proceed even if tab_widget fails

        # --- Simplified Layout ---
        # Directly add the tab_widget (if created) to the main layout, removing the splitter for now.
        # Apply user patch: Change check to 'is not None'
        if self.tab_widget is not None:
             parent_layout.addWidget(self.tab_widget)
             print("UIInitializer: Added tab_widget (from MainWindow) directly to central layout.")
        else:
             # This case is handled by the check above, but keep the print for clarity if needed
             print("UIInitializer: tab_widget is None, central layout will be empty.")

        # --- Original Splitter Code (Commented Out) ---
        # # Main Horizontal Splitter (Sidebar <-> Central Area)
        # self.main_window.main_h_splitter = QSplitter(Qt.Orientation.Horizontal)
        # self.main_window.main_h_splitter.setObjectName("MainHSplitter")
        # self.main_window.main_h_splitter.setHandleWidth(1)
        # self.main_window.main_h_splitter.setChildrenCollapsible(False)
        #
        # # Central Area (Tabs + potentially other panes like browser later)
        # # For now, just the tab widget
        # central_area_widget = self.ui_manager.tab_widget
        # # If a browser or other panes are needed, they'd go into another splitter here
        #
        # # Add central area to the main splitter
        # # Sidebar dock will be added separately by QMainWindow docking system
        # self.main_window.main_h_splitter.addWidget(central_area_widget)
        # self.main_window.main_h_splitter.setStretchFactor(0, 1) # Central area expands
        #
        # parent_layout.addWidget(self.main_window.main_h_splitter)

    def _setup_activity_bar_dock(self):
         """设置左侧活动栏 DockWidget"""
         self.main_window.activity_bar_dock = QDockWidget("活动", self.main_window)
         self.main_window.activity_bar_dock.setObjectName("ActivityBarDock")
         self.main_window.activity_bar_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
         self.main_window.activity_bar_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures) # Remove title bar, close button etc.

         activity_bar_widget = QWidget()
         activity_layout = QVBoxLayout(activity_bar_widget)
         activity_layout.setContentsMargins(0, 5, 0, 5)
         activity_layout.setSpacing(5)
         activity_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
         activity_bar_widget.setMinimumWidth(40) # **Set a minimum width for the container**

         # --- Activity Bar Buttons ---
         # Files Button (Toggles Sidebar Dock)
         files_btn = QToolButton()
         files_btn.setIcon(QIcon.fromTheme("folder", QIcon(":/icons/default_folder.png"))) # Add fallback icon path
         files_btn.setToolTip("文件浏览器 (切换侧边栏)")
         files_btn.setCheckable(True)
         files_btn.clicked.connect(self._toggle_sidebar_dock)
         activity_layout.addWidget(files_btn)
         self.main_window.toggle_sidebar_button = files_btn # Store reference

         # --- Dynamically Add Buttons for Registered Views ---
         print("UIInitializer: Adding buttons for registered views to activity bar...")
         if hasattr(self.ui_manager, 'registered_views'):
             for view_name, view_info in self.ui_manager.registered_views.items():
                 try:
                     # Skip FileExplorer as it's handled by the sidebar toggle
                     # Also skip PDFViewer as it's opened contextually
                     if view_name in ["FileExplorer", "PdfViewer"]:
                          continue

                     icon_name = view_info.get("icon")
                     icon = QIcon() # Default empty icon
                     use_text = True # Default to using text

                     if icon_name:
                         loaded_icon = QIcon.fromTheme(icon_name)
                         # Check if the theme icon is valid (not null)
                         if not loaded_icon.isNull():
                              icon = loaded_icon
                              use_text = False
                         # else: print(f"  Warning: Theme icon '{icon_name}' not found for {view_name}.") # Optional warning

                     # If no valid icon was found, use text
                     view_btn = QToolButton()
                     view_btn.setToolTip(f"打开/切换到 {view_name}") # Set tooltip first
                     if use_text:
                         view_btn.setText(view_name[:3]) # Use first 3 chars as short text, or full name
                         view_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly) # **Set text only style**
                         # view_btn.setMinimumSize(30, 25) # Optional: Ensure minimum size for text buttons
                         print(f"  Using text '{view_btn.text()}' for button: {view_name}")
                     else:
                         view_btn.setIcon(icon)
                         view_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly) # Explicitly set icon only
                         print(f"  Using icon for button: {view_name}")

                     view_btn.setCheckable(False) # Keep as non-checkable for simple open action

                     # Connect to open_view, prefer opening tools in docks
                     # Use a lambda that captures the current view_name
                     view_btn.clicked.connect(lambda checked=False, v_name=view_name: self.ui_manager.open_view(v_name, open_in_dock=True))

                     activity_layout.addWidget(view_btn)
                     print(f"  Added button for: {view_name}")

                 except Exception as e:
                      print(f"  Error adding button for view '{view_name}': {e}")
         else:
              print("UIInitializer: ui_manager has no registered_views attribute.")


         activity_layout.addStretch() # Push buttons to top

         self.main_window.activity_bar_dock.setWidget(activity_bar_widget)
         self.main_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.main_window.activity_bar_dock)
         # self.main_window.activity_bar_dock.show() # **Explicitly show the dock (optional)**

         # Set initial state (e.g., sidebar visible means button checked)
         # This depends on whether the sidebar dock starts visible
         # files_btn.setChecked(self.main_window.sidebar_dock.isVisible())


    def _setup_sidebar_dock(self):
        """设置侧边栏 DockWidget (包含文件浏览器等)"""
        self.main_window.sidebar_dock = QDockWidget("浏览器", self.main_window)
        self.main_window.sidebar_dock.setObjectName("SidebarDock")
        self.main_window.sidebar_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)

        sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # --- File Explorer ---
        # FileExplorer is now an atomic widget
        self.main_window.file_explorer = FileExplorer(initial_path=os.getcwd()) # Start in CWD or a default path
        # Connect signal to MainWindow's handler (now in FileOperations)
        self.main_window.file_explorer.file_double_clicked.connect(self.main_window.file_operations.open_file_from_path)
        sidebar_layout.addWidget(self.main_window.file_explorer)

        # --- Add other sidebar elements if needed (e.g., Outline, Search Results) ---
        # The old function_list is removed, functionality handled by UIManager/Actions

        self.main_window.sidebar_dock.setWidget(sidebar_widget)
        self.main_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.main_window.sidebar_dock)

        # Connect visibility changes to the activity bar button state
        self.main_window.sidebar_dock.visibilityChanged.connect(self.main_window.toggle_sidebar_button.setChecked)
        # Set initial button state based on dock visibility
        self.main_window.toggle_sidebar_button.setChecked(self.main_window.sidebar_dock.isVisible())


    def _toggle_sidebar_dock(self, checked):
         """Slot to show/hide the sidebar dock based on activity bar button."""
         self.main_window.sidebar_dock.setVisible(checked)


    def _register_views(self):
        """Dynamically scans the views directory and registers found views."""
        print("--- 开始动态注册视图 ---")
        try:
            views_dir = Path(__file__).parent.parent / "views" # src/ui/views
            if not views_dir.is_dir():
                print(f"错误: 视图目录未找到: {views_dir}")
                return

            for filepath in views_dir.glob("*_view.py"):
                module_name = f"src.ui.views.{filepath.stem}" # Construct module path
                try:
                    module = importlib.import_module(module_name)
                    print(f"  加载模块: {module_name}")
                    for name, obj in inspect.getmembers(module):
                        # Check if it's a class, defined in this module, and inherits from BaseWidget (but not BaseWidget itself)
                        if inspect.isclass(obj) and obj.__module__ == module_name and \
                           issubclass(obj, BaseWidget) and obj is not BaseWidget and \
                           not issubclass(obj, BaseDialog): # Exclude dialogs for now

                            view_name = getattr(obj, 'VIEW_NAME', name.replace('View', '')) # Get name or derive
                            icon_name = getattr(obj, 'VIEW_ICON', None) # Get icon hint
                            print(f"    发现视图: {name} (注册名: {view_name}, 图标: {icon_name})")
                            # Register with UIManager
                            self.ui_manager.register_view(
                                view_class=obj,
                                view_name=view_name,
                                icon_name=icon_name
                                # Add other metadata if needed (e.g., default location)
                            )
                except ImportError as e:
                    print(f"  错误: 导入模块 {module_name} 失败: {e}")
                except Exception as e:
                    print(f"  错误: 处理模块 {module_name} 时出错: {e}")
        except Exception as e:
            print(f"错误: 扫描视图目录时发生异常: {e}")
            import traceback
            traceback.print_exc()
        print("--- 视图注册完成 ---")
