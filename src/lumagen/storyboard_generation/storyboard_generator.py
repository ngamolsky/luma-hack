from typing import List

from lumagen.models.text_model.base import BaseTextModel

from .prompt import (
    GenerateStoryboardPrompt,
    MemeContent,
    StoryboardSchema,
)


class StoryboardGenerator:
    def __init__(self, text_model: BaseTextModel):
        self.text_model = text_model

    async def generate_storyboard(
        self,
        script: str,
        duration: int,
        reference_material: str,
        memes: List[MemeContent],
    ) -> StoryboardSchema:
        prompt = GenerateStoryboardPrompt(
            script=script,
            duration=duration,
            reference_material=reference_material,
            meme_database=memes,
        ).prompt

        storyboard = await self.text_model.generate(
            prompt=prompt,
            response_format=StoryboardSchema,
        )

        if storyboard is None:
            raise ValueError("Failed to generate storyboard")

        return storyboard
