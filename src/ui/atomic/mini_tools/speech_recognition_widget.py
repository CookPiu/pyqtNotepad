import os
import tempfile
import wave
import time
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QTextEdit, 
                             QLabel, QProgressBar, QMessageBox, QComboBox, QHBoxLayout,
                             QDialog, QGridLayout, QApplication)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QIcon
import pyaudio
from aip import AipSpeech
from .speech_config import SpeechConfig

class RecordingThread(QThread):
    """录音线程"""
    update_signal = pyqtSignal(int)  # 更新进度条信号
    finished_signal = pyqtSignal(str)  # 录音完成信号，传递文件路径
    error_signal = pyqtSignal(str)  # 错误信号
    
    def __init__(self, max_seconds=60, sample_rate=16000, channels=1, chunk=1024, format_type=pyaudio.paInt16, device_index=None):
        super().__init__()
        self.max_seconds = max_seconds
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk = chunk
        self.format = format_type
        self.device_index = device_index
        self.is_recording = False
        self.audio = None
        self.frames = []
        
    def run(self):
        try:
            # 创建临时文件
            temp_dir = tempfile.gettempdir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_file = os.path.join(temp_dir, f"recording_{timestamp}.wav")
            
            # 初始化PyAudio
            self.audio = pyaudio.PyAudio()
            stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.chunk
            )
            
            self.frames = []
            self.is_recording = True
            start_time = time.time()
            
            # 录音循环
            while self.is_recording and (time.time() - start_time) < self.max_seconds:
                data = stream.read(self.chunk)
                self.frames.append(data)
                elapsed = int((time.time() - start_time))
                progress = int((elapsed / self.max_seconds) * 100)
                self.update_signal.emit(progress)
            
            # 停止录音
            stream.stop_stream()
            stream.close()
            self.audio.terminate()
            
            # 保存录音文件
            self.save_recording()
            self.finished_signal.emit(self.output_file)
            
        except Exception as e:
            self.error_signal.emit(str(e))
    
    def stop(self):
        self.is_recording = False
    
    def save_recording(self):
        # 保存为WAV文件
        with wave.open(self.output_file, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.audio.get_sample_size(self.format))
            wf.setframerate(self.sample_rate)
            wf.writeframes(b''.join(self.frames))

