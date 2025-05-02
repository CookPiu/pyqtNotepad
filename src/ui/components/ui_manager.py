from PyQt6.QtWidgets import QDockWidget, QMessageBox
from PyQt6.QtCore import Qt
from src.ui.combined_tools_widget import CombinedToolsWidget
from src.ui.calculator_widget import CalculatorWindow
from src.ui.note_downloader_widget import NoteDownloaderWidget

class UIManager:
    """处理MainWindow的UI管理功能，包括主题应用和工具窗口管理"""
    
    def __init__(self, main_window):
        self.main_window = main_window
    
    def apply_current_theme(self):
        """应用当前主题到UI组件"""
        # 获取当前主题的样式表
        style_sheet = self.main_window.theme_manager.get_current_style_sheet()
        
        # 应用样式表到主窗口
        self.main_window.setStyleSheet(style_sheet)
        
        # 更新状态栏消息
        current_theme = "暗色" if self.main_window.theme_manager.is_dark_theme() else "亮色"
        self.main_window.statusBar.showMessage(f"已应用{current_theme}主题")
    
    def open_note_downloader_tab(self):
        """打开笔记下载器标签页"""
        # 检查是否已经存在笔记下载器标签页
        for i in range(self.main_window.tab_widget.count()):
            if isinstance(self.main_window.tab_widget.widget(i), NoteDownloaderWidget):
                self.main_window.tab_widget.setCurrentIndex(i)
                self.main_window.statusBar.showMessage("已切换到笔记下载器")
                return
        
        # 创建新的笔记下载器标签页
        downloader = NoteDownloaderWidget(self.main_window)
        index = self.main_window.tab_widget.addTab(downloader, "笔记下载器")
        self.main_window.tab_widget.setCurrentIndex(index)
        self.main_window.statusBar.showMessage("已打开笔记下载器")
    
    def open_pdf_preview(self, pdf_path):
        """打开PDF预览窗口"""
        from src.ui.pdf_viewer import PDFViewer
        
        # 创建PDF查看器对话框
        pdf_viewer = PDFViewer(pdf_path, self.main_window)
        pdf_viewer.convert_to_html_signal.connect(self.main_window.convert_pdf_to_html)
        
        # 显示PDF查看器对话框
        pdf_viewer.exec()
    
    def sidebar_item_clicked(self, item):
        """处理侧边栏项目点击事件"""
        item_text = item.text()
        is_combined_tool = item_text in ("计时器", "便签与待办", "日历")
        combined_dock_key = "CombinedTools"
        # 确定要查找或存储的dock的key
        dock_key = combined_dock_key if is_combined_tool else item_text

        dock = self.main_window.tool_docks.get(dock_key) # 尝试获取已存在的dock

        if dock is None: # 如果dock不存在，则创建
            widget_instance = None
            dock_title = item_text # 默认标题

            # 根据item_text创建对应的widget实例
            if is_combined_tool:
                widget_instance = CombinedToolsWidget(self.main_window)
                dock_title = "工具箱"
            elif item_text == "计算器":
                widget_instance = CalculatorWindow(self.main_window)
            elif item_text == "笔记下载":
                self.main_window.open_note_downloader_tab()
                return # 笔记下载不创建dock
            # Add other non-combined tools here if needed

            # 如果成功创建了widget实例，则创建Dock并进行处理
            if widget_instance:
                # 使用临时变量new_dock存储新创建的dock
                new_dock = QDockWidget(dock_title, self.main_window)
                new_dock.setWidget(widget_instance)
                new_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.BottomDockWidgetArea)
                self.main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, new_dock)

                # --- Attempt to Tabify ---
                tabified = False
                # 尝试将新dock与该区域已存在的dock合并为Tab
                for existing in self.main_window.findChildren(QDockWidget):
                    # 确保existing不是new_dock本身，并且在同一个区域
                    if existing is not new_dock and self.main_window.dockWidgetArea(existing) == self.main_window.dockWidgetArea(new_dock):
                        self.main_window.tabifyDockWidget(existing, new_dock)
                        tabified = True
                        break

                # 将新创建的dock存储到self.tool_docks中，并赋值给dock变量
                self.main_window.tool_docks[dock_key] = new_dock
                dock = new_dock # 关键：确保后续操作使用的是新创建的dock

            # 如果没有创建widget实例，且不是合并工具（即真正的占位符）
            elif not is_combined_tool:
                QMessageBox.information(self.main_window, "功能占位符", f"'{item_text}' 功能尚未实现。")
                return # Exit if no widget created

        # --- dock存在（无论是找到的还是新创建的）---
        if dock: # 检查dock是否有效
            dock.show() # 添加显式显示
            dock.raise_() # 提升到顶层并显示

            # 如果是合并工具，切换内部Tab
            if is_combined_tool and isinstance(dock.widget(), CombinedToolsWidget):
                tab_map = {"日历": 0, "便签与待办": 1, "计时器": 2}
                target_index = tab_map.get(item_text)
                if target_index is not None:
                    dock.widget().tabs.setCurrentIndex(target_index)

            # 更新状态栏消息
            if is_combined_tool:
                self.main_window.statusBar.showMessage(f"已切换到工具箱中的 '{item_text}'")
            else:
                self.main_window.statusBar.showMessage(f"已打开 {item_text} 功能")
    
    def convert_pdf_to_html(self, pdf_path):
        """将PDF转换为HTML并在编辑器中打开"""
        from src.utils.pdf_utils import extract_pdf_content
        
        try:
            # 提取PDF内容
            html_content, temp_dir = extract_pdf_content(pdf_path)
            if not html_content:
                QMessageBox.warning(self.main_window, "警告", "无法提取PDF内容")
                return
            
            # 创建新的HTML编辑器标签页
            from src.ui.html_editor import HtmlEditor
            editor = HtmlEditor()
            editor.setFontPointSize(12)
            
            # 设置HTML内容
            editor.set_html(html_content)
            
            # 连接修改信号
            editor.document_modified.connect(lambda modified: self.main_window.update_tab_title(modified))
            
            # 添加标签页
            file_name = os.path.basename(pdf_path)
            index = self.main_window.tab_widget.addTab(editor, f"{file_name} (转换)")
            self.main_window.tab_widget.setCurrentIndex(index)
            
            # 设置属性
            editor.setProperty("file_path", None)  # 转换后的内容没有关联文件路径
            editor.setProperty("is_new", True)     # 视为新文件
            editor.setProperty("is_pdf_converted", True)  # 标记为PDF转换
            editor.setProperty("pdf_temp_dir", temp_dir)  # 保存临时目录路径以便清理
            editor.document().setModified(False)  # 初始状态为未修改
            
            # 更新状态栏
            self.main_window.statusBar.showMessage(f"已将PDF转换为HTML: {file_name}")
            
            # 更新编辑操作状态
            self.main_window.update_edit_actions_state(editor)
            
        except Exception as e:
            QMessageBox.critical(self.main_window, "错误", f"转换PDF时出错: {str(e)}")