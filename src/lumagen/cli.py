import argparse

from lumagen import main as lumagen_main


def main():
    parser = argparse.ArgumentParser(description="LumaGen CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run the Lumagen workflow")
    run_parser.add_argument("--project-name", required=True, help="Project name")
    run_parser.add_argument(
        "--source", required=True, help="Path to source file, url or markdown"
    )
    run_parser.add_argument("--duration", required=False, help="Duration of the video")
    run_parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    run_parser.add_argument(
        "--overwrite", action="store_true", help="Overwrite existing content and state"
    )

    # Clear command
    clear_parser = subparsers.add_parser("clear", help="Clear the state of the project")
    clear_parser.add_argument("--project-name", required=True, help="Project name")

    # Load source command
    load_parser = subparsers.add_parser("load_source", help="Load source material")
    load_parser.add_argument(
        "--source", required=True, help="Path to source file or URL"
    )
    load_parser.add_argument("--project-name", required=True, help="Project name")
    load_parser.add_argument(
        "--overwrite", action="store_true", help="Overwrite existing content"
    )
    # Process scene command
    process_parser = subparsers.add_parser(
        "process_scene", help="Process a specific scene"
    )
    process_parser.add_argument("--scene-id", required=True, help="Scene ID")
    process_parser.add_argument("--project-name", required=True, help="Project name")
    process_parser.add_argument(
        "--debug", action="store_true", help="Enable debug mode"
    )
    args = parser.parse_args()

    if args.command == "run":
        kwargs = {
            "project_name": args.project_name,
            "source": args.source,
            "debug_mode": args.debug,
            "overwrite": args.overwrite,
        }
        if args.duration:
            kwargs["duration"] = args.duration
        lumagen_main.main(**kwargs)
    elif args.command == "clear":
        lumagen_main.clear_state(args.project_name)
    elif args.command == "load_source":
        lumagen_main.load_source(args.project_name, args.source, args.overwrite)
    elif args.command == "process_scene":
        lumagen_main.process_scene_by_id(args.project_name, args.scene_id, args.debug)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
