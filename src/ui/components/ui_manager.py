import os
from PyQt6.QtWidgets import QDockWidget, QMessageBox, QWidget, QTabWidget, QApplication
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, pyqtSlot, QUrl
from PyQt6.QtGui import QIcon, QColor
import shutil # Added for cleaning up resource directory

# --- Corrected Relative Imports ---
from ..composite.combined_tools import CombinedTools
from ..atomic.mini_tools.calculator_widget import CalculatorWidget
from ..atomic.mini_tools.timer_widget import TimerWidget
from ..atomic.mini_tools.speech_recognition_widget import SpeechRecognitionWidget
from ..views.note_downloader_view import NoteDownloaderView
from ..views.pdf_viewer_view import PdfViewerView # This is the QWebEngineView based one
from ..dialogs.pdf_action_dialog import PdfActionChoiceDialog # For PDF action choices
from ...utils import pdf_utils # For extract_pdf_content
# Import BaseWidget for type checking if needed
from ..core.base_widget import BaseWidget
# Import editor types for checking
from ..atomic.editor.text_editor import TextEditor
from ..atomic.editor.html_editor import HtmlEditor
from ..atomic.markdown_editor_widget import MarkdownEditorWidget
# Import ThemeManager if needed directly
from ..core.theme_manager import ThemeManager
from ..composite.editor_group_widget import EditorGroupWidget # Added

# --- Worker for PDF to HTML conversion ---
class PdfToHtmlWorkerForUIManager(QObject):
    # Signal now emits: pdf_path, full_html_file_path, resource_base_dir_path
    conversion_finished = pyqtSignal(str, str, str) 
    conversion_error = pyqtSignal(str, str)    # error_title, error_message

    def __init__(self, pdf_path):
        super().__init__()
        self.pdf_path = pdf_path

    @pyqtSlot()
    def run(self):
        try:
            # extract_pdf_content now returns (full_html_path, temp_dir_path)
            full_html_path, resource_base_dir_path = pdf_utils.extract_pdf_content(self.pdf_path)
            self.conversion_finished.emit(self.pdf_path, full_html_path, resource_base_dir_path)
        except FileNotFoundError as e:
            self.conversion_error.emit("文件错误", str(e))
        except RuntimeError as e:
            self.conversion_error.emit("HTML 转换失败", str(e))
        except Exception as e:
            self.conversion_error.emit("未知转换错误", f"转换过程中发生意外错误: {e}")

