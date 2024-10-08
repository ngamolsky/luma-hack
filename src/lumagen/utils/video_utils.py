import asyncio
import tempfile
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

import requests
from moviepy.editor import (
    AudioFileClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    VideoFileClip,
    concatenate_videoclips,
)

from lumagen.state_manager import SceneState
from lumagen.utils.logger import WorkflowLogger

logger = WorkflowLogger()

# Create a thread pool for CPU-bound tasks
video_thread_pool = ThreadPoolExecutor(max_workers=4)


async def download_video_from_url(url: str, output_path: Optional[str] = None) -> str:
    """
    Download a video from a given URL.

    Args:
        url (str): URL of the video to download.
        output_path (str, optional): Path to save the downloaded video. If not provided, a temporary file will be created.

    Returns:
        str: Path to the downloaded video file.
    """
    response = requests.get(url, stream=True)
    response.raise_for_status()

    if output_path is None:
        # Create a temporary file with .mp4 extension
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
            output_path = temp_file.name

    with open(output_path, "wb") as file:
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)

    return output_path


async def create_static_video(
    image_path: str, duration: float, output_path: str
) -> str:
    """
    Create a static video from an image.

    Args:
        image_path (str): Path to the input image file.
        duration (float): Duration of the output video in seconds.
        output_path (str): Path to save the output video file.

    Returns:
        str: Path to the created video file.
    """

    def _create_static_video():
        image_clip = ImageClip(image_path).set_duration(duration)
        image_clip.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            logger=None,
        )
        return output_path

    return await asyncio.get_event_loop().run_in_executor(
        video_thread_pool, _create_static_video
    )


async def clip_video(input_path: str, duration: float, output_path: str) -> str:
    """
    Clip a video to the specified duration.

    Args:
        video_path (Union[str, VideoFileClip]): Path to the input video file or a VideoFileClip object.
        duration (float): Desired duration of the output video in seconds.
        output_path (str): Path to save the output video file.

    Returns:
        str: Path to the clipped video file.
    """

    def _clip_video():
        with VideoFileClip(input_path) as video:
            clipped = video.subclip(0, duration)
            clipped.write_videofile(
                output_path, codec="libx264", audio_codec="aac", logger=None
            )
        return output_path

    return await asyncio.get_event_loop().run_in_executor(
        video_thread_pool, _clip_video
    )


def create_final_video(
    scenes: List[SceneState], audio_path: str, output_path: str
) -> str:
    """
    Create the final video by combining scene clips, adding audio, and captions.

    Args:
        scenes (List[Dict]): List of scene dictionaries from the storyboard.
        audio_path (str): Path to the audio file.
        output_path (str): Path to save the final video.

    Returns:
        str: Path to the final video file.
    """
    logger.info("Starting to create final video")

    # Load audio
    logger.debug(f"Loading audio from {audio_path}")
    audio = AudioFileClip(audio_path)

    # Prepare video clips and captions
    video_clips = []

    for scene in scenes:
        if scene.final_video_path:
            logger.debug(f"Loading video clip from {scene.final_video_path}")
            clip = VideoFileClip(scene.final_video_path, target_resolution=(1024, None))

            caption = TextClip(
                scene.source_scene.script_chunk,
                fontsize=40,
                font="Arial",
                color="white",
                size=(int(clip.w * 0.8), None),
                bg_color="black",
                method="caption",
                align="center",
            )
            caption = (
                caption.set_position(("center", "bottom"))
                .set_duration(clip.duration)
                .margin(bottom=60, opacity=0)
            )

            # Combine the video clip with its caption
            captioned_clip = CompositeVideoClip([clip, caption])
            video_clips.append(captioned_clip)

    # Concatenate video clips (now including captions)
    logger.debug("Concatenating video clips with captions")
    final_video = concatenate_videoclips(
        video_clips,
        method="compose",
    )

    # Add audio
    final_video = final_video.set_audio(audio)

    # Write final video
    logger.debug(f"Writing final video to {output_path}")
    final_video.write_videofile(
        output_path, codec="libx264", audio_codec="aac", logger=None
    )

    # Close all clips to release resources
    audio.close()
    for clip in video_clips:
        clip.close()
    final_video.close()

    logger.debug("Final video creation completed")
    return output_path
