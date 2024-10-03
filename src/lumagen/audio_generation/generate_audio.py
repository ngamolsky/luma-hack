import io
import os

import numpy as np
import soundfile as sf
from cartesia import AsyncCartesia


async def generate_audio_from_script(
    project_id: str,
    script,
    voice_id="421b3369-f63f-4b03-8980-37a44df1d4e8",
    language="en",
):
    """
    Generate audio from a given script using Cartesia's text-to-speech API and convert to WAV on the fly.

    :param project_id: str, the ID of the project
    :param script: str, the text to convert to speech
    :param voice_id: str, the ID of the voice to use (default: "421b3369-f63f-4b03-8980-37a44df1d4e8")
    :param language: str, the language code (default: "en" for English)
    """

    client = AsyncCartesia(api_key=os.environ.get("CARTESIA_API_KEY"))

    model_id = "sonic-english"
    sample_rate = 44100

    os.makedirs(f"src/data/output/{project_id}", exist_ok=True)
    wav_file_path = f"src/data/output/{project_id}/audio.wav"

    # Use BytesIO to accumulate audio data in memory
    audio_buffer = io.BytesIO()

    async for output in await client.tts.sse(
        model_id=model_id,
        transcript=script,
        voice_id=voice_id,
        output_format={
            "container": "raw",
            "encoding": "pcm_f32le",
            "sample_rate": sample_rate,
        },
        language=language,
    ):  # type: ignore
        audio_buffer.write(output["audio"])

    # Convert the accumulated audio data to a numpy array
    audio_buffer.seek(0)
    audio_data = np.frombuffer(audio_buffer.read(), dtype=np.float32)

    # Write the audio data directly to a WAV file
    sf.write(wav_file_path, audio_data, sample_rate, subtype="FLOAT")

    # Calculate the duration of the audio clip
    duration = len(audio_data) / sample_rate

    await client.close()

    return wav_file_path, duration
