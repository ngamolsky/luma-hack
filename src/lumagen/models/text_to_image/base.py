from abc import ABC, abstractmethod
from typing import Union

from lumagen.utils.image_utils import AspectRatio


class TextToImageModel(ABC):
    @abstractmethod
    async def generate_image(
        self, prompt: str, aspect_ratio: AspectRatio = AspectRatio.SQUARE
    ) -> Union[bytes, str]:
        """
        Generate an image based on the given text prompt and aspect ratio.

        Args:
            prompt (str): The text description of the image to generate.
            aspect_ratio (AspectRatio): The desired aspect ratio for the generated image. Defaults to SQUARE.

        Returns:
            Union[bytes, str]: Either the raw image data as bytes or a URL to the generated image.
        """
        pass
