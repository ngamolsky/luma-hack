import os
import traceback

from tenacity import (
    RetryCallState,
    RetryError,
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from tweetcapture import TweetCapture

from lumagen.audio_generation.audio_generator import AudioGenerator
from lumagen.models.text_to_image.fal_t2i import FalTextToImageModel
from lumagen.models.text_to_video.luma_t2v import LumaAITextToVideoModel
from lumagen.models.tts.cartesia_tts import CartesiaTTSModel
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
    resize_and_pad_image_async,
    save_image_to_file,
)
from lumagen.utils.logger import WorkflowLogger
from lumagen.utils.video_utils import (
    clip_video,
    create_static_video,
    download_video_from_url,
)


def retry_callback(retry_state: RetryCallState):
    logger = WorkflowLogger()
    logger.increment_retry_count()

    function_name = retry_state.fn.__name__ if retry_state.fn else "unknown"
    exception = retry_state.outcome.exception() if retry_state.outcome else None

    if isinstance(exception, RetryError) and exception.last_attempt.exception():
        exception = exception.last_attempt.exception()

    exception_name = exception.__class__.__name__ if exception else "unknown"
    logger.debug(f"Retrying {function_name} after {exception_name}...")


class SceneProcessorError(Exception):
    def __init__(self, scene_id: str, original_exception: Exception):
        while isinstance(original_exception, RetryError):
            if original_exception.last_attempt.exception():
                original_exception = original_exception.last_attempt.exception()  # type: ignore
                break

        super().__init__(
            f"Error processing scene {scene_id}: {str(original_exception)}"
        )
        self.scene_id = scene_id
        self.original_exception = original_exception

    def __str__(self):
        return f"{super().__str__()}\n\nOriginal exception stacktrace:\n{self.original_exception.__traceback__}"


class TwitterSceneError(Exception):
    def __init__(self, tweet_url: str, original_exception: Exception):
        super().__init__(
            f"Error processing Twitter scene for URL {tweet_url}: {str(original_exception)}"
        )
        self.tweet_url = tweet_url
        self.original_exception = original_exception
        self.stack_trace = traceback.format_exc()


class InvalidTweetUrlError(Exception):
    def __init__(self, tweet_url: str):
        super().__init__(f"Invalid tweet URL: {tweet_url}")
        self.tweet_url = tweet_url


class TweetNotFoundError(Exception):
    def __init__(
        self,
        tweet_url: str,
    ):
        super().__init__(f"Tweet not found for URL {tweet_url}")
        self.tweet_url = tweet_url


class SceneProcessor:
    def __init__(
        self,
        project_name: str,
        ttv_model: LumaAITextToVideoModel,
        tts_model: CartesiaTTSModel,
    ):
        self.logger = WorkflowLogger()
        self.ttv_model = ttv_model
        self.tts_model = tts_model
        self.project_id = project_name
        self.state_manager = StateManager(project_name)

        os.makedirs(self.state_manager.temp_dir, exist_ok=True)

        self.logger.debug(f"Initialized SceneProcessor for project {project_name}")

    async def process_scene(self, scene: SceneState) -> SceneState:
        async with self.logger.task(
            f"[SCENE {scene.scene_index + 1 if scene.scene_index is not None else 1 }] - {scene.source_scene.type} - {scene.id[:8]}..."
        ):
            self.logger.start_progress(total=3, stage="IMAGE")
            try:
                scene_temp_dir = os.path.join(
                    self.state_manager.temp_dir, f"scene_{scene.id}"
                )
                os.makedirs(scene_temp_dir, exist_ok=True)

                # Generate image
                if not scene.image_path:
                    scene.image_path = await self.generate_image(
                        scene.source_scene, scene_temp_dir
                    )
                    self.state_manager.save_scene_state(scene)

                # Upload image to get a URL
                self.logger.update_progress(increment=1, stage="IMAGE_UPLOAD")
                if not scene.image_cloudflare_url:
                    scene.image_cloudflare_url = upload_to_cloudflare(scene.image_path)
                    self.state_manager.save_scene_state(scene)

                # Generate video
                self.logger.update_progress(increment=1, stage="VIDEO")
                if not scene.final_video_path:
                    scene.final_video_path = await self.generate_video(
                        scene, scene_temp_dir
                    )
                    self.state_manager.save_scene_state(scene)

                self.logger.update_progress(increment=1, stage="DONE")
                return scene

            except Exception as e:
                self.logger.error(f"Error processing scene {scene.id}: {str(e)}")
                raise SceneProcessorError(scene.id, e)

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
        meme_image_path = await save_image_to_file(meme_image, meme_image_path)
        self.logger.debug(f"Saved meme image to {meme_image_path}")

        return meme_image_path

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_not_exception_type((TweetNotFoundError, InvalidTweetUrlError)),
        after=retry_callback,
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
                tweet_image = await open_image_from_file(tweet_filename)
                tweet_image = await resize_and_pad_image_async(
                    tweet_image, AspectRatio.PORTRAIT
                )

                # Print resolution and aspect ratio of the tweet image
                final_image_path = os.path.join(
                    temp_dir, f"tweet_{hash(tweet_url)}.png"
                )
                await save_image_to_file(tweet_image, final_image_path)

                self.logger.debug(f"Generated tweet image: {final_image_path}")
                return final_image_path
            else:
                raise ValueError(f"Failed to capture tweet from URL: {tweet_url}")
        except Exception as e:
            if "Tweets not found" in str(e):
                raise TweetNotFoundError(tweet_url)
            elif "Invalid tweet url" in str(e):
                raise InvalidTweetUrlError(tweet_url)
            else:
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

            image = await download_image_from_url(image_url)

            image = resize_and_pad_image(image, AspectRatio.PORTRAIT, padding_percent=0)

            image_path = os.path.join(
                temp_dir, f"generic_{hash(generic_scene.image_description)}.png"
            )

            await save_image_to_file(image, image_path)
            self.logger.debug(f"Generated generic image: {image_path}")
            return image_path
        except Exception:
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        after=retry_callback,
    )
    async def generate_audio(self, script_chunk: str, temp_dir: str) -> str:
        self.logger.debug("Generating audio for scene")
        audio_generator = AudioGenerator(tts_model=self.tts_model, script=script_chunk)
        audio_path = os.path.join(temp_dir, "scene_audio.wav")
        file_path, _ = await audio_generator.generate_audio_and_save_to_file(audio_path)
        return str(file_path)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        after=retry_callback,
    )
    async def generate_video(self, scene: SceneState, temp_dir: str) -> str:
        if not scene.image_path:
            raise ValueError("Image is required to generate a video")

        self.logger.debug("Generating video for scene")
        if scene.source_scene.type == "twitter":
            tmp_video_path = os.path.join(temp_dir, "scene_video.mp4")
            video_path = await create_static_video(
                scene.image_path, scene.duration, tmp_video_path
            )
            return video_path
        else:
            generated_video_url = await self.ttv_model.generate_video(
                start_image=scene.image_cloudflare_url,
                aspect_ratio=AspectRatio.PORTRAIT,
            )
            video_path = await download_video_from_url(
                generated_video_url,
                os.path.join(temp_dir, "generated_video.mp4"),
            )
            clipped_video = await clip_video(
                video_path,
                scene.duration,
                os.path.join(temp_dir, "scene_clip.mp4"),
            )
        return clipped_video
