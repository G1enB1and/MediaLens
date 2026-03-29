import sys, os, time
from PySide6.QtWidgets import QApplication
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl
from pathlib import Path

# Create a valid minimal mp4 file
test_mp4 = os.path.abspath("test_lock.mp4")

app = QApplication(sys.argv)

print("Simulating Rapid Double Open:")
player = QMediaPlayer()
player.setSource(QUrl.fromLocalFile(test_mp4))
player.play()

# Let it spin for just a tiny bit
for _ in range(2): QApplication.processEvents(); time.sleep(0.01)

# BAM, second open_video immediately!
print("Second open_video replacing first player")
# Without the fix:
player.stop()
player.deleteLater() # Leaks the file lock!

player = QMediaPlayer()
player.setSource(QUrl.fromLocalFile(test_mp4))
player.play()

for _ in range(10): QApplication.processEvents(); time.sleep(0.01)

print("Now attempting delete...")
player.stop()
player.setSource(QUrl())
for _ in range(10): QApplication.processEvents(); time.sleep(0.01)

try:
    with open(test_mp4, "a") as f: pass
    print("UNLOCKED!")
except Exception as e:
    print("LOCKED! (This means the first player leaked!)", e)

sys.exit(0)
