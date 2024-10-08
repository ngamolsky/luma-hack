import asyncio
import traceback
import uuid
from typing import Optional

from lumagen.audio_generation.audio_generator import AudioGenerator
from lumagen.meme_db import get_memes
from lumagen.models.text_model.openai_llm import OpenAITextModel
from lumagen.models.text_to_video.luma_t2v import LumaAITextToVideoModel
from lumagen.models.tts.cartesia_tts import CartesiaTTSModel
from lumagen.scene_processing.scene_processor import SceneProcessor, SceneProcessorError
from lumagen.script_generation.script_generator import ScriptGenerator
from lumagen.state_manager import Audio, SceneState, StateManager, StoryboardState
from lumagen.storyboard_generation.storyboard_generator import StoryboardGenerator
from lumagen.utils import video_utils
from lumagen.utils.logger import WorkflowLogger

SCENE_PROCESSING_BATCH_SIZE = (
    None  # Set to None to process all in parallel, or an integer for batching
)


class WorkflowManager:
    def __init__(
        self,
        project_id: str,
        duration: int = 40,
        source_material: Optional[str] = None,
    ):
        self.project_id = project_id
        self.state_manager = StateManager(project_id)
        self.source_material = source_material
        self.duration = duration
        self.state = self.state_manager.load_state()
        self.logger = WorkflowLogger()

    async def run(self):
        try:
            self.logger.start()
            async with self.logger.task("[SCRIPT]"):
                try:
                    if self.state.script is None:
                        if not self.source_material:
                            raise ValueError(
                                "Can't generate script without source material."
                            )

                        self.logger.log(
                            f"Generating new script with duration {self.duration} seconds"
                        )

                        script_generator = ScriptGenerator(text_model=OpenAITextModel())
                        self.state.script = await script_generator.generate_script(
                            self.source_material, self.duration
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
                    self.logger.error(
                        f"Traceback:\n{''.join(traceback.format_exception(type(e), e, e.__traceback__))}"
                    )

            async with self.logger.task("[AUDIO] - [VIDEO]"):
                self.logger.start_progress(total=2)
                await asyncio.gather(
                    self.generate_audio(),
                    self.generate_video(),
                )

        except Exception as e:
            self.logger.error(f"Error running workflow: {e}")
            self.logger.error(
                f"Traceback:\n{''.join(traceback.format_exception(type(e), e, e.__traceback__))}"
            )
        finally:
            self.logger.stop()

    async def generate_audio(self):
        async with self.logger.task("[AUDIO]"):
            try:
                if not self.state.script:
                    raise ValueError("Can't generate audio without a script.")

                if self.state.audio is None:
                    self.logger.log("Generating new audio")
                    tts_model = CartesiaTTSModel()
                    audio_generator = AudioGenerator(
                        tts_model=tts_model, script=self.state.script
                    )
                    (
                        file_path,
                        duration,
                    ) = await audio_generator.generate_audio_and_save_to_file(
                        f"{self.state_manager.temp_dir}/script.wav"
                    )
                    self.state.audio = Audio(path=str(file_path), duration=duration)
                    self.state_manager.save_state(self.state, on_step="AUDIO")
                    self.logger.log(
                        f"Audio generated successfully with duration {duration} seconds"
                    )
                else:
                    self.logger.log(
                        f"Audio already exists with duration {self.state.audio.duration} seconds"
                    )

            except Exception as e:
                self.logger.error(f"Error generating audio: {e}")
                self.logger.error(
                    f"Traceback:\n{''.join(traceback.format_exception(type(e), e, e.__traceback__))}"
                )
                return
        self.logger.update_progress()
        return self.state.audio

    async def generate_video(self):
        async with self.logger.task("[VIDEO]"):
            try:
                missing_dependencies = []
                if not self.source_material:
                    missing_dependencies.append("source material")

                if missing_dependencies:
                    raise ValueError(
                        f"Can't generate video without {', '.join(missing_dependencies)}."
                    )

                async with self.logger.task("[STORYBOARD]"):
                    if self.state.storyboard is None:
                        if not self.state.script:
                            raise ValueError(
                                "Can't generate storyboard without a script."
                            )

                        if not self.source_material:
                            raise ValueError(
                                "Can't generate storyboard without source material."
                            )

                        self.logger.log("Fetching memes to select from")
                        memes = get_memes()
                        self.logger.log(f"Retrieved {len(memes)} memes")

                        self.logger.log("Generating new storyboard")
                        storyboard_generator = StoryboardGenerator(
                            text_model=OpenAITextModel()
                        )
                        storyboard = await storyboard_generator.generate_storyboard(
                            script=self.state.script,
                            duration=self.duration,
                            reference_material=self.source_material,
                            memes=memes,
                        )

                        self.state.storyboard = StoryboardState(
                            scenes=[
                                SceneState(
                                    id=str(uuid.uuid4()),
                                    duration=ScriptGenerator.words_to_duration(
                                        len(scene.script_chunk.split())
                                    ),
                                    source_scene=scene,
                                )
                                for scene in storyboard.scenes
                            ]
                        )
                        self.state_manager.save_state(self.state, on_step="STORYBOARD")
                        self.logger.log(
                            f"Storyboard generated successfully with {len(storyboard.scenes)} scenes",
                        )
                    else:
                        self.logger.log(
                            f"Storyboard already exists with {len(self.state.storyboard.scenes)} scenes",
                        )

                async with self.logger.task("[SCENE_PROCESSING]"):
                    if self.state.storyboard is None:
                        raise ValueError("Can't process scenes without a storyboard.")

                    completed_scenes = [
                        scene
                        for scene in self.state.storyboard.scenes
                        if scene.final_video_path is not None
                    ]
                    num_completed_scenes = len(completed_scenes)

                    to_process_scenes = [
                        scene
                        for scene in self.state.storyboard.scenes
                        if scene.final_video_path is None
                    ]

                    num_to_process_scenes = len(to_process_scenes)

                    if num_completed_scenes > 0:
                        self.logger.log(
                            f"Processed {num_completed_scenes} scenes, {num_to_process_scenes} scenes remaining"
                        )
                    else:
                        self.logger.log(f"Processing {num_to_process_scenes} scenes")

                    self.logger.start_progress(total=num_to_process_scenes)
                    scene_processor = SceneProcessor(
                        project_id=self.project_id,
                        ttv_model=LumaAITextToVideoModel(),
                    )

                    if SCENE_PROCESSING_BATCH_SIZE is None:
                        # Process all scenes in parallel
                        results = await asyncio.gather(
                            *[
                                scene_processor.process_scene(scene)
                                for scene in to_process_scenes
                            ],
                            return_exceptions=True,
                        )
                    else:
                        # Process scenes in batches
                        results = []
                        for i in range(
                            0, num_to_process_scenes, SCENE_PROCESSING_BATCH_SIZE
                        ):
                            batch = to_process_scenes[
                                i : i + SCENE_PROCESSING_BATCH_SIZE
                            ]
                            batch_results = await asyncio.gather(
                                *[
                                    scene_processor.process_scene(scene)
                                    for scene in batch
                                ],
                                return_exceptions=True,
                            )
                            results.extend(batch_results)

                    processed_scenes = []
                    failed_scenes = []
                    for scene in results:
                        if isinstance(scene, SceneProcessorError):
                            self.logger.error(str(scene))

                            failed_scenes.append(scene)
                        elif isinstance(scene, SceneState):
                            processed_scenes.append(scene)

                    if (
                        len(processed_scenes) != num_to_process_scenes
                        and len(failed_scenes) > 0
                    ):
                        self.logger.warning(
                            f"Not all scenes were processed successfully. {len(processed_scenes)} out of {num_to_process_scenes} scenes were processed."
                        )
                        self.logger.warning(
                            "Please rerun the process to retry failed scenes."
                        )
                        return  # Exit the workflow

                    self.logger.info(
                        f"Successfully processed all {num_to_process_scenes} scenes."
                    )

                # If any tasks were redone, we need to recompose the video
                if num_to_process_scenes > 0 or self.state.final_video_path is None:
                    await self.compose_video()

            except Exception as e:
                self.logger.error(f"Error generating video: {e}")
                self.logger.error(
                    f"Traceback:\n{''.join(traceback.format_exception(type(e), e, e.__traceback__))}"
                )
                return
        self.logger.update_progress()
        return self.state.final_video_path

    async def compose_video(self):
        async with self.logger.task("[COMPOSE_VIDEO]"):
            try:
                if not self.state.script:
                    raise ValueError("Can't create video without a script.")

                if not self.state.audio:
                    raise ValueError("Can't create video without audio.")

                if not self.state.storyboard:
                    raise ValueError("Can't create video without a storyboard.")

                # Create the final video
                final_output_path = f"{self.state_manager.data_dir}/final_video.mp4"
                final_video_path = video_utils.create_final_video(
                    [scene for scene in self.state.storyboard.scenes],
                    self.state.audio.path,
                    final_output_path,
                )
                self.state.final_video_path = final_video_path
                self.state_manager.save_state(self.state, on_step="VIDEO")

                self.logger.log(f"Final video created at {final_video_path}")

                self.state_manager.clear_temp_dir()

            except Exception as e:
                self.logger.error(f"Error composing video: {e}")
                self.logger.error(
                    f"Traceback:\n{''.join(traceback.format_exception(type(e), e, e.__traceback__))}"
                )
                return

    async def generate_video_from_scene_id(self, scene_id: str):
        if not self.state.storyboard:
            raise ValueError("Can't generate video without a storyboard.")

        scene = next(
            (scene for scene in self.state.storyboard.scenes if scene.id == scene_id),
            None,
        )
        if not scene:
            raise ValueError(f"Scene with id {scene_id} not found in storyboard.")

        self.logger.log(f"Processing scene with id {scene_id}")

        scene_processor = SceneProcessor(
            project_id=self.project_id,
            ttv_model=LumaAITextToVideoModel(),
        )

        processed_scene = await scene_processor.process_scene(scene)
        self.logger.log(f"Processed scene with id {scene_id}")

        # After processing the scene, recompose the video
        await self.compose_video()

        return processed_scene
