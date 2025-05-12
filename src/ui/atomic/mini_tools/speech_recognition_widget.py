import os
import tempfile
import wave
import time
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QTextEdit, 
                             QLabel, QProgressBar, QMessageBox, QComboBox, QHBoxLayout,
                              QDialog, QGridLayout, QApplication)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QMutex # Added QMutex
from PyQt6.QtGui import QIcon, QTextCursor # Added QTextCursor
import pyaudio
from aip import AipSpeech
from .speech_config import SpeechConfig

class RecordingThread(QThread):
    """录音线程 - 修改为持续录音，按需分块处理"""
    # update_signal = pyqtSignal(int) # May not be needed for continuous recording or re-purpose
    error_signal = pyqtSignal(str)  # 错误信号
    # finished_signal is no longer used by this thread directly for chunking
    # Instead, SpeechRecognitionWidget will manage when the overall session is "finished"

    def __init__(self, sample_rate=16000, channels=1, chunk_size=1024, audio_format=pyaudio.paInt16, device_index=None):
        super().__init__()
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size # Renamed from chunk for clarity
        self.audio_format = audio_format # Renamed from format_type
        self.device_index = device_index
        
        self.is_recording = False
        self.audio_interface = None # Renamed from audio
        self.audio_stream = None # Renamed from stream
        self.frames_buffer = [] # Renamed from frames
        self._lock = QMutex() # Corrected: Instantiate QMutex directly

    def run(self):
        try:
            self.audio_interface = pyaudio.PyAudio()
            self.audio_stream = self.audio_interface.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.chunk_size
            )
            
            self.frames_buffer = []
            self.is_recording = True
            
            while self.is_recording:
                try:
                    data = self.audio_stream.read(self.chunk_size, exception_on_overflow=False)
                    self.frames_buffer.append(data)
                except IOError as e:
                    if e.errno == pyaudio.paInputOverflowed:
                        print("Warning: Input overflowed. Some audio data may have been lost.")
                        # Optionally, clear frames or handle as needed
                    else:
                        raise # Re-raise other IOErrors
                QThread.msleep(10) # Small sleep to be responsive and not hog CPU

        except Exception as e:
            self.error_signal.emit(f"RecordingThread Error: {str(e)}")
        finally:
            if self.audio_stream:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
            if self.audio_interface:
                self.audio_interface.terminate()
            self.is_recording = False # Ensure flag is reset

    def stop(self):
        self.is_recording = False

    def get_current_frames_and_clear(self) -> list:
        """Returns a copy of current frames and clears the internal buffer."""
        # self._lock.lock() # If using QMutex
        if not self.frames_buffer:
            return []
        frames_copy = list(self.frames_buffer) # Create a shallow copy
        self.frames_buffer.clear()
        # self._lock.unlock()
        return frames_copy

    def save_frames_to_wav(self, frames_to_save: list, file_path: str) -> bool:
        """Saves a list of audio frames to a WAV file."""
        if not frames_to_save:
            return False
        try:
            with wave.open(file_path, 'wb') as wf:
                wf.setnchannels(self.channels)
                # Ensure audio_interface is available or pass format info
                # For simplicity, assuming self.audio_interface is valid or PyAudio object is created to get sample size
                pa_temp = pyaudio.PyAudio()
                sample_width = pa_temp.get_sample_size(self.audio_format)
                pa_temp.terminate()

                wf.setsampwidth(sample_width)
                wf.setframerate(self.sample_rate)
                wf.writeframes(b''.join(frames_to_save))
            return True
        except Exception as e:
            print(f"Error saving frames to WAV: {e}") # Log or emit error
            self.error_signal.emit(f"Error saving WAV: {e}")
            return False

