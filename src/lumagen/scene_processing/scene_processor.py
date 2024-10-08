import os
import traceback

from tenacity import (
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from tweetcapture import TweetCapture

from lumagen.models.text_to_image.fal_t2i import FalTextToImageModel
from lumagen.models.text_to_video.luma_t2v import LumaAITextToVideoModel
from lumagen.state_manager import SceneState, StateManager
from lumagen.storyboard_generation.prompt import (
    GenericVideoContent,
    MemeContent,
    Scene,
    TwitterContent,
)
from lumagen.utils.file_utils import upload_to_cloudflare
from lumagen.utils.image_utils import (
    AspectRatio,
    download_image_from_url,
    open_image_from_file,
    resize_and_pad_image,
    save_image_to_file,
)
from lumagen.utils.logger import WorkflowLogger
from lumagen.utils.video_utils import (
    clip_video,
    create_static_video,
    download_video_from_url,
)


class SceneProcessorError(Exception):
    def __init__(self, scene_id: str, original_exception: Exception):
        super().__init__(
            f"Error processing scene {scene_id}: {str(original_exception)}"
        )
        self.scene_id = scene_id
        self.original_exception = original_exception
        self.stack_trace = traceback.format_exc()

    def __str__(self):
        return (
            f"{super().__str__()}\n\nOriginal exception stacktrace:\n{self.stack_trace}"
        )


class TwitterSceneError(Exception):
    def __init__(self, tweet_url: str, original_exception: Exception):
        super().__init__(
            f"Error processing Twitter scene for URL {tweet_url}: {str(original_exception)}"
        )
        self.tweet_url = tweet_url
        self.original_exception = original_exception
        self.stack_trace = traceback.format_exc()

    def __str__(self):
        return (
            f"{super().__str__()}\n\nOriginal exception stacktrace:\n{self.stack_trace}"
        )


class TweetNotFoundError(Exception):
    def __init__(self, tweet_url: str, message: str):
        super().__init__(f"Tweet not found for URL {tweet_url}: {message}")
        self.tweet_url = tweet_url
        self.stack_trace = traceback.format_exc()

    def __str__(self):
        return f"{super().__str__()}\n\nStacktrace:\n{self.stack_trace}"


class SceneProcessor:
    def __init__(self, project_id: str, ttv_model: LumaAITextToVideoModel):
        self.logger = WorkflowLogger()
        self.ttv_model = ttv_model
        self.project_id = project_id
        self.state_manager = StateManager(project_id)

        os.makedirs(self.state_manager.temp_dir, exist_ok=True)
        os.makedirs(self.state_manager.temp_dir, exist_ok=True)

        self.logger.debug(f"Initialized SceneProcessor for project {project_id}")

    async def process_scene(self, scene: SceneState) -> SceneState:
        try:
            # Use the persistent temporary directory with scene id
            scene_temp_dir = os.path.join(
                self.state_manager.temp_dir, f"scene_{scene.id}"
            )
            os.makedirs(scene_temp_dir, exist_ok=True)

            if not scene.image_path:
                self.logger.debug(f"Generating image for {scene.source_scene.type}")
                scene.image_path = await self.generate_image(
                    scene.source_scene, scene_temp_dir
                )
                self.save_processed_scene(scene)
                self.logger.debug(f"Generated image for {scene.source_scene.type}")
            else:
                self.logger.debug(f"Using existing image for {scene.source_scene.type}")

            if not scene.image_cloudflare_url:
                self.logger.debug(
                    f"Uploading image to Cloudflare for {scene.image_path}"
                )
                scene.image_cloudflare_url = upload_to_cloudflare(scene.image_path)
                self.save_processed_scene(scene)
                self.logger.debug(
                    f"Uploaded image to Cloudflare for {scene.source_scene.type}"
                )
            else:
                self.logger.debug(
                    f"Using existing image from Cloudflare for {scene.source_scene.type}"
                )

            if not scene.final_video_path:
                self.logger.debug(f"Generating video for {scene.id}")
                if scene.source_scene.type in ["meme", "generic"]:
                    generated_video_url = await self.ttv_model.generate_video(
                        start_image=scene.image_cloudflare_url,
                        aspect_ratio=AspectRatio.PORTRAIT,
                    )
                    self.logger.debug(f"Generated video for {scene.source_scene.type}")

                    downloaded_video = await download_video_from_url(
                        generated_video_url,
                        os.path.join(scene_temp_dir, "generated_video.mp4"),
                    )
                    final_video_path = await clip_video(
                        downloaded_video,
                        scene.duration,
                        os.path.join(scene_temp_dir, "scene_clip.mp4"),
                    )
                    self.logger.debug(f"Clipped video for {scene.source_scene.type}")

                elif scene.source_scene.type == "twitter":
                    final_video_path = await create_static_video(
                        scene.image_path,
                        scene.duration,
                        os.path.join(scene_temp_dir, "scene_clip.mp4"),
                    )
                    self.logger.debug("Created static video for Twitter scene")

                scene.final_video_path = final_video_path
                self.save_processed_scene(scene)
                self.logger.debug(f"Saved final video for {scene.source_scene.type}")

            else:
                self.logger.debug(
                    f"Using existing final video at {scene.final_video_path}"
                )

        except Exception as e:
            raise SceneProcessorError(scene.id, e)

        self.logger.update_progress()

        return scene

    async def generate_image(self, scene: Scene, temp_dir: str) -> str:
        self.logger.debug(f"Generating image for scene type: {scene.type}")
        if scene.type == "meme":
            if not scene.meme:
                raise ValueError("Meme scene has no meme content")
            return await self.generate_meme_image(scene.meme, temp_dir)
        elif scene.type == "twitter":
            if not scene.twitter:
                raise ValueError("Twitter scene has no tweet URL")
            return await self.generate_tweet_image(scene.twitter, temp_dir)
        elif scene.type == "generic":
            if not scene.generic:
                raise ValueError("Generic scene has no image description")
            return await self.generate_generic_image(scene.generic, temp_dir)
        else:
            raise ValueError(f"Unknown scene type: {scene.type}")

    async def generate_meme_image(self, meme_scene: MemeContent, temp_dir: str) -> str:
        self.logger.debug("Generating meme image")

        meme_image = await download_image_from_url(meme_scene.image_url)
        meme_image = resize_and_pad_image(meme_image, AspectRatio.PORTRAIT)

        meme_image_path = os.path.join(
            temp_dir, f"meme_{hash(meme_scene.image_url)}.png"
        )
        meme_image_path = save_image_to_file(meme_image, meme_image_path)
        self.logger.debug(f"Saved meme image to {meme_image_path}")

        return meme_image_path

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_not_exception_type(TweetNotFoundError),
    )
    async def generate_tweet_image(
        self, twitter_scene: TwitterContent, temp_dir: str
    ) -> str:
        self.logger.debug(f"Generating tweet image for {twitter_scene.tweet_url}")
        try:
            tweet_url = twitter_scene.tweet_url

            tweet = TweetCapture()
            tweet.add_chrome_argument("--remote-debugging-port=9222")

            tweet_filename = os.path.join(temp_dir, f"tweet_{hash(tweet_url)}.png")
            await tweet.screenshot(tweet_url, path=tweet_filename, overwrite=True)

            if os.path.exists(tweet_filename):
                tweet_image = open_image_from_file(tweet_filename)
                tweet_image = resize_and_pad_image(tweet_image, AspectRatio.PORTRAIT)

                # Print resolution and aspect ratio of the tweet image
                final_image_path = os.path.join(
                    temp_dir, f"tweet_{hash(tweet_url)}.png"
                )
                save_image_to_file(tweet_image, final_image_path)

                self.logger.debug(f"Generated tweet image: {final_image_path}")
                return final_image_path
            else:
                raise ValueError(f"Failed to capture tweet from URL: {tweet_url}")
        except Exception as e:
            if "Tweets not found" in str(e):
                raise TweetNotFoundError(
                    tweet_url, "Tweet not found, check the url and retry."
                )
            raise TwitterSceneError(tweet_url, e)

    async def generate_generic_image(
        self, generic_scene: GenericVideoContent, temp_dir: str
    ) -> str:
        self.logger.debug("Generating generic image")
        try:
            text_to_image_model = FalTextToImageModel()
            image_url = await text_to_image_model.generate_image(
                generic_scene.image_description, AspectRatio.PORTRAIT
            )
            image_path = os.path.join(
                temp_dir, f"generic_{hash(generic_scene.image_description)}.png"
            )
            image = await download_image_from_url(image_url)

            save_image_to_file(image, image_path)
            self.logger.debug(f"Generated generic image: {image_path}")
            return image_path
        except Exception:
            raise

    def save_processed_scene(self, scene: SceneState):
        self.logger.debug(f"Saving processed scene with ID: {scene.id}")
        state = self.state_manager.load_state(skip_logs=True)
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

        self.state_manager.save_state(state, skip_logs=True)
