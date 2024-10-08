from lumagen.models.text_model.base import BaseTextModel
from lumagen.utils.logger import WorkflowLogger

from .prompt import GenerateScriptPrompt, ScriptSchema

WORDS_PER_SECOND = 2.7


class ScriptGenerator:
    def __init__(self, text_model: BaseTextModel):
        self.text_model = text_model
        self.logger = WorkflowLogger()

    async def generate_script(self, source_markdown: str, total_duration: int) -> str:
        num_words = self.duration_to_words(total_duration)
        self.logger.debug(f"Generating script with {num_words} words")
        prompt = GenerateScriptPrompt(
            summary=source_markdown, num_words=num_words
        ).prompt

        script = await self.text_model.generate(
            prompt=prompt,
            response_format=ScriptSchema,
        )
        return script.text

    @staticmethod
    def duration_to_words(
        duration_seconds: int,
        words_per_second: float = WORDS_PER_SECOND,
    ) -> int:
        """
        Convert a duration in seconds to an estimated number of words.

        Args:
            duration_seconds (int): The duration in seconds.
            words_per_second (float): The average number of words spoken per second. Default is {WORDS_PER_SECOND}  .

        Returns:
            int: The estimated number of words for the given duration.
        """
        words = duration_seconds * words_per_second
        return int(words)

    @staticmethod
    def words_to_duration(
        num_words: int,
        words_per_second: float = WORDS_PER_SECOND,
    ) -> float:
        """
        Convert a number of words to an estimated duration in seconds.
        """
        duration = num_words / words_per_second
        return duration
