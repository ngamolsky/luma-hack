from dotenv import load_dotenv

load_dotenv()

# ruff: noqa
import argparse
import asyncio
import os
import shutil
import urllib.request

from lumagen.state_manager import StateManager

from .workflow_manager import WorkflowManager


PROJECT_ID = "wordpress-drama"


def load_source(source):
    if source.startswith(("http://", "https://")):
        with urllib.request.urlopen(source) as response:
            return response.read().decode("utf-8")
    else:
        with open(source, "r") as file:
            return file.read()


def main():
    parser = argparse.ArgumentParser(description="Run the Lumagen workflow")
    parser.add_argument(
        "--source",
        default="src/data/source/source.md",
        help="Path or URL to the source material",
    )
    parser.add_argument(
        "--duration", type=int, default=40, help="Duration of the video in seconds"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear the state of the project before running",
    )
    args = parser.parse_args()

    if args.clear:
        clear_state()

    source_material = load_source(args.source)
    duration = args.duration

    workflow = WorkflowManager(
        PROJECT_ID, source_material=source_material, duration=duration
    )

    asyncio.run(workflow.run())


def clear_state():
    state_manager = StateManager(PROJECT_ID)
    state_manager.clear_state()

    output_dir = os.path.join("src", "data", "output", PROJECT_ID)

    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)


def process_scene_by_id():
    parser = argparse.ArgumentParser(description="Run the Lumagen workflow")
    parser.add_argument("--scene_id", type=str, help="ID of the scene to process")
    args = parser.parse_args()

    scene_id = args.scene_id
    workflow = WorkflowManager(PROJECT_ID)
    asyncio.run(workflow.generate_video_from_scene_id(scene_id))


if __name__ == "__main__":
    main()
