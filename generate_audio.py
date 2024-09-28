from cartesia import AsyncCartesia
import asyncio
import os
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


async def write_stream():
    client = AsyncCartesia(api_key=os.environ.get("CARTESIA_API_KEY"))

    # "Friendly Australian Man"
    voice_id = "421b3369-f63f-4b03-8980-37a44df1d4e8"
    voice = client.voices.get(id=voice_id)

    model_id = "sonic-english"

    output_format = {
        "container": "raw",
        "encoding": "pcm_f32le",
        "sample_rate": 44100,
    }

    output_file = open("output.pcm", "wb")
    chunk_count = 0

    async for chunk in await client.tts.sse(
        model_id=model_id,
        transcript=TRANSCRIPT,
        voice_embedding=voice["embedding"],
        stream=True,
        output_format=output_format,
    ):
        buffer = chunk["audio"]
        output_file.write(buffer)
        chunk_count += 1
        print(f"Chunks received: {chunk_count}")

    output_file.close()
    await client.close()


asyncio.run(write_stream())
