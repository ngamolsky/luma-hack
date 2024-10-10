import os
from typing import Union

import aiohttp

from lumagen.models.text_to_image.base import AspectRatio, TextToImageModel
from lumagen.utils.logger import WorkflowLogger

logger = WorkflowLogger()

IDEOGRAM_URL = "https://api.ideogram.ai/generate"

IDEOGRAM_ASPECT_RATIO_MAP = {
    AspectRatio.SQUARE: "ASPECT_1_1",
    AspectRatio.LANDSCAPE: "ASPECT_16_9",
    AspectRatio.PORTRAIT: "ASPECT_9_16",
    AspectRatio.WIDE: "ASPECT_21_9",
    AspectRatio.ULTRAWIDE: "ASPECT_32_9",
}


class IdeogramTextToImageModel(TextToImageModel):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("IDEOGRAM_API_KEY")
        if not self.api_key:
            raise ValueError("IDEOGRAM_API_KEY is not set")

        self.headers = {
            "Api-Key": self.api_key,
            "Content-Type": "application/json",
        }

    async def generate_image(
        self, prompt: str, aspect_ratio: AspectRatio = AspectRatio.SQUARE
    ) -> Union[bytes, str]:
        """
        Generate an image based on the given text prompt using Ideogram API.

        Args:
            prompt (str): The text description of the image to generate.
            aspect_ratio (AspectRatio): The desired aspect ratio for the generated image. Defaults to SQUARE.

        Returns:
            Union[bytes, str]: URL to the generated image.
        """
        image_request = {
            "image_request": {
                "prompt": prompt,
                "model": "V_2",
                "magic_prompt_option": "AUTO",
                "aspect_ratio": IDEOGRAM_ASPECT_RATIO_MAP[aspect_ratio],
            }
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    IDEOGRAM_URL, json=image_request, headers=self.headers
                ) as response:
                    result = await response.json()

                    if "data" in result and result["data"]:
                        image_data = result["data"][0]
                        if "url" in image_data:
                            return image_data["url"]

                    logger.error(
                        f"Ideogram API error: {result.get('error', 'Unknown error')}",
                    )
                    raise Exception("Failed to generate image")
        except Exception as e:
            logger.error(f"Error generating image with Ideogram: {str(e)}")
            raise
