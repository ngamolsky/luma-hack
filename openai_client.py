import json
import os
from typing import List, Literal, Union

from pyairtable import Api
from pydantic import BaseModel, Field

from openai import OpenAI

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


SOURCE_MARKDOWN = """
**Subject: The Wordpress vs WP Engine Drama**

In a surprising twist of events, the open-source giant WordPress is entangled in a dramatic controversy surrounding its licensing policies aimed squarely at WP Engine, stirring fierce discussions across the web. **"How can you expect any goodwill towards open-source from a community when you insist on enforcing fees?"** This quote captures the mounting frustration many in the tech community feel as these events unfold.

**Background Context**  
WordPress, an open-source content management system, has thrived on its community-driven model for years. However, recently, the organization faced backlash due to new licensing fee structures selectively impacting WP Engine, a leading managed Wordpress host. This move has raised concerns among other hosting companies and developers about potential instability and implications for open-source projects.

---

**The Emergence of Tension**  
The friction began to surface as Automattic, the parent company of WordPress, targeted WP Engine for allegedly not contributing enough to the WordPress ecosystem. **James Ivings** pointed out in one of his tweets, *"You can't go IPO with just a happy customer base, you need to be extracting profits from the entire market (via licensing)."* This sentiment echoes the belief that the motives behind the licensing changes extend beyond simply supporting the open-source initiative. ([source](https://twitter.com/jamesivings/status/1839422193681481750))

---

**Mixed Reactions Among Developers**  
As the news broke, reaction from the community was polarized. While some developers supported Automattic's actions as a means to ensure sustainable growth, others voiced concerns about stifling innovation and creating a hostile environment for open source. One developer remarked that experienced consequences, like **"Being blocked from installing plugins,"** could negatively impact WP Engine's customer base and, subsequently, WordPress's reputation as a stable and reliable platform. ([source](https://twitter.com/arvidkahl/status/1839445536686174387))

---

**The Financial Perspective**  
Conversations centered around revenue models emerged, as seen in **Danny Postmaa's** reflections on his experiences, *"more growth != more support tickets."* He noted that despite their expanding user base, support requests remained steady, indicating a deeper complexity in managing resources amid growth. ([source](https://twitter.com/dannypostmaa/status/1839847665338925293))

There's a growing belief that this drama could lead to significant changes in how hosting services operate with WordPress, resulting in a shift towards licensing strategies that others, like NewFoldDigital, have already embraced. Many felt securing licensing is a smart strategic move, potentially raising the licensing fees for all WP hosting partners. ([source](https://twitter.com/jessethanley/status/1839569215000588641))

---

**Community Support and Reactions**  
While the turmoil has pushed various developers to share their thoughts online, there's a palpable sense of disbelief among users and developers alike. The unforeseen changes raise questions about open-source integrity, As **Arvid Kahl** noted, emphasizing the need for transparency from Automattic in their reasoning. *"I hope the ecosystem is self-healing. I just hope WPE being blocked from installing can be healed without causing massive reputational damage,"* he expressed. ([source](https://twitter.com/arvidkahl/status/1839445536686174387))

---

In conclusion, the **WordPress vs. WP Engine drama** reveals not just a licensing issue but digs into the larger questions surrounding the sustainability of open-source models and the balance of growth, community trust, and corporate influence. As this saga unfolds, the tech community watches closely, ready to respond.
"""

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
