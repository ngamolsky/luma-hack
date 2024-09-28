import asyncio

sample_rate = 44100


async def mux_audio_and_video():
    print("Encoding video file...")

    # fmt: off
    ffmpeg_command = [
        "ffmpeg",
        "-i", "output.mp4",
        "-f", "f32le",
        "-ar", f"{sample_rate}",
        "-ac", "1",
        "-i", "audio.pcm",
        "-vf", "subtitles=captions.srt:force_style='FontSize=50,PrimaryColour=&HFFFFFF&'",
        "-c:a", "aac",
        "-b:a", "192k",
        "-c:v", "copy",
        "-shortest",
        "final_output.mp4"
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
