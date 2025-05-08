# src/ui/views/pdf_viewer_view.py
import os
import fitz  # PyMuPDF for image preview
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QScrollArea, QMessageBox, QSizePolicy, QStackedLayout,
                             QFrame, QApplication)
# QWebEngineView is not used in the simplified dialog, can be removed if not needed for other reasons
# from PyQt6.QtWebEngineWidgets import QWebEngineView 
from PyQt6.QtGui import QPixmap, QImage, QColor
from PyQt6.QtCore import Qt, pyqtSignal, QUrl, pyqtSlot, QObject, QThread, QTimer

# Correct relative import from views to core
from ..core.base_dialog import BaseDialog
from ...utils import pdf_utils # For the new extract_pdf_content

# --- Worker for PDF to HTML conversion ---
class PdfToHtmlWorker(QObject):
    conversion_finished = pyqtSignal(str) # Emits HTML content on success
    conversion_error = pyqtSignal(str, str) # Emits error title and message on failure

    def __init__(self, pdf_path): 
        super().__init__()
        self.pdf_path = pdf_path
        print(f"PdfToHtmlWorker.__init__: Instance {id(self)} created for PDF: {self.pdf_path}")

    @pyqtSlot()
    def run(self):
        print(f"PdfToHtmlWorker.run: Instance {id(self)}. Starting conversion for {self.pdf_path}")
        try:
            html_content = pdf_utils.extract_pdf_content(self.pdf_path)
            self.conversion_finished.emit(html_content)
            print(f"PdfToHtmlWorker.run: Instance {id(self)}. Conversion successful.")
        except FileNotFoundError as e:
            print(f"PdfToHtmlWorker.run: Instance {id(self)}. FileNotFoundError: {e}")
            self.conversion_error.emit("文件错误", str(e))
        except RuntimeError as e: 
            print(f"PdfToHtmlWorker.run: Instance {id(self)}. RuntimeError: {e}")
            self.conversion_error.emit("HTML 转换失败", str(e))
        except Exception as e: 
            print(f"PdfToHtmlWorker.run: Instance {id(self)}. Exception: {e}")
            self.conversion_error.emit("未知转换错误", f"转换过程中发生意外错误: {e}")

