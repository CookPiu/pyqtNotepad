# src/ui/atomic/file_explorer.py
import os
from PyQt6.QtWidgets import (QTreeView, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QFileDialog, QInputDialog, QMessageBox,
                             QSizePolicy)
from PyQt6.QtGui import QFileSystemModel, QIcon, QPalette, QColor
from PyQt6.QtCore import QDir, Qt, pyqtSignal, QEvent, QModelIndex

# Correct relative import from atomic to core
from ..core.base_widget import BaseWidget
# from ..core.theme_manager import ThemeManager # Optional

class FileExplorer(BaseWidget):
    """
    文件浏览器原子组件，用于显示文件系统树状视图。
    继承自 BaseWidget。
    """
    # Signal emitted when a file is double-clicked
    file_double_clicked = pyqtSignal(str)
    # Signal emitted when the root path changes
    root_path_changed = pyqtSignal(str)

    def __init__(self, parent=None, initial_path=None):
        # Determine initial path: provided, user home, or current working directory
        if initial_path and os.path.isdir(initial_path):
            self._current_path = initial_path
        else:
            self._current_path = os.path.expanduser("~") # Default to user home
            if not os.path.isdir(self._current_path):
                self._current_path = os.getcwd() # Fallback to CWD

        super().__init__(parent) # Calls _init_ui, _connect_signals, _apply_theme

    def _init_ui(self):
        """初始化文件浏览器 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0) # No margins for the widget itself
        layout.setSpacing(0)

        # --- File System Model ---
        self.model = QFileSystemModel()
        # Set filters before setting root path for better performance
        self.model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot | QDir.Filter.Hidden) # Show hidden files
        self.model.setRootPath(self._current_path) # Set initial root

        # --- Tree View ---
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.model)
        self.tree_view.setRootIndex(self.model.index(self._current_path))
        self.tree_view.setAnimated(False) # Animation can be slow with many files
        self.tree_view.setIndentation(15) # Adjust indentation
        self.tree_view.setSortingEnabled(True)
        self.tree_view.sortByColumn(0, Qt.SortOrder.AscendingOrder) # Sort by name initially

        # Hide unnecessary columns (Size, Type, Date Modified)
        self.tree_view.setHeaderHidden(True)
        for i in range(1, self.model.columnCount()):
            self.tree_view.hideColumn(i)

        # Set size policy to expand
        self.tree_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout.addWidget(self.tree_view)
        self.setLayout(layout)

    def _connect_signals(self):
        """连接信号与槽"""
        self.tree_view.doubleClicked.connect(self._on_item_double_clicked)
        # Optional: Connect selection changes if needed
        # self.tree_view.selectionModel().selectionChanged.connect(self._on_selection_changed)

    def _apply_theme(self):
        """应用主题样式 (由 BaseWidget 调用)"""
        self.update_styles(is_dark=False) # Default light

    def update_styles(self, is_dark: bool):
        """根据主题更新控件样式"""
        bg_color = "#1e1e1e" if is_dark else "#ffffff"
        text_color = "#f0f0f0" if is_dark else "#2c3e50"
        border_color = "#555555" if is_dark else "#cccccc"
        selected_bg = "#3498db"
        selected_text = "#ffffff"

        # Apply to TreeView
        self.tree_view.setStyleSheet(f"""
            QTreeView {{
                background-color: {bg_color};
                color: {text_color};
                border: none; /* Remove border from treeview itself */
                /* font-size: 12px; */ /* Removed hardcoded font-size to allow global/programmatic scaling */
            }}
            QTreeView::item {{
                padding: 3px 0px; /* Adjust vertical padding */
            }}
            QTreeView::item:selected {{
                background-color: {selected_bg};
                color: {selected_text};
            }}
            QTreeView::item:hover {{
                background-color: {"#444" if is_dark else "#e0e0e0"};
            }}
            QTreeView::branch {{ /* Style for expand/collapse indicators */
                /* background: transparent; */ /* Use default */
            }}
            QTreeView::branch:has-children:!has-siblings:closed,
            QTreeView::branch:closed:has-children:has-siblings {{
                /* image: url(path/to/closed_arrow_{'dark' if is_dark else 'light'}.png); */
            }}
            QTreeView::branch:open:has-children:!has-siblings,
            QTreeView::branch:open:has-children:has-siblings {{
                /* image: url(path/to/open_arrow_{'dark' if is_dark else 'light'}.png); */
            }}
        """)
        # Consider setting palette for more robust color application
        # palette = self.tree_view.palette()
        # palette.setColor(QPalette.ColorRole.Base, QColor(bg_color))
        # palette.setColor(QPalette.ColorRole.Text, QColor(text_color))
        # palette.setColor(QPalette.ColorRole.Highlight, QColor(selected_bg))
        # palette.setColor(QPalette.ColorRole.HighlightedText, QColor(selected_text))
        # self.tree_view.setPalette(palette)

    # --- Public Methods ---
    def set_root_path(self, path: str):
        """设置文件浏览器的根路径"""
        norm_path = os.path.normpath(path)
        if os.path.isdir(norm_path):
            self._current_path = norm_path
            root_index = self.model.setRootPath(norm_path) # Update model's root
            self.tree_view.setRootIndex(root_index)       # Update view's root
            self.root_path_changed.emit(norm_path) # Emit signal
        else:
            print(f"路径无效或不是目录: {norm_path}")

    def get_root_path(self) -> str:
        """获取当前的根路径"""
        return self._current_path

    def get_selected_path(self) -> str | None:
        """获取当前选中的文件或目录路径"""
        indexes = self.tree_view.selectedIndexes()
        if indexes:
            return self.model.filePath(indexes[0])
        return None

    def select_path(self, path: str):
        """尝试选中指定路径"""
        index = self.model.index(path)
        if index.isValid():
            self.tree_view.setCurrentIndex(index)
            self.tree_view.scrollTo(index, QTreeView.ScrollHint.PositionAtCenter)
        else:
            print(f"无法在树中找到路径: {path}")

    # --- Action Methods (Consider moving trigger logic to parent/view) ---
    def browse_for_folder(self):
        """打开文件夹选择对话框并设置根路径"""
        folder_path = QFileDialog.getExistingDirectory(self, "选择根文件夹", self._current_path)
        if folder_path:
            self.set_root_path(folder_path)

    def create_new_folder_at_selection(self):
        """在当前选中项下或根目录下创建新文件夹"""
        selected_path = self.get_selected_path()
        parent_path = self._current_path # Default to root
        if selected_path:
            if os.path.isdir(selected_path):
                parent_path = selected_path
            else:
                parent_path = os.path.dirname(selected_path)

        folder_name, ok = QInputDialog.getText(self, "新建文件夹", "请输入文件夹名称:", QLineEdit.EchoMode.Normal, "")
        if ok and folder_name:
            # Basic validation for folder name
            if not re.match(r'^[a-zA-Z0-9_.\-\s]+$', folder_name) or '..' in folder_name:
                 QMessageBox.warning(self, "无效名称", "文件夹名称包含无效字符。")
                 return
            new_folder_path = os.path.join(parent_path, folder_name)
            try:
                # Use QFileSystemModel to create directory to ensure view updates
                index = self.model.index(parent_path)
                if index.isValid():
                    self.model.mkdir(index, folder_name)
                else: # Fallback if parent index is somehow invalid
                     os.makedirs(new_folder_path, exist_ok=True)
                     # Manually refresh might be needed in fallback case
                     # self.model.setRootPath(self._current_path) # Force refresh (can be slow)
            except Exception as e:
                QMessageBox.critical(self, "创建错误", f"创建文件夹失败: {e}")

    def create_new_file_at_selection(self):
        """在当前选中项下或根目录下创建新文件"""
        selected_path = self.get_selected_path()
        parent_path = self._current_path # Default to root
        if selected_path:
            if os.path.isdir(selected_path):
                parent_path = selected_path
            else:
                parent_path = os.path.dirname(selected_path)

        file_name, ok = QInputDialog.getText(self, "新建文件", "请输入文件名称:", QLineEdit.EchoMode.Normal, "")
        if ok and file_name:
             # Basic validation for file name
            if not re.match(r'^[a-zA-Z0-9_.\-\s]+$', file_name) or '..' in file_name:
                 QMessageBox.warning(self, "无效名称", "文件名称包含无效字符。")
                 return
            new_file_path = os.path.join(parent_path, file_name)
            if os.path.exists(new_file_path):
                 QMessageBox.warning(self, "文件已存在", f"文件 '{file_name}' 已存在。")
                 return
            try:
                # Create the file
                with open(new_file_path, 'w') as f:
                    f.write("") # Create empty file
                # QFileSystemModel should pick up the change automatically
                # Select the newly created file
                self.select_path(new_file_path)
            except Exception as e:
                QMessageBox.critical(self, "创建错误", f"创建文件失败: {e}")


    # --- Slots ---
    def _on_item_double_clicked(self, index: QModelIndex):
        """处理项目双击事件"""
        if not index.isValid(): return
        file_path = self.model.filePath(index)
        if self.model.isDir(index):
            # Optional: Expand/collapse on double click? Default behavior handles this.
            pass
        else: # It's a file
            self.file_double_clicked.emit(file_path) # Emit signal for file

    # def _on_selection_changed(self, selected, deselected):
    #     """Handle selection changes if needed"""
    #     selected_path = self.get_selected_path()
    #     if selected_path:
    #         print(f"Selected: {selected_path}")
    #     else:
    #         print("Selection cleared")
