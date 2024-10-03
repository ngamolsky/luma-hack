import os
from typing import Optional

import aiohttp

IDEOGRAM_URL = "https://api.ideogram.ai/generate"

IDEOGRAM_HEADERS = {
    "Api-Key": os.getenv("IDEOGRAM_API_KEY"),
    "Content-Type": "application/json",
}


async def generate_ideo_image(prompt: str, starting_image_url: Optional[str] = None):
    image_request = {
        "image_request": {
            "prompt": prompt,
            "model": "V_2",
            "magic_prompt_option": "AUTO",
            "aspect_ratio": "ASPECT_9_16",
        }
    }

    if starting_image_url:
        image_request["image_request"]["keyframe"] = {
            "frame0": {"type": "image", "url": starting_image_url}
        }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            IDEOGRAM_URL, json=image_request, headers=IDEOGRAM_HEADERS
        ) as response:
            return await response.json()
