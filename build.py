import os
import sys
import subprocess
from pathlib import Path
from PIL import Image

def create_icon():
    print("Generating app.ico from web logo...")
    try:
        img_path = Path("native/mediamanagerx_app/web/media-manager-logo-256.png")
        if not img_path.exists():
            print(f"Error: {img_path} not found.")
            return False
        
        img = Image.open(img_path)
        ico_path = Path("app.ico")
        img.save(ico_path, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
        print("Successfully created app.ico")
        return True
    except Exception as e:
        print(f"Failed to create icon: {e}")
        return False

def build_exe():
    print("Building standalone executable with PyInstaller...")
    # Add native directory (which includes web) to PyInstaller
    # In PyInstaller, data format is 'source_path;destination_folder' on Windows
    add_data = "native;native"
    
    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onedir",
        "--windowed", # Don't open a console window for the GUI app
        "--icon=app.ico",
        f"--add-data={add_data}",
        "--name=MediaManagerX",
        "run.py"
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    print("Build successful. Output in dist/MediaManagerX")

if __name__ == "__main__":
    if create_icon():
        build_exe()
    else:
        print("Build aborted due to icon generation failure.")
        sys.exit(1)
