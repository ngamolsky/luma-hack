import os
import subprocess
import tempfile
from typing import Dict, List, Union


def download_image(url: str, output_path: str):
    subprocess.run(["curl", "-L", url, "-o", output_path], check=True)


def download_video(url: str, output_path: str, duration: int):
    # Fetch the video trimming it to just the {duration * 1.2} seconds, with the
    # 20% buffer accounting for the fact that there is often not enough content
    # to fill the audio duration.
    # fmt: off
    subprocess.run(
        [
            "ffmpeg",
            "-i", url,
            "-t", str(round(duration * 1.2, 1)),
            "-c", "copy",
            output_path,
        ],
        check=True,
    )
    # fmt: on


def combine_clips(clips: List[Dict[str, Union[str, int]]], output_file: str):
    with tempfile.TemporaryDirectory() as temp_dir:
        input_files = []
        for i, clip in enumerate(clips):
            print(">> clip:", clip)
            if clip["type"] == "video":
                print(f"Loading video {i}...")
                file_path = os.path.join(temp_dir, f"video_{i}.mp4")
                download_video(clip["url"], file_path, clip["duration"])
                input_files.append(f"file '{file_path}'")
            elif clip["type"] == "image":
                print(f"Loading image {i}...")
                file_path = os.path.join(temp_dir, f"image_{i}.png")
                download_image(clip["url"], file_path)
                video_path = os.path.join(temp_dir, f"image_video_{i}.mp4")
                # fmt: off
                subprocess.run([
                    "ffmpeg", "-loop", "1", "-i", file_path,
                    "-c:v", "libx264", "-t", str(clip["duration"]),
                    "-pix_fmt", "yuv420p", "-vf", "scale=1080:1920",
                    video_path
                ], check=True)
                # fmt: on
                input_files.append(f"file '{video_path}'")

        input_list_file = os.path.join(temp_dir, "input_list.txt")
        with open(input_list_file, "w") as f:
            f.write("\n".join(input_files))

        # fmt: off
        subprocess.run([
            "ffmpeg", "-f", "concat", "-safe", "0", "-i", input_list_file,
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-vf", "scale=1080:1920", "-c:a", "aac", "-b:a", "192k",
            output_file
        ], check=True)
        # fmt: on
