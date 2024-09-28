import os
from io import BytesIO

import numpy as np
import requests
from PIL import Image


def create_meme_backdrop(meme_url, backdrop_width=1080, backdrop_height=1920):
    # Download the meme image
    response = requests.get(meme_url)
    if response.status_code != 200:
        print(f"Failed to download image. Status code: {response.status_code}")
        return None

    content_type = response.headers.get("Content-Type", "")
    if not content_type.startswith("image"):
        print(f"The URL does not point to an image. Content-Type: {content_type}")
        return None

    try:
        meme_image = Image.open(BytesIO(response.content))
    except Exception as e:
        print(f"Failed to open image: {str(e)}")
        return None

    # Create a 9:16 aspect ratio backdrop
    img_array = np.array(meme_image)
    average_color = np.mean(img_array)
    background_color = (0, 0, 0) if average_color > 128 else (255, 255, 255)

    backdrop = Image.new("RGB", (backdrop_width, backdrop_height), background_color)

    # Calculate the maximum size for the meme image to fit the backdrop
    meme_aspect_ratio = meme_image.width / meme_image.height
    backdrop_aspect_ratio = backdrop_width / backdrop_height

    if meme_aspect_ratio > backdrop_aspect_ratio:
        # Meme is wider, fit to width
        new_width = backdrop_width
        new_height = int(backdrop_width / meme_aspect_ratio)
    else:
        # Meme is taller, fit to height
        new_height = backdrop_height
        new_width = int(backdrop_height * meme_aspect_ratio)

    # Resize meme image to fit within the backdrop while maintaining aspect ratio
    meme_image = meme_image.resize((new_width, new_height), Image.LANCZOS)

    # Calculate position to center the meme image
    x = (backdrop_width - new_width) // 2
    y = (backdrop_height - new_height) // 2

    # Paste the meme image onto the backdrop
    backdrop.paste(meme_image, (x, y))

    # Save the combined image to a BytesIO object
    combined_image_io = BytesIO()
    backdrop.save(combined_image_io, format="PNG")
    combined_image_io.seek(0)

    # Save the combined image to the memes directory

    # Ensure the memes directory exists
    memes_dir = "memes"
    os.makedirs(memes_dir, exist_ok=True)

    # Generate a unique filename
    import uuid

    filename = f"meme_{uuid.uuid4()}.png"
    filepath = os.path.join(memes_dir, filename)

    # Save the image
    with open(filepath, "wb") as f:
        f.write(combined_image_io.getvalue())

    print(f"Meme saved to: {filepath}")

    return filepath
