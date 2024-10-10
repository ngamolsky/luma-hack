from dotenv import load_dotenv

from lumagen.utils.logger import WorkflowLogger

load_dotenv()

import asyncio
from pathlib import Path
from typing import Union

from lumagen.source_loader import SourceLoader
from lumagen.state_manager import StateManager
from lumagen.workflow_manager import WorkflowManager

DEFAULT_DURATION = 40


def main(
    project_name: str,
    source: Union[str, Path],
    duration: int = DEFAULT_DURATION,
    debug_mode: bool = False,
    overwrite: bool = False,
):
    workflow = WorkflowManager(
        project_name,
        source=source,
        duration=duration,
        debug_mode=debug_mode,
        overwrite=overwrite,
    )

    asyncio.run(workflow.run())


def clear_state(project_name: str):
    logger = WorkflowLogger()
    logger.start()

    if not project_name:
        raise ValueError("Project name is required")

    state_manager = StateManager(project_name)
    state_manager.clear_state()
    logger.stop()


def process_scene_by_id(project_name: str, scene_id: str, debug_mode: bool = False):
    if not project_name:
        raise ValueError("Project name is required")

    if not scene_id:
        raise ValueError("Scene ID is required")

    workflow = WorkflowManager(project_name, debug_mode=debug_mode)
    asyncio.run(workflow.generate_video_from_scene_id(scene_id))


def load_source(
    project_name: str, url: Union[str, Path], overwrite: bool = False
) -> int:
    logger = WorkflowLogger()
    logger.start()

    try:
        _, output_path = SourceLoader.load(project_name, url, overwrite)
        logger.info(f"Source loaded successfully and saved to {output_path}")
        logger.stop()
        return 0  # Return 0 to indicate success
    except Exception as e:
        logger.error(f"Error loading source: {str(e)}")
        logger.stop()
        return 1  # Return non-zero to indicate failure
    finally:
        logger.stop()
