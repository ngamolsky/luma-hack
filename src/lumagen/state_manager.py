import json
import logging
import os
import shutil
from typing import Dict, Optional

from pydantic import BaseModel

from lumagen.storyboard_generation.prompt import Scene

from .utils.logger import TaskNode, WorkflowLogger


class Audio(BaseModel):
    path: str
    duration: float


class SceneState(BaseModel):
    id: str
    duration: float
    source_scene: Scene
    image_path: Optional[str] = None
    image_cloudflare_url: Optional[str] = None
    audio_path: Optional[str] = None
    video_path: Optional[str] = None
    final_video_path: Optional[str] = None
    scene_index: Optional[int] = None


class StoryboardState(BaseModel):
    scenes: list[SceneState]

    def all_scenes_completed(self) -> bool:
        return all(scene.final_video_path is not None for scene in self.scenes)


class LumagenState(BaseModel):
    script: Optional[str] = None
    storyboard: Optional[StoryboardState] = None
    audio: Optional[Audio] = None
    final_video_path: Optional[str] = None


class StateManager:
    _instances: Dict[str, "StateManager"] = {}

    def __new__(cls, project_id: str):
        if project_id not in cls._instances:
            instance = super().__new__(cls)
            instance.__init__(project_id)
            cls._instances[project_id] = instance
        return cls._instances[project_id]

    def __init__(self, project_id: str):
        if hasattr(self, "project_id"):
            return
        self.project_id = project_id
        self.state_file = f"src/data/state/{project_id}_state.json"
        self.data_dir = f"src/data/output/{project_id}"
        self.temp_dir = f"{self.data_dir}/temp"
        self.logger = WorkflowLogger()
        os.makedirs(self.data_dir, exist_ok=True)

        # Create a separate TaskNode for state logs
        self.state_log_node = TaskNode("[STATE]")
        self.logger.root_task.add_child(self.state_log_node)

    def _log_state(self, message: str, level: int = logging.INFO):
        self.state_log_node.add_log(self.logger._format_log(message, level))

    def save_state(
        self,
        state: LumagenState,
        skip_logs: bool = False,
        on_step: Optional[str] = None,
    ):
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        try:
            with open(self.state_file, "w") as f:
                json.dump(state.model_dump(), f, indent=4, sort_keys=True)
            if not skip_logs:
                self._log_state(
                    f"State saved successfully for project {self.project_id}, "
                    f"on step {on_step}"
                    if on_step
                    else ""
                )
        except IOError as e:
            self._log_state(
                f"Error saving state for project {self.project_id}: {str(e)}",
                logging.ERROR,
            )

    def save_scene_state(self, scene: SceneState):
        self.logger.debug(f"Saving processed scene with ID: {scene.id}")
        state = self.load_state(skip_logs=True)
        if not state.storyboard:
            raise ValueError("Can't save scene without a storyboard.")

        # Find the index of the existing scene
        existing_scene_index = next(
            (i for i, s in enumerate(state.storyboard.scenes) if s.id == scene.id), None
        )

        if existing_scene_index is not None:
            # Replace the existing scene at the same index
            state.storyboard.scenes[existing_scene_index] = scene
        else:
            # If the scene doesn't exist, append it to the end
            state.storyboard.scenes.append(scene)

        self.save_state(state, skip_logs=True)

    def load_state(
        self, skip_logs: bool = False, on_step: Optional[str] = None
    ) -> LumagenState:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    state_dict = json.load(f)
                state = LumagenState.model_validate(state_dict)
                completed_steps = []
                if state.script:
                    completed_steps.append("script")
                if state.storyboard and state.audio:
                    completed_steps.append("storyboard and audio")
                if state.storyboard and all(
                    scene.final_video_path for scene in state.storyboard.scenes
                ):
                    completed_steps.append("processing scenes")
                if state.final_video_path:
                    completed_steps.append("final video")
                if not skip_logs:
                    self._log_state(
                        f"State loaded successfully for project {self.project_id}, "
                        f"on step {on_step}. "
                        if on_step
                        else "" f"Completed steps: {', '.join(completed_steps)}"
                    )
                return state
            except (json.JSONDecodeError, IOError, ValueError) as e:
                self._log_state(
                    f"Error loading state for project {self.project_id}: {str(e)}",
                    logging.ERROR,
                )
        else:
            self._log_state(
                f"No existing state found for project {self.project_id}. Creating new state."
            )
        return LumagenState()

    def clear_temp_dir(self):
        self._log_state("Clearing temporary directory")
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            self.logger.debug(f"Removed temporary directory: {self.temp_dir}")

    def clear_state(self):
        if os.path.exists(self.state_file):
            try:
                os.remove(self.state_file)
                self._log_state(
                    f"State cleared successfully for project {self.project_id}"
                )
            except OSError as e:
                self._log_state(
                    f"Error clearing state for project {self.project_id}: {str(e)}",
                    logging.ERROR,
                )
        else:
            self._log_state(
                f"No state file found to clear for project {self.project_id}"
            )

        # Clear the data directory
        for filename in os.listdir(self.data_dir):
            file_path = os.path.join(self.data_dir, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                self._log_state(
                    f"Error deleting file {file_path}: {str(e)}",
                    logging.ERROR,
                )

    @classmethod
    def get_instance(cls, project_id: str) -> "StateManager":
        return cls(project_id)

    def get_data_dir(self) -> str:
        return self.data_dir
