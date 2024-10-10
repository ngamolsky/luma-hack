import io
import os

from cartesia import AsyncCartesia

from lumagen.models.tts.base import TTSModel
from lumagen.utils.logger import WorkflowLogger

TIMEOUT = 60


class CartesiaTTSModel(TTSModel):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("CARTESIA_API_KEY")
        if not self.api_key:
            raise ValueError("CARTESIA_API_KEY is not set")

        self.client = AsyncCartesia(api_key=api_key, timeout=TIMEOUT)
        self.model_id = "sonic-english"
        self.voice_id = "421b3369-f63f-4b03-8980-37a44df1d4e8"
        self.language = "en"
        self.logger = WorkflowLogger()

    async def generate_audio(self, script: str, sample_rate: int) -> bytes:
        audio_buffer = io.BytesIO()

        async for output in await self.client.tts.sse(
            model_id=self.model_id,
            transcript=script,
            voice_id=self.voice_id,
            output_format={
                "container": "raw",
                "encoding": "pcm_f32le",
                "sample_rate": sample_rate,
            },
            language=self.language,
        ):  # type: ignore
            audio_buffer.write(output["audio"])

        audio_buffer.seek(0)
        audio_data = audio_buffer.getvalue()
        await self.client.close()
        return audio_data
