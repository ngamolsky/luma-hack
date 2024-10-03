from typing import List

from openai import AsyncOpenAI

from .prompt import (
    GenerateStoryboardPrompt,
    MemeScene,
    StoryboardSchema,
)


async def generate_storyboard(
    script: str,
    duration: int,
    reference_material: str,
    memes: List[MemeScene],
) -> StoryboardSchema:
    client = AsyncOpenAI()

    response = await client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[
            {
                "role": "system",
                "content": GenerateStoryboardPrompt(
                    script=script,
                    duration=duration,
                    reference_material=reference_material,
                    memes=memes,
                ).prompt,
            },
        ],
        response_format=StoryboardSchema,
    )

    storyboard = response.choices[0].message.parsed

    if storyboard is None:
        raise ValueError("Failed to generate storyboard")

    return storyboard
