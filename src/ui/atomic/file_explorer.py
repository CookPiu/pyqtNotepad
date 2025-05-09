# src/ui/atomic/file_explorer.py
import os
import re # Added import for regex
import shutil # Added for rmtree if needed
from PyQt6.QtWidgets import (QTreeView, QWidget, QVBoxLayout, QHBoxLayout,
                              QPushButton, QFileDialog, QInputDialog, QMessageBox,
                              QSizePolicy, QMenu, QLineEdit) # Added QMenu, QLineEdit
from PyQt6.QtGui import QFileSystemModel, QIcon, QPalette, QColor, QAction # Added QAction
from PyQt6.QtCore import QDir, Qt, pyqtSignal, QEvent, QModelIndex, QPoint, QStandardPaths # Added QStandardPaths

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
        # Determine initial path
        if initial_path and os.path.isdir(initial_path):
            self._current_path = os.path.normpath(initial_path)
        else:
            # Default to Desktop, then home, then CWD
            desktop_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
            if desktop_path and os.path.isdir(desktop_path):
                self._current_path = desktop_path
            else:
                home_path = os.path.expanduser("~")
                if os.path.isdir(home_path):
                    self._current_path = home_path
                else:
                    self._current_path = os.getcwd()
        
        print(f"FileExplorer initial path: {self._current_path}")
        super().__init__(parent) # Calls _init_ui, _connect_signals, _apply_theme

    def _init_ui(self):
        """初始化文件浏览器 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0) 
        layout.setSpacing(0) # Remove spacing if button is removed

        # --- Top Bar for Actions (e.g., Select Workspace) ---
        # Button is removed, functionality moved to main menu
        # top_bar_layout = QHBoxLayout()
        # top_bar_layout.setContentsMargins(2, 2, 2, 2)
        # self.select_workspace_button = QPushButton("选择工作区...")
        # self.select_workspace_button.setToolTip("选择一个新的根文件夹作为工作区")
        # top_bar_layout.addWidget(self.select_workspace_button)
        # top_bar_layout.addStretch(1)
        # layout.addLayout(top_bar_layout)

        # --- File System Model ---
        self.model = QFileSystemModel()
        self.model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot | QDir.Filter.Hidden)
        self.model.setRootPath(self._current_path)

        # --- Tree View ---
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.model)
        self.tree_view.setRootIndex(self.model.index(self._current_path))
        self.tree_view.setAnimated(False)
        self.tree_view.setIndentation(15)
        self.tree_view.setSortingEnabled(True)
        self.tree_view.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.tree_view.setHeaderHidden(True)
        for i in range(1, self.model.columnCount()):
            self.tree_view.hideColumn(i)
        self.tree_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Context Menu for TreeView
        self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        # Enable dragging from the tree view
        self.tree_view.setDragEnabled(True)
        # self.tree_view.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly) # Recommended
        # For QFileSystemModel, it might handle internal moves if set to DragDrop.
        # Let's start with DragOnly to ensure it only initiates drags for external drops.
        # If DragOnly prevents default mime data generation needed for external drop,
        # we might need to use DragDrop and then ignore drops on the treeview itself,
        # or handle mimeData manually in a startDrag method.
        # QTreeView's default drag behavior with QFileSystemModel should provide necessary URLs.
        # Let's test default behavior of setDragEnabled(True) first.
        # If issues, then specify DragDropMode.
        from PyQt6.QtWidgets import QAbstractItemView # Import for DragDropMode
        self.tree_view.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)


        layout.addWidget(self.tree_view)
        self.setLayout(layout)

    def _connect_signals(self):
        """连接信号与槽"""
        # self.select_workspace_button.clicked.connect(self.browse_for_folder) # Button removed
        self.tree_view.doubleClicked.connect(self._on_item_double_clicked)
        self.tree_view.customContextMenuRequested.connect(self._show_context_menu)
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

    def _show_context_menu(self, position: QPoint):
        """在TreeView中显示右键菜单"""
        index = self.tree_view.indexAt(position)
        if not index.isValid():
            return

        menu = QMenu(self.tree_view)
        
        rename_action = QAction("重命名", self)
        rename_action.triggered.connect(lambda: self._rename_item(index))
        menu.addAction(rename_action)

        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self._delete_item(index))
        menu.addAction(delete_action)
        
        menu.exec(self.tree_view.viewport().mapToGlobal(position))

    def _rename_item(self, index: QModelIndex):
        """重命名选中的文件或文件夹"""
        if not index.isValid():
            return

        old_path = self.model.filePath(index)
        old_name = self.model.fileName(index)

        new_name, ok = QInputDialog.getText(self, "重命名", f"请输入新的名称 '{old_name}':", QLineEdit.EchoMode.Normal, old_name)

        if ok and new_name and new_name != old_name:
            # Basic validation for new name
            if not re.match(r'^[a-zA-Z0-9_.\-\s]+$', new_name) or '..' in new_name or '/' in new_name or '\\' in new_name:
                 QMessageBox.warning(self, "无效名称", "名称包含无效字符。")
                 return

            parent_index = self.model.parent(index)
            # QFileSystemModel does not have a direct rename method.
            # We need to use os.rename and then rely on the model to detect changes,
            # or refresh the parent directory.
            # A more robust way with QFileSystemModel is often to remove and re-add,
            # but that's complex. os.rename is simpler if the model picks it up.
            
            # For files, setData with EditRole might work for renaming the display name,
            # but it doesn't rename on the filesystem.
            # Let's try os.rename and see if QFileSystemModel updates.
            # If not, we might need to refresh the parent directory view.
            
            new_path = os.path.join(os.path.dirname(old_path), new_name)

            try:
                # Attempt to rename using QFileSystemModel.setData if it triggers a rename.
                # This is often not implemented for actual file system rename by QFileSystemModel.
                # if self.model.setData(index, new_name, Qt.ItemDataRole.EditRole):
                #    print(f"Renamed '{old_name}' to '{new_name}' using setData (unlikely to work on FS).")
                # else:
                #    print(f"setData for rename failed, falling back to os.rename.")
                
                # Fallback to os.rename
                os.rename(old_path, new_path)
                print(f"Renamed '{old_path}' to '{new_path}' using os.rename.")
                # QFileSystemModel should ideally pick this up.
                # If not, a refresh of the parent might be needed, e.g., by resetting root or specific dir.
                # Forcing a refresh can be disruptive. Let's see if it auto-updates.
                # If issues, consider:
                # self.model.setRootPath(self.model.rootPath()) # Force full refresh (heavy)
                # Or more targeted refresh if possible.

            except OSError as e:
                QMessageBox.critical(self, "重命名失败", f"无法重命名 '{old_name}':\n{e}")
            except Exception as e: # Catch any other unexpected errors
                QMessageBox.critical(self, "重命名错误", f"重命名时发生未知错误:\n{e}")


    def _delete_item(self, index: QModelIndex):
        """删除选中的文件或文件夹"""
        if not index.isValid():
            return

        path_to_delete = self.model.filePath(index)
        is_dir = self.model.isDir(index)
        item_name = self.model.fileName(index)

        confirm_msg = f"您确定要删除 {'文件夹' if is_dir else '文件'} '{item_name}' 吗？"
        if is_dir:
            confirm_msg += "\n此操作无法撤销，文件夹内的所有内容都将被删除。"

        reply = QMessageBox.question(self, "确认删除", confirm_msg,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Use QFileSystemModel.remove() for proper integration with the view
                if self.model.remove(index):
                    print(f"成功删除: {path_to_delete}")
                else:
                    # If model.remove() fails, it might be due to permissions or other issues.
                    # It could also mean the model doesn't handle recursive deletion well for non-empty dirs.
                    # QFileSystemModel.remove() should handle both files and directories.
                    # For directories, it should be recursive.
                    print(f"QFileSystemModel.remove() 返回 false 对于: {path_to_delete}")
                    # Fallback for directories if model.remove fails and it's a directory.
                    # This is less ideal as the model might not update as cleanly.
                    if is_dir and os.path.exists(path_to_delete): # Check existence before shutil
                        print(f"尝试使用 shutil.rmtree() 作为后备方案删除目录: {path_to_delete}")
                        shutil.rmtree(path_to_delete)
                        print(f"使用 shutil.rmtree() 成功删除: {path_to_delete}")
                        # Manually trigger a refresh of the parent if needed
                        parent_index = self.model.parent(index)
                        # This is a bit of a hack; ideally, model.remove() works.
                        # self.model.dataChanged.emit(parent_index, parent_index) # This might not be enough
                        # self.model.layoutChanged.emit() # Too broad
                        # Simplest heavy-handed refresh:
                        # current_root = self.model.rootPath()
                        # self.model.setRootPath("") # Clear
                        # self.model.setRootPath(current_root) # Reset
                    elif not is_dir and os.path.exists(path_to_delete): # Fallback for files
                         os.remove(path_to_delete)
                         print(f"使用 os.remove() 作为后备方案成功删除文件: {path_to_delete}")
                    else:
                         QMessageBox.warning(self, "删除失败", f"无法删除 '{item_name}'. 项目可能已被外部删除或权限不足。")

            except Exception as e:
                QMessageBox.critical(self, "删除错误", f"删除 '{item_name}' 时出错:\n{e}")
