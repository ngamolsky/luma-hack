import asyncio
import os
from cartesia import AsyncCartesia
from dotenv import load_dotenv

load_dotenv()

TRANSCRIPT = """
WordPress is at war… with itself... kind of.
In a plot twist nobody saw coming, WordPress, the open-source darling of the web, is throwing licensing fees at WP Engine, a big-time managed WordPress host.

Why?
Automattic, WordPress’ parent company, says WP Engine isn’t "contributing enough" to the WordPress ecosystem. Translation? They want more $$$.

You can’t go IPO with happy customers alone. You need profits.

This spicy move has everyone talking.

Some developers are like “Great! Let’s secure growth.”
Others? “Wait, this could break WordPress’ open-source vibe!”

The wildest part? WP Engine’s customers are reporting issues like blocked plugins—ouch.

With rumors of higher fees for all hosting partners, people are wondering: is this the start of a full-on licensing grab?

In the end, this drama hits right at the heart of open-source: trust, growth, and… corporate cash grabs.

Stay tuned, this isn’t over…
"""


async def send_transcripts(ctx):
    # "Friendly Australian Man"
    voice_id = "421b3369-f63f-4b03-8980-37a44df1d4e8"

    model_id = "sonic-english"

    output_format = {
        "container": "raw",
        "encoding": "pcm_f32le",
        "sample_rate": 44100,
    }

    transcript_lines = [line.strip() for line in TRANSCRIPT.split("\n") if line.strip()]

    for transcript in transcript_lines:
        await ctx.send(
            model_id=model_id,
            transcript=transcript,
            voice_id=voice_id,
            continue_=True,
            output_format=output_format,
            add_timestamps=True,
        )

    await ctx.no_more_inputs()


async def receive_audio(ctx):
    with open("audio.pcm", "wb") as output_file, open("captions.srt", "w") as srt_file:
        subtitle_count = 0
        async for chunk in ctx.receive():
            if "audio" in chunk:
                buffer = chunk["audio"]
                output_file.write(buffer)
            if "word_timestamps" in chunk:
                word_timestamps = chunk["word_timestamps"]
                words = word_timestamps["words"]
                start_times = word_timestamps["start"]
                end_times = word_timestamps["end"]

                for word, start, end in zip(words, start_times, end_times):
                    subtitle_count += 1
                    start_time = format_time(start)
                    end_time = format_time(end)

                    srt_file.write(f"{subtitle_count}\n")
                    srt_file.write(f"{start_time} --> {end_time}\n")
                    srt_file.write(f"{word}\n\n")


def format_time(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int((seconds % 1) * 1000)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d},{milliseconds:03d}"


async def stream_and_listen():
    client = AsyncCartesia(api_key=os.environ.get("CARTESIA_API_KEY"))

    ws = await client.tts.websocket()

    ctx = ws.context()

    send_task = asyncio.create_task(send_transcripts(ctx))
    listen_task = asyncio.create_task(receive_audio(ctx))

    await asyncio.gather(send_task, listen_task)

    await ws.close()
    await client.close()


asyncio.run(stream_and_listen())
