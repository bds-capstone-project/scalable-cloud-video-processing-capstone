

import subprocess
from pathlib import Path


def process_video(input_path, output_dir):
    input_path = Path(input_path)
    output_dir = Path(output_dir)

    output_file = output_dir / f"processed_{input_path.name}"

    command = [
        "ffmpeg",
        "-y",
        "-i", str(input_path),
        "-vf", "scale=-2:720",
        "-c:v", "libx264",
        "-crf", "28",
        "-preset", "fast",
        "-c:a", "aac",
        "-b:a", "128k",
        str(output_file)
    ]

    subprocess.run(
        command,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    return output_file
