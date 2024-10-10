import io
from typing import Tuple

import numpy as np
import soundfile as sf
from pydantic import FilePath
from tenacity import retry, stop_after_attempt, wait_exponential

from lumagen.models.tts.base import TTSModel
from lumagen.utils.file_utils import save_bytes_to_file
from lumagen.utils.logger import WorkflowLogger

SAMPLE_RATE = 44100


class AudioGenerator:
    def __init__(self, tts_model: TTSModel, script: str):
        self.tts_model = tts_model
        self.script = script
        self.logger = WorkflowLogger()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    async def generate_audio_and_save_to_file(
        self, filepath: str
    ) -> Tuple[FilePath, float]:
        audio_data = await self.tts_model.generate_audio(self.script, SAMPLE_RATE)
        audio_data = self.convert_to_wav(audio_data)

        # Calculate the duration of the audio
        audio_array = np.frombuffer(audio_data, dtype=np.float32)
        duration = len(audio_array) / SAMPLE_RATE
        file_path = save_bytes_to_file(audio_data, filepath)
        return file_path, duration

    def convert_to_wav(self, audio_data: bytes) -> bytes:
        # Convert bytes to numpy array
        audio_array = np.frombuffer(audio_data, dtype=np.float32)

        # Create a BytesIO object to hold the WAV data
        wav_buffer = io.BytesIO()

        # Write the numpy array to the BytesIO object as a WAV file
        sf.write(wav_buffer, audio_array, SAMPLE_RATE, format="WAV", subtype="FLOAT")

        # Get the WAV data as bytes
        wav_buffer.seek(0)
        wav_bytes = wav_buffer.getvalue()

        return wav_bytes
