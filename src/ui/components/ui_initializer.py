import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QToolBar, QMenuBar, QMenu,
                             QStatusBar, QSplitter, QTabWidget, QToolButton, QListWidget, 
                             QListWidgetItem, QSizePolicy)
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import Qt, QSize, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView

class UIInitializer:
    """负责初始化MainWindow的UI组件"""
    
    def __init__(self, main_window):
        self.main_window = main_window
    
    def setup_ui(self):
        """设置主窗口UI"""
        self.main_window.setWindowTitle("多功能记事本")
        self.main_window.setGeometry(100, 100, 1000, 700)
        central_widget = QWidget()
        self.main_window.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 初始化各个UI组件
        self._setup_toolbar()
        self._setup_activity_bar()
        self._setup_browser()
        self._setup_tab_widget()
        self._setup_sidebar()
        self._setup_splitters(main_layout)
        self._setup_status_bar()
        
        # 连接信号
        self.main_window.tab_widget.currentChanged.connect(self.main_window.on_current_tab_changed)
        
        # 设置初始状态
        self.main_window.update_edit_actions_state(self.main_window.get_current_editor())
        print("▶ initUI 完成") # ★ 添加打印
    
    def _setup_toolbar(self):
        """设置顶部工具栏"""
        self.main_window.toolbar = QToolBar("主工具栏")
        self.main_window.toolbar.setIconSize(QSize(20, 20))
        self.main_window.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonFollowStyle)
        self.main_window.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.main_window.toolbar)
    
    def _setup_activity_bar(self):
        """设置左侧活动栏"""
        self.main_window.activity_bar = QToolBar("ActivityBar", self.main_window)
        self.main_window.activity_bar.setOrientation(Qt.Orientation.Vertical)
        self.main_window.activity_bar.setIconSize(QSize(20, 20))
        self.main_window.activity_bar.setFixedWidth(48)  # VS Code 默认 48
        self.main_window.activity_bar.setMovable(False)
        
        # 添加文件资源管理器按钮
        files_action = self.main_window.activity_bar.addAction("Files", lambda: self.main_window.toggle_sidebar())
        files_action.setToolTip("文件资源管理器 (切换侧边栏)")
        self.main_window.activity_bar.addSeparator()
        
        # 添加笔记下载器按钮
        act_download = self.main_window.activity_bar.addAction("DL")  # DL = Download 缩写
        act_download.setToolTip("笔记下载器")
        act_download.triggered.connect(lambda: (self.main_window.toggle_sidebar(False), self.main_window.open_note_downloader_tab()))
        self.main_window.activity_bar.addSeparator()
        
        self.main_window.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self.main_window.activity_bar)
    
    def _setup_browser(self):
        """初始化浏览器视图"""
        self.main_window.browser = QWebEngineView(self.main_window)
        self.main_window.browser.setUrl(QUrl("about:blank"))
    
    def _setup_tab_widget(self):
        """设置标签页组件"""
        self.main_window.tab_widget = QTabWidget()
        self.main_window.tab_widget.setDocumentMode(True)
        self.main_window.tab_widget.setTabsClosable(True)
        self.main_window.tab_widget.setMovable(True)
        self.main_window.tab_widget.tabCloseRequested.connect(self.main_window.close_tab)
    
    def _setup_sidebar(self):
        """设置侧边栏"""
        # 垂直分割器用于原始侧边栏内容（列表+资源管理器）
        self.main_window.sidebar_content_splitter = QSplitter(Qt.Orientation.Vertical)
        self.main_window.sidebar_content_splitter.setHandleWidth(1)
        
        # 侧边栏功能列表
        self.main_window.function_list = QListWidget()
        sidebar_items = [
            {"name": "计时器", "icon": "clock"},
            {"name": "便签与待办", "icon": "note"},
            {"name": "计算器", "icon": "calculator"},
            {"name": "日历", "icon": "calendar"},
            {"name": "笔记下载", "icon": "download"},
        ]
        for item in sidebar_items:
            list_item = QListWidgetItem(item["name"])
            list_item.setToolTip(f"{item['name']}功能（占位符）")
            self.main_window.function_list.addItem(list_item)
        self.main_window.function_list.itemClicked.connect(self.main_window.sidebar_item_clicked)
        
        # 添加组件到垂直侧边栏内容分割器
        self.main_window.sidebar_content_splitter.addWidget(self.main_window.function_list)
        self.main_window.sidebar_content_splitter.addWidget(self.main_window.file_explorer)
        self.main_window.sidebar_content_splitter.setSizes([200, 400])
        
        # 侧边栏容器
        self.main_window.sidebar = QWidget()
        self.main_window.sidebar.setObjectName("SideBarContainer")
        side_layout = QVBoxLayout(self.main_window.sidebar)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(0)
        side_layout.addWidget(self.main_window.sidebar_content_splitter)
    
    def _setup_splitters(self, main_layout):
        """设置分割器"""
        # 编辑器/浏览器分割器（垂直）
        self.main_window.editor_browser_splitter = QSplitter(Qt.Orientation.Vertical)
        self.main_window.editor_browser_splitter.setHandleWidth(1)
        self.main_window.editor_browser_splitter.addWidget(self.main_window.tab_widget)
        self.main_window.editor_browser_splitter.addWidget(self.main_window.browser)
        self.main_window.editor_browser_splitter.setSizes([500, 200])
        
        # 主水平分割器（VS Code布局）
        self.main_window.v_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_window.v_splitter.setHandleWidth(1)
        
        # 添加侧边栏容器和编辑器/浏览器区域到水平分割器
        self.main_window.v_splitter.addWidget(self.main_window.sidebar)
        self.main_window.v_splitter.addWidget(self.main_window.editor_browser_splitter)
        
        # 设置拉伸因子：编辑器区域（索引1）扩展，侧边栏（索引0）最初不扩展
        self.main_window.v_splitter.setStretchFactor(0, 0)
        self.main_window.v_splitter.setStretchFactor(1, 1)
        self.main_window.v_splitter.setSizes([self.main_window.sidebar_original_width, 800])
        
        # 将主水平分割器设置为中央小部件的布局项
        main_layout.addWidget(self.main_window.v_splitter)
    
    def _setup_status_bar(self):
        """设置状态栏"""
        self.main_window.statusBar = QStatusBar()
        self.main_window.setStatusBar(self.main_window.statusBar)
        self.main_window.statusBar.showMessage("就绪")