import asyncio

sample_rate = 44100


async def mux_audio_and_video(
    audio_path: str, captions_path: str, duration_seconds: int
):
    print("Encoding video file...")

    # fmt: off
    ffmpeg_command = [
        "ffmpeg",
        "-f", "lavfi",
        "-i", f"color=c=black:s=1920x1080:d={duration_seconds}",
        "-f", "f32le",
        "-ar", f"{sample_rate}",
        "-ac", "1",
        "-i", "audio.pcm",
        "-vf", "subtitles=captions.srt:force_style='FontSize=50,PrimaryColour=&HFFFFFF&'",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "output.mp4"
    ]
    # fmt: on

    process = await asyncio.create_subprocess_exec(
        *ffmpeg_command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        print(f"Error running FFmpeg command: {stderr.decode()}")
        raise RuntimeError("FFmpeg command failed")

    print("Done.")