class PdfViewerView(BaseDialog):
    """
    PDF 查看器视图对话框。
    提供图片预览和将PDF内容转换为HTML源代码的功能。
    """
    htmlGenerated = pyqtSignal(str, str) # pdf_path, html_content

    def __init__(self, pdf_path, parent=None):
        self.pdf_path = pdf_path 
        print(f"PdfViewerView.__init__: Instance {id(self)} created for PDF: {self.pdf_path}")
        
        super().__init__(parent) 
        
        self.pdf_document_for_images = None 
        self.current_page_for_images = 0
        self.total_pages_for_images = 0
        
        self.conversion_thread = None
        self.conversion_worker = None
        self._conversion_successful = False # Flag to indicate successful conversion

        self.load_pdf_for_image_preview()

    def _init_dialog_ui(self):
        self.setWindowTitle(f"PDF预览 - {os.path.basename(self.pdf_path)}")
        self.resize(800, 600) 
        self.main_layout.setSpacing(5)

        view_mode_layout = QHBoxLayout()
        self.btn_image_preview = QPushButton("图片预览") # Kept for consistency, though it's the only view now
        self.btn_convert_to_html = QPushButton("转换为HTML") 
        view_mode_layout.addWidget(self.btn_image_preview)
        view_mode_layout.addWidget(self.btn_convert_to_html)
        view_mode_layout.addStretch()
        self.main_layout.addLayout(view_mode_layout)

        self.image_preview_widget = QWidget()
        image_preview_main_layout = QVBoxLayout(self.image_preview_widget)
        image_preview_main_layout.setContentsMargins(0,0,0,0)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("PdfScrollArea")
        scroll_content = QWidget()
        scroll_content_layout = QVBoxLayout(scroll_content)
        scroll_content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_display_label = QLabel("正在加载 PDF 图片预览...")
        self.image_display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_display_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.image_display_label.setScaledContents(True)
        scroll_content_layout.addWidget(self.image_display_label)
        scroll_content.setLayout(scroll_content_layout)
        self.scroll_area.setWidget(scroll_content)
        image_preview_main_layout.addWidget(self.scroll_area)
        image_nav_layout = QHBoxLayout()
        self.prev_button = QPushButton("上一页")
        self.page_label = QLabel("页码")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.next_button = QPushButton("下一页")
        image_nav_layout.addWidget(self.prev_button)
        image_nav_layout.addStretch()
        image_nav_layout.addWidget(self.page_label)
        image_nav_layout.addStretch()
        image_nav_layout.addWidget(self.next_button)
        image_preview_main_layout.addLayout(image_nav_layout)
        self.image_preview_widget.setLayout(image_preview_main_layout)
        
        self.main_layout.addWidget(self.image_preview_widget, 1) 
        self._update_image_nav_visibility(True) 

    def _connect_dialog_signals(self):
        self.btn_image_preview.clicked.connect(self._show_image_preview) 
        self.btn_convert_to_html.clicked.connect(self._trigger_html_conversion) 
        self.prev_button.clicked.connect(self.prev_image_page)
        self.next_button.clicked.connect(self.next_image_page)

    def _apply_dialog_theme(self):
        self.update_styles(is_dark=False) 

    def update_styles(self, is_dark: bool):
        bg_color = "#1e1e1e" if is_dark else "#ffffff"
        text_color = "#f0f0f0" if is_dark else "#2c3e50"
        # ... (rest of styling, QWebEngineView specific styling removed) ...
        border_color = "#555555" if is_dark else "#cccccc"
        button_bg = "#555" if is_dark else "#f0f0f0"
        button_text = text_color
        scroll_bg = "#2d2d2d" if is_dark else "#f8f8f8"
        self.scroll_area.setStyleSheet(f"QScrollArea#PdfScrollArea {{ background-color: {scroll_bg}; border: 1px solid {border_color}; border-radius: 4px; }}")
        self.scroll_area.widget().setStyleSheet(f"background-color: {scroll_bg};")
        self.page_label.setStyleSheet(f"color: {text_color}; background: transparent;")
        self.image_display_label.setStyleSheet(f"color: {text_color}; background-color: {scroll_bg};")
        button_style = f"QPushButton {{ background-color: {button_bg}; color: {button_text}; border: 1px solid {border_color}; border-radius: 4px; padding: 5px 10px; font-size: 12px; }} QPushButton:hover {{ background-color: {'#666' if is_dark else '#e0e0e0'}; }} QPushButton:pressed {{ background-color: {'#444' if is_dark else '#d0d0d0'}; }} QPushButton:disabled {{ background-color: {'#444' if is_dark else '#e0e0e0'}; color: {'#888' if is_dark else '#a0a0a0'}; border-color: {'#666' if is_dark else '#d0d0d0'}; }}"
        self.btn_image_preview.setStyleSheet(button_style)
        self.btn_convert_to_html.setStyleSheet(button_style)
        self.prev_button.setStyleSheet(button_style)
        self.next_button.setStyleSheet(button_style)

    @pyqtSlot()
    def _show_image_preview(self):
        self._update_image_nav_visibility(True) 
        self._stop_conversion_thread() 

    @pyqtSlot()
    def _trigger_html_conversion(self):
        print(f"PdfViewerView._trigger_html_conversion: Instance {id(self)}. Button clicked.")
        self.btn_convert_to_html.setEnabled(False)
        self.btn_convert_to_html.setText("正在转换...") 
        QApplication.processEvents()

        self._stop_conversion_thread() 
        print(f"PdfViewerView._trigger_html_conversion: Instance {id(self)}. Creating worker and thread.")
        
        self.conversion_thread = QThread(self) # Parented to self
        self.conversion_worker = PdfToHtmlWorker(self.pdf_path) 
        self.conversion_worker.moveToThread(self.conversion_thread)

        self.conversion_worker.conversion_finished.connect(self._on_html_conversion_finished)
        self.conversion_worker.conversion_error.connect(self._on_html_conversion_error) 
        
        self.conversion_thread.started.connect(self.conversion_worker.run)
        self.conversion_thread.finished.connect(self.conversion_worker.deleteLater)
        self.conversion_thread.finished.connect(self.conversion_thread.deleteLater) # Thread deletes itself
        self.conversion_thread.finished.connect(self._cleanup_python_references_on_finish) # Cleanup Python refs
            
        self.conversion_thread.start()
        print(f"PdfViewerView._trigger_html_conversion: Instance {id(self)}. Thread started (id: {id(self.conversion_thread)}).")

    @pyqtSlot(str)
    def _on_html_conversion_finished(self, html_content):
        print(f"PdfViewerView._on_html_conversion_finished: Instance {id(self)}. Received HTML content. Emitting htmlGenerated.")
        self.htmlGenerated.emit(self.pdf_path, html_content)
        QMessageBox.information(self, "转换成功", "HTML源代码已生成，将在编辑器中打开。")
        self.btn_convert_to_html.setText("转换为HTML")
        self.btn_convert_to_html.setEnabled(True)
        self._conversion_successful = True # Set flag for cleanup to handle dialog closing
        print(f"PdfViewerView._on_html_conversion_finished: Instance {id(self)}. Conversion successful, flag set.")
        # QTimer.singleShot(0, self.accept) # Moved to _cleanup_python_references_on_finish

    @pyqtSlot(str, str) 
    def _on_html_conversion_error(self, title, error_message):
        print(f"PdfViewerView._on_html_conversion_error: Instance {id(self)}. Error: {title} - {error_message}")
        if not self.isVisible(): 
            print(f"HTML转换错误 (对话框不可见): {title} - {error_message}")
            return
        QMessageBox.critical(self, title, error_message)
        self.btn_convert_to_html.setText("转换为HTML")
        self.btn_convert_to_html.setEnabled(True)

    @pyqtSlot()
    def _cleanup_python_references_on_finish(self):
        """Slot connected to QThread.finished to cleanup Python references."""
        print(f"PdfViewerView._cleanup_python_references_on_finish: Instance {id(self)}. Thread {id(self.conversion_thread) if self.conversion_thread else 'None'} finished.")
        # Worker and Thread objects should have been scheduled for deletion by deleteLater
        # Python references are cleared here after Qt's deleteLater has been scheduled for the QThread and QObject
        old_worker = self.conversion_worker
        old_thread = self.conversion_thread
        
        self.conversion_worker = None 
        self.conversion_thread = None 

        if self._conversion_successful:
            self._conversion_successful = False # Reset flag
            print(f"PdfViewerView._cleanup_python_references_on_finish: Instance {id(self)}. Conversion was successful, scheduling self.accept().")
            # Ensure accept is called safely from the main thread context
            QTimer.singleShot(0, self.accept)
        else:
            print(f"PdfViewerView._cleanup_python_references_on_finish: Instance {id(self)}. Conversion was not marked successful or flag already reset.")

    def _stop_conversion_thread(self) -> bool:
        print(f"PdfViewerView._stop_conversion_thread: Instance {id(self)}. Current Thread: {id(self.conversion_thread) if self.conversion_thread else 'None'}")
        stopped_cleanly = True
        if self.conversion_thread: 
            if self.conversion_thread.isRunning():
                print(f"PdfViewerView._stop_conversion_thread: Instance {id(self)}. Thread is running. Attempting to stop.")
                # Disconnect signals to prevent calls on partially destroyed objects
                if self.conversion_worker:
                    try: self.conversion_worker.conversion_finished.disconnect(self._on_html_conversion_finished)
                    except: pass
                    try: self.conversion_worker.conversion_error.disconnect(self._on_html_conversion_error)
                    except: pass
                try: self.conversion_thread.started.disconnect(self.conversion_worker.run)
                except: pass
                try: self.conversion_thread.finished.disconnect(self.conversion_worker.deleteLater)
                except: pass
                try: self.conversion_thread.finished.disconnect(self.conversion_thread.deleteLater)
                except: pass
                try: self.conversion_thread.finished.disconnect(self._cleanup_python_references_on_finish)
                except: pass
                
                print(f"PdfViewerView._stop_conversion_thread: Instance {id(self)}. Calling quit() on thread {id(self.conversion_thread)}.")
                self.conversion_thread.quit()
                wait_result = self.conversion_thread.wait(5000) 
                print(f"PdfViewerView._stop_conversion_thread: Instance {id(self)}. wait(5000) returned: {wait_result}")
                if not wait_result:
                    stopped_cleanly = False
                    print(f"PdfViewerView._stop_conversion_thread: Instance {id(self)}. Thread wait timed out. Calling terminate() on thread {id(self.conversion_thread)}.")
                    self.conversion_thread.terminate()
                    term_wait_result = self.conversion_thread.wait(1000) 
                    print(f"PdfViewerView._stop_conversion_thread: Instance {id(self)}. Terminate wait returned: {term_wait_result}. Thread terminated.")
                    if self.conversion_worker:
                        print(f"PdfViewerView._stop_conversion_thread: Instance {id(self)}. Scheduling terminated worker {id(self.conversion_worker)} for deleteLater.")
                        self.conversion_worker.deleteLater()
                    if self.conversion_thread: # Thread object itself
                        self.conversion_thread.deleteLater() 
                else:
                    print(f"PdfViewerView._stop_conversion_thread: Instance {id(self)}. Thread {id(self.conversion_thread)} stopped cleanly.")
            else: # Thread object exists but is not running
                print(f"PdfViewerView._stop_conversion_thread: Instance {id(self)}. Thread {id(self.conversion_thread)} exists but is not running.")
                # It might have finished and its 'finished' signal already processed deleteLater for worker and thread.
                # _cleanup_python_references_on_finish should have set Python refs to None.
        else: # No thread object
            print(f"PdfViewerView._stop_conversion_thread: Instance {id(self)}. No conversion thread object exists.")
        
        # Clear Python references if not already cleared by _cleanup_python_references_on_finish
        print(f"PdfViewerView._stop_conversion_thread: Instance {id(self)}. Finalizing Python references.")
        self.conversion_worker = None
        self.conversion_thread = None
        print(f"PdfViewerView._stop_conversion_thread: Instance {id(self)}. Finished stopping attempts. Cleanly: {stopped_cleanly}")
        return stopped_cleanly

    def _update_image_nav_visibility(self, visible: bool):
        self.prev_button.setVisible(visible)
        self.page_label.setVisible(visible)
        self.next_button.setVisible(visible)

    def load_pdf_for_image_preview(self):
        if not self.pdf_path or not os.path.exists(self.pdf_path):
             QMessageBox.critical(self, "错误", f"PDF 文件路径无效或文件不存在:\n{self.pdf_path}")
             self.image_display_label.setText("无法加载 PDF 图片预览")
             self._update_image_button_states()
             return
        try:
            self.pdf_document_for_images = fitz.open(self.pdf_path)
            self.total_pages_for_images = len(self.pdf_document_for_images)
            if self.total_pages_for_images > 0:
                self.current_page_for_images = 0
                self.show_image_page(self.current_page_for_images)
            else:
                self.image_display_label.setText("PDF 文件为空 (图片预览)")
                QMessageBox.warning(self, "警告", "PDF 文件没有页面。")
            self._update_image_button_states()
            self.update_image_page_label()
        except Exception as e:
            self.image_display_label.setText(f"加载 PDF 图片预览时出错:\n{e}")
            QMessageBox.critical(self, "错误", f"无法加载 PDF 文件进行图片预览:\n{e}")
            self.pdf_document_for_images = None
            self.total_pages_for_images = 0
            self._update_image_button_states()
            self.update_image_page_label()

    def show_image_page(self, page_num):
        if not self.pdf_document_for_images or not (0 <= page_num < self.total_pages_for_images):
            return
        try:
            page = self.pdf_document_for_images.load_page(page_num)

            # Dynamic zoom calculation
            screen = QApplication.primaryScreen()
            if screen: # Ensure screen is available (it should be in a GUI app)
                device_pix_ratio = screen.devicePixelRatio() # Use F version for float, more precise
            else:
                device_pix_ratio = 1.0 # Fallback

            page_width_points = page.rect.width
            available_width_pixels = self.scroll_area.viewport().width()

            if page_width_points > 0:
                # Calculate zoom to fit available width
                base_zoom = available_width_pixels / page_width_points
            else:
                base_zoom = 1.5 # Fallback if page width is zero

            # Apply device pixel ratio for sharpness.
            # base_zoom calculates the scaling to fit the width.
            # Multiplying by device_pix_ratio aims to render at native resolution for the target logical size.
            zoom = base_zoom * device_pix_ratio
            # Cap zoom to a reasonable maximum to prevent excessive memory usage if needed, e.g., zoom = min(zoom, 5.0)
            
            mat = fitz.Matrix(zoom, zoom)
            
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB, alpha=False)
            if pix.width == 0 or pix.height == 0:
                self.image_display_label.setText(f"无法渲染第 {page_num + 1} 页 (空图像)")
                return
            if pix.n != 3: 
                pix = fitz.Pixmap(fitz.csRGB, pix) 
            if pix.n != 3: 
                self.image_display_label.setText(f"图像格式错误 (预期3通道RGB, 得到 {pix.n} 即使在转换后)")
                return

            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
            if img.isNull():
                 self.image_display_label.setText(f"无法渲染第 {page_num + 1} 页 (QImage为空)")
                 return
            
            q_pixmap = QPixmap.fromImage(img)
            q_pixmap.setDevicePixelRatio(device_pix_ratio if screen else 1.0) # Set DPR for the pixmap
            self.image_display_label.setPixmap(q_pixmap)
            self.current_page_for_images = page_num
            self.update_image_page_label()
            self._update_image_button_states()
            self.scroll_area.verticalScrollBar().setValue(0)
        except Exception as e:
            self.image_display_label.setText(f"渲染第 {page_num + 1} 页时出错:\n{e}")
            self._update_image_button_states()

    def update_image_page_label(self):
        if self.total_pages_for_images > 0:
            self.page_label.setText(f"第 {self.current_page_for_images + 1} / {self.total_pages_for_images} 页")
        else:
            self.page_label.setText("无页面")

    def _update_image_button_states(self):
        has_doc = self.pdf_document_for_images is not None and self.total_pages_for_images > 0
        self.prev_button.setEnabled(has_doc and self.current_page_for_images > 0)
        self.next_button.setEnabled(has_doc and self.current_page_for_images < self.total_pages_for_images - 1)

    def prev_image_page(self):
        if self.current_page_for_images > 0:
            self.show_image_page(self.current_page_for_images - 1)

    def next_image_page(self):
        if self.current_page_for_images < self.total_pages_for_images - 1:
            self.show_image_page(self.current_page_for_images + 1)

    def closeEvent(self, event):
        print(f"PdfViewerView.closeEvent: Instance {id(self)} triggered. Stopping thread...")
        self._stop_conversion_thread() 
        print(f"PdfViewerView.closeEvent: Instance {id(self)} _stop_conversion_thread returned. Cleaning up PDF document.")
        if self.pdf_document_for_images:
            try:
                self.pdf_document_for_images.close()
                self.pdf_document_for_images = None
                print(f"PdfViewerView.closeEvent: Instance {id(self)}. PDF document closed.")
            except Exception as e:
                print(f"PdfViewerView.closeEvent: Instance {id(self)}. Error closing PDF document: {e}")
        
        print(f"PdfViewerView.closeEvent: Instance {id(self)}. Calling super().closeEvent.")
        super().closeEvent(event)
        print(f"PdfViewerView.closeEvent: Instance {id(self)}. super().closeEvent finished.")

