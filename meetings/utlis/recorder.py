# utils/recorder.py

import os
import subprocess
import time
from django.conf import settings

FFMPEG_PATH = r"C:\ffmpeg\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe"

def start_recording_to_db(meeting):
    filename = f"meeting_{meeting.id}.mp4"
    output_path = os.path.join(settings.BASE_DIR, "temp_recordings", filename)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # FFmpeg command
    command = [
        FFMPEG_PATH,
        "-y",
        "-f", "gdigrab",  # Windows screen recording
        "-framerate", "30",
        "-i", "desktop",
        "-t", "00:00:10",  # 10 seconds test recording
        output_path
    ]

    subprocess.run(command)

    # Read file and store as binary
    with open(output_path, "rb") as f:
        meeting.recording_data = f.read()
        meeting.recording_filename = filename
        meeting.save()

    # Clean temp file
    os.remove(output_path)
