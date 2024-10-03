import os
from typing import List

from pyairtable import Api

from lumagen.storyboard_generation.prompt import MemeScene


def get_memes() -> List[MemeScene]:
    airtable_api = Api(os.environ["AIRTABLE_API_KEY"])
    table = airtable_api.table("appi0R6F1ckhy8JpZ", "table1")
    records = table.all()
    memes = []
    for record in records:
        name = record["fields"].get("Name", "")
        notes = record["fields"].get("Notes", "")
        image_url = ""

        # Get the first image URL if available
        if "image" in record["fields"] and record["fields"]["image"]:
            image_url = record["fields"]["image"][0].get("url", "")

        if not image_url:
            continue

        memes.append(MemeScene(name=name, description=notes, image_url=image_url))

    return memes
