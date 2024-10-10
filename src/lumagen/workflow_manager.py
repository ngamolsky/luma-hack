import asyncio
import logging
import traceback
import uuid
from pathlib import Path
from typing import Optional, Union

from lumagen.audio_generation.audio_generator import AudioGenerator
from lumagen.meme_db import get_memes
from lumagen.models.text_model.openai_llm import OpenAITextModel
from lumagen.models.text_to_video.luma_t2v import LumaAITextToVideoModel
from lumagen.models.tts.cartesia_tts import CartesiaTTSModel
from lumagen.scene_processing.scene_processor import SceneProcessor, SceneProcessorError
from lumagen.script_generation.script_generator import ScriptGenerator
from lumagen.source_loader import SourceLoader
from lumagen.state_manager import Audio, SceneState, StateManager, StoryboardState
from lumagen.storyboard_generation.storyboard_generator import StoryboardGenerator
from lumagen.utils import video_utils
from lumagen.utils.logger import WorkflowLogger


class WorkflowManager:
    def __init__(
        self,
        project_name: str,
        duration: Optional[int] = None,
        source: Optional[Union[str, Path]] = None,
        debug_mode: bool = False,
        overwrite: bool = False,
    ):
        self.project_name = project_name
        self.state_manager = StateManager(project_name)
        self.state = self.state_manager.load_state()
        self.logger = WorkflowLogger()

        if duration is not None and source is not None:
            self.requested_duration = duration
            self.debug_mode = debug_mode
            self.source_markdown, self.source_path = SourceLoader.load(
                project_name, source
            )

            if self.debug_mode:
                self.logger.set_default_log_level(logging.DEBUG)
        else:
            self.requested_duration = None
            self.debug_mode = False
            self.source_markdown = None
            self.source_path = None

        if overwrite:
            self.state_manager.clear_state()

    async def run(self):
        try:
            self.logger.start()

            # Generate script
            await self.generate_script()

            # Generate storyboard and audio in parallel
            await asyncio.gather(self.generate_storyboard(), self.generate_audio())

            # Process scenes
            await self.process_scenes()

            # Stitch final video
            await self.stitch_final_video()

        except Exception as e:
            self.logger.error(f"Error running workflow: {e}")
            if self.debug_mode:
                self.logger.error(
                    f"Traceback:\n{''.join(traceback.format_exception(type(e), e, e.__traceback__))}"
                )
        finally:
            self.logger.stop()

    async def generate_script(self):
        async with self.logger.task("[SCRIPT]"):
            try:
                if self.state.script is None:
                    if not self.source_markdown:
                        raise ValueError(
                            "Can't generate script without source markdown."
                        )

                    if self.requested_duration is None:
                        raise ValueError("Can't generate script without duration.")

                    self.logger.log(
                        f"Generating new script with duration {self.requested_duration} seconds"
                    )

                    script_generator = ScriptGenerator(text_model=OpenAITextModel())
                    self.state.script = await script_generator.generate_script(
                        self.source_markdown, self.requested_duration
                    )
                    num_words = len(self.state.script.split())
                    self.logger.log(
                        f"Script generated successfully with {num_words} words"
                    )
                    self.state_manager.save_state(self.state, on_step="SCRIPT")
                else:
                    num_words = len(self.state.script.split())
                    self.logger.log(f"Script already exists with {num_words} words")

            except Exception as e:
                self.logger.error(f"Error generating script: {e}")

                if self.debug_mode:
                    self.logger.error(
                        f"Traceback:\n{''.join(traceback.format_exception(type(e), e, e.__traceback__))}"
                    )

    async def generate_storyboard(self):
        async with self.logger.task("[STORYBOARD]"):
            try:
                if self.state.storyboard is None:
                    if not self.state.script:
                        raise ValueError("Can't generate storyboard without a script.")

                    if not self.source_markdown:
                        raise ValueError(
                            "Can't generate storyboard without source markdown."
                        )

                    if self.requested_duration is None:
                        raise ValueError("Can't generate storyboard without duration.")

                    self.logger.log("Fetching memes from database")
                    memes = get_memes()
                    self.logger.debug(f"Retrieved {len(memes)} memes")

                    self.logger.log("Generating new storyboard")
                    storyboard_generator = StoryboardGenerator(
                        text_model=OpenAITextModel()
                    )
                    storyboard = await storyboard_generator.generate_storyboard(
                        script=self.state.script,
                        duration=self.requested_duration,
                        reference_material=self.source_markdown,
                        memes=memes,
                    )

                    self.state.storyboard = StoryboardState(
                        scenes=[
                            SceneState(
                                id=str(uuid.uuid4()),
                                scene_index=index,
                                duration=ScriptGenerator.words_to_duration(
                                    len(scene.script_chunk.split())
                                ),
                                source_scene=scene,
                            )
                            for index, scene in enumerate(storyboard.scenes)
                        ]
                    )
                    self.state_manager.save_state(self.state, on_step="STORYBOARD")
                    self.logger.log(
                        f"Storyboard generated successfully with {len(storyboard.scenes)} scenes"
                    )
                else:
                    self.logger.log(
                        f"Storyboard already exists with {len(self.state.storyboard.scenes)} scenes"
                    )
            except Exception as e:
                self.logger.error(f"Error generating storyboard: {e}")

                if self.debug_mode:
                    self.logger.error(
                        f"Traceback:\n{''.join(traceback.format_exception(type(e), e, e.__traceback__))}"
                    )

    async def generate_audio(self):
        async with self.logger.task("[AUDIO]"):
            try:
                if self.state.audio is None:
                    if not self.state.script:
                        raise ValueError("Can't generate audio without a script.")

                    self.logger.log("Generating full audio for the entire script")
                    audio_generator = AudioGenerator(
                        tts_model=CartesiaTTSModel(), script=self.state.script
                    )
                    audio_path = f"{self.state_manager.temp_dir}/full_audio.wav"
                    result = await audio_generator.generate_audio_and_save_to_file(
                        audio_path
                    )
                    self.state.audio = Audio(path=str(result[0]), duration=result[1])
                    self.logger.log(
                        f"Full audio generated successfully: {self.state.audio.path} with duration {self.state.audio.duration}"
                    )
                    self.state_manager.save_state(self.state, on_step="AUDIO")
                else:
                    self.logger.log(
                        f"Audio already exists with duration {self.state.audio.duration}"
                    )
            except Exception as e:
                self.logger.error(f"Error generating full audio: {e}")

                if self.debug_mode:
                    self.logger.error(
                        f"Traceback:\n{''.join(traceback.format_exception(type(e), e, e.__traceback__))}"
                    )

    async def process_scenes(self):
        async with self.logger.task("[SCENE_PROCESSING]"):
            if self.state.storyboard is None:
                raise ValueError("Can't process scenes without a storyboard.")

            scene_processor = SceneProcessor(
                project_name=self.project_name,
                ttv_model=LumaAITextToVideoModel(),
                tts_model=CartesiaTTSModel(),
            )

            self.logger.start_progress(total=len(self.state.storyboard.scenes))

            async def process_single_scene(scene):
                if not self.state.storyboard:
                    raise ValueError("Can't process scenes without a storyboard.")

                try:
                    processed_scene = await scene_processor.process_scene(scene)
                    self.state.storyboard.scenes[
                        self.state.storyboard.scenes.index(scene)
                    ] = processed_scene

                    self.logger.update_progress()
                except SceneProcessorError as e:
                    raise e

            tasks = [
                process_single_scene(scene) for scene in self.state.storyboard.scenes
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            errors = [
                error for error in results if isinstance(error, SceneProcessorError)
            ]

            if errors:
                self.logger.warning(
                    "Some scenes failed to process. Please rerun the process to retry failed scenes."
                )
            else:
                self.logger.info(
                    f"Successfully processed all {len(self.state.storyboard.scenes)} scenes."
                )

    async def stitch_final_video(self):
        async with self.logger.task("[STITCH_FINAL_VIDEO]"):
            self.logger.log("Stitching final video")
            try:
                if (
                    not self.state.storyboard
                    or not self.state.storyboard.all_scenes_completed()
                ):
                    self.logger.warning(
                        "Can't create video without a completed storyboard."
                    )
                    return

                if not self.state.audio:
                    self.logger.warning("Can't create final video without audio.")
                    return

                # Stitch the final video
                final_output_path = f"{self.state_manager.data_dir}/final_video.mp4"
                final_video_path = video_utils.stitch_final_video(
                    [scene for scene in self.state.storyboard.scenes],
                    self.state.audio.path,
                    final_output_path,
                )
                self.state.final_video_path = final_video_path
                self.state_manager.save_state(self.state, on_step="VIDEO")

                self.logger.log(f"Final video created at {final_video_path}")

                if not self.debug_mode:
                    self.state_manager.clear_temp_dir()

            except Exception as e:
                self.logger.error(f"Error stitching final video: {e}")

                if self.debug_mode:
                    self.logger.error(
                        f"Traceback:\n{''.join(traceback.format_exception(type(e), e, e.__traceback__))}"
                    )

    async def generate_video_from_scene_id(self, scene_id: str):
        self.logger.start()
        try:
            if not self.state.storyboard:
                raise ValueError("Can't generate video without a storyboard.")

            scene = next(
                (
                    scene
                    for scene in self.state.storyboard.scenes
                    if scene.id == scene_id
                ),
                None,
            )
            if not scene:
                raise ValueError(f"Scene with id {scene_id} not found in storyboard.")

            self.logger.log(f"Processing scene with id {scene_id}")

            scene_processor = SceneProcessor(
                project_name=self.project_name,
                ttv_model=LumaAITextToVideoModel(),
                tts_model=CartesiaTTSModel(),
            )

            processed_scene = await scene_processor.process_scene(scene)
            self.logger.log(f"Processed scene with id {scene_id}")

            # After processing the scene, recompose the video
            await self.stitch_final_video()
        except Exception as e:
            self.logger.error(f"Error generating video from scene id {scene_id}: {e}")
            if self.debug_mode:
                self.logger.error(
                    f"Traceback:\n{''.join(traceback.format_exception(type(e), e, e.__traceback__))}"
                )
            raise
        finally:
            self.logger.log(f"Finished processing scene with id {scene_id}")
            self.logger.stop()

        return processed_scene
