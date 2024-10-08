from abc import ABC, abstractmethod
from typing import Optional

from typing_extensions import TypeVar

ResponseFormatT = TypeVar("ResponseFormatT", default=None)


class BaseTextModel(ABC):
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        response_format: Optional[type[ResponseFormatT]] = None,
    ) -> ResponseFormatT:
        """
        Generate text based on the given prompt.

        Args:
            prompt (str): The input prompt to generate text from.
            max_tokens (int): The maximum number of tokens to generate.
            temperature (float): Controls randomness in generation. Higher values make output more random.
            response_format (Optional[type[ResponseFormatT]]): The expected response format type.

        Returns:
            Optional[ResponseFormatT]: The generated text, parsed into the specified format if provided.
        """
        pass
