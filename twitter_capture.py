import asyncio
import os
from typing import List

from PIL import Image
from tweetcapture import TweetCapture

from cloudflare import upload_to_cloudflare


async def capture_tweet(url, port):
    try:
        tweet = TweetCapture()
        tweet.add_chrome_argument(f"--remote-debugging-port={port}")

        # Create 'tweets' directory if it doesn't exist
        os.makedirs("tweets", exist_ok=True)

        # Generate a filename based on the URL and username
        username = url.split("/")[
            -3
        ]  # Assuming the URL format is twitter.com/username/status/id
        filename = f"tweets/{username}_{url.split('/')[-1]}.png"

        await tweet.screenshot(url, path=filename, overwrite=True)

        return filename
    except Exception as e:
        print(f"Error capturing tweet {url}: {str(e)}")
        return None


def create_backdrop(tweet_image_path, output_path):
    tweet_image = Image.open(tweet_image_path)
    tweet_width, tweet_height = tweet_image.size

    # Add padding
    padding = 50
    tweet_width_padded = tweet_width + 2 * padding
    tweet_height_padded = tweet_height + 2 * padding

    # Create a 9:16 backdrop
    backdrop_width = max(tweet_width_padded, int(tweet_height_padded * 9 / 16))
    backdrop_height = max(tweet_height_padded, int(tweet_width_padded * 16 / 9))

    # Determine background color based on tweet image
    tweet_colors = tweet_image.getcolors(tweet_image.size[0] * tweet_image.size[1])
    avg_color = sum(color[0] * color[1][0] for color in tweet_colors) / sum(
        color[0] for color in tweet_colors
    )
    bg_color = "white" if avg_color < 128 else "black"

    backdrop = Image.new("RGB", (backdrop_width, backdrop_height), bg_color)

    # Calculate position to center the tweet
    x = (backdrop_width - tweet_width_padded) // 2
    y = (backdrop_height - tweet_height_padded) // 2

    # Create a new image with padding for shadow
    padded_tweet = Image.new(
        "RGBA", (tweet_width_padded, tweet_height_padded), (0, 0, 0, 0)
    )

    # Paste the original tweet image
    padded_tweet.paste(tweet_image, (padding, padding))

    # Paste the padded tweet onto the backdrop
    backdrop.paste(padded_tweet, (x, y), padded_tweet)

    backdrop.save(output_path)
    return output_path


async def capture_tweets(tweet_urls: List[str | None]):
    port = 9222
    tasks = []
    for url in tweet_urls:
        tasks.append(asyncio.create_task(capture_tweet(url, port)))
        port += 1

    filenames = []
    for task in asyncio.as_completed(tasks):
        try:
            filename = await task
            if filename:
                output_filename = f"{os.path.splitext(filename)[0]}_backdrop.png"
                backdrop_filename = create_backdrop(filename, output_filename)
                url = await upload_to_cloudflare(backdrop_filename)
                filenames.append(url)
        except Exception as e:
            print(f"Error processing task: {str(e)}")

    return filenames
