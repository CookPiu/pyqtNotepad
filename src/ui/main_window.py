import sys
import os
import json
from PyQt6.QtWidgets import (QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QTextEdit, QListWidget, QListWidgetItem, QToolBar, QMenuBar, QMenu,
                             QStatusBar, QFileDialog, QFontDialog, QColorDialog, QMessageBox,
                             QInputDialog, QSplitter, QTabWidget) # Import QTabWidget
from PyQt6.QtGui import QAction, QFont, QColor, QTextCursor, QIcon, QImage, QTextDocument, QPainter
from PyQt6.QtCore import Qt, QSize, QUrl, QRect, QEvent, pyqtSignal, QPointF, QFile, QTextStream, QPoint, QSignalBlocker
import fitz  # PyMuPDF库

# Updated imports for moved components
from src.utils.theme_manager import ThemeManager
from src.ui.file_explorer import FileExplorer
from src.utils.pdf_utils import extract_pdf_content, cleanup_temp_images
from src.ui.pdf_viewer import PDFViewer
from src.ui.timer_widget import TimerWindow # Renamed from timer.py
from src.ui.editor import TextEditWithLineNumbers # Import the editor component
from src.ui.calculator_widget import CalculatorWindow
from src.ui.calendar_widget import CalendarWindow
from src.ui.sticky_note_widget import StickyNote, StickyNoteWindow
from src.ui.todo_widget import TodoWidget


