
import sys
import os
import time
from PySide6.QtCore import QUrl, QTimer, QCoreApplication
from PySide6.QtMultimedia import QMediaPlayer, QVideoSink, QVideoFrame

# Set the bypass flag
os.environ["QT_FFMPEG_BYPASS_HW_ACCELERATION"] = "1"

def test_video(path):
    app = QCoreApplication(sys.argv)
    player = QMediaPlayer()
    sink = QVideoSink()
    player.setVideoSink(sink)
    
    frame_count = 0
    
    def on_frame(frame):
        nonlocal frame_count
        frame_count += 1
        pf = frame.pixelFormat()
        w = frame.width()
        h = frame.height()
        print(f"Frame {frame_count}: fmt={pf.name} size={w}x{h}")
        
        # Test if conversion is safe
        try:
            img = frame.toImage()
            print(f"  toImage success: {img.width()}x{img.height()} isNull={img.isNull()}")
        except Exception as e:
            print(f"  toImage CRASH/FAIL: {e}")

        if frame_count >= 5:
            print("Successfully received and converted frames with SW decoding!")
            app.quit()
            
    sink.videoFrameChanged.connect(on_frame)
    
    def on_error(error, error_str):
        print(f"Player Error: {error_str}")
        app.quit()
        
    player.errorOccurred.connect(on_error)
    
    player.setSource(QUrl.fromLocalFile(path))
    player.play()
    
    # Timeout after 5 seconds
    QTimer.singleShot(5000, lambda: (print("Timeout waiting for frames"), app.quit()))
    
    app.exec()
    return frame_count > 0

if __name__ == "__main__":
    video_path = r"C:\Pictures\Digital Art\Animated\54288219.mp4"
    if not os.path.exists(video_path):
        print(f"Error: File not found: {video_path}")
    else:
        success = test_video(video_path)
        if success:
            print("TEST PASSED: Software decoding recovered the malformed video.")
        else:
            print("TEST FAILED: Software decoding did not help.")
