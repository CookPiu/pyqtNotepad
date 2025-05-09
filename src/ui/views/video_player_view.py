# src/ui/views/video_player_view.py
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSlider, 
                             QStyle, QMessageBox, QLabel, QSizePolicy)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QUrl, QStandardPaths, QTime

class VideoPlayerWidget(QWidget):
    """
    视频播放器 Widget。
    使用 QMediaPlayer 和 QVideoWidget 播放视频，并提供基本控制。
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_path = None
        self.media_player = None
        self.audio_output = None
        self.video_widget = None
        self.play_button = None
        self.position_slider = None
        self.duration_label = None
        self.current_time_label = None

        self._setup_ui()
        self._setup_player()

    def _setup_ui(self):
        # Video display
        self.video_widget = QVideoWidget(self)
        self.video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Controls
        self.play_button = QPushButton(self)
        self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.play_button.setEnabled(False)
        self.play_button.clicked.connect(self.toggle_play_pause)

        self.position_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.position_slider.setRange(0, 0)
        self.position_slider.sliderMoved.connect(self.set_position)
        self.position_slider.setEnabled(False)

        self.current_time_label = QLabel("00:00", self)
        self.duration_label = QLabel("/ 00:00", self)

        controls_layout = QHBoxLayout()
        controls_layout.addWidget(self.play_button)
        controls_layout.addWidget(self.current_time_label)
        controls_layout.addWidget(self.position_slider)
        controls_layout.addWidget(self.duration_label)
        controls_layout.setContentsMargins(5, 5, 5, 5)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.video_widget)
        main_layout.addLayout(controls_layout)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)

    def _setup_player(self):
        self.media_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self) # Required for audio playback
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)

        # Connect signals
        self.media_player.playbackStateChanged.connect(self.update_play_button_icon)
        self.media_player.positionChanged.connect(self.update_slider_position)
        self.media_player.durationChanged.connect(self.update_duration)
        self.media_player.errorOccurred.connect(self.handle_error)

    def load_video(self, file_path: str) -> bool:
        self.file_path = file_path
        if not self.file_path or not os.path.exists(self.file_path):
            QMessageBox.critical(self, "错误", f"视频文件路径无效或文件不存在:\n{self.file_path}")
            self.play_button.setEnabled(False)
            self.position_slider.setEnabled(False)
            return False

        try:
            url = QUrl.fromLocalFile(self.file_path)
            self.media_player.setSource(url)
            self.play_button.setEnabled(True)
            self.position_slider.setEnabled(True)
            # Automatically play when loaded, or wait for user action?
            # self.media_player.play() 
            return True
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载视频时出错:\n{e}")
            self.play_button.setEnabled(False)
            self.position_slider.setEnabled(False)
            return False

    def toggle_play_pause(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def update_play_button_icon(self, state: QMediaPlayer.PlaybackState):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        else:
            self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))

    def set_position(self, position: int):
        self.media_player.setPosition(position)

    def update_slider_position(self, position: int):
        self.position_slider.setValue(position)
        self.current_time_label.setText(self._format_time(position))


    def update_duration(self, duration: int):
        self.position_slider.setRange(0, duration)
        self.duration_label.setText(f"/ {self._format_time(duration)}")

    def _format_time(self, ms: int) -> str:
        seconds = (ms / 1000) % 60
        minutes = (ms / (1000 * 60)) % 60
        hours = (ms / (1000 * 60 * 60)) % 24
        if hours > 0:
            return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
        else:
            return f"{int(minutes):02}:{int(seconds):02}"

    def handle_error(self, error: QMediaPlayer.Error, error_string: str):
        # error_string is often more informative for QMediaPlayer
        QMessageBox.critical(self, "播放器错误", f"播放视频时发生错误:\n{self.media_player.errorString()}")
        self.play_button.setEnabled(False)
        self.position_slider.setEnabled(False)

    def get_file_path(self) -> str | None:
        return self.file_path

    def cleanup(self):
        if self.media_player:
            self.media_player.stop()
            self.media_player.setSource(QUrl()) # Clear source
            # Properly delete Qt objects if they are not parented or to ensure cleanup
            # self.media_player.deleteLater() # Causes issues if parented
            # self.audio_output.deleteLater()
        self.file_path = None

    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)

if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication, QFileDialog

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    main_win = QWidget()
    main_win.setWindowTitle("Video Player Widget Test")
    main_win.setGeometry(100, 100, 800, 600)

    player_widget = VideoPlayerWidget(main_win)

    btn = QPushButton("Open Video File", main_win)

    vbox = QVBoxLayout(main_win)
    vbox.addWidget(btn)
    vbox.addWidget(player_widget)
    main_win.setLayout(vbox)

    def open_test_video():
        # Try to get a default video location
        default_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.MoviesLocation)
        if not default_dir:
            default_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.HomeLocation)

        file_path, _ = QFileDialog.getOpenFileName(main_win, "Select Video File", default_dir,
                                                   "Video Files (*.mp4 *.avi *.mkv *.mov *.webm)")
        if file_path:
            if not player_widget.load_video(file_path):
                print(f"Failed to load video: {file_path}")

    btn.clicked.connect(open_test_video)

    main_win.show()
    sys.exit(app.exec())