class MainWindow(QMainWindow):
    current_editor_changed = pyqtSignal(QTextEdit) # Keep QTextEdit for broader compatibility, or change to TextEditWithLineNumbers if specific methods are needed

    def __init__(self):
        super().__init__()
        # Initialize ThemeManager using the correct import path
        self.theme_manager = ThemeManager()
        self.untitled_counter = 0
        self.previous_editor = None
        
        # 初始化便签列表
        self.sticky_notes = []
        
        self.initUI()
        self.apply_current_theme()
        
        # 加载保存的便签
        try:
            self.load_sticky_notes()
        except Exception as e:
            print(f"加载便签时出错: {str(e)}")
        
        # Check if tab widget is empty before creating a new file
        if self.tab_widget.count() == 0:
            self.new_file()

    def initUI(self):
        self.setWindowTitle("多功能记事本")
        self.setGeometry(100, 100, 1000, 700)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.toolbar = QToolBar("主工具栏")
        self.toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)

        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        # Connect currentChanged later, after UI is fully initialized

        # --- Sidebar Splitter ---
        self.sidebar_splitter = QSplitter(Qt.Orientation.Vertical)
        self.sidebar_splitter.setHandleWidth(1)

        # --- Sidebar Function List ---
        self.sidebar = QListWidget()
        sidebar_items = [
            {"name": "计时器", "icon": "clock"}, {"name": "待办事项", "icon": "task-list"},
            {"name": "便签", "icon": "note"}, {"name": "计算器", "icon": "calculator"},
            {"name": "日历", "icon": "calendar"}
        ]
        for item in sidebar_items:
            list_item = QListWidgetItem(item["name"])
            list_item.setToolTip(f"{item['name']}功能（占位符）")
            # You might want to associate icons properly here if available
            self.sidebar.addItem(list_item)
        self.sidebar.itemClicked.connect(self.sidebar_item_clicked)

        # --- File Explorer (using imported class) ---
        self.file_explorer = FileExplorer()
        self.file_explorer.file_double_clicked.connect(self.open_file_from_path)

        # --- Add Widgets to Sidebar Splitter ---
        self.sidebar_splitter.addWidget(self.sidebar)
        self.sidebar_splitter.addWidget(self.file_explorer)
        self.sidebar_splitter.setSizes([200, 400])

        # --- Main Splitter ---
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setHandleWidth(1)
        self.main_splitter.addWidget(self.sidebar_splitter)
        self.main_splitter.addWidget(self.tab_widget)
        self.main_splitter.setSizes([200, 800])
        main_layout.addWidget(self.main_splitter)

        self.create_actions()
        self.create_menu_bar()
        self.create_toolbar()
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("就绪")
        # Connect currentChanged signal after UI is fully initialized
        # to ensure initial state is handled correctly
        self.tab_widget.currentChanged.connect(self.on_current_tab_changed)
        # Set initial state for actions based on whether a tab exists
        self.update_edit_actions_state(self.get_current_editor())


    def create_actions(self):
        # Action creation remains largely the same, ensure icons are handled
        # (QIcon.fromTheme might need fallback or direct path if theme icons aren't available)
        self.new_action = QAction(QIcon.fromTheme("document-new", QIcon("assets/icons/document-new.png")), "新建", self, shortcut="Ctrl+N", triggered=self.new_file) # Added fallback example
        self.open_action = QAction(QIcon.fromTheme("document-open"), "打开...", self, shortcut="Ctrl+O", triggered=self.open_file_dialog)
        self.save_action = QAction(QIcon.fromTheme("document-save"), "保存", self, shortcut="Ctrl+S", triggered=self.save_file, enabled=False)
        self.save_as_action = QAction(QIcon.fromTheme("document-save-as"), "另存为...", self, shortcut="Ctrl+Shift+S", triggered=self.save_file_as, enabled=False)
        self.close_tab_action = QAction("关闭标签页", self, shortcut="Ctrl+W", triggered=lambda: self.close_tab(self.tab_widget.currentIndex()), enabled=False)
        self.exit_action = QAction("退出", self, shortcut="Ctrl+Q", triggered=self.close)

        self.undo_action = QAction(QIcon.fromTheme("edit-undo"), "撤销", self, shortcut="Ctrl+Z", triggered=self.undo_action_handler, enabled=False)
        self.redo_action = QAction(QIcon.fromTheme("edit-redo"), "重做", self, shortcut="Ctrl+Y", triggered=self.redo_action_handler, enabled=False)
        self.cut_action = QAction(QIcon.fromTheme("edit-cut"), "剪切", self, shortcut="Ctrl+X", triggered=self.cut_action_handler, enabled=False)
        self.copy_action = QAction(QIcon.fromTheme("edit-copy"), "复制", self, shortcut="Ctrl+C", triggered=self.copy_action_handler, enabled=False)
        self.paste_action = QAction(QIcon.fromTheme("edit-paste"), "粘贴", self, shortcut="Ctrl+V", triggered=self.paste_action_handler, enabled=False)
        self.select_all_action = QAction("全选", self, shortcut="Ctrl+A", triggered=self.select_all_action_handler, enabled=False)

        self.font_action = QAction("字体...", self, triggered=self.change_font, enabled=False)
        self.color_action = QAction("颜色...", self, triggered=self.change_color, enabled=False)
        self.insert_image_action = QAction(QIcon.fromTheme("insert-image"), "插入图片...", self, triggered=self.insert_image, enabled=False)
        self.find_action = QAction(QIcon.fromTheme("edit-find"), "查找", self, shortcut="Ctrl+F", triggered=self.find_text, enabled=False)
        self.replace_action = QAction(QIcon.fromTheme("edit-find-replace"), "替换", self, shortcut="Ctrl+H", triggered=self.replace_text, enabled=False)

        self.toggle_theme_action = QAction("切换主题", self, shortcut="Ctrl+T", triggered=self.toggle_theme)
        self.about_action = QAction("关于", self, triggered=self.show_about)

    def create_menu_bar(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("文件")
        file_menu.addActions([self.new_action, self.open_action, self.save_action, self.save_as_action])
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
        edit_menu.addActions([self.find_action, self.replace_action]) # Added find/replace

        format_menu = menu_bar.addMenu("格式")
        format_menu.addActions([self.font_action, self.color_action])
        format_menu.addSeparator()
        format_menu.addAction(self.insert_image_action)
        format_menu.addSeparator()
        format_menu.addAction(self.toggle_theme_action)

        help_menu = menu_bar.addMenu("帮助")
        help_menu.addAction(self.about_action)

    def create_toolbar(self):
        self.toolbar.addActions([self.new_action, self.open_action, self.save_action])
        self.toolbar.addSeparator()
        self.toolbar.addActions([self.undo_action, self.redo_action])
        self.toolbar.addSeparator()
        self.toolbar.addActions([self.cut_action, self.copy_action, self.paste_action])
        self.toolbar.addSeparator()
        self.toolbar.addActions([self.find_action, self.replace_action]) # Added find/replace

    def get_current_editor(self) -> TextEditWithLineNumbers | None:
        # Ensure we return the correct type or None
        widget = self.tab_widget.currentWidget()
        return widget if isinstance(widget, TextEditWithLineNumbers) else None

    def on_current_tab_changed(self, index):
        # This function remains mostly the same
        editor = self.get_current_editor()
        self.update_edit_actions_state(editor)
        self.update_window_title()
        # Ensure signal emits the correct type or None
        self.current_editor_changed.emit(editor if editor else None)

    def _update_copy_cut_state(self, available: bool):
        # This helper function remains the same
        self.copy_action.setEnabled(available)
        self.cut_action.setEnabled(available)

    def update_edit_actions_state(self, editor: TextEditWithLineNumbers | None):
        # This function remains largely the same, ensures actions are enabled/disabled correctly
        has_editor = isinstance(editor, TextEditWithLineNumbers)
        # Attempt to get clipboard data safely
        try:
            can_paste = QApplication.clipboard().text() != "" if has_editor else False
        except Exception:
            can_paste = False # Handle cases where clipboard access might fail

        # Disconnect previous signals safely
        if self.previous_editor:
            try: self.previous_editor.document().undoAvailable.disconnect(self.undo_action.setEnabled)
            except TypeError: pass
            try: self.previous_editor.document().redoAvailable.disconnect(self.redo_action.setEnabled)
            except TypeError: pass
            try: self.previous_editor.copyAvailable.disconnect(self._update_copy_cut_state)
            except TypeError: pass
            try: self.previous_editor.document().modificationChanged.disconnect(self.update_tab_title)
            except TypeError: pass

        is_undoable = has_editor and editor.document().isUndoAvailable()
        is_redoable = has_editor and editor.document().isRedoAvailable()
        has_selection = has_editor and editor.textCursor().hasSelection()

        self.undo_action.setEnabled(is_undoable)
        self.redo_action.setEnabled(is_redoable)
        self.cut_action.setEnabled(has_selection)
        self.copy_action.setEnabled(has_selection)
        self.paste_action.setEnabled(has_editor and can_paste)
        self.select_all_action.setEnabled(has_editor)
        self.font_action.setEnabled(has_editor)
        self.color_action.setEnabled(has_editor)
        self.insert_image_action.setEnabled(has_editor)
        self.save_action.setEnabled(has_editor)
        self.save_as_action.setEnabled(has_editor)
        self.close_tab_action.setEnabled(has_editor)
        self.find_action.setEnabled(has_editor)
        self.replace_action.setEnabled(has_editor)


        # Connect signals for the current editor safely
        if has_editor:
            try: editor.document().undoAvailable.connect(self.undo_action.setEnabled)
            except TypeError: pass
            try: editor.document().redoAvailable.connect(self.redo_action.setEnabled)
            except TypeError: pass
            try: editor.copyAvailable.connect(self._update_copy_cut_state)
            except TypeError: pass
            try: editor.document().modificationChanged.connect(self.update_tab_title)
            except TypeError: pass
            self.previous_editor = editor
        else:
            self.previous_editor = None


    def update_window_title(self):
        # This function remains mostly the same
        editor = self.get_current_editor()
        title_prefix = "多功能记事本"
        if editor and (index := self.tab_widget.currentIndex()) != -1:
            tab_text = self.tab_widget.tabText(index)
            if tab_text: # Check if tab_text is not empty
                # Strip '*' only if it exists at the end
                base_tab_text = tab_text[:-1].strip() if tab_text.endswith("*") else tab_text
                title_prefix = f"{base_tab_text} - {title_prefix}"
        self.setWindowTitle(title_prefix)

    def update_tab_title(self, modified: bool):
         # This function remains mostly the same
         index = self.tab_widget.currentIndex()
         if index == -1: return
         editor = self.tab_widget.widget(index)
         if not isinstance(editor, TextEditWithLineNumbers): return

         file_path = editor.property("file_path")
         # Use untitled_name if file_path is None, otherwise use base name
         tab_name_base = os.path.basename(file_path) if file_path else (editor.property("untitled_name") or f"未命名-{self.untitled_counter}")

         new_tab_text = f"{tab_name_base}{'*' if modified else ''}"
         self.tab_widget.setTabText(index, new_tab_text)
         self.update_window_title() # Update window title as well


    # --- Action Handlers ---
    def undo_action_handler(self):
        if editor := self.get_current_editor(): editor.undo()
    def redo_action_handler(self):
        if editor := self.get_current_editor(): editor.redo()
    def cut_action_handler(self):
        if editor := self.get_current_editor(): editor.cut()
    def copy_action_handler(self):
        if editor := self.get_current_editor(): editor.copy()
    def paste_action_handler(self):
        if editor := self.get_current_editor(): editor.paste()
    def select_all_action_handler(self):
        if editor := self.get_current_editor(): editor.selectAll()

    # --- Sidebar Click Handler ---
    def sidebar_item_clicked(self, item):
        # Use the imported TimerWindow class
        if item.text() == "计时器":
            # Check if window already exists
            if not hasattr(self, 'timer_window') or not self.timer_window.isVisible():
                 self.timer_window = TimerWindow(self) # Use imported class
                 self.timer_window.show()
            else:
                 self.timer_window.activateWindow()
            self.statusBar.showMessage(f"已打开 {item.text()} 功能")
        elif item.text() == "计算器":
            # 检查计算器窗口是否已经存在
            if not hasattr(self, 'calculator_window') or not self.calculator_window.isVisible():
                 self.calculator_window = CalculatorWindow(self) # 使用导入的CalculatorWindow类
                 self.calculator_window.show()
            else:
                 self.calculator_window.activateWindow()
            self.statusBar.showMessage(f"已打开 {item.text()} 功能")
        elif item.text() == "日历":
            # 检查日历窗口是否已经存在
            if not hasattr(self, 'calendar_window') or not self.calendar_window.isVisible():
                 self.calendar_window = CalendarWindow(self) # 使用导入的CalendarWindow类
                 self.calendar_window.show()
            else:
                 self.calendar_window.activateWindow()
            self.statusBar.showMessage(f"已打开 {item.text()} 功能")
        elif item.text() == "便签":
            try:
                # 直接创建一个新便签
                if not hasattr(self, 'sticky_notes'):
                    self.sticky_notes = []
                
                # 创建新便签
                sticky_note = StickyNote(parent=self)
                
                # 安全连接信号
                try:
                    sticky_note.closed.connect(self.on_sticky_note_closed)
                except Exception:
                    pass
                    
                # 显示便签
                sticky_note.show()
                
                # 添加到便签列表
                self.sticky_notes.append(sticky_note)
                
                self.statusBar.showMessage(f"已创建新便签")
            except Exception as e:
                print(f"创建便签时出错: {str(e)}")
                self.statusBar.showMessage(f"创建便签失败")
        elif item.text() == "待办事项":
            # 检查待办事项窗口是否已经存在
            if not hasattr(self, 'todo_window') or not self.todo_window.isVisible():
                 try:
                     # 尝试创建data目录（如果不存在）
                     os.makedirs("data", exist_ok=True)
                     
                     # 确保todo.json文件存在且格式正确
                     todo_path = os.path.join("data", "todo.json")
                     if not os.path.exists(todo_path):
                         # 创建一个空的todo.json文件
                         with open(todo_path, "w", encoding="utf-8") as f:
                             json.dump([], f)
                         print(f"创建了新的待办事项文件: {todo_path}")
                         
                     self.todo_window = TodoWidget(self)
                     self.todo_window.show()
                     self.statusBar.showMessage(f"已打开 {item.text()} 功能")
                 except Exception as e:
                     print(f"打开待办事项窗口出错: {str(e)}")
                     import traceback
                     traceback.print_exc()
                     # 显示更具体的错误消息
                     QMessageBox.critical(self, "错误", f"无法打开待办事项功能:\n{str(e)}")
                     self.statusBar.showMessage(f"打开待办事项失败")
            else:
                 self.todo_window.activateWindow()
                 self.statusBar.showMessage(f"已打开 {item.text()} 功能")
        else:
            self.statusBar.showMessage(f"'{item.text()}' 是功能占位符，尚未实现实际功能")
            QMessageBox.information(self, "功能占位符", f"'{item.text()}' 功能尚未实现。")

    # --- File Operations ---
    def new_file(self):
        # Use the imported TextEditWithLineNumbers
        editor = TextEditWithLineNumbers()
        editor.setFontPointSize(12)
        self.untitled_counter += 1
        tab_name = f"未命名-{self.untitled_counter}"
        editor.setProperty("untitled_name", tab_name)
        # No need to manually connect signals handled within TextEditWithLineNumbers
        index = self.tab_widget.addTab(editor, tab_name)
        self.tab_widget.setCurrentIndex(index)
        # Set properties directly on the editor instance
        editor.setProperty("file_path", None)
        editor.setProperty("is_new", True)
        editor.setProperty("is_pdf_converted", False)
        editor.setProperty("pdf_temp_dir", None)
        editor.document().setModified(False) # Ensure new file starts unmodified
        self.statusBar.showMessage("新建文件")
        # Update actions state for the new editor
        self.update_edit_actions_state(editor)


    def open_file_dialog(self):
         # This function remains mostly the same
         file_name, _ = QFileDialog.getOpenFileName(self, "打开文件", "", "HTML文件 (*.html);;文本文件 (*.txt);;PDF文件 (*.pdf);;所有文件 (*)")
         if file_name:
             self.open_file_from_path(file_name)

    def open_file_from_path(self, file_path):
        # This function remains mostly the same
        abs_file_path = os.path.abspath(file_path)
        # Check if file is already open
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if isinstance(widget, TextEditWithLineNumbers) and widget.property("file_path") == abs_file_path:
                self.tab_widget.setCurrentIndex(i)
                self.statusBar.showMessage(f"切换到已打开文件: {file_path}")
                return

        # Use the imported TextEditWithLineNumbers
        editor = TextEditWithLineNumbers()
        editor.setFontPointSize(12)
        try:
            _, ext = os.path.splitext(file_path)
            file_base_name = os.path.basename(file_path)

            if ext.lower() == '.pdf':
                 self.open_pdf_preview(abs_file_path)
                 # PDF preview is modal or handles its own lifecycle, don't add an editor tab here
                 return
            elif ext.lower() == '.html':
                # Use QSignalBlocker to prevent premature modification signals
                with open(abs_file_path, 'r', encoding='utf-8') as f: content = f.read()
                with QSignalBlocker(editor.document()): editor.setHtml(content)
            else: # Handle text files
                try:
                    with open(abs_file_path, 'r', encoding='utf-8') as f: content = f.read()
                except UnicodeDecodeError: # Fallback encoding
                    with open(abs_file_path, 'r', encoding='gbk') as f: content = f.read()
                # Use QSignalBlocker here as well
                with QSignalBlocker(editor.document()): editor.setPlainText(content)

            # Add the new editor as a tab
            index = self.tab_widget.addTab(editor, file_base_name)
            self.tab_widget.setCurrentIndex(index)
            editor.setProperty("file_path", abs_file_path)
            editor.setProperty("is_new", False)
            editor.setProperty("is_pdf_converted", False) # Reset PDF flag
            editor.setProperty("pdf_temp_dir", None)    # Reset temp dir
            editor.document().setModified(False) # Mark as unmodified initially
            self.statusBar.showMessage(f"已打开: {file_path}")
            self.update_edit_actions_state(editor) # Update actions for the new tab

        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开文件 '{file_path}':\n{str(e)}")
            # Clean up the tab if editor creation failed mid-way
            # Check if 'index' exists and if the widget at that index is the problematic editor
            if 'index' in locals() and index < self.tab_widget.count() and self.tab_widget.widget(index) == editor:
                 self.tab_widget.removeTab(index)
                 editor.deleteLater()


    def save_file(self) -> bool:
        # This function remains mostly the same
        editor = self.get_current_editor()
        if not editor: return False

        if editor.property("is_new") or not editor.property("file_path"):
            return self.save_file_as()
        else:
            file_path = editor.property("file_path")
            try:
                _, ext = os.path.splitext(file_path)
                # Check if saving as HTML or Plain Text based on extension
                content_to_save = editor.toHtml() if ext.lower() == '.html' else editor.toPlainText()
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content_to_save)
                editor.document().setModified(False)
                self.statusBar.showMessage(f"已保存: {file_path}")
                self.update_tab_title(False) # Update tab title immediately
                return True
            except Exception as e:
                 QMessageBox.critical(self, "错误", f"无法保存文件 '{file_path}':\n{str(e)}")
                 return False

    def save_file_as(self) -> bool:
        # This function remains mostly the same
        editor = self.get_current_editor()
        if not editor: return False

        current_path = editor.property("file_path")
        untitled_name = editor.property("untitled_name")
        # Suggest filename based on current path or untitled name
        suggested_name = os.path.basename(current_path) if current_path else (untitled_name or f"未命名-{self.untitled_counter}")

        default_dir = os.path.dirname(current_path) if current_path else ""

        # Determine default filter based on content or existing extension
        default_filter = "HTML文件 (*.html)"
        is_plain = editor.toPlainText() == editor.toHtml() # Basic check if content is likely plain text
        if current_path and os.path.splitext(current_path)[1].lower() != '.html':
             default_filter = "文本文件 (*.txt)"
        elif is_plain and not current_path: # New file that looks like plain text
             default_filter = "文本文件 (*.txt)"


        file_name, selected_filter = QFileDialog.getSaveFileName(
            self, "另存为", os.path.join(default_dir, suggested_name),
            "HTML文件 (*.html);;文本文件 (*.txt);;所有文件 (*)", default_filter
        )

        if file_name:
            abs_file_path = os.path.abspath(file_name)
            # Ensure extension based on filter if none provided
            _, current_ext = os.path.splitext(abs_file_path)
            if not current_ext:
                 abs_file_path += ".html" if "HTML" in selected_filter else ".txt"

            _, save_ext = os.path.splitext(abs_file_path)
            try:
                # Save as HTML or Plain Text based on final extension
                content_to_save = editor.toHtml() if save_ext.lower() == '.html' else editor.toPlainText()
                with open(abs_file_path, 'w', encoding='utf-8') as f:
                    f.write(content_to_save)

                # Update editor properties
                editor.setProperty("file_path", abs_file_path)
                editor.setProperty("is_new", False)
                editor.setProperty("untitled_name", None) # Clear untitled name
                editor.document().setModified(False)

                # Update tab text for the current editor
                current_index = self.tab_widget.currentIndex()
                if current_index != -1 and self.tab_widget.widget(current_index) == editor:
                     # Update tab text immediately after save as
                     self.tab_widget.setTabText(current_index, os.path.basename(abs_file_path))
                     # Explicitly call update_tab_title to ensure '*' is removed and window title updates
                     self.update_tab_title(False)

                self.statusBar.showMessage(f"已保存: {abs_file_path}")
                return True
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法保存文件 '{abs_file_path}':\n{str(e)}")
        return False

    def close_tab(self, index):
        # This function remains mostly the same, ensure cleanup happens correctly
        if index < 0 or index >= self.tab_widget.count(): return
        widget = self.tab_widget.widget(index)

        # Handle non-editor widgets (like potential future PDF viewer tabs directly)
        if not isinstance(widget, TextEditWithLineNumbers):
            self.tab_widget.removeTab(index)
            widget.deleteLater() # Ensure non-editor widgets are cleaned up
            return

        editor = widget # Now we know it's an editor
        if editor.document().isModified():
            self.tab_widget.setCurrentIndex(index) # Ensure the tab being closed is active for the dialog
            tab_name = self.tab_widget.tabText(index)
            ret = QMessageBox.warning(self, "关闭标签页", f"文档 '{tab_name}' 已被修改。\n是否保存更改？",
                                    QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
            if ret == QMessageBox.StandardButton.Save:
                if not self.save_file(): return # Don't close if save fails
            elif ret == QMessageBox.StandardButton.Cancel: return # Don't close if cancelled

        # Cleanup PDF temp files if this tab was a converted PDF
        temp_dir = editor.property("pdf_temp_dir")
        if temp_dir:
            cleanup_temp_images(temp_dir) # Use imported function

        # Safely disconnect signals before removing
        if self.previous_editor == editor: self.previous_editor = None
        try: editor.document().undoAvailable.disconnect()
        except TypeError: pass
        try: editor.document().redoAvailable.disconnect()
        except TypeError: pass
        try: editor.copyAvailable.disconnect()
        except TypeError: pass
        try: editor.document().modificationChanged.disconnect()
        except TypeError: pass

        self.tab_widget.removeTab(index)
        editor.deleteLater() # Schedule deletion

        # If the last tab was closed, create a new one
        if self.tab_widget.count() == 0:
            self.new_file()
        else:
             # Update actions state based on the potentially new current tab
             current_editor = self.get_current_editor()
             if current_editor:
                 self.update_edit_actions_state(current_editor)
             else: # No editor left after close? Should not happen if new_file is called
                 self.update_edit_actions_state(None)


    def maybe_save_all(self) -> bool:
         # This function remains mostly the same
         original_index = self.tab_widget.currentIndex()
         modified_tabs = [i for i in range(self.tab_widget.count())
                          if isinstance(w := self.tab_widget.widget(i), TextEditWithLineNumbers) and w.document().isModified()]

         if not modified_tabs: return True # No modified tabs, safe to exit

         for i in reversed(modified_tabs): # Iterate backwards for stable indices when saving
              self.tab_widget.setCurrentIndex(i) # Activate the tab
              tab_name = self.tab_widget.tabText(i)
              ret = QMessageBox.warning(self, "退出确认", f"文档 '{tab_name}' 已被修改。\n是否保存更改？",
                                        QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
              if ret == QMessageBox.StandardButton.Save:
                  if not self.save_file(): # Attempt to save
                      # Restore original index if save fails and user cancels exit
                      if original_index < self.tab_widget.count(): self.tab_widget.setCurrentIndex(original_index)
                      return False # Exit cancelled due to save failure
              elif ret == QMessageBox.StandardButton.Cancel:
                  # Restore original index if user cancels exit
                  if original_index < self.tab_widget.count(): self.tab_widget.setCurrentIndex(original_index)
                  return False # Exit cancelled by user

         # If we reach here, all saves/discards were successful or user chose discard
         # Restore a valid index if possible after potential tab closures during save
         # Need to re-check tab count as it might have changed
         current_tab_count = self.tab_widget.count()
         if current_tab_count > 0:
             # Ensure the original index is still valid within the new count
             new_index = max(0, min(original_index, current_tab_count - 1)) if original_index < current_tab_count else 0
             self.tab_widget.setCurrentIndex(new_index)
         return True # Exit approved


    # --- PDF Handling ---
    def open_pdf_preview(self, pdf_path):
        # Use the imported PDFViewer
        try:
            pdf_viewer = PDFViewer(pdf_path, self) # Use imported class
            pdf_viewer.convert_to_html_signal.connect(self.convert_pdf_to_html)
            pdf_viewer.exec() # Show as modal dialog
        except Exception as e:
             QMessageBox.critical(self, "错误", f"无法打开PDF预览: {str(e)}")


    def convert_pdf_to_html(self, pdf_path):
        # Use imported pdf_utils functions
        try:
            # Pass self (main window) as parent for potential dialogs in extract_pdf_content
            html_content, temp_dir = extract_pdf_content(pdf_path, self)
            if html_content:
                # Use imported TextEditWithLineNumbers
                editor = TextEditWithLineNumbers()
                editor.setFontPointSize(12)
                with QSignalBlocker(editor.document()): editor.setHtml(html_content)

                tab_name = f"{os.path.basename(pdf_path)} (HTML)"
                index = self.tab_widget.addTab(editor, tab_name)
                self.tab_widget.setCurrentIndex(index)

                # Set properties for the new editor tab
                editor.setProperty("file_path", None) # Converted content isn't saved yet
                editor.setProperty("is_new", True)     # Treat as a new file until saved
                editor.setProperty("is_pdf_converted", True)
                editor.setProperty("pdf_temp_dir", temp_dir) # Store temp dir for cleanup
                editor.document().setModified(False) # Start as unmodified

                self.statusBar.showMessage(f"已从PDF转换为HTML: {pdf_path}")
                self.update_edit_actions_state(editor) # Update actions
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法转换PDF文件: {str(e)}")


    # --- Formatting ---
    def change_font(self):
        # This function remains mostly the same
        if editor := self.get_current_editor():
            font, ok = QFontDialog.getFont(editor.currentFont(), self, "选择字体")
            if ok:
                editor.setCurrentFont(font)
                editor.document().setModified(True) # Mark as modified

    def change_color(self):
        # This function remains mostly the same
        if editor := self.get_current_editor():
            color = QColorDialog.getColor(editor.textColor(), self, "选择颜色")
            if color.isValid():
                editor.setTextColor(color)
                editor.document().setModified(True) # Mark as modified

    def insert_image(self):
         # This function remains mostly the same
         if editor := self.get_current_editor():
             file_name, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif)")
             if file_name:
                 try:
                     image = QImage(file_name)
                     if image.isNull():
                         QMessageBox.warning(self, "插入图片", "无法加载图片！")
                         return

                     # Basic scaling logic (can be improved)
                     max_width = editor.viewport().width() - 40 # Leave some margin
                     if image.width() > max_width:
                         image = image.scaledToWidth(max_width, Qt.TransformationMode.SmoothTransformation)

                     # Add image resource to document
                     image_url = QUrl.fromLocalFile(file_name)
                     document = editor.document()
                     # Use a unique name for the resource in case the same file is inserted multiple times
                     resource_name = f"{image_url.toString()}_{QDateTime.currentMSecsSinceEpoch()}"
                     document.addResource(QTextDocument.ResourceType.ImageResource, QUrl(resource_name), image)

                     # Insert image at cursor position using the unique resource name
                     editor.textCursor().insertImage(resource_name)
                     self.statusBar.showMessage(f"已插入图片: {os.path.basename(file_name)}")
                     editor.document().setModified(True) # Mark as modified
                 except Exception as e:
                      QMessageBox.critical(self, "插入图片错误", f"插入图片时出错: {str(e)}")
         else:
             QMessageBox.warning(self, "插入图片", "没有活动的编辑窗口！")


    # --- Find and Replace ---
    def find_text(self):
        if editor := self.get_current_editor():
            text, ok = QInputDialog.getText(self, "查找", "输入要查找的文本:", text=getattr(self, '_last_find_text', '')) # Remember last search
            if ok and text:
                 self._last_find_text = text # Store last search term
                 # Start search from current cursor or top if not found initially
                 if not editor.find(text):
                     cursor = editor.textCursor()
                     cursor.movePosition(QTextCursor.MoveOperation.Start)
                     editor.setTextCursor(cursor)
                     if not editor.find(text):
                         QMessageBox.information(self, "查找", f"未找到 '{text}'")
                     else:
                          # Scroll to ensure the found text is visible (optional)
                          editor.ensureCursorVisible()
                 else:
                      editor.ensureCursorVisible()


    def replace_text(self):
        if editor := self.get_current_editor():
            find_text, ok1 = QInputDialog.getText(self, "查找", "输入要查找的文本:", text=getattr(self, '_last_find_text', ''))
            if ok1 and find_text:
                self._last_find_text = find_text # Store search term
                replace_text, ok2 = QInputDialog.getText(self, "替换", "输入要替换的文本:", text=getattr(self, '_last_replace_text', ''))
                if ok2:
                    self._last_replace_text = replace_text # Store replace term
                    # Offer Replace All or Replace Next (Example: Replace All)
                    reply = QMessageBox.question(self, '替换', f"查找 '{find_text}' 并替换为 '{replace_text}'？\n选择 'Yes' 替换所有, 'No' 查找下一个。",
                                               QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)

                    if reply == QMessageBox.StandardButton.Cancel: return

                    if reply == QMessageBox.StandardButton.Yes: # Replace All
                        cursor = editor.textCursor()
                        cursor.movePosition(QTextCursor.MoveOperation.Start)
                        editor.setTextCursor(cursor)
                        count = 0
                        # Use QSignalBlocker for performance during bulk replace
                        # Use document's begin/end macro for better undo grouping
                        editor.document().beginMacro("Replace All")
                        while editor.find(find_text):
                             cursor = editor.textCursor()
                             # Check if the found text is exactly what we search for before replacing
                             if cursor.selectedText() == find_text:
                                  cursor.insertText(replace_text)
                                  count += 1
                             else: # If find highlights something different, stop to avoid issues
                                  break
                        editor.document().endMacro()

                        if count > 0:
                             # No need to set modified=True, endMacro handles it
                             self.statusBar.showMessage(f"已替换 {count} 处匹配项")
                        else:
                             self.statusBar.showMessage("未找到匹配项")
                    elif reply == QMessageBox.StandardButton.No: # Find Next (similar to find_text logic)
                         if not editor.find(find_text):
                             cursor = editor.textCursor()
                             cursor.movePosition(QTextCursor.MoveOperation.Start)
                             editor.setTextCursor(cursor)
                             if not editor.find(find_text):
                                 QMessageBox.information(self, "查找", f"未找到 '{find_text}'")
                             else: editor.ensureCursorVisible()
                         else: editor.ensureCursorVisible()

                    # Update actions state after potential modification
                    self.update_edit_actions_state(editor)


    # --- Help and Theme ---
    def show_about(self):
        # Consider moving this to a separate dialog class (e.g., src/ui/dialogs/about_dialog.py)
        QMessageBox.about(self, "关于多功能记事本",
                         "多功能记事本 v1.3 (重构版)\n\n一个基于PyQt6的记事本应用，支持多文件编辑、HTML、PDF预览/转换、图片插入、主题切换等。")

    def apply_current_theme(self):
        # Use the imported ThemeManager
        try:
            app = QApplication.instance()
            if not app: return # Safety check

            # Apply theme using the manager
            self.theme_manager.apply_theme(app)

            # Update components that need explicit theme refresh
            if hasattr(self, 'file_explorer') and self.file_explorer:
                 self.file_explorer.update_theme(self.theme_manager.get_current_theme())

            # Refresh editor views (line numbers, background)
            for i in range(self.tab_widget.count()):
                 widget = self.tab_widget.widget(i)
                 if isinstance(widget, TextEditWithLineNumbers):
                     # Trigger updates - these might need specific methods if `update()` isn't enough
                     widget.update_line_number_area_width() # Recalculate width based on font
                     widget.update_line_number_area()      # Repaint line numbers
                     widget.viewport().update()            # Repaint editor background/text

            theme_name = "浅色" if self.theme_manager.get_current_theme() == ThemeManager.LIGHT_THEME else "深色"
            self.statusBar.showMessage(f"已应用{theme_name}主题", 3000)
        except Exception as e:
            print(f"应用主题时出错: {str(e)}")
            # Consider showing a user-friendly error message
            # QMessageBox.warning(self, "主题错误", f"应用主题时出错:\n{str(e)}")


    def toggle_theme(self):
        # This function remains the same, relies on ThemeManager
        self.theme_manager.toggle_theme()
        self.apply_current_theme()

    # --- Application Closing ---
    def closeEvent(self, event):
        # This function remains mostly the same
        if self.maybe_save_all(): # Check if user wants to save changes
            try:
                # Cleanup temporary PDF directories before closing
                for i in range(self.tab_widget.count()):
                    widget = self.tab_widget.widget(i)
                    if isinstance(widget, TextEditWithLineNumbers):
                        if temp_dir := widget.property("pdf_temp_dir"):
                            cleanup_temp_images(temp_dir) # Use imported function
                            
                # 保存并关闭所有打开的便签
                try:
                    if hasattr(self, 'sticky_notes'):
                        # 保存所有便签数据
                        self.save_sticky_notes()
                        
                        # 然后关闭所有便签（使用副本防止迭代错误）
                        notes_to_close = list(self.sticky_notes)
                        for note in notes_to_close:
                            if note.isVisible():
                                # 断开信号连接，防止循环
                                try:
                                    note.closed.disconnect(self.on_sticky_note_closed)
                                except:
                                    pass
                                note.close()
                except Exception as e:
                    print(f"关闭便签时出错: {str(e)}")
                    
                # 关闭待办事项窗口
                try:
                    if hasattr(self, 'todo_window') and self.todo_window and self.todo_window.isVisible():
                        self.todo_window.close()
                except Exception as e:
                    print(f"关闭待办事项窗口时出错: {str(e)}")
                    
                # 关闭其他功能窗口
                for window_name in ['timer_window', 'calculator_window', 'calendar_window']:
                    try:
                        if hasattr(self, window_name):
                            window = getattr(self, window_name)
                            if window and window.isVisible():
                                window.close()
                    except Exception as e:
                        print(f"关闭 {window_name} 时出错: {str(e)}")
                            
                event.accept() # Allow closing
            except Exception as e:
                print(f"关闭应用程序时出错: {str(e)}")
                event.accept()  # 确保应用程序可以关闭
        else:
            event.ignore() # Prevent closing
            
    # 处理便签关闭事件
    def on_sticky_note_closed(self, note_id):
        """处理便签关闭事件"""
        try:
            # 从便签列表中移除已关闭的便签
            if not hasattr(self, 'sticky_notes'):
                return
                
            # 找到要移除的便签
            note_to_remove = None
            for note in self.sticky_notes:
                if hasattr(note, 'note_id') and note.note_id == note_id:
                    note_to_remove = note
                    break
                    
            # 如果找到了，从列表中移除
            if note_to_remove in self.sticky_notes:
                self.sticky_notes.remove(note_to_remove)
                
        except Exception as e:
            print(f"处理便签关闭事件出错: {str(e)}")
            
    # 加载便签数据
    def load_sticky_notes(self):
        try:
            # 确保初始化便签列表
            if not hasattr(self, 'sticky_notes'):
                self.sticky_notes = []
                
            notes_file = os.path.join("data", "notes.json")
            if not os.path.exists(notes_file):
                return
                
            with open(notes_file, "r", encoding="utf-8") as f:
                notes_data = json.load(f)
                
            # 创建便签
            for note_data in notes_data:
                try:
                    if not note_data or not isinstance(note_data, dict):
                        continue
                        
                    # 检查必要的字段是否存在
                    if "id" not in note_data:
                        continue
                        
                    sticky_note = StickyNote(
                        note_id=note_data.get("id"),
                        content=note_data.get("content", ""),
                        color=note_data.get("color", "#ffff99"),
                        geometry=note_data.get("geometry"),
                        parent=self
                    )
                    
                    # 安全地连接信号
                    try:
                        sticky_note.closed.connect(self.on_sticky_note_closed)
                    except Exception:
                        pass
                        
                    self.sticky_notes.append(sticky_note)
                except Exception as e:
                    print(f"创建便签时出错: {str(e)}")
                    continue
                    
            return True
        except Exception as e:
            print(f"加载便签失败: {str(e)}")
            # 不向用户显示错误消息，避免干扰用户体验
            # QMessageBox.warning(self, "加载便签失败", f"无法加载便签: {str(e)}")
            return False
    
    # 保存便签数据
    def save_sticky_notes(self):
        try:
            notes_data = []
            
            # 收集所有便签数据
            if hasattr(self, 'sticky_notes') and self.sticky_notes:
                for note in list(self.sticky_notes):
                    try:
                        if note and note.isVisible():  # 确保便签有效且可见
                            notes_data.append(note.get_data())
                    except Exception as e:
                        print(f"获取便签数据时出错: {str(e)}")
                        continue
            
            # 确保目录存在
            os.makedirs("data", exist_ok=True)
            
            # 写入文件
            with open(os.path.join("data", "notes.json"), "w", encoding="utf-8") as f:
                json.dump(notes_data, f, indent=2, ensure_ascii=False)
                
            return True
        except Exception as e:
            print(f"保存便签失败: {str(e)}")
            # 不向用户显示错误消息，避免干扰用户体验
            # QMessageBox.warning(self, "保存便签失败", f"无法保存便签: {str(e)}")
            return False

# Notes for further refactoring (optional):
# - Consider moving Action/Menu/Toolbar creation into separate methods or classes.
# - File operations (new, open, save, save_as) could potentially move to a dedicated service class (e.g., FileService).
# - Error handling could be centralized or improved.
# - Signal connections could be managed more systematically.
# Need QDateTime for unique image resource names
from PyQt6.QtCore import QDateTime