class RecognitionThread(QThread):
    """Speech Recognition Thread"""
    result_signal = pyqtSignal(str)  # Recognition result signal
    error_signal = pyqtSignal(str)  # Error signal
    
    def __init__(self, audio_file, app_id, api_key, secret_key, format_type='wav', language='zh'):
        super().__init__()
        self.audio_file = audio_file
        self.app_id = app_id
        self.api_key = api_key
        self.secret_key = secret_key
        self.format_type = format_type
        self.language = language
    
    def run(self):
        try:
            # Initialize Baidu Speech Recognition client
            client = AipSpeech(self.app_id, self.api_key, self.secret_key)
            
            # Read audio file
            with open(self.audio_file, 'rb') as f:
                audio_data = f.read()
            
            # Set language model ID based on selected language
            dev_pid = 1737 if self.language == 'en' else 1537  # 1737 for English, 1537 for Mandarin
            
            # Send recognition request
            result = client.asr(audio_data, self.format_type, 16000, {
                'dev_pid': dev_pid,
            })
            
            # Process recognition result
            if result['err_no'] == 0:
                text = result['result'][0]
                self.result_signal.emit(text)
            else:
                error_msg = f"Recognition error: {result['err_msg']} (Error code: {result['err_no']})"
                self.error_signal.emit(error_msg)
                
        except Exception as e:
            self.error_signal.emit(f"Error during recognition process: {str(e)}")

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
        self.recognition_thread = None
        
        # 初始化配置管理
        self.config = SpeechConfig()
        
        # 从配置加载API设置
        api_settings = self.config.get_api_settings()
        self.app_id = api_settings["app_id"]
        self.api_key = api_settings["api_key"]
        self.secret_key = api_settings["secret_key"]
        
        # 初始化UI
        self.init_ui()
        
    def init_ui(self):
        # Main layout
        main_layout = QVBoxLayout()
        
        # Settings button
        self.settings_btn = QPushButton("API Settings")
        self.settings_btn.clicked.connect(self.show_api_settings)
        main_layout.addWidget(self.settings_btn)
        
        # Language and sample rate selection
        options_layout = QHBoxLayout()
        
        # Language selection
        self.language_label = QLabel("Language:")
        self.language_combo = QComboBox()
        self.language_combo.addItems(["Mandarin", "English"])
        self.language_combo.setCurrentText(self.config.get_language())
        self.language_combo.currentTextChanged.connect(self.save_language_selection)
        options_layout.addWidget(self.language_label)
        options_layout.addWidget(self.language_combo)
        
        # Sample rate selection
        self.sample_rate_label = QLabel("Sample Rate:")
        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.addItems(["16000 Hz", "8000 Hz"])
        self.sample_rate_combo.setCurrentText(self.config.get_sample_rate())
        self.sample_rate_combo.currentTextChanged.connect(self.save_sample_rate_selection)
        options_layout.addWidget(self.sample_rate_label)
        options_layout.addWidget(self.sample_rate_combo)
        
        main_layout.addLayout(options_layout)
        
        # Microphone selection
        mic_layout = QHBoxLayout()
        self.mic_label = QLabel("Microphone:")
        self.mic_combo = QComboBox()
        self.load_microphone_devices()
        self.mic_combo.currentIndexChanged.connect(self.save_microphone_selection)
        mic_layout.addWidget(self.mic_label)
        mic_layout.addWidget(self.mic_combo)
        
        # Refresh microphone button
        self.refresh_mic_btn = QPushButton("刷新麦克风")
        self.refresh_mic_btn.clicked.connect(self.load_microphone_devices)
        mic_layout.addWidget(self.refresh_mic_btn)
        
        main_layout.addLayout(mic_layout)
        
        # Record button
        self.record_btn = QPushButton("Start Recording (max 60s)")
        self.record_btn.clicked.connect(self.toggle_recording)
        main_layout.addWidget(self.record_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)
        
        # Recognition result display
        self.result_label = QLabel("Recognition Result:")
        main_layout.addWidget(self.result_label)
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        main_layout.addWidget(self.result_text)
        
        # Copy result button
        self.copy_btn = QPushButton("Copy Result")
        self.copy_btn.clicked.connect(self.copy_result)
        main_layout.addWidget(self.copy_btn)
        
        # Clear result button
        self.clear_btn = QPushButton("Clear Result")
        self.clear_btn.clicked.connect(self.clear_result)
        main_layout.addWidget(self.clear_btn)
        
        self.setLayout(main_layout)
    
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
        """Toggle recording state"""
        if self.recording_thread and self.recording_thread.is_recording:
            # Stop recording
            self.recording_thread.stop()
            self.record_btn.setText("Start Recording (max 60s)")
        else:
            # Check API settings
            if not all([self.app_id, self.api_key, self.secret_key]):
                QMessageBox.warning(self, "Warning", "Please configure API settings first")
                self.show_api_settings()
                return
            
            # Start recording
            sample_rate = 16000 if "16000" in self.sample_rate_combo.currentText() else 8000
            language = "en" if self.language_combo.currentText() == "English" else "zh"
            
            # 获取选中的麦克风设备索引
            device_index = self.config.get_selected_microphone_index()
            
            self.recording_thread = RecordingThread(max_seconds=60, sample_rate=sample_rate, device_index=device_index)
            self.recording_thread.update_signal.connect(self.update_progress)
            self.recording_thread.finished_signal.connect(lambda file_path: self.recording_finished(file_path, language))
            self.recording_thread.error_signal.connect(self.show_error)
            
            self.recording_thread.start()
            self.record_btn.setText("Stop Recording")
            self.progress_bar.setValue(0)
            self.result_text.clear()
    
    def update_progress(self, value):
        """Update progress bar"""
        self.progress_bar.setValue(value)
    
    def recording_finished(self, file_path, language):
        """Recording finished, start recognition"""
        self.record_btn.setText("Start Recording (max 60s)")
        self.result_text.append("Recording completed, recognizing...")
        
        # Get file format
        _, ext = os.path.splitext(file_path)
        format_type = ext[1:].lower()  # Remove dot
        
        # Start recognition
        self.recognition_thread = RecognitionThread(
            file_path, self.app_id, self.api_key, self.secret_key, format_type, language
        )
        self.recognition_thread.result_signal.connect(self.show_result)
        self.recognition_thread.error_signal.connect(self.show_error)
        self.recognition_thread.start()
    
    def show_result(self, text):
        """Display recognition result"""
        self.result_text.clear()
        self.result_text.append(text)
    
    def show_error(self, error_msg):
        """Display error message"""
        self.result_text.append(f"Error: {error_msg}")
        QMessageBox.critical(self, "Error", error_msg)
    
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
    
    def cleanup(self):
        """Clean up resources"""
        if self.recording_thread and self.recording_thread.isRunning():
            self.recording_thread.stop()
            self.recording_thread.wait()
        
        if self.recognition_thread and self.recognition_thread.isRunning():
            self.recognition_thread.terminate()
            self.recognition_thread.wait()