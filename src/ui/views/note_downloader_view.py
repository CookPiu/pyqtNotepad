# src/ui/views/note_downloader_view.py
import sys
import os
import requests
import yaml
import urllib.parse
from pathlib import Path
import traceback
import json
import time
import re # Import re for worker

from PyQt6.QtCore import Qt, QDir, QUrl, QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QPlainTextEdit, QMessageBox, QLabel, QSplitter, QSizePolicy)
from PyQt6.QtGui import QPalette, QColor # For styling

# Correct relative import from views to core
from ..core.base_widget import BaseWidget

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEngineProfile # For cookie management (alternative)
    WEB_OK = True
except ImportError:
    WEB_OK = False
    QWebEngineView = None # Define as None if import fails

# === Worker Thread Definition (Keep within the view file for now) ===
class DownloadWorker(QThread):
    log_message = pyqtSignal(str)
    finished = pyqtSignal() # Ensure finished signal is defined

    def __init__(self, session, config, project_root, manifest_path, downloader_src_path, parent=None):
        super().__init__(parent)
        self.session = session
        self.config = config
        self.project_root = project_root # Path to the note_downloader sub-project
        self.manifest_path = manifest_path
        self.downloader_src_path = downloader_src_path # Path to note_downloader/src

    def run(self):
        """Main download logic executed in this thread."""
        added_path = False
        if self.downloader_src_path not in sys.path:
            sys.path.insert(0, self.downloader_src_path)
            added_path = True
            self.log_message.emit(f"临时将 {self.downloader_src_path} 添加到 sys.path")

        try:
            # Perform imports *after* potentially modifying sys.path
            # Use absolute imports relative to the added path
            import utils as nd_utils
            import crawler as nd_crawler
            import downloader as nd_downloader
            from classifier import FileClassifier as NDFileClassifier
            import checker as nd_checker

            # --- Helper function ---
            def sanitize_foldername(name):
                name = re.sub(r'[\\/*?:"<>|\r\n]+', '_', name)
                name = name.strip('. ')
                if not name: name = "untitled_course"
                return name

            # --- Core logic ---
            start_time = time.time()
            self.log_message.emit("=" * 50)
            self.log_message.emit("--- Note Downloader (后台线程) 开始运行 ---")
            self.log_message.emit("=" * 50)

            total_courses_found = 0
            processed_courses_success = 0
            processed_courses_failed = 0
            total_files_downloaded = 0
            total_files_skipped = 0
            total_files_failed = 0

            cfg = self.config
            session = self.session

            if not session:
                self.log_message.emit("错误：无效的会话对象。无法继续。")
                return
            if not cfg:
                self.log_message.emit("错误：无效的配置对象。无法继续。")
                return

            # --- Load Manifest ---
            self.log_message.emit(f"--- [预处理 1/2] 加载现有文件清单: {self.manifest_path} ---")
            manifest = nd_checker.load_manifest(self.manifest_path)

            # --- Initialize Classifier ---
            self.log_message.emit(f"--- [预处理 2/2] 初始化文件分类器...")
            rules_file_path = Path(self.project_root) / "config" / "classify_rules.yaml"
            if not rules_file_path.is_file():
                 self.log_message.emit(f"警告：分类规则文件未找到于 {rules_file_path}，将使用默认分类。")
                 classifier_instance = NDFileClassifier(rules_path=None) # Use default rules
            else:
                 classifier_instance = NDFileClassifier(rules_path=str(rules_file_path))

            # --- Get Course List ---
            self.log_message.emit("[步骤 1/3] 获取课程列表...")
            try:
                if 'base_url' not in cfg:
                    raise ValueError("配置中缺少 'base_url'")
                courses = nd_crawler.get_course_list(session, cfg)
                total_courses_found = len(courses)
                self.log_message.emit(f"成功获取 {total_courses_found} 门课程。")
            except Exception as crawl_list_err:
                 self.log_message.emit(f"错误: 获取课程列表时发生错误: {crawl_list_err}")
                 self.log_message.emit(traceback.format_exc())
                 return

            # --- Prepare Download Directory ---
            download_dir_name = cfg.get("download_directory", "downloads")
            base_download_dir = Path(self.project_root) / download_dir_name
            self.log_message.emit(f"[步骤 2/3] 检查/创建基础下载目录: {base_download_dir}")
            try:
                 nd_utils.safe_mkdir(str(base_download_dir))
            except Exception as mkdir_err:
                 self.log_message.emit(f"错误: 无法创建基础下载目录 '{base_download_dir}': {mkdir_err}")
                 return

            # --- Process Courses ---
            if total_courses_found > 0:
                self.log_message.emit(f"[步骤 3/3] 开始遍历 {total_courses_found} 门课程进行处理...")
                for i, (course_name, course_url) in enumerate(courses):
                    if self.isInterruptionRequested():
                        self.log_message.emit("用户请求中断。")
                        break

                    course_start_time = time.time()
                    self.log_message.emit("-" * 40)
                    self.log_message.emit(f"-> 开始处理课程 [{i+1}/{total_courses_found}]: '{course_name}'")
                    course_failed_flag = False

                    try:
                        safe_course_name = sanitize_foldername(course_name)
                        course_download_folder = base_download_dir / safe_course_name
                        nd_utils.safe_mkdir(str(course_download_folder))

                        self.log_message.emit(f"   [{i+1}/{total_courses_found}] 获取 '{course_name}' 的资源链接...")
                        resource_links = nd_crawler.get_resource_links(session, course_url, cfg)

                        if not resource_links:
                            self.log_message.emit(f"   [{i+1}/{total_courses_found}] 课程 '{course_name}' 中未找到有效资源链接。")
                        else:
                            self.log_message.emit(f"   [{i+1}/{total_courses_found}] 找到 {len(resource_links)} 个资源，准备下载...")
                            # Pass log_message signal directly
                            downloaded, skipped, failed = nd_downloader.bulk_download(
                                session,
                                resource_links,
                                str(course_download_folder),
                                manifest,
                                classifier_instance
                                # logger_func=self.log_message.emit # Removed unexpected argument
                            )
                            total_files_downloaded += downloaded
                            total_files_skipped += skipped
                            total_files_failed += failed

                    except Exception as course_err:
                        self.log_message.emit(f"   !!! 处理课程 '{course_name}' 时发生错误: {course_err} !!!")
                        self.log_message.emit(traceback.format_exc())
                        course_failed_flag = True

                    course_end_time = time.time()
                    course_duration = course_end_time - course_start_time
                    status = "失败" if course_failed_flag else "成功"
                    self.log_message.emit(f"<- 课程 [{i+1}/{total_courses_found}] '{course_name}' 处理{status} (耗时: {course_duration:.2f} 秒)")
                    if course_failed_flag: processed_courses_failed += 1
                    else: processed_courses_success += 1
                    self.log_message.emit("-" * 40)
            else:
                self.log_message.emit("[步骤 3/3] 未找到课程，跳过课程处理步骤。")

            end_time = time.time()
            duration = end_time - start_time
            self.log_message.emit("=" * 50)
            self.log_message.emit("--- Note Downloader (后台线程) 运行结束 ---")
            self.log_message.emit(f"总耗时: {duration:.2f} 秒")
            self.log_message.emit(f"共找到课程数: {total_courses_found}")
            self.log_message.emit(f"成功处理课程数: {processed_courses_success}")
            self.log_message.emit(f"处理失败课程数: {processed_courses_failed}")
            self.log_message.emit("--- 文件统计 ---")
            self.log_message.emit(f"实际下载文件数: {total_files_downloaded}")
            self.log_message.emit(f"跳过文件数 (已存在/签名未变): {total_files_skipped}")
            self.log_message.emit(f"处理失败文件数: {total_files_failed}")
            self.log_message.emit("=" * 50)

            # --- Save Manifest ---
            if manifest is not None:
                 try:
                     manifest_dir = Path(self.manifest_path).parent
                     manifest_dir.mkdir(parents=True, exist_ok=True)
                     with open(self.manifest_path, 'w', encoding='utf-8') as f:
                         json.dump(manifest, f, indent=2, ensure_ascii=False, sort_keys=True)
                     self.log_message.emit(f"✅ 内容签名清单已更新并保存到: {self.manifest_path}")
                 except Exception as save_manifest_err:
                     self.log_message.emit(f"错误: 保存 Manifest 到 '{self.manifest_path}' 时出错: {save_manifest_err}")

        except ImportError as imp_err:
             self.log_message.emit(f"错误：在工作线程中导入模块失败: {imp_err}")
             self.log_message.emit(traceback.format_exc())
             self.log_message.emit(f"请确保 note_downloader 及其依赖项已正确安装并且路径设置正确 ({self.downloader_src_path})。")
        except Exception as e:
            self.log_message.emit(f"!!! 工作线程发生未处理的严重错误: {e} !!!")
            self.log_message.emit(traceback.format_exc())
        finally:
            if added_path and self.downloader_src_path in sys.path:
                 try:
                     sys.path.remove(self.downloader_src_path)
                     self.log_message.emit(f"清理 sys.path: 已移除 {self.downloader_src_path}")
                 except ValueError: pass
            self.log_message.emit("--- 工作线程执行完毕 ---")
            self.finished.emit() # Emit finished signal


