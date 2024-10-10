from typing import List, Literal, Optional

from pydantic import BaseModel, Field

MEME_CONTENT_DESCRIPTION = """

If the scene is of type "meme", you must select a meme from the database.
Otherwise, the meme field should be left empty.

The database will contain a list of meme objects with the following schema:

```
name: string
description: string
image_url: string
```
"""


TWITTER_CONTENT_DESCRIPTION = """
If the scene is of type "twitter", you must select a twitter URL from the source material.

Otherwise, the twitter field should be left empty.

A scene of type "twitter" is a scene where the script chunk references a tweet.

Never use the same tweet twice in a storyboard.

"""


GENERIC_CONTENT_DESCRIPTION = """
If the scene is of type "generic", you must provide an image description that would work well for the script chunk.
Otherwise, the generic field should be left empty.

A scene of type "generic" is a scene that is a place holder for a more generic scene that isn't a tweet or a meme.

We can create simple scenes based on a starter image, so please give us an image description that would work well for the script chunk.
"""


class MemeContent(BaseModel):
    name: str = Field(..., description="The name of the meme")
    image_url: str = Field(..., description="The image url of the meme")
    description: str = Field(..., description="The description of the meme")


class TwitterContent(BaseModel):
    tweet_url: str


class GenericVideoContent(BaseModel):
    image_description: str


class Scene(BaseModel):
    type: Literal["meme", "twitter", "generic"] = Field(
        ..., description="The type of scene: 'meme', 'twitter', or 'generic'"
    )

    script_chunk: str = Field(..., description="The script chunk for the scene")

    meme: Optional[MemeContent] = Field(None, description=MEME_CONTENT_DESCRIPTION)
    twitter: Optional[TwitterContent] = Field(
        None, description=TWITTER_CONTENT_DESCRIPTION
    )
    generic: Optional[GenericVideoContent] = Field(
        None, description=GENERIC_CONTENT_DESCRIPTION
    )


STORYBOARD_PROMPT = """
You are tasked with creating a storyboard for a short-form video. You will be provided with a script, the desired video duration, reference material used to create the script, and a meme database.

Your objective is to break down the script into a sequence of scenes.

## Scene Types: 

Use three types of scenes - "meme", "twitter", and "generic".

## Scene Selection:

Choose the most appropriate scene type for the script chunk. 

IMPORTANT: Only use the twitter scene type if the script chunk references a tweet AND the source material contains a tweet or X URL.


## Script Chunking:

Split the script into chunks that are between 10 and 20 words. 

IMPORTANT: The entire script should be represented in the storyboard in script chunks. Don't change or cut anything out.

## Meme Selection:

If the scene is of type "meme", you must select a meme from the database.
Otherwise, the meme field should be left empty.

The database will contain a list of meme objects with the following schema:

```
name: string
description: string
image_url: string

```

Only use memes from the meme database, and always include the image_url from the meme database.

Never use the same meme twice in a storyboard.

## Twitter Selection:

A scene of type "twitter" is a scene where the script chunk references a tweet. 
If it does, find the most relevant tweet from the source material.

If the scene is of type "twitter", you must select a twitter URL from the source material.
Otherwise, the twitter field should be left empty.

IMPORTANT: Never use the same tweet twice in a storyboard.

It is completely ok to generate an entire storyboard without using the twitter scene type.

## Generic Selection:

If the scene is of type "generic", you must provide an image description that would work well for the script chunk.
Otherwise, the generic field should be left empty.

A scene of type "generic" is a scene that is a place holder for a more generic scene that isn't a tweet or a meme.

We can create simple scenes based on a starter image, so please give us an image description that would work well for the script chunk.


# Script

```
{script}
```
    

# Duration

```
{duration}  
```

# Reference Material

```
{reference_material}
```

# Meme Database

```
{meme_database}
```
"""


class GenerateStoryboardPrompt(BaseModel):
    script: str = Field(..., description="The script for the video")
    duration: float = Field(..., description="The duration of the video in seconds")
    reference_material: str = Field(
        ..., description="The reference material used to create the script"
    )
    meme_database: List[MemeContent] = Field(
        ..., description="The meme database to choose from"
    )

    @property
    def prompt(self):
        return STORYBOARD_PROMPT.format(
            script=self.script,
            duration=self.duration,
            reference_material=self.reference_material,
            meme_database=self.meme_database,
        )


class StoryboardSchema(BaseModel):
    scenes: List[Scene]