class UIManager(QObject): # Inherit from QObject
    """处理MainWindow的UI管理功能，包括主题应用、视图/编辑器管理和工具窗口管理"""
    
    def __init__(self, main_window):
        super().__init__(main_window) # Call QObject constructor, parent to main_window
        self.main_window = main_window
        self.tab_widget = None 
        self.theme_manager = ThemeManager() 
        self.registered_views = {} 
        self.view_instances = {} 
        self.view_docks = {} 
        self.active_editor_group: EditorGroupWidget | None = None
        
        self.pdf_conversion_thread = None 
        self.pdf_conversion_worker = None
        self.pdf_conversion_resource_dirs = {} # pdf_path: resource_dir_path

    def apply_current_theme(self):
        """应用当前主题和缩放级别到UI组件"""
        base_style_sheet = self.theme_manager.get_current_style_sheet()
        if not base_style_sheet: 
            print("警告: 未能加载基础样式表，无法应用主题。")
            return

        effective_font_size = self.main_window.base_font_size_pt * self.main_window.current_zoom_factor
        effective_font_size = max(1.0, effective_font_size)
        
        font_rules_str = (
            f"QWidget {{ font-size: {effective_font_size:.1f}pt; }}\n"
            f"QToolButton {{ font-size: {effective_font_size:.1f}pt; }}\n"
            f"QMenu {{ font-size: {effective_font_size:.1f}pt; }}\n"
            f"QMenuBar {{ font-size: {effective_font_size:.1f}pt; }}\n"
            f"QStatusBar {{ font-size: {effective_font_size:.1f}pt; }}\n"
            f"QTreeView {{ font-size: {effective_font_size:.1f}pt; }}\n"
            f"QTreeView::item {{ font-size: {effective_font_size:.1f}pt; }}\n"
            f"QListWidget {{ font-size: {effective_font_size:.1f}pt; }}\n"
            f"QListWidget::item {{ font-size: {effective_font_size:.1f}pt; }}\n"
            f"QToolBar#ActivityBarToolBar QToolButton {{ font-size: {effective_font_size:.1f}pt; }}\n"
        )
        
        dock_widget_style = """
            QDockWidget { border: 1px solid #A9A9A9; }
            QSplitter::handle { background-color: #D3D3D3; border: 1px solid #A9A9A9; }
            QSplitter::handle:hover { background-color: #BEBEBE; }
        """
        
        style_sheet_with_zoom = font_rules_str + base_style_sheet
        final_style_sheet = style_sheet_with_zoom + dock_widget_style
        self.main_window.setStyleSheet(final_style_sheet)

        from PyQt6.QtGui import QFont
        from PyQt6.QtWidgets import QToolButton, QTreeView

        if hasattr(self.main_window, 'file_explorer') and self.main_window.file_explorer:
            try:
                current_tree_font = self.main_window.file_explorer.font()
                current_tree_font.setPointSizeF(effective_font_size)
                self.main_window.file_explorer.setFont(current_tree_font)
            except Exception as e:
                print(f"Error setting font programmatically for FileExplorer: {e}")

        if hasattr(self.main_window, 'activity_bar_toolbar') and self.main_window.activity_bar_toolbar:
            toolbar = self.main_window.activity_bar_toolbar
            original_toolbar_width_design = 60 
            width_scale_factor = 1.0
            if self.main_window.base_font_size_pt > 0:
                width_scale_factor = effective_font_size / self.main_window.base_font_size_pt
            scaled_toolbar_width = int(round(original_toolbar_width_design * width_scale_factor))
            min_toolbar_width, max_toolbar_width = 40, 150
            scaled_toolbar_width = max(min_toolbar_width, min(scaled_toolbar_width, max_toolbar_width))
            toolbar.setFixedWidth(scaled_toolbar_width)
            try:
                current_toolbar_font = toolbar.font()
                current_toolbar_font.setPointSizeF(effective_font_size)
                toolbar.setFont(current_toolbar_font)
                activity_buttons = toolbar.findChildren(QToolButton)
                for button in activity_buttons:
                    new_font = QFont(button.font().family()) 
                    new_font.setPointSizeF(effective_font_size)
                    button.setFont(new_font)
                    button.updateGeometry()
            except Exception as e:
                print(f"Error setting font programmatically for Activity Bar buttons: {e}")

        if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar:
            status_bar = self.main_window.statusBar
            try:
                current_msg = status_bar.currentMessage()
                current_statusbar_font = status_bar.font()
                new_statusbar_font = QFont(current_statusbar_font)
                new_statusbar_font.setPointSizeF(effective_font_size)
                status_bar.setFont(new_statusbar_font)
                if current_msg: status_bar.showMessage(current_msg) 
                else: status_bar.repaint()
                status_bar.adjustSize()
                if status_bar.layout(): status_bar.layout().activate()
            except Exception as e:
                print(f"Error setting font programmatically for StatusBar: {e}")
        
        is_dark = self.theme_manager.is_dark_theme()
        if hasattr(self.main_window, 'sidebar_dock') and hasattr(self.main_window.sidebar_dock.widget(), 'update_styles'):
            self.main_window.sidebar_dock.widget().update_styles(is_dark)
        
        if self.tab_widget:
            for i in range(self.tab_widget.count()):
                widget_in_tab = self.tab_widget.widget(i)
                editor_text_color = QColor("#D4D4D4") if is_dark else QColor("#000000")
                editor_bg_color = QColor("#1E1E1E") if is_dark else QColor("#FFFFFF")
                border_color = QColor("#333333") if is_dark else QColor("#D0D0D0")
                current_line_bg = QColor("#3A3D41") if is_dark else QColor(Qt.GlobalColor.yellow).lighter(160)
                preview_bg_color = QColor("#252526") if is_dark else QColor("#FFFFFF")

                if isinstance(widget_in_tab, MarkdownEditorWidget):
                    widget_in_tab.set_preview_background_color(preview_bg_color)
                    if hasattr(widget_in_tab, 'update_editor_theme_colors'):
                        widget_in_tab.update_editor_theme_colors(editor_text_color, editor_bg_color, border_color, current_line_bg)
                elif isinstance(widget_in_tab, HtmlEditor):
                    if hasattr(widget_in_tab, 'update_editor_theme_colors'):
                         widget_in_tab.update_editor_theme_colors(editor_text_color, editor_bg_color, border_color, current_line_bg)
                elif isinstance(widget_in_tab, TextEditor):
                    if hasattr(widget_in_tab, 'update_colors'):
                        widget_in_tab.update_colors(is_dark)
                elif hasattr(widget_in_tab, 'update_styles'): 
                    widget_in_tab.update_styles(is_dark)

        current_theme_name = "暗色" if is_dark else "亮色"
        if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar:
            self.main_window.statusBar.showMessage(f"已应用{current_theme_name}主题")

    def toggle_theme(self):
        self.theme_manager.toggle_theme()
        self.apply_current_theme()
        if hasattr(self.main_window, 'theme_changed'):
             self.main_window.theme_changed.emit(self.theme_manager.is_dark_theme())

    def open_note_downloader_tab(self):
        self.open_view(view_name="NoteDownloader")
    
    def open_pdf_preview(self, pdf_path: str):
        try:
            abs_pdf_path = os.path.abspath(pdf_path)
            dialog = PdfActionChoiceDialog(abs_pdf_path, self.main_window)
            choice = dialog.exec()

            if choice == PdfActionChoiceDialog.PREVIEW_AS_PDF_IN_TAB:
                pdf_viewer_tab_widget = PdfViewerView(self.main_window) 
                if pdf_viewer_tab_widget.load_pdf(abs_pdf_path):
                    tab_name = os.path.basename(abs_pdf_path)
                    
                    current_tab_widget = self.tab_widget
                    if not current_tab_widget and hasattr(self.main_window, 'tab_widget') and self.main_window.tab_widget:
                        current_tab_widget = self.main_window.tab_widget
                        self.tab_widget = current_tab_widget 

                    if not current_tab_widget:
                        QMessageBox.critical(self.main_window, "错误", "标签页管理器未能正确初始化或访问。")
                        pdf_viewer_tab_widget.deleteLater()
                        return
                        
                    index = current_tab_widget.addTab(pdf_viewer_tab_widget, tab_name)
                    current_tab_widget.setCurrentIndex(index)
                    pdf_viewer_tab_widget.setProperty("file_path", abs_pdf_path) 
                    pdf_viewer_tab_widget.setFocus()
                    if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar:
                        self.main_window.statusBar.showMessage(f"已打开 PDF 预览: {pdf_path}")
                else:
                    pdf_viewer_tab_widget.deleteLater()

            elif choice == PdfActionChoiceDialog.CONVERT_TO_HTML_SOURCE:
                self._start_pdf_to_html_conversion(abs_pdf_path)
            
        except Exception as e:
            QMessageBox.critical(self.main_window, "错误", f"处理 PDF 文件时出错: {e}")
            import traceback
            traceback.print_exc()

    def _start_pdf_to_html_conversion(self, pdf_path: str):
        if hasattr(self, 'pdf_conversion_thread') and self.pdf_conversion_thread and self.pdf_conversion_thread.isRunning():
            self.pdf_conversion_thread.quit()
            self.pdf_conversion_thread.wait(1000) 
        
        self.pdf_conversion_thread = QThread(self.main_window) 
        self.pdf_conversion_worker = PdfToHtmlWorkerForUIManager(pdf_path)
        self.pdf_conversion_worker.moveToThread(self.pdf_conversion_thread)

        self.pdf_conversion_worker.conversion_finished.connect(self._on_pdf_to_html_conversion_finished)
        self.pdf_conversion_worker.conversion_error.connect(self._on_pdf_to_html_conversion_error)
        
        self.pdf_conversion_thread.started.connect(self.pdf_conversion_worker.run)
        self.pdf_conversion_thread.finished.connect(self.pdf_conversion_worker.deleteLater)
        self.pdf_conversion_thread.finished.connect(self.pdf_conversion_thread.deleteLater)
        self.pdf_conversion_thread.finished.connect(self._clear_conversion_refs)

        if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar:
            self.main_window.statusBar.showMessage(f"正在转换 '{os.path.basename(pdf_path)}' 为 HTML...")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.pdf_conversion_thread.start()

    @pyqtSlot(str, str, str) # pdf_path, full_html_file_path, resource_base_dir_path
    def _on_pdf_to_html_conversion_finished(self, pdf_path: str, full_html_file_path: str, resource_base_dir_path: str):
        QApplication.restoreOverrideCursor()
        status_bar = getattr(self.main_window, 'statusBar', None)
        if status_bar:
            status_bar.showMessage(f"'{os.path.basename(pdf_path)}' 已成功转换为 HTML。", 5000)

        if not full_html_file_path or not os.path.exists(full_html_file_path):
            QMessageBox.warning(self.main_window, "警告", f"PDF转换后的HTML文件未找到或无效: {full_html_file_path}")
            self._clear_conversion_refs()
            if resource_base_dir_path and os.path.isdir(resource_base_dir_path):
                try:
                    shutil.rmtree(resource_base_dir_path)
                    print(f"DEBUG UIManager: Cleaned up resource dir {resource_base_dir_path} due to missing HTML file.")
                except Exception as e_shutil:
                    print(f"DEBUG UIManager: Error cleaning up resource dir {resource_base_dir_path}: {e_shutil}")
            return

        # Store the resource directory path for later cleanup when the tab is closed
        self.pdf_conversion_resource_dirs[pdf_path] = resource_base_dir_path
        
        base_name = os.path.basename(pdf_path)
        untitled_name = f"{os.path.splitext(base_name)[0]}.html (预览)"

        # Import HtmlViewContainer
        from ..composite.html_view_container import HtmlViewContainer
        
        try:
            # Read the content of the generated HTML file
            html_content_for_container = ""
            try:
                with open(full_html_file_path, 'r', encoding='utf-8') as f_html:
                    html_content_for_container = f_html.read()
            except Exception as e_read:
                QMessageBox.critical(self.main_window, "错误", f"无法读取转换后的HTML文件内容: {full_html_file_path}\n{e_read}")
                if resource_base_dir_path and os.path.isdir(resource_base_dir_path):
                    shutil.rmtree(resource_base_dir_path)
                self._clear_conversion_refs()
                return

            target_tab_widget = self.tab_widget
            if not target_tab_widget and hasattr(self.main_window, 'tab_widget') and self.main_window.tab_widget:
                target_tab_widget = self.main_window.tab_widget
            
            if not target_tab_widget:
                QMessageBox.critical(self.main_window, "错误", "标签页管理器未能正确初始化或访问。")
                self._clear_conversion_refs()
                if resource_base_dir_path and os.path.isdir(resource_base_dir_path): 
                    shutil.rmtree(resource_base_dir_path)
                return
            
            # Create HtmlViewContainer instead of EditableHtmlPreviewWidget directly
            # Treat it as an "existing" file (is_new_file=False) so it loads from file_path in preview mode
            # The file_path here is the temporary HTML file from PDF conversion.
            html_viewer_container = HtmlViewContainer(parent=self.main_window,
                                                      file_path=full_html_file_path,
                                                      initial_content=html_content_for_container,
                                                      is_new_file=False, # So it loads from file_path
                                                      main_window_ref=self.main_window)
            
            # HtmlViewContainer's __init__ for is_new_file=False should call:
            # self.preview_widget.load(QUrl.fromLocalFile(self.file_path))
            # So, no explicit load() call needed here on html_viewer_container.preview_widget
            
            html_viewer_container.setProperty("is_new", True) # Still mark as "new" in terms of not being a user-saved file
            html_viewer_container.setProperty("untitled_name", untitled_name)
            html_viewer_container.setProperty("pdf_source_path", pdf_path) # Store original PDF path
            # The resource_dir_path is implicitly handled by loading the HTML file from that dir.
            # However, we still need to pass it for cleanup if HtmlViewContainer doesn't manage it.
            # Let's assume HtmlViewContainer's internal preview_widget needs this for cleanup if it's special.
            # For now, UIManager tracks pdf_conversion_resource_dirs for cleanup.
            # If HtmlViewContainer's tab is closed, FileOperations.close_tab needs to know if it's a PDF-converted HTML.
            # We can set a property on HtmlViewContainer itself.
            html_viewer_container.setProperty("resource_dir_path", resource_base_dir_path)


            index = target_tab_widget.addTab(html_viewer_container, untitled_name)
            target_tab_widget.setCurrentIndex(index)
            html_viewer_container.setFocus() # HtmlViewContainer will delegate focus
            
            # HtmlViewContainer's __init__ (for is_new_file=False) calls on_editor_content_changed
            # for its preview_widget. If we need to signal for the container itself:
            if hasattr(self.main_window, 'on_editor_content_changed'):
                 from PyQt6.QtCore import QTimer
                 # Signal for the container, initially not modified.
                 QTimer.singleShot(0, lambda ed=html_viewer_container: self.main_window.on_editor_content_changed(ed, initially_modified=False))

        except Exception as e:
            QMessageBox.critical(self.main_window, "错误", f"创建HTML预览容器时出错: {e}")
            if resource_base_dir_path and os.path.isdir(resource_base_dir_path): # Cleanup on error
                shutil.rmtree(resource_base_dir_path)
        
        self._clear_conversion_refs()

    @pyqtSlot(str, str)
    def _on_pdf_to_html_conversion_error(self, title: str, error_message: str):
        QApplication.restoreOverrideCursor()
        status_bar = getattr(self.main_window, 'statusBar', None)
        if status_bar:
            status_bar.showMessage(f"HTML 转换失败: {title}", 5000)
        QMessageBox.critical(self.main_window, title, error_message)
        self._clear_conversion_refs()
        # Note: resource_base_dir_path is not available here to clean up,
        # as it's only passed on success. The converter should handle its own temp dir on error.

    def _clear_conversion_refs(self):
        self.pdf_conversion_worker = None
        self.pdf_conversion_thread = None
    
    def _handle_pdf_html_generated(self, pdf_path: str, html_content: str):
        pass
    
    def sidebar_item_clicked(self, item):
        item_text = item.text()
        view_map = {
            "计时器": "Timer", "便签与待办": "CombinedNotes", 
            "计算器": "Calculator", "日历": "Calendar",
            "笔记下载": "NoteDownloader", "语音识别": "SpeechRecognition",
        }
        view_name_to_open = view_map.get(item_text)

        if view_name_to_open:
             self.open_view(view_name=view_name_to_open, open_in_dock=True)
             if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar:
                  self.main_window.statusBar.showMessage(f"已打开/切换到 {item_text}")
        else:
             QMessageBox.information(self.main_window, "功能占位符", f"'{item_text}' 功能尚未实现或注册。")

    def convert_pdf_to_html_wrapper(self, pdf_path: str): 
         self._start_pdf_to_html_conversion(pdf_path) 
    
    def convert_pdf_to_html(self, pdf_path: str): 
        self._start_pdf_to_html_conversion(pdf_path)

    def create_tab_widget(self):
         try:
             new_tab_widget = QTabWidget()
             if new_tab_widget:
                 self.tab_widget = new_tab_widget
                 self.tab_widget.setDocumentMode(True)
                 self.tab_widget.setTabsClosable(True)
                 self.tab_widget.setMovable(True)
                 if hasattr(self.main_window, 'file_operations'):
                      self.tab_widget.tabCloseRequested.connect(self.main_window.file_operations.close_tab)
                 self.main_window.tab_widget = self.tab_widget
             else:
                 self.tab_widget = None 
                 self.main_window.tab_widget = None
         except Exception as e:
             print(f"UIManager: EXCEPTION during QTabWidget creation: {e}")
             self.tab_widget = None
             self.main_window.tab_widget = None

    def register_view(self, view_class: type[BaseWidget], view_name: str, icon_name: str | None = None):
         print(f"DEBUG UIManager.register_view: Attempting to register '{view_name}' with class {view_class.__name__}")
         if view_name in self.registered_views:
             print(f"警告: 视图 '{view_name}' 已注册。将被覆盖。")
         self.registered_views[view_name] = {"class": view_class, "icon": icon_name}
         print(f"视图已注册: {view_name} (Class: {view_class.__name__}), Total registered: {len(self.registered_views)}")

    def open_view(self, view_name: str, open_in_dock: bool = False, open_in_tool_box: bool = False, bring_to_front: bool = True):
        if view_name not in self.registered_views:
            QMessageBox.warning(self.main_window, "视图未注册", f"视图 '{view_name}' 未找到或未注册。")
            return None

        view_info = self.registered_views[view_name]
        view_class = view_info["class"]
        icon_name = view_info["icon"]
        icon = QIcon.fromTheme(icon_name) if icon_name else QIcon()
        instance = self.view_instances.get(view_name)

        if open_in_tool_box:
            if not hasattr(self.main_window, 'tool_box_widget') or not self.main_window.tool_box_widget:
                QMessageBox.critical(self.main_window, "错误", "底部工具箱未初始化。")
                return None
            
            tool_box = self.main_window.tool_box_widget
            for i in range(tool_box.count()):
                if tool_box.widget(i) == instance and instance is not None: 
                    if bring_to_front: tool_box.setCurrentIndex(i)
                    tool_box.show() 
                    instance.show() 
                    return instance
            try:
                if instance is None: 
                    if view_name == "NoteDownloader" and hasattr(self.main_window, 'note_downloader_panel'):
                        instance = self.main_window.note_downloader_panel
                        if view_name not in self.view_instances or self.view_instances[view_name] != instance:
                             self.view_instances[view_name] = instance
                    else:
                        instance = view_class(self.main_window)
                        self.view_instances[view_name] = instance
                
                if hasattr(instance, 'show') and callable(instance.show):
                    instance.show()

                index = tool_box.addTab(instance, icon, view_name) 
                if bring_to_front: 
                    tool_box.setCurrentIndex(index)
                
                if not tool_box.isVisible(): 
                    tool_box.show()
                return instance
            except Exception as e:
                QMessageBox.critical(self.main_window, "打开工具错误", f"在工具箱中创建视图 '{view_name}' 时出错: {e}")
                return None

        elif open_in_dock:
            dock = self.view_docks.get(view_name)
            instance_to_use = instance 

            if view_name == "NoteDownloader":
                if hasattr(self.main_window, 'note_downloader_view_content') and self.main_window.note_downloader_view_content:
                    instance_to_use = self.main_window.note_downloader_view_content
                    if view_name not in self.view_instances or self.view_instances[view_name] != instance_to_use:
                        self.view_instances[view_name] = instance_to_use
                else:
                    QMessageBox.critical(self.main_window, "错误", "NoteDownloader 内容视图未初始化。")
                    return None
            
            if instance_to_use and (not dock or dock.widget() != instance_to_use):
                if dock: 
                    if view_name == "NoteDownloader" and dock.widget() == self.main_window.note_downloader_panel:
                        pass 
                    
                    current_widget_in_dock = dock.widget()
                    dock.setWidget(None) 
                    if current_widget_in_dock and current_widget_in_dock != self.main_window.note_downloader_view_content:
                        pass

                    dock.deleteLater()
                    if view_name in self.view_docks: 
                        del self.view_docks[view_name]
                dock = None 

            if dock and dock.widget() == instance_to_use and instance_to_use is not None:
                if bring_to_front:
                    dock.show()
                    dock.raise_()
                return dock 
            
            try:
                if instance_to_use is None: 
                    instance_to_use = view_class(self.main_window)
                    self.view_instances[view_name] = instance_to_use

                dock = QDockWidget(view_name, self.main_window)
                dock.setObjectName(f"{view_name}Dock")
                dock.setWidget(instance_to_use) 
                dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
                self.main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock) 
                self.view_docks[view_name] = dock
                
                dock.visibilityChanged.connect(
                    lambda visible, vn=view_name: self._handle_dock_visibility_change(vn, visible)
                )

                for existing_dock_name, existing_dock_obj in self.view_docks.items():
                    if existing_dock_obj != dock and self.main_window.dockWidgetArea(existing_dock_obj) == self.main_window.dockWidgetArea(dock):
                        self.main_window.tabifyDockWidget(existing_dock_obj, dock)
                        break 
                
                if bring_to_front:
                    dock.show()
                    dock.raise_()
                
                if view_name == "NoteDownloader":
                    try:
                        if hasattr(self.main_window, 'width') and callable(self.main_window.width):
                            main_window_width = self.main_window.width()
                            if main_window_width > 0:
                                desired_width = int(main_window_width * 0.45) 
                                
                                if instance_to_use and hasattr(instance_to_use, 'setMinimumWidth'):
                                    instance_to_use.setMinimumWidth(desired_width)
                                    print(f"NoteDownloader content widget minimum width set to {desired_width}px.")
                                self.main_window.resizeDocks([dock], [desired_width], Qt.Orientation.Horizontal)
                                print(f"NoteDownloader dock '{view_name}' resize attempted to {desired_width}px width (45% of main window).")
                            else:
                                print(f"NoteDownloader dock '{view_name}' not resized: main_window width is not positive.")
                        else:
                             print(f"NoteDownloader dock '{view_name}' not resized: main_window has no width method or it's not callable.")
                    except Exception as e_resize:
                        print(f"Error trying to resize NoteDownloader dock '{view_name}': {e_resize}")
                        
                return dock 
            except Exception as e:
                QMessageBox.critical(self.main_window, "打开视图错误", f"创建停靠视图 '{view_name}' 时出错: {e}")
                import traceback
                traceback.print_exc()
                return None
        else: 
            QMessageBox.information(self.main_window, "提示", f"视图 '{view_name}' 通常在工具箱或作为可停靠窗口打开。")
            return None

    def _handle_dock_visibility_change(self, view_name: str, visible: bool):
        if not visible: 
            if hasattr(self.main_window, 'activity_view_buttons'):
                button = self.main_window.activity_view_buttons.get(view_name)
                if button and button.isChecked():
                    button.setChecked(False) 

    def close_dock_view(self, view_name: str):
        dock = self.view_docks.get(view_name)
        if dock:
            dock.hide() 
        
    def close_view_in_tool_box(self, view_name: str):
        if not hasattr(self.main_window, 'tool_box_widget') or not self.main_window.tool_box_widget:
            return

        tool_box = self.main_window.tool_box_widget
        instance_to_find = None
        if view_name == "NoteDownloader":
            instance_to_find = getattr(self.main_window, 'note_downloader_panel', None)
        else:
            instance_to_find = self.view_instances.get(view_name)

        if not instance_to_find:
            return 

        for i in range(tool_box.count()):
            widget_in_tab = tool_box.widget(i)
            if widget_in_tab == instance_to_find:
                tool_box.removeTab(i)
                if view_name != "NoteDownloader" and view_name in self.view_instances:
                    pass 
                break
        
        if tool_box.count() == 0 and tool_box.isVisible():
             tool_box.hide() 


    def is_widget_editor(self, widget: QWidget | None) -> bool:
        if widget is None: return False
        from PyQt6.QtWidgets import QPlainTextEdit 
        from ..atomic.editor.text_editor import _InternalTextEdit
        return isinstance(widget, (_InternalTextEdit, QPlainTextEdit))

    def is_widget_html_editor(self, widget: QWidget | None) -> bool:
         if widget is None: return False
         return isinstance(widget, HtmlEditor)

    def get_widget_base_name(self, widget: QWidget | None) -> str | None:
         actual_content_widget = widget
         if isinstance(widget, EditorGroupWidget): 
             actual_content_widget = widget.current_widget() 
         
         if not actual_content_widget: return None
         
         file_path = actual_content_widget.property("file_path")
         if file_path: return os.path.basename(file_path)
         untitled_name = widget.property("untitled_name")
         if untitled_name: return untitled_name
         if hasattr(widget, 'windowTitle') and callable(widget.windowTitle): return widget.windowTitle()
         return widget.__class__.__name__

    def is_file_open(self, file_path: str) -> bool:
        abs_file_path = os.path.abspath(file_path)
        if hasattr(self.main_window, 'root_editor_area') and self.main_window.root_editor_area:
            for group in self.main_window.root_editor_area.editor_groups:
                tab_widget = group.get_tab_widget()
                for i in range(tab_widget.count()):
                    widget_in_tab = tab_widget.widget(i) 
                    editor_path = widget_in_tab.property("file_path")
                    if editor_path and os.path.abspath(editor_path) == abs_file_path:
                        return True
        elif self.tab_widget: 
            for i in range(self.tab_widget.count()):
                widget = self.tab_widget.widget(i)
                editor_path = widget.property("file_path")
                if editor_path and os.path.abspath(editor_path) == abs_file_path:
                    return True
        return False

    def focus_tab_by_filepath(self, file_path: str):
        abs_file_path = os.path.abspath(file_path)
        if hasattr(self.main_window, 'root_editor_area') and self.main_window.root_editor_area:
            for group in self.main_window.root_editor_area.editor_groups:
                tab_widget = group.get_tab_widget()
                for i in range(tab_widget.count()):
                    widget_in_tab = tab_widget.widget(i)
                    editor_path = widget_in_tab.property("file_path")
                    if editor_path and os.path.abspath(editor_path) == abs_file_path:
                        self.set_active_editor_group(group) 
                        group.get_tab_widget().setCurrentIndex(i)
                        if hasattr(self.main_window, 'root_editor_area'):
                           self.main_window.root_editor_area.activateWindow() 
                        widget_in_tab.setFocus()
                        return
        elif self.tab_widget:
             for i in range(self.tab_widget.count()):
                widget = self.tab_widget.widget(i)
                editor_path = widget.property("file_path")
                if editor_path and os.path.abspath(editor_path) == abs_file_path:
                    self.tab_widget.setCurrentIndex(i)
                    widget.setFocus()
                    break
                    
    def register_speech_recognition(self):
        self.register_view(SpeechRecognitionWidget, "SpeechRecognition", "microphone")

    def set_active_editor_group(self, group: EditorGroupWidget | None):
        self.active_editor_group = group
        if group: 
            self.tab_widget = group.get_tab_widget()
            if hasattr(self.main_window, 'tab_widget'):
                self.main_window.tab_widget = self.tab_widget

    def get_active_editor_group(self) -> EditorGroupWidget | None:
        if self.active_editor_group and self.active_editor_group.isVisible() and self.active_editor_group.count() > 0:
            return self.active_editor_group
        
        if hasattr(self.main_window, 'root_editor_area') and self.main_window.root_editor_area:
            active_group_from_root = self.main_window.root_editor_area.get_active_editor_group()
            if active_group_from_root:
                self.set_active_editor_group(active_group_from_root) 
                return active_group_from_root
        
        return None
