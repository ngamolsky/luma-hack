import time
from typing import Literal, Optional, Union

from lumaai import NOT_GIVEN, AsyncLumaAI
from lumaai.types.generation_create_params import Keyframes
from tenacity import retry, stop_after_attempt, wait_exponential

from lumagen.utils.logger import WorkflowLogger

from .base import AspectRatio, TextToVideoModel

MAX_ATTEMPTS = 30
POLL_INTERVAL = 5


LUMA_ASPECT_RATIO = Literal["1:1", "16:9", "9:16", "4:3", "3:4", "21:9", "9:21"]

LUMA_ASPECT_RATIO_MAP: dict[AspectRatio, LUMA_ASPECT_RATIO] = {
    AspectRatio.SQUARE: "1:1",
    AspectRatio.LANDSCAPE: "16:9",
    AspectRatio.PORTRAIT: "9:16",
    AspectRatio.WIDE: "21:9",
}


class LumaAITextToVideoModel(TextToVideoModel):
    def __init__(self):
        self.client = AsyncLumaAI()
        self.logger = WorkflowLogger()

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _generate_luma_video(
        self,
        prompt: Optional[str] = None,
        start_image_url: Optional[str] = None,
        end_image_url: Optional[str] = None,
        aspect_ratio: AspectRatio = AspectRatio.PORTRAIT,
    ):
        keyframes: Keyframes = {}
        if start_image_url:
            keyframes["frame0"] = {"type": "image", "url": start_image_url}
        if end_image_url:
            keyframes["frame1"] = {"type": "image", "url": end_image_url}

        generation = await self.client.generations.create(
            prompt=prompt or NOT_GIVEN,
            keyframes=keyframes,
            aspect_ratio=LUMA_ASPECT_RATIO_MAP[aspect_ratio],
        )
        return generation.id

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _poll_generation(
        self,
        generation_id: str,
        max_attempts=MAX_ATTEMPTS,
        delay=POLL_INTERVAL,
    ):
        for attempt in range(max_attempts):
            try:
                status = await self.client.generations.get(generation_id)
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise e
                time.sleep(delay)
                continue

            if status.state == "completed":
                return status
            elif status.state == "failed":
                raise Exception(f"Generation failed: {status.failure_reason}")

            time.sleep(delay)

        raise Exception("Max attempts reached")

    async def generate_video(
        self,
        prompt: Optional[str] = None,
        start_image: Optional[Union[bytes, str]] = None,
        end_image: Optional[Union[bytes, str]] = None,
        aspect_ratio: AspectRatio = AspectRatio.PORTRAIT,
    ) -> str:
        if (start_image and not isinstance(start_image, str)) or (
            end_image and not isinstance(end_image, str)
        ):
            raise ValueError("Both start_image and end_image must be URLs (strings)")

        start_image_url = start_image if isinstance(start_image, str) else None
        end_image_url = end_image if isinstance(end_image, str) else None
        self.logger.debug(
            f"Generating video with prompt: {prompt}, aspect ratio: {aspect_ratio}, start_image_url: {start_image_url}, end_image_url: {end_image_url}",
        )
        generation_id = await self._generate_luma_video(
            prompt=prompt,
            start_image_url=start_image_url,
            end_image_url=end_image_url,
            aspect_ratio=aspect_ratio,
        )

        if not generation_id:
            raise Exception("Generation ID not found")

        result = await self._poll_generation(generation_id)

        video_url = (
            result.assets.video
            if result and result.assets and result.assets.video
            else None
        )
        if not video_url:
            raise Exception("Video URL not found")

        return video_url
