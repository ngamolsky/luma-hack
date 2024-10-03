from typing import List, Literal, Union

from pydantic import BaseModel, Field, field_validator

MEME_SCENE_DESCRIPTION = """
A scene of type "meme" is a scene that pics the most relevant meme from a database of memes we will provide.
The database will contain a list of meme objects with the following schema:

```
name: string
description: string
image_url: string
```

We want you to output the meme name and image_url. The image URL needs to be a valid URL to an image.

Never user the same meme twice in a storyboard.

```
{meme_database}
```
"""


class MemeScene(BaseModel):
    name: str
    image_url: str
    description: str


TWITTER_SCENE_DESCRIPTION = """
A scene of type "twitter" is a scene that is a static image of a tweet.

It needs to stay on the screen for long enough to be read, which depends on the length of the tweet.

Please provide the URL to the tweet.

Never use the same tweet twice in a storyboard.
"""


class TwitterScene(BaseModel):
    tweet_url: str


GENERIC_VIDEO_SCENE_DESCRIPTION = """
A scene of type "generic" is a scene that is a place holder for a more generic scene that isn't a tweet or a meme.

We can create simple scenes based on a starter image, so please give us an image description. 

Please provide the description of the image and the duration it should stay on the screen.

"""


class GenericVideoScene(BaseModel):
    image_description: str


class Scene(BaseModel):
    type: Literal["meme", "twitter", "generic"] = Field(
        ..., description="The type of scene: 'meme', 'twitter', or 'generic'"
    )
    content: Union[MemeScene, TwitterScene, GenericVideoScene] = Field(
        ..., description="The content of the scene"
    )

    script_chunk: str = Field(..., description="The script chunk for the scene")

    duration: float = Field(..., description="The duration of the scene in seconds")

    @field_validator("content")
    def validate_content_type(cls, v, values):
        data = values.data
        if "type" in data:
            if data["type"] == "meme" and not isinstance(v, MemeScene):
                raise ValueError("Content must be a MemeScene for type 'meme'")
            elif data["type"] == "twitter" and not isinstance(v, TwitterScene):
                raise ValueError("Content must be a TwitterScene for type 'twitter'")
            elif data["type"] == "generic" and not isinstance(v, GenericVideoScene):
                raise ValueError(
                    "Content must be a GenericVideoScene for type 'generic'"
                )
        return v


STORYBOARD_PROMPT = """
You will be given a a script for a short form video, the duration the video should be, and the reference material used to create the script.

Assume the script will take up the entire duration of the video.

Create a storyboard for this video. The storyboard should be a list of scenes. 

There are three types of scenes: "meme", "twitter", and "generic".

Break the script into scenes. Each scene should be no more than 3 seconds, and should contain what the narrator says.

Pick the most apprropriate scene type for each scene.

Never put two "twitter" scenes in a row.

You should also output a duration for each scene, depending on the lenght of the script chunk.

The durations for each scene should add up to the total duration of the video.

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

# Memes
```
{memes}
```
"""


class GenerateStoryboardPrompt(BaseModel):
    script: str = Field(..., description="The script for the video")
    duration: float = Field(..., description="The duration of the video in seconds")
    reference_material: str = Field(
        ..., description="The reference material used to create the script"
    )
    memes: List[MemeScene] = Field(
        ..., description="The list of memes to use for the video"
    )

    @property
    def prompt(self):
        return STORYBOARD_PROMPT.format(
            script=self.script,
            duration=self.duration,
            reference_material=self.reference_material,
            memes=self.memes,
        )


class StoryboardSchema(BaseModel):
    scenes: List[Scene]
