import os
import shutil
from pathlib import Path
import sys

# Add project root to path
sys.path.append(os.getcwd())

# Mock PySide6 components to avoid GUI dependency complexities if possible,
# or just rely on them being installed.
# Using minimal mocks for what Bridge uses if import fails would be complex.
# We assume the environment has dependencies installed (like user ran the app).

try:
    from native.mediamanagerx_app.main import Bridge
    from PySide6.QtWidgets import QApplication
    # specific fix for "QApplication: Must construct a QApplication before a QPaintDevice"
    app = QApplication(sys.argv) 
except ImportError:
    print("Failed to import app components. Ensure dependencies are installed.")
    sys.exit(1)

def setup_test_files(root: Path):
    if root.exists():
        shutil.rmtree(root)
    root.mkdir()
    
    (root / "img.jpg").touch()
    (root / "img.png").touch()
    (root / "anim.gif").touch()
    (root / "anim.webp").touch() # We will mock _is_animated to say this is animated
    (root / "static.webp").touch()
    (root / "video.mp4").touch()

def mock_is_animated(path: Path) -> bool:
    name = path.name.lower()
    if name.endswith(".gif"):
        return True
    if name == "anim.webp":
        return True
    return False

def verify():
    test_dir = Path("test_media_filter")
    setup_test_files(test_dir)
    
    print(f"Testing in {test_dir.absolute()}")
    
    bridge = Bridge()
    # Mock _is_animated method
    bridge._is_animated = mock_is_animated
    
    # Test Image Filter
    print("\n--- Testing Filter: image ---")
    images = bridge.list_media(str(test_dir), filter_type="image")
    image_names = {Path(x["path"]).name for x in images}
    print(f"Result: {image_names}")
    
    expected_images = {"img.jpg", "img.png", "static.webp"}
    if image_names == expected_images:
        print("PASS: Only static images included.")
    else:
        print(f"FAIL: Expected {expected_images}, got {image_names}")
        if "anim.gif" in image_names or "anim.webp" in image_names:
            print("  -> FAILURE: Animated files leaked into image filter!")

    # Test Animated Filter
    print("\n--- Testing Filter: animated ---")
    animated = bridge.list_media(str(test_dir), filter_type="animated")
    anim_names = {Path(x["path"]).name for x in animated}
    print(f"Result: {anim_names}")
    
    expected_anim = {"anim.gif", "anim.webp"}
    if anim_names == expected_anim:
        print("PASS: Animated files included.")
    else:
        print(f"FAIL: Expected {expected_anim}, got {anim_names}")

    # Cleanup
    shutil.rmtree(test_dir)

if __name__ == "__main__":
    verify()
