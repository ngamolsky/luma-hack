import os
import subprocess
import tempfile
from typing import Dict, List, Union

clips: List[Dict[str, Union[str, int]]] = [
    {
        "type": "video",
        "url": "https://storage.cdn-luma.com/lit_lite_inference_v1.6-xl/c267b46c-26ba-44cb-8501-177381bf76a4/675196bc-e1c6-4008-b970-4a9afb595e59_video07f097e24b13b4b74a067d712b9289530.mp4",
    },
    {
        "type": "image",
        "url": "https://pub-2576bbab2f764a5a9c3fdc59f470ef1a.r2.dev/jamesivings_1839422193681481750_backdrop.png",
        "duration": 2,
    },
    {
        "type": "video",
        "url": "https://storage.cdn-luma.com/lit_lite_inference_v1.6-xl/40696db8-a5f8-4cec-8f23-408081aeb6c2/d4f3d919-6ca8-4cf0-abf1-d41a86e428d3_video0863ea24b7cca4aa7b8f2010439e37824.mp4",
    },
    {
        "type": "video",
        "url": "https://storage.cdn-luma.com/lit_lite_inference_v1.6-xl/6dc9a30e-7130-464d-ba93-f6d07105ae84/77791f45-802a-4414-91bc-b096be74d84d_video012cc1a7473a84ff2a7c6247a0b3828e2.mp4",
    },
    {
        "type": "image",
        "url": "https://pub-2576bbab2f764a5a9c3fdc59f470ef1a.r2.dev/arvidkahl_1839445536686174387_backdrop.png",
        "duration": 2,
    },
]


def download_file(url: str, output_path: str):
    subprocess.run(["curl", "-L", url, "-o", output_path], check=True)


def combine_clips(clips: List[Dict[str, Union[str, int]]], output_file: str):
    with tempfile.TemporaryDirectory() as temp_dir:
        input_files = []
        for i, clip in enumerate(clips):
            if clip["type"] == "video":
                print(f"Loading video {i}...")
                file_path = os.path.join(temp_dir, f"video_{i}.mp4")
                download_file(clip["url"], file_path)
                input_files.append(f"file '{file_path}'")
            elif clip["type"] == "image":
                print(f"Loading image {i}...")
                file_path = os.path.join(temp_dir, f"image_{i}.png")
                download_file(clip["url"], file_path)
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
