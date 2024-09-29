import time
from typing import Optional

from lumaai import AsyncLumaAI
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

MAX_ATTEMPTS = 30
POLL_INTERVAL = 5

client = AsyncLumaAI()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(1),
    retry=retry_if_exception_type(Exception),
)
async def generate_luma_video(
    prompt: Optional[str] = None,
    start_image_url: Optional[str] = None,
    aspect_ratio: str = "16:9",
):
    generation = await client.generations.create(
        prompt=prompt,
        keyframes={"frame0": {"type": "image", "url": start_image_url}}
        if start_image_url
        else {},
        aspect_ratio=aspect_ratio,
    )
    return generation.id


async def poll_generation(
    generation_id, max_attempts=MAX_ATTEMPTS, delay=POLL_INTERVAL
):
    for attempt in range(max_attempts):
        print(
            f"Attempt {attempt + 1}/{max_attempts} to poll generation {generation_id}"
        )
        status = await client.generations.get(generation_id)
        print(f"Current status: {status.state}")
        if status.state == "completed":
            print(f"Generation {generation_id} completed successfully")
            return status
        elif status.state == "failed":
            print(f"Generation {generation_id} failed")
            raise Exception(f"Generation failed: {status.failure_reason}")

        print(f"Waiting {delay} seconds before next attempt")
        time.sleep(delay)

    print(f"Max attempts ({max_attempts}) reached for generation {generation_id}")
    raise Exception("Max attempts reached")
