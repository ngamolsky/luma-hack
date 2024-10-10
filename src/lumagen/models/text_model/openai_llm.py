import os
from typing import Optional

from openai import AsyncOpenAI

from lumagen.utils.logger import WorkflowLogger

from .base import BaseTextModel, ResponseFormatT


class OpenAITextModel(BaseTextModel):
    def __init__(self, model: str = "gpt-4o-2024-08-06", api_key: str | None = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set")

        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model = model
        self.logger = WorkflowLogger()

    async def generate(
        self,
        prompt: str,
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        response_format: Optional[type[ResponseFormatT]] = None,
    ):
        kwargs = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format

        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        response = await self.client.beta.chat.completions.parse(**kwargs)
        return response.choices[0].message.parsed
