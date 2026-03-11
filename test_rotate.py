import subprocess
import json
import os
def get_rotation(path):
    cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams', path]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(res.stdout)
        for st in data.get('streams', []):
            if st.get('codec_type') == 'video':
                tags = st.get('tags', {})
                if 'rotate' in tags:
                    return int(tags['rotate'])
                for sd in st.get('side_data_list', []):
                    if 'rotation' in sd:
                        # rotation in ffprobe is counter-clockwise?
                        # actually positive or negative, let's just return it
                        # sometimes rotation is e.g. -90, 90
                        return float(sd['rotation'])
    except Exception as e:
        print("Error checking rotation:", e)
    return 0

print("No file created yet to test.")
