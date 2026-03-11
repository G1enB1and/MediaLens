import sys
from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)
player = QMediaPlayer()

def play_test(path):
    print("Testing path:", path)
    player.setSource(QUrl.fromLocalFile(path))
    player.play()
    import time
    time.sleep(1)
    print("State:", player.playbackState(), "Status:", player.mediaStatus())
    player.stop()

play_test(r"c:\pictures\demo - cute animals\ssstik.mp4")
play_test(r"c:\pictures\demo - cute animals\.\ssstik.mp4")
play_test(r"c:\pictures\demo - cute animals\.\.\ssstik.mp4")

app.quit()
