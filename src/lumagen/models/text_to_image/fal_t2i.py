import os

import fal_client

from lumagen.models.text_to_image.base import AspectRatio, TextToImageModel
from lumagen.utils.logger import WorkflowLogger

logger = WorkflowLogger()

FAL_ASPECT_RATIO_MAP = {
    AspectRatio.SQUARE: "square",
    AspectRatio.LANDSCAPE: "landscape_16_9",
    AspectRatio.PORTRAIT: "portrait_16_9",
    AspectRatio.WIDE: "landscape_16_9",  # Fal doesn't have a wider option
    AspectRatio.ULTRAWIDE: "landscape_16_9",  # Fal doesn't have an ultrawide option
}


class FalTextToImageModel(TextToImageModel):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("FAL_KEY")
        if not self.api_key:
            raise ValueError("FAL_KEY is not set")

    async def generate_image(
        self, prompt: str, aspect_ratio: AspectRatio = AspectRatio.SQUARE
    ) -> str:
        """
        Generate an image based on the given text prompt using Fal API.

        Args:
            prompt (str): The text description of the image to generate.
            aspect_ratio (AspectRatio): The desired aspect ratio for the generated image. Defaults to SQUARE.

        Returns:
            str: URL to the generated image.
        """
        fal_aspect_ratio = FAL_ASPECT_RATIO_MAP.get(aspect_ratio, "square")

        handler = await fal_client.submit_async(
            "fal-ai/flux/dev",
            arguments={
                "prompt": prompt,
                "image_size": fal_aspect_ratio,
            },
        )

        result = await handler.get()
        return result["images"][0]["url"]
