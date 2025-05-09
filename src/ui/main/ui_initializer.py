# src/ui/main/ui_initializer.py
import os
import importlib
import inspect
from pathlib import Path
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QToolBar, QMenuBar, QMenu,
                             QStatusBar, QSplitter, QTabWidget, QToolButton, QListWidget,
                             QListWidgetItem, QSizePolicy, QDockWidget, QMainWindow, QApplication) # Added QApplication
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
# EditorGroupWidget and DockableTabWidget will be used by RootEditorAreaWidget
# from ..composite.editor_group_widget import EditorGroupWidget 
# from ..core.dockable_tab_widget import DockableTabWidget
from ..composite.root_editor_area_widget import RootEditorAreaWidget # Added

# Conditional import for QWebEngineView
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    WEB_OK = True
except ImportError:
    WEB_OK = False
    QWebEngineView = None


class UIInitializer:
    """负责初始化 MainWindow 的核心 UI 结构和动态视图注册"""

    def __init__(self, main_window: QMainWindow, ui_manager: UIManager): # tab_widget no longer passed
        self.main_window = main_window
        self.ui_manager = ui_manager # UIManager is now passed in
        # self.tab_widget is no longer stored here directly from constructor
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
        
        print("DEBUG: UIInitializer - Attempting to process events before setup_ui completes.")
        QApplication.processEvents()
        print("DEBUG: UIInitializer - Events processed.")

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
        """设置主内容区域的分割器布局 (FileExplorer | RootEditorAreaWidget | NoteDownloaderView)"""
        
        # Create the RootEditorAreaWidget which will manage editor groups and splits
        self.main_window.root_editor_area = RootEditorAreaWidget(self.main_window)
        self.main_window.root_editor_area.setObjectName("RootEditorArea")

        # --- BEGIN IMMEDIATE CHECK OF root_editor_area ---
        print(f"DEBUG: UIInitializer - Created root_editor_area: {self.main_window.root_editor_area}, type: {type(self.main_window.root_editor_area)}, id: {id(self.main_window.root_editor_area) if self.main_window.root_editor_area else 'N/A'}")
        try:
            if self.main_window.root_editor_area:
                rea_obj_name = self.main_window.root_editor_area.objectName()
                print(f"DEBUG: UIInitializer - root_editor_area.objectName() is '{rea_obj_name}'. RootEditorAreaWidget seems valid after creation.")
                if not self.main_window.root_editor_area.parent(): # Check if it has a parent
                    print(f"WARNING DEBUG: UIInitializer - root_editor_area.parent() is None immediately after creation with parent {self.main_window}")
                else:
                    print(f"DEBUG: UIInitializer - root_editor_area.parent() is {self.main_window.root_editor_area.parent()}")

            else:
                print(f"CRITICAL DEBUG: UIInitializer - self.main_window.root_editor_area is None or evaluates to False IMMEDIATELY after creation.")
        except RuntimeError as e_rea:
            print(f"CRITICAL DEBUG: UIInitializer - RuntimeError when accessing root_editor_area IMMEDIATELY after creation: {e_rea}")
        except Exception as e_rea_other:
            print(f"CRITICAL DEBUG: UIInitializer - Unexpected error with root_editor_area IMMEDIATELY after creation: {e_rea_other}")
        # --- END IMMEDIATE CHECK OF root_editor_area ---
        
        # Set MainWindow's and UIManager's tab_widget to the DockableTabWidget 
        # from the initial group within RootEditorAreaWidget.
        initial_tab_widget = self.main_window.root_editor_area.get_initial_tab_widget()
        print(f"DEBUG: UIInitializer - Received initial_tab_widget: {initial_tab_widget}, type: {type(initial_tab_widget)}, id: {id(initial_tab_widget) if initial_tab_widget else 'N/A'}")
        
        is_cpp_deleted_for_log = False # For logging purposes
        if initial_tab_widget is not None: # Ensure Python object exists before checking sip
            try:
                from PyQt6 import sip
                is_cpp_deleted_for_log = sip.isdeleted(initial_tab_widget)
                print(f"DEBUG: UIInitializer - sip.isdeleted(initial_tab_widget) is {is_cpp_deleted_for_log} (for logging)")
            except ImportError:
                print("WARNING DEBUG: UIInitializer - Could not import sip to check isdeleted().")
            except Exception as e_sip:
                print(f"WARNING DEBUG: UIInitializer - Error checking sip.isdeleted(): {e_sip}")
        
        # --- New logic: Assign if Python object exists, log warning if boolean context is False, but proceed ---
        if initial_tab_widget is not None: # Check if the Python object itself is None
            self.main_window.tab_widget = initial_tab_widget
            if self.ui_manager:
                self.ui_manager.tab_widget = self.main_window.tab_widget
                # print(f"DEBUG: UIInitializer - Assigned initial_tab_widget (id: {id(initial_tab_widget)}) to main_window.tab_widget and ui_manager.tab_widget")
            else:
                # This is a separate critical issue if ui_manager is None and needs tab_widget.
                print("CRITICAL WARNING in _setup_main_layout: self.ui_manager is None. Cannot assign its tab_widget. Layout continues.")
                # Note: If ui_manager being None is fatal for later stages, this might need a return,
                # but for now, we prioritize completing the layout to fix the current specific error.

            # Log a warning if the widget evaluates to False in boolean context, but proceed.
            if not initial_tab_widget: # This is the problematic boolean check we've been observing
                 print(f"WARNING in _setup_main_layout: initial_tab_widget (Python obj: {initial_tab_widget}, "
                       f"sip.isdeleted: {is_cpp_deleted_for_log}) evaluates to False in boolean context. "
                       f"Layout will proceed. Tab functionality might be affected later if it's truly unusable.")
            else:
                # This is the expected "good" path if the boolean context is also True.
                print(f"DEBUG: UIInitializer - initial_tab_widget (Python obj: {initial_tab_widget}, "
                      f"sip.isdeleted: {is_cpp_deleted_for_log}) evaluates to True. Proceeding normally with assignments.")

        else: # initial_tab_widget (Python object) is None from get_initial_tab_widget()
            print("CRITICAL ERROR in _setup_main_layout: get_initial_tab_widget() returned Python None. "
                  "self.main_window.tab_widget will be None. Tab functionality will be broken. "
                  "Proceeding with layout to allow full UI structure attempt.")
            # self.main_window.tab_widget remains None or its previous value (if any)
            # No 'return' here, to allow the rest of the layout to be built.

        # The function no longer returns prematurely based on initial_tab_widget's boolean state.
        # The rest of the layout setup will now always attempt to execute.

        if self.main_window.file_explorer is None:
            print("错误: UIInitializer 未能创建 file_explorer，无法设置主布局!")
            return
        if self.main_window.note_downloader_panel is None: 
            print("错误: UIInitializer 未能创建 note_downloader_panel，无法设置主布局!")
            return

        # Main Content Splitter (FileExplorer | RootEditorAreaWidget)
        # NoteDownloaderPanel is no longer part of this initial layout, will be added to toolbox.
        main_content_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_content_splitter.setObjectName("MainContentSplitter")
        main_content_splitter.setHandleWidth(2)
        main_content_splitter.setChildrenCollapsible(False)

        self.main_window.root_editor_area.setMinimumSize(200, 150)
        main_content_splitter.addWidget(self.main_window.file_explorer)
        main_content_splitter.addWidget(self.main_window.root_editor_area) # RootEditorAreaWidget directly here
        
        # Adjust stretch factors for file explorer and editor area
        # Target: File Explorer ~15%, Editor ~40% of total, if NoteDownloader is ~45%
        # So, within their combined 55%, File Explorer is 15/55, Editor is 40/55
        # Simplified ratio for stretch factors: FE:Editor = 15:40 = 3:8
        main_content_splitter.setStretchFactor(0, 3) 
        main_content_splitter.setStretchFactor(1, 8) 
        
        # Set initial sizes based on a typical window width, maintaining the 3:8 ratio
        # This helps establish a reasonable starting point before user resizes.
        # Example: if main_content_splitter is expected to be ~550px (if total is 1000px)
        # Then FE = (3/11)*550 = 150px, Editor = (8/11)*550 = 400px
        # We can set these as initial pixel values.
        # However, QMainWindow's initial size might not be stable yet.
        # Let's try with a common initial width for the splitter itself.
        # If the main window is ~1100px wide, and NoteDownloader takes ~45% (495px),
        # then main_content_splitter gets ~605px.
        # FE = (3/11)*605 = ~165px
        # Editor = (8/11)*605 = ~440px
        main_content_splitter.setSizes([165, 440]) # Adjust initial sizes
        
        # The bottom toolbox tab widget is no longer needed.
        # self.main_window.tool_box_widget = QTabWidget()
        # ... (相关的tool_box_widget代码已删除)

        # The app_level_splitter is no longer needed as there's no bottom toolbox.
        # main_content_splitter will be added directly to the parent_layout.
        parent_layout.addWidget(main_content_splitter)

        # NoteDownloaderPanel and its content (note_downloader_view_content) are created in _create_core_views.
        # UIManager will use note_downloader_view_content directly when opening NoteDownloader as a dock.
        # The self.main_window.note_downloader_panel (PanelWidget wrapper) is likely no longer needed
        # unless it provides functionality beyond what QDockWidget offers for this view.
        # For now, we assume QDockWidget is sufficient.

        print("UIInitializer: Setup main layout with RootEditorAreaWidget and QSplitter. Bottom toolbox removed.")

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
        """Handles clicks from activity bar buttons for registered views.
        Opens views as dock widgets or closes them.
        """
        if button.isChecked():
            # Open the view as a dock widget.
            # The UIManager's open_view method should handle showing/raising if already open.
            # NoteDownloader's pre-created panel (self.main_window.note_downloader_panel)
            # and its content (self.main_window.note_downloader_view_content)
            # will be handled by UIManager if view_name is "NoteDownloader".
            # UIManager should use the existing instance if available.
            
            # If view_name is "NoteDownloader", UIManager's open_view will use
            # self.main_window.note_downloader_view_content.
            # The self.main_window.note_downloader_panel (PanelWidget) is not used for docking.
            view_instance_or_dock = self.ui_manager.open_view(view_name, open_in_dock=True, bring_to_front=True)
            
            if not view_instance_or_dock:
                # If opening failed, uncheck the button
                button.setChecked(False)
            # else:
                # UIManager.open_view with bring_to_front=True should handle visibility.
                # If specific sizing is needed for NoteDownloader, UIManager can handle it.
                # if view_name == "NoteDownloader" and isinstance(view_instance_or_dock, QDockWidget):
                #     desired_width = self.main_window.width() // 3 # Example
                #     view_instance_or_dock.setFixedWidth(desired_width) # Or resizeDocks

        else: # Button was unchecked by user click
            if hasattr(self.ui_manager, 'close_dock_view'):
                self.ui_manager.close_dock_view(view_name)
            else:
                print(f"Warning: UIManager does not have 'close_dock_view' method. Cannot close/hide {view_name}.")
                dock_to_close = self.ui_manager.view_docks.get(view_name)
                if dock_to_close:
                    dock_to_close.hide()


    def _toggle_file_explorer_visibility(self, checked):
         """Toggles visibility of FileExplorer in the QSplitter."""
         if self.main_window.file_explorer:
             self.main_window.file_explorer.setVisible(checked)
             # Optionally, adjust splitter sizes when hiding/showing to reclaim space
             # This can be complex; QSplitter usually handles this if children are collapsible (False here)

    def _toggle_note_downloader_panel_visibility(self, checked): # This method is now effectively replaced by handle_activity_button_click
         """DEPRECATED: Toggles visibility of NoteDownloaderPanel. Use activity bar button."""
         # This logic is now part of handle_activity_button_click for "NoteDownloader"
         if self.main_window.note_downloader_panel:
             button = self.main_window.activity_view_buttons.get("NoteDownloader")
             if button:
                 button.setChecked(checked) # Sync button state
                 self.handle_activity_button_click("NoteDownloader", button) # Trigger the new logic
             else: # Fallback if button not found (should not happen)
                if checked:
                    self.main_window.tool_box_widget.addTab(self.main_window.note_downloader_panel, "笔记下载器")
                    self.main_window.tool_box_widget.setCurrentWidget(self.main_window.note_downloader_panel)
                    self.main_window.tool_box_widget.show()
                else:
                    for i in range(self.main_window.tool_box_widget.count()):
                        if self.main_window.tool_box_widget.widget(i) == self.main_window.note_downloader_panel:
                            self.main_window.tool_box_widget.removeTab(i)
                            break


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
