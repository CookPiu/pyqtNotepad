import os
from PyQt6.QtWidgets import QDockWidget, QMessageBox, QWidget, QTabWidget, QApplication
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, pyqtSlot, QUrl
from PyQt6.QtGui import QIcon, QColor

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

# --- Worker for PDF to HTML conversion ---
class PdfToHtmlWorkerForUIManager(QObject): # Worker is already a QObject
    conversion_finished = pyqtSignal(str, str) # pdf_path, html_content
    conversion_error = pyqtSignal(str, str)    # error_title, error_message

    def __init__(self, pdf_path):
        super().__init__()
        self.pdf_path = pdf_path

    @pyqtSlot()
    def run(self):
        try:
            html_content = pdf_utils.extract_pdf_content(self.pdf_path)
            self.conversion_finished.emit(self.pdf_path, html_content)
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
        
        self.pdf_conversion_thread = None 
        self.pdf_conversion_worker = None 
        
        self.register_speech_recognition()
        self.register_view(NoteDownloaderView, "NoteDownloader") 
        self.register_view(CalculatorWidget, "计算器")
        self.register_view(TimerWidget, "计时器")
    
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
                    if not self.tab_widget:
                        QMessageBox.critical(self.main_window, "错误", "标签页管理器未初始化。")
                        pdf_viewer_tab_widget.deleteLater()
                        return
                    index = self.tab_widget.addTab(pdf_viewer_tab_widget, tab_name)
                    self.tab_widget.setCurrentIndex(index)
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

    @pyqtSlot(str, str)
    def _on_pdf_to_html_conversion_finished(self, pdf_path: str, html_content: str):
        QApplication.restoreOverrideCursor()
        status_bar = getattr(self.main_window, 'statusBar', None)
        if status_bar:
            status_bar.showMessage(f"'{os.path.basename(pdf_path)}' 已成功转换为 HTML。", 5000)

        if not html_content:
            QMessageBox.warning(self.main_window, "警告", "从 PDF 提取的 HTML 内容为空。")
            self._clear_conversion_refs()
            return

        base_name = os.path.basename(pdf_path)
        untitled_name = f"{os.path.splitext(base_name)[0]}.html (源码)"

        file_ops = getattr(self.main_window, 'file_operations', None)
        if file_ops:
            file_ops.add_editor_tab(
                content=html_content,
                file_path=None, 
                file_type='html',
                set_current=True,
                untitled_name=untitled_name
            )
        else:
            QMessageBox.critical(self.main_window, "内部错误", "FileOperations 未初始化。")
        
        self._clear_conversion_refs()

    @pyqtSlot(str, str)
    def _on_pdf_to_html_conversion_error(self, title: str, error_message: str):
        QApplication.restoreOverrideCursor()
        status_bar = getattr(self.main_window, 'statusBar', None)
        if status_bar:
            status_bar.showMessage(f"HTML 转换失败: {title}", 5000)
        QMessageBox.critical(self.main_window, title, error_message)
        self._clear_conversion_refs()

    def _clear_conversion_refs(self):
        self.pdf_conversion_worker = None
        self.pdf_conversion_thread = None
    
    # _handle_pdf_html_generated is effectively replaced by the threaded conversion logic above.
    # If it was connected to any signals, those connections should be reviewed.
    # For now, commenting out its old content.
    def _handle_pdf_html_generated(self, pdf_path: str, html_content: str):
        """
        DEPRECATED: This method's functionality is now handled by 
        _start_pdf_to_html_conversion and its connected slots.
        """
        # print("DEPRECATED: _handle_pdf_html_generated called. This logic should be reviewed.")
        # If this is still called, it means an old signal connection might exist.
        # The new PdfViewerView (QWebEngineView based) does not emit htmlGenerated.
        # The PdfActionChoiceDialog triggers the new threaded conversion.
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

    def convert_pdf_to_html_wrapper(self, pdf_path: str): # This might be called from a menu?
         self._start_pdf_to_html_conversion(pdf_path) # Use the threaded version
    
    def convert_pdf_to_html(self, pdf_path: str): # Direct call, also use threaded version
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
         if view_name in self.registered_views:
             print(f"警告: 视图 '{view_name}' 已注册。将被覆盖。")
         self.registered_views[view_name] = {"class": view_class, "icon": icon_name}
         print(f"视图已注册: {view_name} (Class: {view_class.__name__})")

    def open_view(self, view_name: str, open_in_dock: bool = False, bring_to_front: bool = True):
        if view_name not in self.registered_views:
            QMessageBox.warning(self.main_window, "视图未注册", f"视图 '{view_name}' 未找到或未注册。")
            return

        view_info = self.registered_views[view_name]
        view_class = view_info["class"]
        icon = QIcon.fromTheme(view_info["icon"]) if view_info["icon"] else QIcon()

        if open_in_dock:
            dock = self.view_docks.get(view_name)
            if dock and dock.widget():
                 if bring_to_front: dock.show(); dock.raise_()
                 return dock.widget()
            elif dock and not dock.widget():
                 del self.view_docks[view_name] 
            try:
                 instance = view_class(self.main_window)
                 dock = QDockWidget(view_name, self.main_window)
                 dock.setObjectName(f"{view_name}Dock")
                 dock.setWidget(instance)
                 dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
                 self.main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
                 self.view_docks[view_name] = dock
                 self.view_instances[view_name] = instance
                 for existing_dock in self.view_docks.values():
                      if existing_dock != dock and self.main_window.dockWidgetArea(existing_dock) == self.main_window.dockWidgetArea(dock):
                           self.main_window.tabifyDockWidget(existing_dock, dock)
                           break
                 if bring_to_front: dock.show(); dock.raise_()
                 return instance
            except Exception as e:
                 QMessageBox.critical(self.main_window, "打开视图错误", f"创建视图 '{view_name}' 时出错: {e}")
                 return None
        else: # Tabbed view
            for i in range(self.tab_widget.count()):
                 widget = self.tab_widget.widget(i)
                 if isinstance(widget, view_class):
                      if bring_to_front: self.tab_widget.setCurrentIndex(i)
                      return widget
            try:
                 instance = view_class(self.main_window)
                 index = self.tab_widget.addTab(instance, icon, view_name)
                 if bring_to_front: self.tab_widget.setCurrentIndex(index)
                 return instance
            except Exception as e:
                 QMessageBox.critical(self.main_window, "打开视图错误", f"创建视图 '{view_name}' 时出错: {e}")
                 return None

    def is_widget_editor(self, widget: QWidget | None) -> bool:
        if widget is None: return False
        from PyQt6.QtWidgets import QPlainTextEdit 
        from ..atomic.editor.text_editor import _InternalTextEdit
        return isinstance(widget, (_InternalTextEdit, QPlainTextEdit))

    def is_widget_html_editor(self, widget: QWidget | None) -> bool:
         if widget is None: return False
         return isinstance(widget, HtmlEditor)

    def get_widget_base_name(self, widget: QWidget | None) -> str | None:
         if not widget: return None
         file_path = widget.property("file_path")
         if file_path: return os.path.basename(file_path)
         untitled_name = widget.property("untitled_name")
         if untitled_name: return untitled_name
         if hasattr(widget, 'windowTitle') and callable(widget.windowTitle): return widget.windowTitle()
         return widget.__class__.__name__

    def is_file_open(self, file_path: str) -> bool:
        if not self.tab_widget: return False
        abs_file_path = os.path.abspath(file_path)
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            # This check needs to be more robust if tabs can contain non-editor widgets with file_path
            editor_path = widget.property("file_path") # Assuming only editor tabs have 'file_path'
            if editor_path and os.path.abspath(editor_path) == abs_file_path:
                return True
        return False

    def focus_tab_by_filepath(self, file_path: str):
        if not self.tab_widget: return
        abs_file_path = os.path.abspath(file_path)
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            editor_path = widget.property("file_path")
            if editor_path and os.path.abspath(editor_path) == abs_file_path:
                self.tab_widget.setCurrentIndex(i)
                break
                    
    def register_speech_recognition(self):
        """注册语音识别组件"""
        self.register_view(SpeechRecognitionWidget, "SpeechRecognition", "microphone")
