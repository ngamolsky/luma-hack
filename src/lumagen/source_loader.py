import os
from pathlib import Path
from typing import Tuple, Union

import html2text
import httpx

from lumagen.utils.logger import WorkflowLogger

logger = WorkflowLogger()


class SourceLoader:
    @staticmethod
    def load(
        project_name: str,
        source: Union[str, Path],
        overwrite: bool = False,
    ) -> Tuple[str, Path]:
        """
        Load content from a URL, markdown string, or file path, save it as markdown, and return the content and path.

        Args:
            source (Union[str, Path]): The source, which can be a URL, markdown string, or file path.
            project_id (str): The project ID used to name the output file.
            overwrite (bool): Whether to overwrite existing content if it exists.

        Returns:
            Tuple[str, Path]: A tuple containing the content as markdown and the Path object where it's saved.

        Raises:
            ValueError: If the source type cannot be determined or if there's an error loading the content.
        """
        output_path = Path("src") / "data" / "source" / f"{project_name}.md"

        # Check if content already exists and load it if not overwriting
        if output_path.exists() and not overwrite:
            logger.info(
                f"Content already exists at {output_path}. Loading from existing file."
            )
            return output_path.read_text(encoding="utf-8"), output_path

        content = ""
        if isinstance(source, str):
            if source.startswith(("http://", "https://")):
                content = SourceLoader._load_from_url(source)
            elif Path(source).is_file():
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
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")

        logger.info(f"Loaded content from {source} and saved to {output_path}")
        return content, output_path

    @staticmethod
    def _load_from_url(url: str) -> str:
        try:
            with httpx.Client() as client:
                response = client.get(url)
                response.raise_for_status()
                html_content = response.text

            h = html2text.HTML2Text()
            h.ignore_links = False
            markdown_content = h.handle(html_content)
            return markdown_content
        except Exception as e:
            raise ValueError(f"Error loading content from URL: {e}")

    @staticmethod
    def _load_from_file(file_path: Union[str, os.PathLike]) -> str:
        try:
            return Path(file_path).read_text(encoding="utf-8")
        except Exception as e:
            raise ValueError(f"Error loading content from file: {e}")
