import os
import urllib.request
from typing import Union

from lumagen.utils.logger import WorkflowLogger

logger = WorkflowLogger()


class SourceLoader:
    @staticmethod
    def load(
        source: Union[str, os.PathLike], project_id: str, overwrite: bool = False
    ) -> str:
        """
        Load content from a URL, markdown string, or file path, save it as markdown, and return the content.

        Args:
            source (Union[str, os.PathLike]): The source, which can be a URL, markdown string, or file path.
            project_id (str): The project ID used to name the output file.
            overwrite (bool): Whether to overwrite existing content if it exists.

        Returns:
            str: The content as markdown.

        Raises:
            ValueError: If the source type cannot be determined or if there's an error loading the content.
        """
        output_path = os.path.join("src", "data", "source", f"{project_id}.md")

        # Check if content already exists and load it if not overwriting
        if os.path.exists(output_path) and not overwrite:
            logger.info(
                f"Content already exists at {output_path}. Loading from existing file."
            )
            with open(output_path, "r", encoding="utf-8") as f:
                return f.read()

        content = ""
        if isinstance(source, str):
            if source.startswith(("http://", "https://")):
                content = SourceLoader._load_from_url(source)
            elif os.path.isfile(source):
                content = SourceLoader._load_from_file(source)
            else:
                # Assume it's already markdown
                content = source
        elif isinstance(source, os.PathLike):
            content = SourceLoader._load_from_file(source)
        else:
            raise ValueError(
                "Invalid source type. Expected URL, file path, or markdown string."
            )

        # Save the content to a file
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        return content

    @staticmethod
    def _load_from_url(url: str) -> str:
        try:
            with urllib.request.urlopen(url) as response:
                return response.read().decode("utf-8")
        except Exception as e:
            raise ValueError(f"Error loading content from URL: {e}")

    @staticmethod
    def _load_from_file(file_path: Union[str, os.PathLike]) -> str:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return file.read()
        except Exception as e:
            raise ValueError(f"Error loading content from file: {e}")
