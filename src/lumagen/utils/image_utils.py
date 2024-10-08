import io
from enum import Enum

import httpx
import numpy as np
from PIL import Image
from tenacity import retry, stop_after_attempt, wait_exponential


class AspectRatio(Enum):
    SQUARE = "1:1"
    LANDSCAPE = "16:9"
    PORTRAIT = "9:16"
    WIDE = "21:9"
    ULTRAWIDE = "32:9"


def place_image_on_backdrop(
    image: Image.Image,
    aspect_ratio: AspectRatio,
    padding: float = 0.1,
    target_resolution: tuple = (1024, 1024),
) -> Image.Image:
    """
    Place an image on a backdrop with the given aspect ratio and scale to the target resolution.

    Args:
        image (Image.Image): The input image.
        aspect_ratio (AspectRatio): The desired aspect ratio from the AspectRatio enum.
        padding (float): The padding around the image as a fraction of the shorter dimension. Default is 0.1 (10%).
        target_resolution (tuple): The target resolution (width, height) for the final image. Default is (1024, 1024).

    Returns:
        Image.Image: The image placed on the backdrop and scaled to the target resolution.
    """
    # Parse aspect ratio
    width_ratio, height_ratio = map(int, aspect_ratio.value.split(":"))

    # Calculate target dimensions
    target_ratio = width_ratio / height_ratio
    current_ratio = image.width / image.height

    if current_ratio > target_ratio:
        new_width = image.width
        new_height = int(new_width / target_ratio)
    else:
        new_height = image.height
        new_width = int(new_height * target_ratio)

    # Calculate padding
    pad = int(min(new_width, new_height) * padding)
    new_width += 2 * pad
    new_height += 2 * pad

    # Determine background color
    img_array = np.array(image)
    mean_color = np.mean(img_array)
    background_color = (0, 0, 0) if mean_color > 128 else (255, 255, 255)

    # Create new image with background
    new_image = Image.new("RGB", (new_width, new_height), background_color)

    # Calculate position to paste original image
    paste_x = (new_width - image.width) // 2
    paste_y = (new_height - image.height) // 2

    # Paste original image onto new image
    new_image.paste(image, (paste_x, paste_y))

    # Scale the image to the target resolution, maintaining aspect ratio
    scale_factor = max(target_resolution) / max(new_image.size)
    new_size = (
        int(new_image.width * scale_factor),
        int(new_image.height * scale_factor),
    )
    return new_image.resize(new_size, Image.Resampling.LANCZOS)


def resize_image(image: Image.Image, max_size: int) -> Image.Image:
    """
    Resize an image while maintaining its aspect ratio.

    Args:
        image (Image.Image): The input image.
        max_size (int): The maximum size of the longer dimension.

    Returns:
        Image.Image: The resized image.
    """
    ratio = max_size / max(image.size)
    new_size = (int(image.width * ratio), int(image.height * ratio))
    return image.resize(new_size, Image.Resampling.LANCZOS)


def resize_and_pad_image(
    image: Image.Image,
    aspect_ratio: AspectRatio,
    target_resolution: tuple = (1024, 1024),
) -> Image.Image:
    """
    Process an image by resizing it, placing it on a backdrop, and scaling to the target resolution.

    Args:
        image (Image.Image): The input image.
        aspect_ratio (AspectRatio): The desired aspect ratio from the AspectRatio enum.
        target_resolution (tuple): The target resolution (width, height) for the final image. Default is (1024, 1024).

    Returns:
        Image.Image: The processed image with the specified aspect ratio and target resolution.
    """
    # Parse target aspect ratio
    width_ratio, height_ratio = map(int, aspect_ratio.value.split(":"))
    target_aspect = width_ratio / height_ratio

    # Calculate the dimensions that fit the target aspect ratio
    if target_aspect > 1:  # Landscape or wider
        new_width = target_resolution[0]
        new_height = int(new_width / target_aspect)
    else:  # Portrait or square
        new_height = target_resolution[1]
        new_width = int(new_height * target_aspect)

    # Create a new image with the target aspect ratio
    new_image = Image.new(
        "RGB", (new_width, new_height), (255, 255, 255)
    )  # White background

    # Resize the input image to fit within the new dimensions while maintaining its aspect ratio
    resized_image = resize_image(image, min(new_width, new_height))

    # Calculate position to paste the resized image
    paste_x = (new_width - resized_image.width) // 2
    paste_y = (new_height - resized_image.height) // 2

    # Paste the resized image onto the new image
    new_image.paste(resized_image, (paste_x, paste_y))

    # Scale the image to the target resolution, maintaining aspect ratio
    scale_factor = max(target_resolution) / max(new_image.size)
    new_size = (
        int(new_image.width * scale_factor),
        int(new_image.height * scale_factor),
    )
    final_image = new_image.resize(new_size, Image.Resampling.LANCZOS)

    return final_image


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
)
async def download_image_from_url(url: str) -> Image.Image:
    """
    Download an image from a given URL and return it as a PIL Image.

    Args:
        url (str): The URL of the image to download.

    Returns:
        Image.Image: The downloaded image as a PIL Image object.

    Raises:
        httpx.HTTPError: If there's an error during the HTTP request.
        ValueError: If the content type is not an image.
        PIL.UnidentifiedImageError: If the downloaded data cannot be opened as an image.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("image/"):
            raise ValueError(
                f"URL does not point to an image. Content-Type: {content_type}"
            )

        image_data = response.content
        return Image.open(io.BytesIO(image_data))


def save_image_to_file(image: Image.Image, filepath: str) -> str:
    """
    Save an image to a file.

    Args:
        image (Image.Image): The image to save.
        filepath (str): The path to save the image to.
    """
    image.save(filepath)
    return filepath


def open_image_from_file(filepath: str) -> Image.Image:
    """
    Open an image from a file.

    Args:
        filepath (str): The path to the image file.

    Returns:
        Image.Image: The opened image.
    """
    return Image.open(filepath)