if __name__ == '__main__':
    import sys
    app = QApplication.instance() 
    if app is None:
        app = QApplication(sys.argv)
    
    dummy_pdf_path = os.path.join(os.getcwd(), "dummy_test_pdf_viewer.pdf") 
    if not os.path.exists(dummy_pdf_path):
        try:
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((50, 72), "Hello, this is a test PDF for PdfViewerView.")
            page.draw_rect((40,60,250,90), color=(0,1,0), fill=(0.8,0.8,0.8))
            for i in range(1,5):
                page = doc.new_page()
                page.insert_text((50, 72 + i*20), f"This is page {i+1}.")
                if i % 2 == 0: 
                    try:
                        page.draw_circle((100, 200), 50, color=(1,0,0), fill=(1,1,0), overlay=False)
                        page.draw_line((50,250), (200,350), color=(0,0,1), width=3)
                    except Exception as img_e:
                        print(f"Error adding drawing to dummy PDF page {i+1}: {img_e}")
            doc.save(dummy_pdf_path)
            doc.close()
            print(f"Dummy PDF created at: {dummy_pdf_path}")
        except Exception as e:
            print(f"Could not create dummy PDF: {e}")

    if os.path.exists(dummy_pdf_path):
        viewer = PdfViewerView(dummy_pdf_path)
        viewer.show()
        sys.exit(app.exec())
    else:
        print(f"Dummy PDF {dummy_pdf_path} not found, cannot run test.")
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setText(f"测试所需的虚拟PDF文件 '{dummy_pdf_path}' 未找到或无法创建。")
        msg_box.setWindowTitle("测试环境错误")
        msg_box.exec()
        sys.exit(1)
