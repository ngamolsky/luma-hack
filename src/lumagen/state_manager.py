import json
import os
from typing import Optional

from pydantic import BaseModel

from .storyboard_generation.prompt import StoryboardSchema


class Audio(BaseModel):
    path: str
    duration: float


class LumagenState(BaseModel):
    script: Optional[str] = None
    storyboard: Optional[StoryboardSchema] = None
    audio: Optional[Audio] = None


class StateManager:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.state_file = f"src/data/state/{project_id}_state.json"

    def save_state(self, state: LumagenState):
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        try:
            with open(self.state_file, "w") as f:
                json.dump(state.model_dump(), f, indent=4, sort_keys=True)
        except IOError:
            pass

    def load_state(self) -> LumagenState:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    state_dict = json.load(f)
                state = LumagenState.model_validate(state_dict)
                return state
            except (json.JSONDecodeError, IOError, ValueError):
                pass
        return LumagenState()

    def clear_state(self):
        if os.path.exists(self.state_file):
            try:
                os.remove(self.state_file)
            except OSError:
                pass
