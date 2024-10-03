from pydantic import BaseModel

SCRIPT_PROMPT = """
You will be given a summary of a news story or research topic. 

Write a narrative transcript for a {duration} second short form video that represent this source material. 

The duration should be based on the average time it would take to read the script out loud.

This transcript should capture the key points of the source material.

This video should be in the style of a young sarcastic creator. It should be terse, fast-paced, clever, witty, meme filled and often roasting the subjects/products/companies involved.

This script will be read aloud by a narrator so do not include emojis, markdown, ellipsis, excessive symbols like "$$$" or any styling.

Don't add filler words or phrases like "let's begin", just get to the meat of the content.


```
{summary}
```
"""


class GenerateScriptPrompt(BaseModel):
    duration: int
    summary: str

    @property
    def prompt(self):
        return SCRIPT_PROMPT.format(duration=self.duration, summary=self.summary)
