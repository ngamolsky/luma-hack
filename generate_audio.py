import asyncio
import os

from cartesia import AsyncCartesia
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

openai_client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

PROMPT = """
Read the following summary of a currently unfolding drama in the tech industry.

Write a transcript for a 40s TikTok video that presents current events and news in a fast-paced attention-captivating way.

This transcript should capture the key points to catch viewers up on what's happening.

This video should be in the style of a young sarcastic creator. It should be terse, fast-paced, clever, witty, meme filled and often roasting the subjects/products/companies involved.

This script will be read aloud by a narrator so don't include emojis, markdown, ellipsis or any styling.

Don't add filler words or phrases like "let's begin", just get to the meat of the content.

```
{summary}
```
"""


async def generate_transcript(summary: str):
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": PROMPT.format(summary=summary)}],
    )
    print(response)
    transcript = response.choices[0].message.content
    print(transcript)
    return transcript


sample_rate = 44100


def compute_duration(total_bytes: int):
    bytes_per_sample = 4
    duration_seconds = total_bytes / (bytes_per_sample * sample_rate)
    return duration_seconds


async def send_transcripts(ctx, transcript: str):
    # "Friendly Australian Man"
    voice_id = "421b3369-f63f-4b03-8980-37a44df1d4e8"

    model_id = "sonic-english"

    output_format = {
        "container": "raw",
        "encoding": "pcm_f32le",
        "sample_rate": sample_rate,
    }

    transcript_lines = [line.strip() for line in transcript.split("\n") if line.strip()]

    for transcript in transcript_lines:
        await ctx.send(
            model_id=model_id,
            transcript=transcript,
            voice_id=voice_id,
            continue_=True,
            output_format=output_format,
            add_timestamps=True,
            _experimental_voice_controls={
                "speed": 0.3,
                "emotion": ["positivity", "curiosity"],
            },
        )

    await ctx.no_more_inputs()


async def receive_audio(ctx):
    total_bytes = 0
    print("Generating audio...")
    timestamp_chunks = []
    with open("audio.pcm", "wb") as output_file:
        async for chunk in ctx.receive():
            if "audio" in chunk:
                buffer = chunk["audio"]
                output_file.write(buffer)
                total_bytes += len(buffer)
            if "word_timestamps" in chunk:
                timestamp_chunks.append(chunk)

    print("Generating captions...")
    with open("captions.srt", "w") as srt_file:
        subtitle_count = 0
        for i, chunk in enumerate(timestamp_chunks):
            word_timestamps = chunk["word_timestamps"]
            words = word_timestamps["words"]
            start_times = word_timestamps["start"]
            end_times = word_timestamps["end"]

            subtitle_count += 1
            start_time = format_time(start_times[0])
            end_time = None

            # Peek ahead to grab the end time of the next chunk
            if i < len(timestamp_chunks) - 1:
                next_chunk = timestamp_chunks[i + 1]
                next_start_time = next_chunk["word_timestamps"]["start"][0]
                end_time = format_time(next_start_time)
            else:
                end_time = format_time(end_times[-1])

            accumulated_words = " ".join(words)

            srt_file.write(f"{subtitle_count}\n")
            srt_file.write(f"{start_time} --> {end_time}\n")
            srt_file.write(f"{accumulated_words}\n\n")

    return total_bytes


def format_time(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int((seconds % 1) * 1000)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d},{milliseconds:03d}"


async def generate_audio(summary: str):
    client = AsyncCartesia(api_key=os.environ.get("CARTESIA_API_KEY"))

    ws = await client.tts.websocket()

    ctx = ws.context()

    transcript = await generate_transcript(summary)

    send_task = asyncio.create_task(send_transcripts(ctx, transcript))
    listen_task = asyncio.create_task(receive_audio(ctx))

    _, total_bytes = await asyncio.gather(send_task, listen_task)

    duration_seconds = compute_duration(total_bytes)

    print(f"Generated {duration_seconds} seconds of audio.")
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
