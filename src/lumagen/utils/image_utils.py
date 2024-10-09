import asyncio
import io
from concurrent.futures import ThreadPoolExecutor
from enum import Enum

import httpx
from PIL import Image, ImageStat
from tenacity import retry, stop_after_attempt, wait_exponential

# Create a thread pool for CPU-bound image processing tasks
image_thread_pool = ThreadPoolExecutor(max_workers=4)


class AspectRatio(Enum):
    SQUARE = "1:1"
    LANDSCAPE = "16:9"
    PORTRAIT = "9:16"
    WIDE = "21:9"
    ULTRAWIDE = "32:9"


TARGET_RESOLUTION = (720, 1280)  # HD resolution


def resize_and_pad_image(
    image: Image.Image,
    aspect_ratio: AspectRatio,
    padding_percent: float = 0.05,  # 5% padding by default
) -> Image.Image:
    """
    Process an image by resizing it to fit within the target resolution while maintaining
    its original aspect ratio, then adding padding to reach the target aspect ratio.

    Args:
        image (Image.Image): The input image.
        aspect_ratio (AspectRatio): The desired aspect ratio for the final image.
        padding_percent (float): The minimum percentage of padding to add around the image. Default is 0.05 (5%).

    Returns:
        Image.Image: The processed image with HD resolution and the specified aspect ratio and minimum padding.
    """
    # Calculate target resolution based on aspect ratio
    ratio = [int(x) for x in aspect_ratio.value.split(":")]
    target_resolution = (
        TARGET_RESOLUTION[0],
        int(TARGET_RESOLUTION[0] * ratio[1] / ratio[0]),
    )

    # Calculate the maximum size the image can be while maintaining its aspect ratio
    img_ratio = image.width / image.height
    if img_ratio > target_resolution[0] / target_resolution[1]:
        new_width = int(target_resolution[0] * (1 - 2 * padding_percent))
        new_height = int(new_width / img_ratio)
    else:
        new_height = int(target_resolution[1] * (1 - 2 * padding_percent))
        new_width = int(new_height * img_ratio)

    # Resize the input image
    resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Determine the best contrasting background color
    bg_color = get_contrasting_color(image)

    # Create a new image with the target resolution
    new_image = Image.new("RGB", target_resolution, bg_color)

    # Calculate position to paste the resized image
    paste_x = (target_resolution[0] - new_width) // 2
    paste_y = (target_resolution[1] - new_height) // 2

    # Paste the resized image onto the new image
    new_image.paste(resized_image, (paste_x, paste_y))

    return new_image


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


async def save_image_to_file(image: Image.Image, filepath: str) -> str:
    """
    Save an image to a file asynchronously.

    Args:
        image (Image.Image): The image to save.
        filepath (str): The path to save the image to.

    Returns:
        str: The filepath where the image was saved.
    """
    return await asyncio.get_event_loop().run_in_executor(
        image_thread_pool, lambda: image.save(filepath) or filepath
    )


async def open_image_from_file(filepath: str) -> Image.Image:
    """
    Open an image from a file asynchronously.

    Args:
        filepath (str): The path to the image file.

    Returns:
        Image.Image: The opened image.
    """
    return await asyncio.get_event_loop().run_in_executor(
        image_thread_pool, Image.open, filepath
    )


async def resize_and_pad_image_async(
    image: Image.Image,
    aspect_ratio: AspectRatio,
    padding_percent: float = 0.05,
) -> Image.Image:
    return await asyncio.get_event_loop().run_in_executor(
        image_thread_pool,
        resize_and_pad_image,
        image,
        aspect_ratio,
        padding_percent,
    )


def get_contrasting_color(image: Image.Image) -> tuple:
    """
    Determine the best contrasting color (black or white) for the image.

    Args:
        image (Image.Image): The input image.

    Returns:
        tuple: RGB values for the contrasting color (black or white).
    """
    stat = ImageStat.Stat(image)
    avg_brightness = sum(stat.mean[:3]) / 3
    return (0, 0, 0) if avg_brightness > 127 else (255, 255, 255)
