from openai import AsyncOpenAI

from .prompt import (
    GenerateScriptPrompt,
)


async def generate_script(source_markdown: str, total_duration: int) -> str:
    client = AsyncOpenAI()

    response = await client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[
            {
                "role": "system",
                "content": GenerateScriptPrompt(
                    duration=total_duration, summary=source_markdown
                ).prompt,
            },
        ],
    )

    script = response.choices[0].message.content

    if script is None:
        raise ValueError("Failed to generate script")

    return script
