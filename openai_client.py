import json
import os
from typing import List, Literal, Union

from openai import OpenAI
from pyairtable import Api
from pydantic import BaseModel, Field

api = Api(os.environ["AIRTABLE_API_KEY"])
table = api.table("appi0R6F1ckhy8JpZ", "table1")

client = OpenAI()
# Reformat the data
records = table.all()

# Reformat the data
reformatted_data = {}

for record in records:
    name = record["fields"].get("Name", "")
    notes = record["fields"].get("Notes", "")
    image_url = ""

    # Get the first image URL if available
    if "image" in record["fields"] and record["fields"]["image"]:
        image_url = record["fields"]["image"][0].get("url", "")

    reformatted_data[name] = {"notes": notes, "image_url": image_url}


with open("source.md", "r") as file:
    SOURCE_MARKDOWN = file.read()

STORYBOARD_PROMPT = """
I will provide you with a source string that represents a news article.

Your job is to create a storyboard for a video that will be generated from the news article.

The storyboard should be an array of objects, where each object represents a starting frame for a video, which will then be animated to create a video segment with a fixed duration.

Don't put two of the same type in a row, and use at least one of each type.

I will also supply a total duration for the video, generate enough frames to fill the duration given a duration of 2 seconds for each frame. Print out the total number of frames you will generate.
"""

TYPE_DESCRIPTION = {
    "meme": "a meme image, that will be animated",
    "twitter_screenshot": "a screenshot of a twitter thread",
    "stock_video": "a stock video based on an initial image",
}

STOCK_IMAGE_DESCRIPTION = """
A description of an image that will be used as a prompt to generate a stock image. We want the image to be photo realistic, showing a scene that matches the source markdown in some way.
"""


class StoryboardItem(BaseModel):
    type: Literal["meme", "twitter_screenshot", "stock_video"] = Field(
        ..., description=str(TYPE_DESCRIPTION)
    )
    stock_image_description: Union[str, None] = Field(
        ..., description=STOCK_IMAGE_DESCRIPTION
    )
    twitter_url: Union[str, None] = Field(
        ...,
        description="The url of the twitter thread to screenshot if the type is twitter_screenshot. Leave blank if the type is not twitter_screenshot. Make sure the tweet is in the source markdown.",
    )


class Storyboard(BaseModel):
    items: List[StoryboardItem] = Field(..., description="The storyboard items")
    total_duration: int = Field(
        ..., description="The total duration of the video in seconds"
    )
    total_frames: int = Field(
        ..., description="The total number of frames in the video"
    )


def generate_storyboard(source_markdown: str, total_duration: int) -> Storyboard:
    # TODO: Here we need ensure that the number of storyboard items is the total duration / 2
    # Often there will not be enough content to fill the duration.
    # Also we should ensure that tweets don't get repeated.
    response = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "system", "content": STORYBOARD_PROMPT},
            {"role": "user", "content": source_markdown},
            {
                "role": "user",
                "content": f"The total duration of the video is {total_duration} seconds.",
            },
        ],
        response_format=Storyboard,
    )

    return response.choices[0].message.parsed


class ImageUrl(BaseModel):
    url: str


def find_meme(meme_description: str) -> str:
    dict_memes = json.dumps(reformatted_data)
    model_response = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "system", "content": "You are a helpful assistant"},
            {
                "role": "user",
                "content": f"Given the following memes {dict_memes}, give the closest matching meme URL to {meme_description}",
            },
        ],
        response_format=ImageUrl,
    )
    meme_url = model_response.choices[0].message.parsed
    return meme_url
