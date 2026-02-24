from PySide6.QtWidgets import QApplication
from PIL import Image
import json
import base64
import sys
import os

# Create a dummy image
img = Image.new('RGB', (100, 100))
img.save('test_embed.png')

# Now let's try calling the same embedding code that _save_to_exif_cmd uses
p = 'test_embed.png'
from PIL import PngImagePlugin
import tempfile

comm_raw = "This is a comment"
tags_raw = "Tag1, Tag2"

with Image.open(p) as img_load:
    pnginfo = PngImagePlugin.PngInfo()
    win_tags = tags_raw.replace(",", ";") 

    pnginfo.add_itxt("Description", comm_raw)
    pnginfo.add_itxt("Comment", comm_raw)
    pnginfo.add_itxt("Subject", comm_raw)
    pnginfo.add_itxt("Keywords", win_tags)

    exif = img_load.getexif()
    exif[0x9C9C] = (comm_raw + "\x00").encode("utf-16le")
    exif[0x9C9E] = (win_tags + "\x00").encode("utf-16le")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".png", dir=".") as as_tmp:
        tmp_name = as_tmp.name
    
    img_load.load()
    img_load.save(tmp_name, "PNG", pnginfo=pnginfo, exif=exif)
    os.replace(tmp_name, p)

print(f"Saved {p}")
