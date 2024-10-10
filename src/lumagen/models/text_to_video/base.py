from abc import ABC, abstractmethod
from typing import Optional, Union

from lumagen.utils.image_utils import AspectRatio


class TextToVideoModel(ABC):
    @abstractmethod
    async def generate_video(
        self,
        prompt: Optional[str] = None,
        start_image: Optional[Union[bytes, str]] = None,
        end_image: Optional[Union[bytes, str]] = None,
        aspect_ratio: AspectRatio = AspectRatio.PORTRAIT,
    ) -> Union[bytes, str]:
        """
        Generate a video based on the given parameters.

        Args:
            prompt (Optional[str]): The text description of the video to generate.
            start_image (Optional[Union[bytes, str]]): The starting image for the video, either as raw bytes or a file path.
            end_image (Optional[Union[bytes, str]]): The ending image for the video, either as raw bytes or a file path.
            aspect_ratio (AspectRatio): The desired aspect ratio for the generated video. Defaults to PORTRAIT.

        Returns:
            Union[bytes, str]: Either the raw video data as bytes or a URL to the generated video.
        """
        pass