class RecognitionThread(QThread):
    """Speech Recognition Thread"""
    result_signal = pyqtSignal(str)  # Recognition result signal
    error_signal = pyqtSignal(str)  # Error signal
    
    # Modified __init__ to accept a pre-loaded whisper_model object
    def __init__(self, audio_file, app_id, api_key, secret_key, format_type='wav', language='zh', 
                 engine_type="Baidu", whisper_model_size=None, whisper_model_instance=None):
        self.app_id = app_id
        self.api_key = api_key
        self.secret_key = secret_key
        self.format_type = format_type
        self.language = language
        self.engine_type = engine_type
        self.whisper_model_size = whisper_model_size
        self.audio_file = audio_file # Store audio_file path
        super().__init__() # Call super-class __init__
    
    def run(self):
        try:
            if self.engine_type == "Baidu":
                # Initialize Baidu Speech Recognition client
                client = AipSpeech(self.app_id, self.api_key, self.secret_key)
                
                # Read audio file
                with open(self.audio_file, 'rb') as f:
                    audio_data = f.read()
                
                # Set language model ID based on selected language
                # Baidu: 1537 for Mandarin (default), 1737 for English.
                # Whisper language codes are simpler e.g. "zh", "en"
                dev_pid = 1737 if self.language.lower() == 'english' or self.language.lower() == 'en' else 1537 
                
                # Send recognition request
                result = client.asr(audio_data, self.format_type, 16000, { # Assuming 16000Hz for Baidu
                    'dev_pid': dev_pid,
                })
                
                # Process recognition result
                if result['err_no'] == 0:
                    text = result['result'][0]
                    self.result_signal.emit(text)
                else:
                    error_msg = f"Baidu ASR Error: {result['err_msg']} (Code: {result['err_no']})"
                    self.error_signal.emit(error_msg)

            elif self.engine_type == "Whisper":
                import whisper # Ensure whisper is installed

                # Map language to whisper format if needed, e.g., "Mandarin" -> "zh"
                lang_map = {"mandarin": "zh", "english": "en"}
                whisper_lang = lang_map.get(self.language.lower(), self.language.lower())


                model = whisper.load_model(self.whisper_model_size if self.whisper_model_size else "base")
                
                # Transcribe
                # Ensure audio_file is the path to the audio file
                result = model.transcribe(self.audio_file, language=whisper_lang) 
                
                text = result["text"]
                self.result_signal.emit(text)
            else:
                self.error_signal.emit(f"Unsupported engine type: {self.engine_type}")
                
        except Exception as e:
            self.error_signal.emit(f"Error during {self.engine_type} recognition: {str(e)}")

class APIConfigDialog(QDialog):
    """API Configuration Dialog"""
    
    def __init__(self, parent=None, app_id="", api_key="", secret_key=""):
        super().__init__(parent)
        self.setWindowTitle("API Configuration")
        self.setMinimumWidth(400)
        
        self.app_id = app_id
        self.api_key = api_key
        self.secret_key = secret_key
        
        self.init_ui()
    
    def init_ui(self):
        layout = QGridLayout()
        
        # APP ID input
        self.app_id_label = QLabel("APP ID:")
        self.app_id_input = QTextEdit()
        self.app_id_input.setMaximumHeight(30)
        self.app_id_input.setPlaceholderText("Enter Baidu Speech APP ID")
        self.app_id_input.setText(self.app_id)
        layout.addWidget(self.app_id_label, 0, 0)
        layout.addWidget(self.app_id_input, 0, 1)
        
        # API Key input
        self.api_key_label = QLabel("API Key:")
        self.api_key_input = QTextEdit()
        self.api_key_input.setMaximumHeight(30)
        self.api_key_input.setPlaceholderText("Enter Baidu Speech API Key")
        self.api_key_input.setText(self.api_key)
        layout.addWidget(self.api_key_label, 1, 0)
        layout.addWidget(self.api_key_input, 1, 1)
        
        # Secret Key input
        self.secret_key_label = QLabel("Secret Key:")
        self.secret_key_input = QTextEdit()
        self.secret_key_input.setMaximumHeight(30)
        self.secret_key_input.setPlaceholderText("Enter Baidu Speech Secret Key")
        self.secret_key_input.setText(self.secret_key)
        layout.addWidget(self.secret_key_label, 2, 0)
        layout.addWidget(self.secret_key_input, 2, 1)
        
        # Buttons
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout, 3, 0, 1, 2)
        
        self.setLayout(layout)
    
    def get_api_settings(self):
        return {
            "app_id": self.app_id_input.toPlainText().strip(),
            "api_key": self.api_key_input.toPlainText().strip(),
            "secret_key": self.secret_key_input.toPlainText().strip()
        }

