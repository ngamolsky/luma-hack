from pydantic import BaseModel

SCRIPT_PROMPT = """
You will be given a summary of a news story or research topic. 

Please generate a script for a short video that is as close as possible to {num_words} words long that captures the key points of the source material.

This video should be in the style of a young sarcastic creator. It should be terse, fast-paced, clever, witty, meme filled and often roasting the subjects/products/companies involved.

# IMPORTANT:
This script will be read aloud by a narrator so do not include asterisks, emojis, markdown, ellipsis, excessive symbols like "$$$" or any styling.

Don't add filler words or phrases like "let's begin", just get to the meat of the content.

Also don't add anny stage direction or other non-textual elements, just the script.

```
{summary}
```
"""


class GenerateScriptPrompt(BaseModel):
    summary: str
    num_words: int

    @property
    def prompt(self):
        return SCRIPT_PROMPT.format(summary=self.summary, num_words=self.num_words)


class ScriptSchema(BaseModel):
    text: str