# === Main View Widget ===
class NoteDownloaderView(BaseWidget):
    """
    嵌入式 Note-Downloader 视图页面。
    继承自 BaseWidget。
    """
    log_message = pyqtSignal(str) # Signal for logging

    def __init__(self, parent=None, note_downloader_root=None):
        # Determine the root path for the note_downloader sub-project
        if note_downloader_root and os.path.isdir(note_downloader_root):
             self.project_root = note_downloader_root
        else:
             # Fallback: Assume it's in a 'note_downloader' subdir of the main project
             main_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")) # Adjust based on actual structure
             self.project_root = os.path.join(main_project_root, "note_downloader")
             if not os.path.isdir(self.project_root):
                  # Last resort: Use current working directory (less reliable)
                  self.project_root = os.path.join(os.getcwd(), "note_downloader")
                  print(f"警告: 无法自动确定 note_downloader 根目录，将尝试使用 {self.project_root}")

        self.session: requests.Session | None = None
        self.worker: DownloadWorker | None = None
        self.cfg: dict | None = None
        self.base_url: str | None = None
        self._added_sys_path: str | None = None # Track added sys.path

        super().__init__(parent) # Calls _init_ui, _connect_signals, _apply_theme

        # Automatically start loading config and login page after setup
        QTimer.singleShot(0, self.load_login_page)

    def _init_ui(self):
        """初始化 Note Downloader UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(5, 5, 5, 5) # Reduced margins

        # Log Output Area (Create first for signal connection)
        self.log = QPlainTextEdit(self)
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(2000)
        self.log.setObjectName("NoteDownloaderLog") # For styling
        self.log.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Splitter for Web View and Log
        splitter = QSplitter(Qt.Orientation.Vertical, self)
        splitter.setChildrenCollapsible(False)

        # Embedded Browser (Optional)
        if WEB_OK and QWebEngineView is not None:
            self.web = QWebEngineView(self)
            self.web.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            splitter.addWidget(self.web)
        else:
            no_web_label = QLabel("错误：PyQtWebEngine 未安装或无法加载。\n无法使用内嵌浏览器进行登录。", self)
            no_web_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_web_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            splitter.addWidget(no_web_label)
            self.web = None # Ensure self.web is None if not created

        # Add log widget to splitter
        splitter.addWidget(self.log)

        # Set initial sizes (adjust as needed)
        splitter.setSizes([int(self.height() * 0.75), int(self.height() * 0.25)])

        layout.addWidget(splitter, 1) # Splitter takes up expanding space
        self.setLayout(layout)

    def _connect_signals(self):
        """连接信号与槽"""
        self.log_message.connect(self._append_log)
        if self.web:
            self.web.loadFinished.connect(self._on_page_load_finished)

    def _apply_theme(self):
        """应用主题样式 (由 BaseWidget 调用)"""
        self.update_styles(is_dark=False) # Default light

    def update_styles(self, is_dark: bool):
        """根据主题更新样式"""
        log_bg = "#1e1e1e" if is_dark else "#ffffff"
        log_text = "#d4d4d4" if is_dark else "#000000"
        border_color = "#555555" if is_dark else "#cccccc"

        self.log.setStyleSheet(f"""
            QPlainTextEdit#NoteDownloaderLog {{
                background-color: {log_bg};
                color: {log_text};
                border: 1px solid {border_color};
                font-family: Consolas, Monaco, monospace;
                font-size: 10pt;
            }}
        """)
        # Optionally style the splitter handle
        # self.splitter.setStyleSheet(...)

    # --- Helper and Slot Methods ---
    def _append_log(self, text: str):
        """将日志消息追加到日志窗"""
        self.log.appendPlainText(text.rstrip())
        # Auto-scroll only if the scrollbar is near the bottom
        scrollbar = self.log.verticalScrollBar()
        if scrollbar.value() >= scrollbar.maximum() - 10: # Threshold
             scrollbar.setValue(scrollbar.maximum())

    def _load_config(self) -> bool:
        """尝试加载 note_downloader 配置"""
        if self.cfg: return True

        config_file_path = Path(self.project_root) / "config" / "config.yaml"
        self.log_message.emit(f"加载配置文件: {config_file_path}")
        try:
            if not config_file_path.is_file():
                raise FileNotFoundError(f"配置文件未找到: {config_file_path}")
            with open(config_file_path, 'r', encoding="utf-8") as f:
                self.cfg = yaml.safe_load(f)
            if not self.cfg:
                 raise ValueError("配置文件为空或格式错误。")
            self.base_url = self.cfg.get("base_url")
            self.log_message.emit("配置文件加载成功。")
            if not self.base_url:
                self.log_message.emit("警告：配置文件中未找到 'base_url'。")
            return True
        except Exception as e:
            self.log_message.emit(f"错误: 加载配置文件时出错: {e}")
            QMessageBox.critical(self, "配置错误", f"加载配置文件 '{config_file_path}' 时出错:\n{e}")
            self.cfg = None
            self.base_url = None
            return False

    def load_login_page(self):
        """加载 Moodle 登录页面到 QWebEngineView"""
        if not self.web:
            self.log_message.emit("错误：无法加载页面，内嵌浏览器不可用。")
            return

        if not self._load_config() or not self.base_url:
            self.log_message.emit("错误：无法加载登录页面，配置文件错误或缺少 'base_url'。")
            return

        login_path = self.cfg.get("login_path", "/login/index.php")
        # Ensure base_url ends with a single '/' before joining
        base_url_clean = self.base_url.rstrip('/') + '/'
        login_url_str = urllib.parse.urljoin(base_url_clean, login_path.lstrip('/'))
        login_qurl = QUrl(login_url_str)

        if login_qurl.isValid():
            self.log_message.emit(f"正在加载登录页面: {login_url_str}")
            self.web.load(login_qurl)
        else:
            self.log_message.emit(f"错误: 构造的登录 URL 无效: {login_url_str}")
            QMessageBox.critical(self, "URL错误", f"构造的登录 URL 无效:\n{login_url_str}")

    def _on_page_load_finished(self, ok: bool):
        """Slot called when QWebEngineView finishes loading a page."""
        if not self.web: return

        if ok:
            current_url = self.web.url().toString()
            self.log_message.emit(f"页面加载完成: {current_url}")
            # Check if logged in (heuristic: base URL is present, login path is not)
            if self.base_url and self.base_url in current_url and "/login/" not in current_url:
                self.log_message.emit("提示：检测到已登录状态，尝试自动开始同步...")
                self.extract_cookies_and_start_worker()
            else:
                self.log_message.emit("提示：请在上方浏览器窗口登录 Moodle。登录成功后将自动开始同步。")
        else:
            # Try to get error details (might require specific Qt version features)
            try:
                 error_string = self.web.page().property("loadErrorString") # Example property access
            except AttributeError:
                 error_string = "未知错误"
            self.log_message.emit(f"错误：页面加载失败。 {error_string}")

    # --- Cookie Extraction and Worker Start ---
    def extract_cookies_and_start_worker(self):
        """通过 JavaScript 获取 Cookies 并启动下载线程"""
        if not self.web:
            self.log_message.emit("错误：浏览器视图不可用，无法提取 Cookies。")
            return

        if self.worker and self.worker.isRunning():
            self.log_message.emit("同步任务已在运行中。")
            return

        if not self._load_config():
             QMessageBox.critical(self, "错误", "无法启动同步，配置文件加载失败。")
             return

        self.log_message.emit("开始从浏览器获取 Cookies (via JavaScript)...")
        # Use the page's profile's cookie store for a more robust method if available
        # Or fallback to document.cookie
        # profile = self.web.page().profile()
        # cookie_store = profile.cookieStore()
        # cookie_store.getAllCookies(self._on_qt_cookies_received) # Async callback
        self.web.page().runJavaScript("document.cookie", self._on_js_cookies_received) # Fallback

    def _on_js_cookies_received(self, js_cookie_string: str | None):
        """Callback after runJavaScript('document.cookie') finishes."""
        if js_cookie_string is None or not js_cookie_string.strip():
            self.log_message.emit("错误：未能通过 JavaScript 从浏览器获取任何 Cookies。请确保已成功登录。")
            QMessageBox.warning(self, "无 Cookies", "未能从浏览器获取 Cookies。\n请确认您已在上方窗口中成功登录 Moodle。")
            return

        self.log_message.emit(f"成功获取 Cookie 字符串，正在解析并创建会话...")
        self.session = requests.Session()
        self.session.headers.update({
             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36'
        })

        try:
            cookie_dict = {}
            for item in js_cookie_string.split(';'):
                item = item.strip()
                if '=' in item:
                    name, value = item.split('=', 1)
                    name = urllib.parse.unquote(name.strip())
                    value = urllib.parse.unquote(value.strip())
                    cookie_dict[name] = value
            if not cookie_dict:
                 raise ValueError("Cookie 字符串解析后为空。")

            requests.utils.add_dict_to_cookiejar(self.session.cookies, cookie_dict)
            self.log_message.emit(f"从字符串解析并添加了 {len(cookie_dict)} 个 Cookie 到会话。")
        except Exception as parse_err:
             self.log_message.emit(f"错误: 解析 Cookie 字符串时出错: {parse_err}")
             QMessageBox.critical(self, "Cookie 解析错误", f"解析 Cookie 字符串时出错:\n{parse_err}")
             self.session = None # Invalidate session
             return

        # --- Session created, proceed to start worker ---
        self._start_worker_thread()

    def _start_worker_thread(self):
        """Starts the DownloadWorker thread."""
        if not self.session or not self.cfg:
            self.log_message.emit("错误：无法启动工作线程，会话或配置无效。")
            return
        if self.worker and self.worker.isRunning():
            self.log_message.emit("错误：工作线程已在运行。")
            return

        self.log_message.emit("会话创建成功。准备启动后台同步任务...")

        # Define paths relative to the note_downloader project root
        downloader_src_path = str(Path(self.project_root) / "src")
        downloads_root = Path(self.project_root) / self.cfg.get("download_directory", "downloads")
        manifest_path = downloads_root / "manifest.json"

        # Ensure the src path exists
        if not os.path.isdir(downloader_src_path):
             self.log_message.emit(f"错误：找不到 note_downloader 的 src 目录: {downloader_src_path}")
             QMessageBox.critical(self, "路径错误", f"找不到 note_downloader 的 src 目录:\n{downloader_src_path}")
             return

        self.worker = DownloadWorker(
            session=self.session,
            config=self.cfg,
            project_root=self.project_root,
            manifest_path=str(manifest_path),
            downloader_src_path=downloader_src_path
        )
        self.worker.log_message.connect(self.log_message) # Connect worker log to view log
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.start()

        self.log_message.emit(">>> 后台同步任务已启动...")

    def _on_worker_finished(self):
        """Slot called when DownloadWorker thread finishes."""
        self.log_message.emit(">>> 后台同步任务已结束。")
        # Clean up worker reference
        self.worker = None
        # Optionally re-enable UI elements disabled during download

    # --- Cleanup ---
    def closeEvent(self, event):
        """Ensure worker thread is stopped on close."""
        if self.worker and self.worker.isRunning():
            self.log_message.emit("正在请求停止后台任务...")
            self.worker.requestInterruption()
            if not self.worker.wait(3000): # Wait 3 seconds
                 self.log_message.emit("警告：后台任务未能及时停止。")
            else:
                 self.log_message.emit("后台任务已停止。")
        super().closeEvent(event)
