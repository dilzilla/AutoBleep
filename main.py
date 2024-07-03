import sys
import os
import logging
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QFileDialog, QVBoxLayout, QWidget, QLabel,
                             QProgressBar, QMessageBox, QStatusBar, QMenuBar, QMenu, QStyle, QHBoxLayout)
from PyQt6.QtCore import QRunnable, QThreadPool, pyqtSignal, QObject, Qt
from PyQt6.QtGui import QAction, QIcon
import whisper
from pydub import AudioSegment
import re
import subprocess
import tempfile

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class WorkerSignals(QObject):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

class BleepWorker(QRunnable):
    def __init__(self, input_file):
        super().__init__()
        self.input_file = input_file
        self.signals = WorkerSignals()
        self.misrecognized_words = {
            "con": "cunt",
            # Add more misrecognized words here if needed
        }
        self.bleep_volume_reduction = 6  # Reduce bleep volume by 6 dB
        self.extended_bleep_words = {"cunt": 0.2}  # Extend bleep by 0.2 seconds for "cunt"

    def is_curse_word(self, word, curse_words):
        clean_word = re.sub(r'[^\w\s]', '', word)
        if clean_word in curse_words:
            return True
        if clean_word in self.misrecognized_words and self.misrecognized_words[clean_word] in curse_words:
            return True
        return any(curse in clean_word for curse in curse_words)

    def run(self):
        try:
            with open('curse_words.txt', 'r') as f:
                curse_words = set(word.strip().lower() for word in f.readlines())
            
            logging.debug(f"Loaded curse words: {curse_words}")

            self.signals.progress.emit(10)
            model = whisper.load_model("base")
            result = model.transcribe(self.input_file, word_timestamps=True)

            self.signals.progress.emit(50)

            logging.debug("Full transcript:")
            for segment in result["segments"]:
                for word_data in segment["words"]:
                    word = word_data["word"]
                    start = word_data["start"]
                    end = word_data["end"]
                    logging.debug(f"Word: {word}, Start: {start}, End: {end}")

            curse_timestamps = []
            for segment in result["segments"]:
                words = segment["words"]
                for word_data in words:
                    word = word_data["word"].lower().strip()
                    if self.is_curse_word(word, curse_words):
                        start = word_data["start"]
                        end = word_data["end"]
                        actual_word = self.misrecognized_words.get(word, word)
                        curse_timestamps.append((start, end, actual_word))
                        logging.debug(f"Found curse word: {actual_word} (transcribed as '{word}') at {start}-{end}")

            self.signals.progress.emit(70)

            audio = AudioSegment.from_file(self.input_file)
            bleep = AudioSegment.from_wav("bleep.wav")
            
            # Reduce the volume of the bleep sound
            bleep = bleep - self.bleep_volume_reduction

            curse_timestamps.sort(key=lambda x: x[0])

            for i, (start, end, word) in enumerate(reversed(curse_timestamps)):
                start_ms = int(start * 1000)
                end_ms = int(end * 1000)
                segment_duration = end_ms - start_ms
                
                # Extend bleep duration for specific words
                if word in self.extended_bleep_words:
                    extra_duration = int(self.extended_bleep_words[word] * 1000)
                    segment_duration += extra_duration
                    end_ms += extra_duration

                bleeped_segment = bleep[:segment_duration]
                if len(bleeped_segment) < segment_duration:
                    bleeped_segment = bleeped_segment * (segment_duration // len(bleeped_segment) + 1)
                bleeped_segment = bleeped_segment[:segment_duration]
                audio = audio[:start_ms] + bleeped_segment + audio[end_ms:]
                logging.debug(f"Bleeped word: {word} at {start}-{end}, duration: {segment_duration}ms")
                self.signals.progress.emit(70 + int((i + 1) / len(curse_timestamps) * 20))

            # Determine output format
            _, ext = os.path.splitext(self.input_file)
            output_file = f"{os.path.splitext(self.input_file)[0]}_bleeped{ext}"

            if ext.lower() == '.mp4':
                # For MP4, we need to handle video separately
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                    audio.export(temp_audio.name, format="wav")
                    
                    # Use FFmpeg to combine the original video with the new audio
                    subprocess.run([
                        'ffmpeg', '-y', '-i', self.input_file, '-i', temp_audio.name,
                        '-c:v', 'copy', '-map', '0:v:0', '-map', '1:a:0', output_file
                    ], check=True)
                    
                    # Clean up the temporary file
                    os.unlink(temp_audio.name)
            else:
                # For other formats, just export the audio
                audio.export(output_file, format=ext[1:])  # Remove the dot from the extension

            self.signals.progress.emit(100)
            self.signals.finished.emit(output_file)
        except Exception as e:
            logging.error(f"Error in BleepWorker: {str(e)}")
            self.signals.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Curse Word Bleeper")
        self.setGeometry(100, 100, 500, 300)
        self.threadpool = QThreadPool()

        self.init_ui()

    def init_ui(self):
        self.create_menu_bar()
        
        main_layout = QVBoxLayout()

        file_layout = QHBoxLayout()
        self.file_button = QPushButton("Select Audio/Video File")
        self.file_button.clicked.connect(self.select_file)
        self.file_label = QLabel("No file selected")
        file_layout.addWidget(self.file_button)
        file_layout.addWidget(self.file_label)

        main_layout.addLayout(file_layout)

        self.status_label = QLabel("Ready")
        main_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def create_menu_bar(self):
        menu_bar = QMenuBar()

        file_menu = QMenu("&File", self)
        open_action = QAction(QIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton)), "&Open", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.select_file)
        file_menu.addAction(open_action)

        exit_action = QAction(QIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton)), "&Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        menu_bar.addMenu(file_menu)

        help_menu = QMenu("&Help", self)
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        menu_bar.addMenu(help_menu)

        self.setMenuBar(menu_bar)

    def select_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select Audio/Video File", "", "Audio/Video Files (*.mp3 *.mp4 *.wav *.avi *.mov)")
        if file_name:
            self.file_label.setText(os.path.basename(file_name))
            self.process_file(file_name)

    def process_file(self, file_name):
        reply = QMessageBox.question(self, 'Confirmation', 
                                     f"Do you want to process the file:\n{file_name}?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            self.status_label.setText(f"Processing: {os.path.basename(file_name)}")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)

            worker = BleepWorker(file_name)
            worker.signals.progress.connect(self.update_progress)
            worker.signals.finished.connect(self.process_finished)
            worker.signals.error.connect(self.process_error)

            self.threadpool.start(worker)
        else:
            self.status_label.setText("Processing cancelled")

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def process_finished(self, output_file):
        self.status_label.setText(f"Finished! Output: {os.path.basename(output_file)}")
        self.progress_bar.setVisible(False)
        QMessageBox.information(self, "Processing Complete", 
                                f"The bleeped file has been saved as:\n{output_file}")
        self.status_bar.showMessage("Processing complete", 5000)

    def process_error(self, error_message):
        self.status_label.setText("Error occurred during processing")
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Error", f"An error occurred:\n{error_message}")
        self.status_bar.showMessage("Processing failed", 5000)

    def show_about(self):
        QMessageBox.about(self, "About Curse Word Bleeper",
                          "Curse Word Bleeper v1.0\n\n"
                          "A simple application to detect and bleep out curse words in audio and video files.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())