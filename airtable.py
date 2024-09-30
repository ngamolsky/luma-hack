import os

from pyairtable import Api

api = Api(os.environ["AIRTABLE_API_KEY"])
table = api.table("appi0R6F1ckhy8JpZ", "table1")


def get_formatted_meme_data():
    records = table.all()
    # Reformat the data

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

    return reformatted_data
