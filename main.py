import asyncio
import os
import time
from datetime import timedelta
from typing import List

import load_env  # noqa: F401
from cloudflare import upload_to_cloudflare
from combine_clips import combine_clips
from generate_audio import generate_audio
from ideogram import generate_ideo_image
from luma import generate_luma_video, poll_generation
from meme import create_meme_backdrop
from mux_audio_and_video import mux_audio_and_video
from openai_client import (
    SOURCE_MARKDOWN,
    StoryboardItem,
    find_meme,
    generate_storyboard,
)
from twitter_capture import capture_tweets
from utils import clear_directory

print("Importing modules and loading environment variables")
start_time = time.time()


async def process_item(item: StoryboardItem):
    item_start_time = time.time()
    print(f"Processing item of type: {item.type}")
    if item.type == "twitter_screenshot":
        raise ValueError("Twitter screenshots dont make videos")
    elif item.type == "stock_video":
        print("Generating ideogram image for stock video")
        ideogram_response = await generate_ideo_image(item.stock_image_description)
        print("Generating Luma video for stock video")
        luma_video_id = await generate_luma_video(
            prompt=None, start_image_url=ideogram_response["data"][0]["url"]
        )

    elif item.type == "meme":
        print("Finding meme URL")
        meme_url = find_meme(item.stock_image_description)
        print("Found meme URL", meme_url)

        print("Creating meme backdrop")
        meme_backdrop = create_meme_backdrop(meme_url.url)
        print("Uploading meme to Cloudflare")
        url = await upload_to_cloudflare(meme_backdrop)
        print("Generating Luma video for meme")
        luma_video_id = await generate_luma_video(prompt=None, start_image_url=url)
    print("Polling for video generation completion")
    result = await poll_generation(luma_video_id)
    item_end_time = time.time()
    print(
        f"Item processing completed in {timedelta(seconds=item_end_time - item_start_time)}"
    )
    return result


async def fetch_all_resources(processed_items: List[StoryboardItem]):
    fetch_start_time = time.time()
    print("Fetching all resources")
    tweet_urls = [
        item.twitter_url
        for item in processed_items
        if item.type == "twitter_screenshot"
    ]
    image_items = [
        item for item in processed_items if item.type in ["stock_video", "meme"]
    ]

    print(f"Found {len(tweet_urls)} tweet URLs and {len(image_items)} image items")

    tweet_tasks = [capture_tweets(tweet_urls)] if tweet_urls else []
    image_tasks = [process_item(item) for item in image_items]
    print("Gathering all tasks")
    results = await asyncio.gather(*tweet_tasks, *image_tasks)

    tweet_files = results[0] if tweet_urls else []
    video_results = results[1:] if image_items else []

    print(
        f"Fetched {len(tweet_files)} tweet files and {len(video_results)} video results"
    )
    fetch_end_time = time.time()
    print(
        f"Resource fetching completed in {timedelta(seconds=fetch_end_time - fetch_start_time)}"
    )
    return tweet_files, video_results


async def main():
    main_start_time = time.time()
    print("Starting main function")
    print("Generating storyboard")
    duration_seconds = await generate_audio(SOURCE_MARKDOWN)
    storyboard = generate_storyboard(SOURCE_MARKDOWN, duration_seconds)

    print("Generated storyboard")
    tweet_files, video_results = await fetch_all_resources(storyboard.items)

    combined_resources = []

    tweet_index = 0
    image_index = 0

    print("Processing storyboard items")
    for item in storyboard.items:
        if item.type == "twitter_screenshot" and item.twitter_url:
            tweet_id = item.twitter_url.split("/")[-1]

            if not any(tweet_id in tweet_file for tweet_file in tweet_files):
                continue
            url = tweet_files[tweet_index]
            print(f"Adding tweet screenshot: {url}")
            combined_resources.append(
                {
                    "type": "image",
                    "url": url,
                    "duration": 2,
                }
            )
            tweet_index += 1
        elif item.type in ["stock_video", "meme"]:
            print(f"Adding video: {video_results[image_index].assets.video}")
            combined_resources.append(
                {
                    "type": "video",
                    "url": video_results[image_index].assets.video,
                    "duration": 2,
                }
            )
            image_index += 1

    memes_dir = "memes"
    tweets_dir = "tweets"

    print("Clearing directories")
    if os.path.exists(memes_dir):
        clear_directory(memes_dir)
        print(f"Cleared contents of {memes_dir} directory")
    else:
        print(f"{memes_dir} directory does not exist")

    if os.path.exists(tweets_dir):
        clear_directory(tweets_dir)
        print(f"Cleared contents of {tweets_dir} directory")
    else:
        print(f"{tweets_dir} directory does not exist")

    print("Combining clips")
    combine_clips(combined_resources, output_file="output.mp4")
    print("Finished combining clips")
    await mux_audio_and_video()
    main_end_time = time.time()
    print(
        f"Main function completed in {timedelta(seconds=main_end_time - main_start_time)}"
    )


if __name__ == "__main__":
    script_start_time = time.time()
    print("Starting script")
    asyncio.run(main())
    script_end_time = time.time()
    print(
        f"Script completed in {timedelta(seconds=script_end_time - script_start_time)}"
    )
