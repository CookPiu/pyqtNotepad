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
from ..views.note_downloader_view import NoteDownloaderView
from ..core.panel_widget import PanelWidget # Added import

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
        if self.tab_widget is not None: # Explicitly check for None
            print(f"DEBUG:UI_INIT.__init__: Received tab_widget.isVisible(): {self.tab_widget.isVisible()}, count: {self.tab_widget.count()}")
        else:
            print("DEBUG:UI_INIT.__init__: Received tab_widget is None. (Checked with 'is None')")
        self.main_window.file_explorer = None
        self.main_window.note_downloader_view_content = None # Stores the actual NoteDownloaderView instance
        self.main_window.note_downloader_panel = None # Stores the PanelWidget wrapper for NoteDownloader

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
        self._create_core_views() # Create views needed for splitter layout
        self._setup_main_layout(main_layout)

        # --- Register Views Dynamically (for other views not in main splitter) ---
        self._register_views() # This might need adjustment if NoteDownloader is handled differently

        # --- Setup Activity Bar ---
        # Sidebar Dock is removed as FileExplorer is now in a QSplitter
        self._setup_activity_bar() # Renamed from _setup_activity_bar_dock

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

    def _create_core_views(self):
        """Creates core view instances needed for the main layout."""
        self.main_window.file_explorer = FileExplorer(parent=self.main_window)
        self.main_window.file_explorer.setObjectName("MainFileExplorer")
        self.main_window.file_explorer.hide() # Ensure initially hidden

        # Create NoteDownloaderView content
        self.main_window.note_downloader_view_content = NoteDownloaderView(parent=self.main_window)
        self.main_window.note_downloader_view_content.setObjectName("MainNoteDownloaderViewContent")

        # Wrap NoteDownloaderView content in a PanelWidget
        self.main_window.note_downloader_panel = PanelWidget(title="笔记下载器", parent=self.main_window)
        self.main_window.note_downloader_panel.setObjectName("NoteDownloaderPanel")
        self.main_window.note_downloader_panel.setContentWidget(self.main_window.note_downloader_view_content)
        self.main_window.note_downloader_panel.hide() # Ensure initially hidden

    def _setup_main_layout(self, parent_layout: QVBoxLayout):
        """设置主内容区域的分割器布局 (FileExplorer | TabWidget | NoteDownloaderView)"""
        if self.tab_widget is None:
            print("CRITICAL ERROR in _setup_main_layout: self.tab_widget is None. Editor area cannot be created.")
            error_label = QLabel(
                "关键错误：编辑器区域 (TabWidget) 未能正确初始化。\n"
                "请检查 MainWindow.py 中 tab_widget 的创建和传递过程。",
                # parent=self.main_window.centralWidget() # Parent will be set when added to layout
            )
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            error_label.setStyleSheet("QLabel { color: red; font-size: 16px; padding: 20px; background-color: #ffe0e0; border: 1px solid red; }")
            
            # Clear existing items from parent_layout and add the error label
            while parent_layout.count():
                item = parent_layout.takeAt(0)
                if item.widget():
                    item.widget().setParent(None) # Ensure old widgets are properly reparented or deleted
            parent_layout.addWidget(error_label)
            return # Stop further layout setup

        if self.main_window.file_explorer is None:
            print("错误: UIInitializer 未能创建 file_explorer，无法设置主布局!")
            # Potentially, we could still set up a layout with just tab_widget and note_downloader_panel
            # For now, let's assume file_explorer is also critical for the intended splitter layout.
            return
        if self.main_window.note_downloader_panel is None: 
            print("错误: UIInitializer 未能创建 note_downloader_panel，无法设置主布局!")
            return

        # Center-Right Splitter (TabWidget | NoteDownloaderPanel)
        center_right_splitter = QSplitter(Qt.Orientation.Horizontal)
        center_right_splitter.setObjectName("CenterRightSplitter")
        center_right_splitter.setHandleWidth(2) # 宽度可以在 QSS 中设置，但这里保留以便更容易调整
        # center_right_splitter.setStyleSheet("QSplitter::handle { background-color: lightgray; border: 1px solid darkgray; } QSplitter::handle:hover { background-color: gray; }") # 交给全局QSS控制
        center_right_splitter.setChildrenCollapsible(False)

        if self.tab_widget is not None: # Explicitly check for None
            print(f"DEBUG:MAIN_LAYOUT: TabWidget initial: isVisible={self.tab_widget.isVisible()}, count={self.tab_widget.count()}, size={self.tab_widget.size()}, minSize={self.tab_widget.minimumSize()}, sizeHint={self.tab_widget.sizeHint()}")
            print(f"DEBUG:MAIN_LAYOUT: TabWidget parent: {self.tab_widget.parentWidget()}")
            print(f"DEBUG:MAIN_LAYOUT: TabWidget sizePolicy: H={self.tab_widget.sizePolicy().horizontalPolicy().name}, V={self.tab_widget.sizePolicy().verticalPolicy().name}")
            
            self.tab_widget.setMinimumSize(200, 150) 
            self.tab_widget.setVisible(True) 
            self.tab_widget.ensurePolished() 
            print(f"DEBUG:MAIN_LAYOUT: TabWidget after setVisible(True): isVisible={self.tab_widget.isVisible()}")
        else:
            print("DEBUG:MAIN_LAYOUT: self.tab_widget is None before adding to CSR-Splitter!")
            
        center_right_splitter.addWidget(self.tab_widget)
        center_right_splitter.addWidget(self.main_window.note_downloader_panel) 
        
        print(f"DEBUG:MAIN_LAYOUT: TabWidget in CSR-Splitter final visible: {self.tab_widget.isVisible() if self.tab_widget else 'N/A'}")
        print(f"DEBUG:MAIN_LAYOUT: NoteDownloaderPanel in CSR-Splitter visible: {self.main_window.note_downloader_panel.isVisible()}")
        
        center_right_splitter.setStretchFactor(0, 1) 
        center_right_splitter.setStretchFactor(1, 1) 
        center_right_splitter.setSizes([700, 300]) 
        
        print(f"DEBUG:MAIN_LAYOUT: CSR-Splitter count: {center_right_splitter.count()}, sizes: {center_right_splitter.sizes()}, handleWidth: {center_right_splitter.handleWidth()}")
        self.main_window.center_right_splitter_ref = center_right_splitter

        # Main Splitter (FileExplorer | center_right_splitter)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setObjectName("MainSplitter")
        main_splitter.setHandleWidth(2) # 宽度可以在 QSS 中设置，但这里保留以便更容易调整
        # main_splitter.setStyleSheet("QSplitter::handle { background-color: lightgray; border: 1px solid darkgray; } QSplitter::handle:hover { background-color: gray; }") # 交给全局QSS控制
        main_splitter.setChildrenCollapsible(False)
        main_splitter.addWidget(self.main_window.file_explorer)
        main_splitter.addWidget(center_right_splitter)
        main_splitter.setStretchFactor(0, 0) 
        main_splitter.setStretchFactor(1, 1) 
        main_splitter.setSizes([200, 800]) 

        parent_layout.addWidget(main_splitter)
        print(f"DEBUG:MAIN_LAYOUT: MainSplitter count: {main_splitter.count()}, sizes: {main_splitter.sizes()}, handleWidth: {main_splitter.handleWidth()}")
        print("UIInitializer: Setup main layout with QSplitters.")

    def _setup_activity_bar(self): # Renamed from _setup_activity_bar_dock
         """设置左侧活动栏 ToolBar"""
         # Ensure activity_bar_toolbar is created on main_window if not already
         if not hasattr(self.main_window, 'activity_bar_toolbar') or self.main_window.activity_bar_toolbar is None:
             self.main_window.activity_bar_toolbar = QToolBar("活动栏", self.main_window)
             self.main_window.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self.main_window.activity_bar_toolbar)
         
         self.main_window.activity_bar_toolbar.clear() # Clear previous buttons if any
         self.main_window.activity_bar_toolbar.setObjectName("ActivityBarToolBar")
         self.main_window.activity_bar_toolbar.setMovable(False)
         self.main_window.activity_bar_toolbar.setFloatable(False)
         self.main_window.activity_bar_toolbar.setFixedWidth(60) 
         self.main_window.activity_bar_toolbar.setStyleSheet("QToolBar { spacing: 5px; padding: 5px; } QToolButton { font-size: 9pt; }") # 统一调整按钮字体

         # Files Button (Toggles File Explorer visibility in QSplitter)
         files_btn = QToolButton(self.main_window.activity_bar_toolbar)
         files_btn.setText("文件") #保持 "文件"
         files_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
         files_btn.setToolTip("文件管理 (切换)")
         files_btn.setCheckable(True)
         # FileExplorer is hidden in _create_core_views, so button should be unchecked
         files_btn.setChecked(False) 
         files_btn.clicked.connect(self._toggle_file_explorer_visibility)
         files_btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
         self.main_window.activity_bar_toolbar.addWidget(files_btn)
         self.main_window.toggle_sidebar_button = files_btn # Keep ref if needed elsewhere

         # --- Dynamically Add Buttons for Registered Views ---
         print("UIInitializer: Adding buttons for registered views to activity toolbar...")
         
         # Define a mapping for shorter button texts or specific texts
         button_text_map = {
             "NoteDownloader": "下载", # Keep "下载" for NoteDownloader
             "Calculator": "计算",     # Keep "计算" for Calculator
             "Timer": "计时",         # Keep "计时" for Timer
             "SpeechRecognition": "语音",
             "StickyNotes": "便签",
             "TodoList": "待办",
             # Add other mappings if needed
         }

         if hasattr(self.ui_manager, 'registered_views'):
             # Ensure a consistent order for buttons if possible, e.g., by sorting view_names
             # sorted_view_names = sorted(self.ui_manager.registered_views.keys()) # Optional: for consistent order
             # for view_name in sorted_view_names:
             #    view_info = self.ui_manager.registered_views[view_name]
             
             for view_name, view_info in self.ui_manager.registered_views.items():
                 try:
                     # Skip FileExplorer as it has a dedicated button already
                     if view_name == "FileExplorer":
                         continue
                     
                     # Skip PdfViewer for now, or handle its button creation if it's to be on the activity bar
                     if view_name == "PdfViewer":
                          continue

                     view_btn = QToolButton(self.main_window.activity_bar_toolbar)
                     
                     # Determine button text: Use map first, then fallback
                     button_text = button_text_map.get(view_name)
                     if button_text is None: # Fallback logic if not in map
                         if all('\u4e00' <= char <= '\u9fff' for char in view_name) and len(view_name) > 1:
                             button_text = view_name[0] 
                         elif len(view_name) > 2:
                             button_text = view_name[:2]
                         else:
                             button_text = view_name
                     
                     view_btn.setText(button_text)
                     view_btn.setToolTip(f"打开/切换到 {view_name}")
                     view_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
                     view_btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
                     
                     # For NoteDownloader, it's now opened via UIManager like other tools
                     # but its panel visibility is still toggled by its own button if that panel is part of main layout.
                     # To make it behave like other dockable tools, we should use open_view.
                     # The original _toggle_note_downloader_panel_visibility was for a fixed panel.
                     # We will now make all registered views (except FileExplorer) open via UIManager.
                     
                     view_btn.setCheckable(True) # Make it checkable to reflect open/closed state of dock
                                                      # UIManager.open_view will show/raise existing dock.
                                                      # We need a way to uncheck button if dock is closed by user.
                     
                     # Connect to UIManager.open_view to open as a dock widget
                     # Pass a lambda to capture the button itself to manage its checked state
                     view_btn.clicked.connect(
                         lambda checked, v_name=view_name, btn=view_btn: self.handle_activity_button_click(v_name, btn)
                     )
                     
                     # Store button to potentially update its checked state if view is closed elsewhere
                     if not hasattr(self.main_window, 'activity_view_buttons'):
                         self.main_window.activity_view_buttons = {}
                     self.main_window.activity_view_buttons[view_name] = view_btn
                     # Initialize button state based on whether the view (dock) is already visible
                     # This is tricky as UIManager.view_docks might not be populated yet or dock might be hidden.
                     # For now, default to unchecked. UIManager.open_view will show it.
                     view_btn.setChecked(False)


                     self.main_window.activity_bar_toolbar.addWidget(view_btn)
                     print(f"  Added button '{button_text}' for: {view_name} (opens via UIManager)")

                 except Exception as e:
                      print(f"  Error adding button for view '{view_name}': {e}")
         else:
              print("UIInitializer: ui_manager has no registered_views attribute.")

         spacer = QWidget()
         spacer.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
         self.main_window.activity_bar_toolbar.addWidget(spacer)
         self.main_window.activity_bar_toolbar.show()

    def handle_activity_button_click(self, view_name: str, button: QToolButton):
        """Handles clicks from activity bar buttons for registered views."""
        # Toggle the checked state of the button that was clicked
        # Note: If open_view fails, or if the view is already open and focused,
        # the button's state should ideally reflect the actual visibility of the dock.
        # This basic toggle might need refinement if the dock can be closed by other means
        # and the button state needs to be synced.
        
        # First, ensure UIManager opens/focuses the view.
        # open_view with open_in_dock=True should handle showing and raising the dock.
        view_instance = self.ui_manager.open_view(view_name, open_in_dock=True)

        if view_instance:
            # If view is successfully opened/focused, ensure button is checked.
            # If the button was already checked (meaning user clicked to potentially hide),
            # UIManager.open_view would have just raised it. We might want to hide it instead.
            # This requires more complex state management of docks.
            # For now, clicking always tries to show/focus, and button reflects this attempt.
            
            # Uncheck all other view buttons in the activity bar
            if hasattr(self.main_window, 'activity_view_buttons'):
                for v_name, btn in self.main_window.activity_view_buttons.items():
                    if btn != button:
                        btn.setChecked(False)
            button.setChecked(True) # Check the clicked button

            # If the view has a corresponding dock, connect its visibilityChanged signal
            # to update the button's checked state.
            dock = self.ui_manager.view_docks.get(view_name)
            if dock:
                # Disconnect previous connections for this button to avoid multiple triggers
                try:
                    dock.visibilityChanged.disconnect() 
                except TypeError: # No connections to disconnect
                    pass
                # Connect to lambda that captures the correct button instance
                dock.visibilityChanged.connect(lambda visible, b=button: b.setChecked(visible))
                # Sync button state immediately
                button.setChecked(dock.isVisible())

        else:
            # If open_view failed, uncheck the button
            button.setChecked(False)


    def _toggle_file_explorer_visibility(self, checked):
         """Toggles visibility of FileExplorer in the QSplitter."""
         if self.main_window.file_explorer:
             self.main_window.file_explorer.setVisible(checked)
             # Optionally, adjust splitter sizes when hiding/showing to reclaim space
             # This can be complex; QSplitter usually handles this if children are collapsible (False here)

    def _toggle_note_downloader_panel_visibility(self, checked): # Renamed slot
         """Toggles visibility of NoteDownloaderPanel in the QSplitter."""
         if self.main_window.note_downloader_panel:
             self.main_window.note_downloader_panel.setVisible(checked)
             if checked:
                 print(f"DEBUG:TOGGLE: NoteDownloaderPanel setVisible(True)")
                 print(f"DEBUG:TOGGLE: NoteDownloaderPanel.isVisible(): {self.main_window.note_downloader_panel.isVisible()}")
                 print(f"DEBUG:TOGGLE: NoteDownloaderPanel.size(): {self.main_window.note_downloader_panel.size()}")
                 print(f"DEBUG:TOGGLE: NoteDownloaderPanel.sizeHint(): {self.main_window.note_downloader_panel.sizeHint()}")
                 if hasattr(self.main_window, 'center_right_splitter_ref'):
                     # Force a refresh of splitter layout if possible, or check sizes
                     # QSplitter should update automatically when a child's visibility changes.
                     # Forcing sizes might be an option if it doesn't.
                     # Example: self.main_window.center_right_splitter_ref.setSizes(self.main_window.center_right_splitter_ref.sizes())
                     print(f"DEBUG:TOGGLE: CSR-Splitter sizes after toggle: {self.main_window.center_right_splitter_ref.sizes()}")
             else:
                 print(f"DEBUG:TOGGLE: NoteDownloaderPanel setVisible(False)")


    # _setup_sidebar_dock is removed as FileExplorer is now part of QSplitter in _setup_main_layout
    # _toggle_sidebar_dock is replaced by _toggle_file_explorer_visibility

    def _register_views(self):
        """
        Dynamically scans the views directory and registers found views.
        Views part of the main QSplitter layout (FileExplorer, NoteDownloaderView)
        are handled separately and might not need re-registration here if UIManager
        is aware of them or if their toggle is handled directly by UIInitializer.
        """
        print("--- 开始动态注册视图 (用于非核心布局视图) ---")
        try:
            views_dir = Path(__file__).parent.parent / "views" # src/ui/views
            if not views_dir.is_dir():
                print(f"错误: 视图目录未找到: {views_dir}")
                return

            for filepath in views_dir.glob("*_view.py"):
                module_name = f"src.ui.views.{filepath.stem}"
                # Skip already handled views
                if filepath.stem in ["file_explorer_view", "note_downloader_view"]: # Adjust if filenames differ
                    print(f"  跳过已在主布局中处理的视图模块: {module_name}")
                    continue
                try:
                    module = importlib.import_module(module_name)
                    print(f"  加载模块: {module_name}")
                    for name, obj in inspect.getmembers(module):
                        if inspect.isclass(obj) and obj.__module__ == module_name and \
                           issubclass(obj, BaseWidget) and obj is not BaseWidget and \
                           not issubclass(obj, BaseDialog):

                            view_name_attr = getattr(obj, 'VIEW_NAME', None)
                            # Ensure NoteDownloaderView is not re-registered if it has a VIEW_NAME
                            if view_name_attr == "NoteDownloader": # Check against its potential VIEW_NAME
                                print(f"    跳过已处理的 NoteDownloaderView (通过 VIEW_NAME 检查): {name}")
                                continue

                            view_name = view_name_attr if view_name_attr else name.replace('View', '')
                            icon_name = getattr(obj, 'VIEW_ICON', None)
                            print(f"    发现视图: {name} (注册名: {view_name}, 图标: {icon_name})")
                            self.ui_manager.register_view(
                                view_class=obj,
                                view_name=view_name,
                                icon_name=icon_name
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