class SpeechRecognitionWidget(QWidget):
    """Speech Recognition Widget"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Speech Recognition")
        self.recording_thread = None
        # self.recognition_thread = None # Will manage multiple for chunks
        self.active_recognition_threads = [] # To keep track of chunk processing threads
        self.chunk_counter = 0 # To create unique filenames for chunks
        
        # 初始化配置管理
        self.config = SpeechConfig()
        self.chunk_timer = QTimer(self)
        self.chunk_timer.setInterval(5000) # Process audio every 5 seconds
        self.chunk_timer.timeout.connect(self.process_and_transcribe_chunk)
        
        # 从配置加载API设置
        api_settings = self.config.get_api_settings()
        self.app_id = api_settings["app_id"]
        self.api_key = api_settings["api_key"]
        self.secret_key = api_settings["secret_key"]
        
        # 初始化UI
        self.init_ui()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self) # Set main_layout directly on self

        # --- Settings Group ---
        settings_group_layout = QGridLayout()
        settings_group_layout.setColumnStretch(1, 1) # Allow combo boxes to stretch
        settings_group_layout.setColumnStretch(3, 1)

        # Engine selection
        self.engine_label = QLabel("识别引擎:")
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["Baidu", "Whisper"])
        self.engine_combo.setCurrentText(self.config.get_engine_type())
        self.engine_combo.currentTextChanged.connect(self.on_engine_changed)
        settings_group_layout.addWidget(self.engine_label, 0, 0)
        settings_group_layout.addWidget(self.engine_combo, 0, 1, 1, 3) # Span 3 columns for now

        # Whisper model selection
        self.whisper_model_label = QLabel("Whisper模型:")
        self.whisper_model_combo = QComboBox()
        self.whisper_model_combo.addItems(["tiny", "base", "small", "medium", "large"])
        self.whisper_model_combo.setCurrentText(self.config.get_whisper_model_size())
        self.whisper_model_combo.currentTextChanged.connect(self.save_whisper_model_selection)
        settings_group_layout.addWidget(self.whisper_model_label, 1, 0)
        settings_group_layout.addWidget(self.whisper_model_combo, 1, 1, 1, 3) # Span 3 columns

        # Settings button (Baidu API settings)
        self.settings_btn = QPushButton("百度API设置")
        self.settings_btn.clicked.connect(self.show_api_settings)
        settings_group_layout.addWidget(self.settings_btn, 2, 0, 1, 4) # Span all 4 columns

        # Language selection
        self.language_label = QLabel("Language:")
        self.language_combo = QComboBox()
        self.language_combo.addItems(["Mandarin", "English"])
        self.language_combo.setCurrentText(self.config.get_language())
        self.language_combo.currentTextChanged.connect(self.save_language_selection)
        settings_group_layout.addWidget(self.language_label, 3, 0)
        settings_group_layout.addWidget(self.language_combo, 3, 1)
        
        # Sample rate selection
        self.sample_rate_label = QLabel("Sample Rate (for recording):")
        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.addItems(["16000 Hz", "8000 Hz"])
        self.sample_rate_combo.setCurrentText(self.config.get_sample_rate())
        self.sample_rate_combo.currentTextChanged.connect(self.save_sample_rate_selection)
        settings_group_layout.addWidget(self.sample_rate_label, 3, 2, Qt.AlignmentFlag.AlignRight) # Align label to right
        settings_group_layout.addWidget(self.sample_rate_combo, 3, 3)
        
        # Microphone selection
        self.mic_label = QLabel("Microphone:")
        self.mic_combo = QComboBox()
        self.load_microphone_devices()
        self.mic_combo.currentIndexChanged.connect(self.save_microphone_selection)
        settings_group_layout.addWidget(self.mic_label, 4, 0)
        settings_group_layout.addWidget(self.mic_combo, 4, 1, 1, 2) # Span 2 columns
        
        # Refresh microphone button
        self.refresh_mic_btn = QPushButton("刷新麦克风")
        self.refresh_mic_btn.clicked.connect(self.load_microphone_devices)
        settings_group_layout.addWidget(self.refresh_mic_btn, 4, 3)
        
        main_layout.addLayout(settings_group_layout)

        # Initial visibility based on selected engine
        self._update_engine_specific_ui(self.config.get_engine_type())

        # --- Controls Group ---
        self.record_btn = QPushButton("开始实时识别")
        self.record_btn.clicked.connect(self.toggle_recording)
        main_layout.addWidget(self.record_btn)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0,0) # Indeterminate progress
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # --- Result Group ---
        self.result_label = QLabel("Recognition Result:")
        main_layout.addWidget(self.result_label)
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        main_layout.addWidget(self.result_text) # QTextEdit will stretch by default
        
        # --- Bottom Buttons Group ---
        bottom_button_layout = QHBoxLayout()
        self.copy_btn = QPushButton("Copy Result")
        self.copy_btn.clicked.connect(self.copy_result)
        self.clear_btn = QPushButton("Clear Result")
        self.clear_btn.clicked.connect(self.clear_result)
        bottom_button_layout.addStretch(1) # Add stretch to push buttons to center or right
        bottom_button_layout.addWidget(self.copy_btn)
        bottom_button_layout.addWidget(self.clear_btn)
        bottom_button_layout.addStretch(1) # Add stretch
        main_layout.addLayout(bottom_button_layout)
        
        # self.setLayout(main_layout) # Already set with QVBoxLayout(self)
    
    def show_api_settings(self):
        """Show API settings dialog"""
        dialog = APIConfigDialog(self, self.app_id, self.api_key, self.secret_key)
        if dialog.exec():
            settings = dialog.get_api_settings()
            self.app_id = settings["app_id"]
            self.api_key = settings["api_key"]
            self.secret_key = settings["secret_key"]
            
            if not all([self.app_id, self.api_key, self.secret_key]):
                QMessageBox.warning(self, "Warning", "Please fill in all API settings fields")
            else:
                # 保存API设置到配置文件
                self.config.save_api_settings(self.app_id, self.api_key, self.secret_key)
                QMessageBox.information(self, "Success", "API settings saved successfully")
    
    def toggle_recording(self):
        """Toggle recording state for chunk-based real-time recognition"""
        if self.recording_thread and self.recording_thread.is_recording:
            # Stop recording
            self.record_btn.setText("开始实时识别")
            self.progress_bar.setVisible(False)
            self.chunk_timer.stop()
            if self.recording_thread:
                self.recording_thread.stop()
                # Process any remaining frames after stopping
                QTimer.singleShot(100, self.process_and_transcribe_chunk) # Allow thread to stop before final chunk
                # self.recording_thread.wait() # Ensure thread finishes
                # self.recording_thread = None # Clean up
            QMessageBox.information(self, "信息", "实时识别已停止。")

        else:
            # Start recording
            current_engine = self.config.get_engine_type()
            if current_engine == "Baidu" and not all([self.app_id, self.api_key, self.secret_key]):
                QMessageBox.warning(self, "警告", "请先配置百度API设置。")
                self.show_api_settings()
                return

            sample_rate_str = self.sample_rate_combo.currentText()
            sample_rate = 16000 if "16000" in sample_rate_str else 8000
            device_index = self.config.get_selected_microphone_index()

            # Use new RecordingThread signature
            self.recording_thread = RecordingThread(
                sample_rate=sample_rate, 
                device_index=device_index,
                # chunk_size and audio_format use defaults in RecordingThread
            )
            self.recording_thread.error_signal.connect(self.append_error_message) # Append errors
            
            self.result_text.clear() # Clear previous results
            self.chunk_counter = 0
            self.active_recognition_threads = []

            self.recording_thread.start()
            self.chunk_timer.start()
            self.record_btn.setText("停止实时识别")
            self.progress_bar.setVisible(True)
            self.result_text.append("实时识别中...\n")

    def process_and_transcribe_chunk(self):
        if not self.recording_thread or not (self.recording_thread.is_recording or self.recording_thread.frames_buffer): # Process if recording or if buffer has data after stop
            if not self.recording_thread.is_recording and not self.recording_thread.frames_buffer : # if not recording and no more frames, stop timer
                 self.chunk_timer.stop()
            return

        frames = self.recording_thread.get_current_frames_and_clear()
        if not frames:
            return

        self.chunk_counter += 1
        temp_dir = tempfile.gettempdir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        chunk_file_path = os.path.join(temp_dir, f"rt_chunk_{timestamp}_{self.chunk_counter}.wav")

        if self.recording_thread.save_frames_to_wav(frames, chunk_file_path):
            current_engine = self.config.get_engine_type()
            language = self.language_combo.currentText() # "Mandarin" or "English"
            whisper_model_s = None
            if current_engine == "Whisper":
                whisper_model_s = self.config.get_whisper_model_size()

            recognition_task = RecognitionThread(
                audio_file=chunk_file_path,
                app_id=self.app_id,
                api_key=self.api_key,
                secret_key=self.secret_key,
                format_type='wav',
                language=language,
                engine_type=current_engine,
                whisper_model_size=whisper_model_s
            )
            recognition_task.result_signal.connect(self.append_recognition_result)
            recognition_task.error_signal.connect(self.append_error_message)
            recognition_task.finished.connect(lambda task=recognition_task, path=chunk_file_path: self.cleanup_chunk_task(task, path))
            
            self.active_recognition_threads.append(recognition_task)
            recognition_task.start()
        else:
            self.append_error_message(f"未能保存音频块: {chunk_file_path}")
            
    def cleanup_chunk_task(self, task, file_path):
        """Remove task from active list and delete temp file."""
        if task in self.active_recognition_threads:
            self.active_recognition_threads.remove(task)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error deleting temp chunk file {file_path}: {e}")


    def append_recognition_result(self, text):
        """Appends recognition result to the text edit."""
        self.result_text.moveCursor(QTextCursor.MoveOperation.End) # Corrected
        self.result_text.insertPlainText(text + " ") # Append with a space
        self.result_text.ensureCursorVisible()

    def append_error_message(self, error_msg):
        """Appends an error message to the text edit."""
        self.result_text.moveCursor(QTextCursor.MoveOperation.End) # Corrected
        self.result_text.insertPlainText(f"\n[错误: {error_msg}]\n")
        self.result_text.ensureCursorVisible()
        # QMessageBox.critical(self, "错误", error_msg) # Optional: also show critical popup

    # update_progress and recording_finished are no longer used in the same way for chunking
    # def update_progress(self, value):
    #     """Update progress bar"""
    #     self.progress_bar.setValue(value)
    
    # def recording_finished(self, file_path, language): # This was for single file mode
    #     pass 

    # show_result is replaced by append_recognition_result
    # def show_result(self, text):
    #    """Display recognition result"""
    #    self.result_text.clear()
    #    self.result_text.append(text)
    
    # show_error is replaced by append_error_message
    # def show_error(self, error_msg):
    #    """Display error message"""
    #    self.result_text.append(f"Error: {error_msg}")
    #    QMessageBox.critical(self, "Error", error_msg)
    
    def copy_result(self):
        """Copy recognition result to clipboard"""
        text = self.result_text.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self.result_text.append("\n(Result copied to clipboard)")
    
    def clear_result(self):
        """Clear recognition result"""
        self.result_text.clear()
    
    def update_styles(self, is_dark):
        """Update component styles"""
        # Can set different styles based on theme
        pass
    
    def load_microphone_devices(self):
        """加载麦克风设备列表"""
        # 保存当前选择的索引
        current_index = self.config.get_selected_microphone_index()
        
        # 清空当前列表
        self.mic_combo.clear()
        
        # 获取麦克风设备列表
        devices = self.config.get_microphone_devices()
        
        # 添加设备到下拉列表
        for device in devices:
            self.mic_combo.addItem(f"{device['name']} (ID: {device['index']})", device['index'])
        
        # 尝试恢复之前选择的设备
        for i in range(self.mic_combo.count()):
            if self.mic_combo.itemData(i) == current_index:
                self.mic_combo.setCurrentIndex(i)
                break
    
    def save_microphone_selection(self, index):
        """保存麦克风选择"""
        if index >= 0 and self.mic_combo.count() > 0:
            device_index = self.mic_combo.itemData(index)
            self.config.save_microphone_selection(device_index)
    
    def save_language_selection(self, language):
        """保存语言选择"""
        self.config.save_language(language)
    
    def save_sample_rate_selection(self, sample_rate):
        """保存采样率选择"""
        self.config.save_sample_rate(sample_rate)

    def on_engine_changed(self, engine_type):
        """Handle engine type change"""
        self.config.save_engine_type(engine_type)
        self._update_engine_specific_ui(engine_type)

    def _update_engine_specific_ui(self, engine_type):
        """Update UI elements based on selected engine"""
        if engine_type == "Whisper":
            self.whisper_model_label.show()
            self.whisper_model_combo.show()
            self.settings_btn.setEnabled(False) # Disable Baidu API settings
            self.settings_btn.setToolTip("Whisper引擎无需API密钥设置")
        elif engine_type == "Baidu":
            self.whisper_model_label.hide()
            self.whisper_model_combo.hide()
            self.settings_btn.setEnabled(True)
            self.settings_btn.setToolTip("")
        else: # Should not happen
            self.whisper_model_label.hide()
            self.whisper_model_combo.hide()
            self.settings_btn.setEnabled(True)
            self.settings_btn.setToolTip("")


    def save_whisper_model_selection(self, model_size):
        """Save Whisper model size selection"""
        self.config.save_whisper_model_size(model_size)
    
    def cleanup(self):
        """Clean up resources"""
        if self.recording_thread and self.recording_thread.isRunning():
            self.recording_thread.stop()
            self.recording_thread.wait() # Wait for thread to finish
        
        # Wait for all chunk recognition threads to finish
        for rec_thread in self.active_recognition_threads:
            if rec_thread.isRunning():
                # rec_thread.terminate() # Terminate might be too abrupt
                rec_thread.wait() 
        self.active_recognition_threads.clear()
        
        if self.chunk_timer.isActive():
            self.chunk_timer.stop()
