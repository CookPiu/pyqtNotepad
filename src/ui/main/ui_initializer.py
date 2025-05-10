# src/ui/main/ui_initializer.py
import os
import importlib
import inspect
from pathlib import Path
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QToolBar, QMenuBar, QMenu,
                             QStatusBar, QSplitter, QTabWidget, QToolButton, QListWidget,
                             QListWidgetItem, QSizePolicy, QDockWidget, QMainWindow, QApplication) # Added QApplication
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import Qt, QSize, QUrl, QTimer # Added QTimer

# Corrected Relative Imports
from ..components.ui_manager import UIManager
from ..core.base_widget import BaseWidget
from ..core.base_dialog import BaseDialog # Needed for type checking
from ..atomic.file_explorer import FileExplorer
from ..views.note_downloader_view import NoteDownloaderView
from ..core.panel_widget import PanelWidget 
from ..composite.root_editor_area_widget import RootEditorAreaWidget

# Conditional import for QWebEngineView
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    WEB_OK = True
except ImportError:
    WEB_OK = False
    QWebEngineView = None


class UIInitializer:
    """负责初始化 MainWindow 的核心 UI 结构和动态视图注册"""

    def __init__(self, main_window: QMainWindow, ui_manager: UIManager): 
        self.main_window = main_window
        self.ui_manager = ui_manager 
        self.main_window.file_explorer = None
        self.main_window.note_downloader_view_content = None 
        self.main_window.note_downloader_panel = None 

    def setup_ui(self):
        """设置主窗口UI结构"""
        self.main_window.setWindowTitle("Pynote Refactored")
        self.main_window.setGeometry(100, 100, 1100, 750) 
        central_widget = QWidget()
        self.main_window.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._setup_toolbar()      
        self._setup_status_bar()   

        self._create_core_views() 
        self._setup_main_layout(main_layout)

        self._register_views() 
        self._setup_activity_bar() 
        
        print("DEBUG: UIInitializer - Attempting to process events before setup_ui completes.")
        QApplication.processEvents()
        print("DEBUG: UIInitializer - Events processed.")

        print("▶ UIInitializer.setup_ui 完成")

    def _setup_toolbar(self):
        self.main_window.toolbar = QToolBar("主工具栏")
        self.main_window.toolbar.setObjectName("MainToolBar")
        self.main_window.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.main_window.toolbar)

    def _setup_status_bar(self):
        self.main_window.statusBar = QStatusBar()
        self.main_window.setStatusBar(self.main_window.statusBar)
        self.main_window.statusBar.showMessage("就绪")

    def _create_core_views(self):
        self.main_window.file_explorer = FileExplorer(parent=self.main_window)
        self.main_window.file_explorer.setObjectName("MainFileExplorer")
        self.main_window.file_explorer.hide() 

        self.main_window.note_downloader_view_content = NoteDownloaderView(parent=self.main_window)
        self.main_window.note_downloader_view_content.setObjectName("MainNoteDownloaderViewContent")

        self.main_window.note_downloader_panel = PanelWidget(title="笔记下载器", parent=self.main_window)
        self.main_window.note_downloader_panel.setObjectName("NoteDownloaderPanel")
        self.main_window.note_downloader_panel.setContentWidget(self.main_window.note_downloader_view_content)
        self.main_window.note_downloader_panel.hide() 

    def _assign_initial_tab_widget(self):
        """Deferred assignment of the initial tab widget."""
        if not self.main_window.root_editor_area:
            print("CRITICAL ERROR in _assign_initial_tab_widget: self.main_window.root_editor_area is None.")
            return

        initial_tab_widget = self.main_window.root_editor_area.get_initial_tab_widget()
        print(f"DEBUG: UIInitializer (_assign_initial_tab_widget) - Received initial_tab_widget: {initial_tab_widget}, type: {type(initial_tab_widget)}")

        is_cpp_deleted_for_log = False
        if initial_tab_widget is not None:
            try:
                from PyQt6 import sip
                is_cpp_deleted_for_log = sip.isdeleted(initial_tab_widget)
                print(f"DEBUG: UIInitializer (_assign_initial_tab_widget) - sip.isdeleted(initial_tab_widget) is {is_cpp_deleted_for_log}")
            except ImportError:
                print("WARNING DEBUG: UIInitializer (_assign_initial_tab_widget) - Could not import sip.")
            except Exception as e_sip:
                print(f"WARNING DEBUG: UIInitializer (_assign_initial_tab_widget) - Error checking sip.isdeleted(): {e_sip}")
        
        if initial_tab_widget is not None:
            self.main_window.tab_widget = initial_tab_widget
            if self.ui_manager:
                self.ui_manager.tab_widget = self.main_window.tab_widget
            
            if not initial_tab_widget: # Check boolean context after assignment
                 print(f"WARNING in _assign_initial_tab_widget: initial_tab_widget (Python obj: {initial_tab_widget}, "
                       f"sip.isdeleted: {is_cpp_deleted_for_log}) evaluates to False in boolean context. "
                       f"Tab functionality might be affected.")
            else:
                print(f"DEBUG: UIInitializer (_assign_initial_tab_widget) - initial_tab_widget evaluates to True. Assignments successful.")
            
            if hasattr(self.main_window, 'tab_widget') and self.main_window.tab_widget is not None:
                 if hasattr(self.main_window.tab_widget, 'tabCloseRequested') and hasattr(self.main_window.file_operations, 'close_tab'):
                    try:
                        self.main_window.tab_widget.tabCloseRequested.disconnect(self.main_window.file_operations.close_tab)
                    except TypeError: pass 
                    self.main_window.tab_widget.tabCloseRequested.connect(self.main_window.file_operations.close_tab)
                 
                 if hasattr(self.main_window.tab_widget, 'currentChanged') and hasattr(self.main_window, 'on_current_tab_changed'):
                    try:
                        self.main_window.tab_widget.currentChanged.disconnect(self.main_window.on_current_tab_changed)
                    except TypeError: pass
                    self.main_window.tab_widget.currentChanged.connect(self.main_window.on_current_tab_changed)
                 
                 self.main_window.on_current_tab_changed(self.main_window.tab_widget.currentIndex())
                 if self.main_window.tab_widget.count() == 0:
                     if self.main_window.current_workspace_path and os.path.isdir(self.main_window.current_workspace_path):
                         if hasattr(self.main_window, 'file_operations'):
                             print(f"DEBUG: UIInitializer (_assign_initial_tab_widget) - Tab count is 0, calling new_file...")
                             self.main_window.file_operations.new_file(workspace_path=self.main_window.current_workspace_path)
                             print(f"DEBUG: UIInitializer (_assign_initial_tab_widget) - After new_file: tab_widget count = {self.main_window.tab_widget.count()}, bool = {bool(self.main_window.tab_widget)}")
            else:
                print("CRITICAL ERROR in _assign_initial_tab_widget: self.main_window.tab_widget is None after assignment attempt.")
        else:
            print("CRITICAL ERROR in _assign_initial_tab_widget: get_initial_tab_widget() returned Python None.")
        
        if self.main_window.tab_widget:
            print(f"DEBUG: UIInitializer (_assign_initial_tab_widget END) - Final state: tab_widget count = {self.main_window.tab_widget.count()}, bool = {bool(self.main_window.tab_widget)}")
        else:
            print("DEBUG: UIInitializer (_assign_initial_tab_widget END) - Final state: tab_widget is None.")

    def _setup_main_layout(self, parent_layout: QVBoxLayout):
        self.main_window.root_editor_area = RootEditorAreaWidget(self.main_window)
        self.main_window.root_editor_area.setObjectName("RootEditorArea")
        
        QTimer.singleShot(0, self._assign_initial_tab_widget)

        if self.main_window.file_explorer is None:
            print("错误: UIInitializer 未能创建 file_explorer，无法设置主布局!")
        if self.main_window.note_downloader_panel is None: 
            print("错误: UIInitializer 未能创建 note_downloader_panel，无法设置主布局!")

        main_content_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_content_splitter.setObjectName("MainContentSplitter")
        main_content_splitter.setHandleWidth(2)
        main_content_splitter.setChildrenCollapsible(False)

        if self.main_window.root_editor_area: 
            self.main_window.root_editor_area.setMinimumSize(200, 150)
            if self.main_window.file_explorer: 
                 main_content_splitter.addWidget(self.main_window.file_explorer)
            main_content_splitter.addWidget(self.main_window.root_editor_area)
        
            if self.main_window.file_explorer:
                main_content_splitter.setStretchFactor(0, 3) 
                main_content_splitter.setStretchFactor(1, 8) 
                main_content_splitter.setSizes([200, 800]) 
            else: 
                main_content_splitter.setStretchFactor(0,1)

        parent_layout.addWidget(main_content_splitter)
        print("UIInitializer: Setup main layout with RootEditorAreaWidget and QSplitter. Bottom toolbox removed.")

    def _setup_activity_bar(self): 
         if not hasattr(self.main_window, 'activity_bar_toolbar') or self.main_window.activity_bar_toolbar is None:
             self.main_window.activity_bar_toolbar = QToolBar("活动栏", self.main_window)
             self.main_window.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self.main_window.activity_bar_toolbar)
         
         self.main_window.activity_bar_toolbar.clear() 
         self.main_window.activity_bar_toolbar.setObjectName("ActivityBarToolBar")
         self.main_window.activity_bar_toolbar.setMovable(False)
         self.main_window.activity_bar_toolbar.setFloatable(False)
         self.main_window.activity_bar_toolbar.setFixedWidth(60) 
         self.main_window.activity_bar_toolbar.setStyleSheet("QToolBar { spacing: 5px; padding: 5px; } QToolButton { font-size: 9pt; }") 

         files_btn = QToolButton(self.main_window.activity_bar_toolbar)
         files_btn.setText("文件") 
         files_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
         files_btn.setToolTip("文件管理 (切换)")
         files_btn.setCheckable(True)
         files_btn.setChecked(False) 
         files_btn.clicked.connect(self._toggle_file_explorer_visibility)
         files_btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
         self.main_window.activity_bar_toolbar.addWidget(files_btn)
         self.main_window.toggle_sidebar_button = files_btn 

         print("UIInitializer: Adding buttons for registered views to activity toolbar...")
         if hasattr(self.ui_manager, 'registered_views'):
            print(f"DEBUG UIInitializer._setup_activity_bar: Registered views in UIManager: {list(self.ui_manager.registered_views.keys())}")
         else:
            print("ERROR UIInitializer._setup_activity_bar: self.ui_manager has no 'registered_views' attribute.")
            
         button_text_map = {
             "NoteDownloader": "下载", 
             "Calculator": "计算",     
             "Timer": "计时",         
             "SpeechRecognition": "语音",
             "StickyNotes": "便签",
             "TodoList": "待办",
         }

         if hasattr(self.ui_manager, 'registered_views'):
             for view_name, view_info in self.ui_manager.registered_views.items():
                 try:
                     if view_name == "FileExplorer": continue
                     if view_name == "PdfViewer": continue

                     view_btn = QToolButton(self.main_window.activity_bar_toolbar)
                     button_text = button_text_map.get(view_name)
                     if button_text is None: 
                         if all('\u4e00' <= char <= '\u9fff' for char in view_name) and len(view_name) > 1:
                             button_text = view_name[0] 
                         elif len(view_name) > 2: button_text = view_name[:2]
                         else: button_text = view_name
                     
                     view_btn.setText(button_text)
                     view_btn.setToolTip(f"打开/切换到 {view_name}")
                     view_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
                     view_btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
                     view_btn.setCheckable(True) 
                     
                     view_btn.clicked.connect(
                         lambda checked, v_name=view_name, btn=view_btn: self.handle_activity_button_click(v_name, btn)
                     )
                     
                     if not hasattr(self.main_window, 'activity_view_buttons'):
                         self.main_window.activity_view_buttons = {}
                     self.main_window.activity_view_buttons[view_name] = view_btn
                     view_btn.setChecked(False)

                     self.main_window.activity_bar_toolbar.addWidget(view_btn)
                     print(f"  Added button '{button_text}' for: {view_name} (opens via UIManager)")

                 except Exception as e:
                      print(f"  Error adding button for view '{view_name}': {e}")
         else:
              print("UIInitializer: ui_manager has no registered_views attribute (loop entry).") # Clarified log

         spacer = QWidget()
         spacer.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
         self.main_window.activity_bar_toolbar.addWidget(spacer)
         self.main_window.activity_bar_toolbar.show()

    def handle_activity_button_click(self, view_name: str, button: QToolButton):
        if button.isChecked():
            view_instance_or_dock = self.ui_manager.open_view(view_name, open_in_dock=True, bring_to_front=True)
            if not view_instance_or_dock:
                button.setChecked(False)
        else: 
            if hasattr(self.ui_manager, 'close_dock_view'):
                self.ui_manager.close_dock_view(view_name)
            else:
                print(f"Warning: UIManager does not have 'close_dock_view' method. Cannot close/hide {view_name}.")
                dock_to_close = self.ui_manager.view_docks.get(view_name)
                if dock_to_close:
                    dock_to_close.hide()

    def _toggle_file_explorer_visibility(self, checked):
         if self.main_window.file_explorer:
             self.main_window.file_explorer.setVisible(checked)

    def _toggle_note_downloader_panel_visibility(self, checked): 
         if self.main_window.note_downloader_panel:
             button = self.main_window.activity_view_buttons.get("NoteDownloader")
             if button:
                 button.setChecked(checked) 
                 self.handle_activity_button_click("NoteDownloader", button) 
             else: 
                if checked:
                    # This fallback logic for tool_box_widget might be outdated if tool_box_widget was removed
                    if hasattr(self.main_window, 'tool_box_widget') and self.main_window.tool_box_widget is not None:
                        self.main_window.tool_box_widget.addTab(self.main_window.note_downloader_panel, "笔记下载器")
                        self.main_window.tool_box_widget.setCurrentWidget(self.main_window.note_downloader_panel)
                        self.main_window.tool_box_widget.show()
                    else:
                        print("Warning: tool_box_widget not found for NoteDownloader fallback.")
                else:
                    if hasattr(self.main_window, 'tool_box_widget') and self.main_window.tool_box_widget is not None:
                        for i in range(self.main_window.tool_box_widget.count()):
                            if self.main_window.tool_box_widget.widget(i) == self.main_window.note_downloader_panel:
                                self.main_window.tool_box_widget.removeTab(i)
                                break
                    else:
                        print("Warning: tool_box_widget not found for NoteDownloader fallback (removeTab).")


    def _register_views(self):
        print("--- 开始动态注册视图 (用于非核心布局视图) ---")
        try:
            views_dir = Path(__file__).parent.parent / "views" 
            if not views_dir.is_dir():
                print(f"错误: 视图目录未找到: {views_dir}")
                return

            for filepath in views_dir.glob("*_view.py"):
                module_name = f"src.ui.views.{filepath.stem}"
                if filepath.stem in ["file_explorer_view", "note_downloader_view"]: 
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
                            if view_name_attr == "NoteDownloader": 
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
