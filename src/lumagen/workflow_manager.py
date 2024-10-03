import asyncio

from lumagen.audio_generation.generate_audio import generate_audio_from_script
from lumagen.meme_db import get_memes
from lumagen.script_generation.script_generator import generate_script
from lumagen.state_manager import Audio, StateManager
from lumagen.storyboard_generation.prompt import Scene
from lumagen.storyboard_generation.storyboard_generator import generate_storyboard
from lumagen.utils.logger import LogLevel, WorkflowLogger


class WorkflowManager:
    def __init__(self, project_id: str, source_material: str, duration: int):
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
                if self.state.script is None:
                    self.logger.log("Generating new script", task="[SCRIPT]")

                    self.state.script = await generate_script(
                        self.source_material, self.duration
                    )
                    self.state_manager.save_state(self.state)
                    self.logger.log("Script generated successfully", task="[SCRIPT]")
                else:
                    self.logger.log("Script already exists", task="[SCRIPT]")

            async with self.logger.task("[AUDIO] - [VIDEO] - [CAPTIONS]"):
                await asyncio.gather(
                    self.generate_audio(),
                    self.generate_video(),
                    self.generate_captions(),
                )

        except Exception as e:
            self.logger.log(f"Error occurred: {str(e)}", LogLevel.ERROR)
            raise
        finally:
            self.logger.stop()

    async def generate_audio(self):
        async with self.logger.task("[AUDIO]", parent="[AUDIO] - [VIDEO] - [CAPTIONS]"):
            if self.state.audio is None:
                self.logger.log("Generating new audio", task="[AUDIO]")
                audio_path, duration = await generate_audio_from_script(
                    self.project_id, self.state.script
                )

                self.state.audio = Audio(path=audio_path, duration=duration)
                self.state_manager.save_state(self.state)
                self.logger.log(
                    f"Audio generated successfully with duration {duration}",
                    task="[AUDIO]",
                )
            else:
                self.logger.log(
                    f"Audio already exists with duration {self.state.audio.duration}",
                    task="[AUDIO]",
                )
            return self.state.audio

    async def generate_video(self):
        async with self.logger.task("[VIDEO]", parent="[AUDIO] - [VIDEO] - [CAPTIONS]"):
            async with self.logger.task("[MEMES]", parent="[VIDEO]"):
                self.logger.log("Fetching memes", task="[MEMES]")
                memes = get_memes()
                self.logger.log(f"Retrieved {len(memes)} memes", task="[MEMES]")

            async with self.logger.task("[STORYBOARD]", parent="[VIDEO]"):
                if not self.state.script:
                    raise ValueError("No script found when generating storyboard")

                if self.state.storyboard is None:
                    self.logger.log("Generating storyboard", task="[STORYBOARD]")

                    storyboard = await generate_storyboard(
                        script=self.state.script,
                        duration=self.duration,
                        reference_material=self.source_material,
                        memes=memes,
                    )
                    self.state.storyboard = storyboard
                    self.state_manager.save_state(self.state)
                    self.logger.log(
                        f"Storyboard generated successfully with {len(storyboard.scenes)} scenes",
                        task="[STORYBOARD]",
                    )
                else:
                    self.logger.log(
                        f"Storyboard already exists with {len(self.state.storyboard.scenes)} scenes",
                        task="[STORYBOARD]",
                    )

            async with self.logger.task("[SCENE_PROCESSING]", parent="[VIDEO]"):
                self.logger.log(
                    f"Processing {len(self.state.storyboard.scenes)} scenes from storyboard",
                    task="[SCENE_PROCESSING]",
                )

                async def process_scene(scene: Scene):
                    scene_type = scene.type

                    async with self.logger.task(
                        f"[{scene_type.upper()}]", parent="[SCENE_PROCESSING]"
                    ):
                        self.logger.log(
                            f"Processing {scene_type} scene",
                            task=f"[{scene_type.upper()}]",
                        )

                        if scene_type == "meme":
                            processed_scene = await self.process_meme_scene(scene)
                        elif scene_type == "twitter":
                            processed_scene = await self.process_twitter_scene(scene)
                        elif scene_type == "generic":
                            processed_scene = await self.process_generic_scene(scene)
                        else:
                            self.logger.log(
                                f"Unknown scene type: {scene_type}", LogLevel.WARNING
                            )
                            return None

                        self.logger.log(
                            f"Processed {scene_type} scene",
                            task=f"[{scene_type.upper()}]",
                        )
                        return processed_scene

                processed_scenes = await asyncio.gather(
                    *[process_scene(scene) for scene in self.state.storyboard.scenes]
                )

                self.logger.log(
                    f"Processed {len(processed_scenes)} scenes",
                    task="[SCENE_PROCESSING]",
                )

            return "video_path_placeholder"

    async def generate_captions(self):
        async with self.logger.task(
            "[CAPTIONS]", parent="[AUDIO] - [VIDEO] - [CAPTIONS]"
        ):
            self.logger.log("Starting caption generation", task="[CAPTIONS]")
            await asyncio.sleep(1)
            self.logger.log("Captions generated", task="[CAPTIONS]")
            return "captions_path_placeholder"

    async def process_meme_scene(self, scene):
        # Implementation for processing meme scenes
        pass

    async def process_twitter_scene(self, scene):
        # Implementation for processing twitter scenes
        pass

    async def process_generic_scene(self, scene):
        # Implementation for processing generic scenes
        pass
