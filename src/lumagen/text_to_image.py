# src/ai_video_generator/text_to_image.py

import os
from pathlib import Path
from typing import Callable, List

from pydantic import BaseModel, DirectoryPath, FilePath


class TextToImageGenerator(BaseModel):
    generator_func: Callable[[str, FilePath], FilePath]

    def generate_image_from_text(self, text: str, output_path: FilePath) -> FilePath:
        """
        Generate an image based on the input text using the provided generator function.

        Args:
        text (str): The text to generate an image from.
        output_path (FilePath): The path to save the generated image.

        Returns:
        FilePath: The path to the generated image.
        """
        return self.generator_func(text, output_path)

    def batch_generate_images(
        self, texts: List[str], output_directory: DirectoryPath
    ) -> List[FilePath]:
        """
        Generate images for a batch of texts.

        Args:
        texts (List[str]): A list of texts to generate images for.
        output_directory (DirectoryPath): The directory to save the generated images.

        Returns:
        List[FilePath]: A list of paths to the generated images.
        """
        os.makedirs(output_directory, exist_ok=True)
        return [self.generate_image_from_text(text, output_directory) for text in texts]


# Example implementation (placeholder)
def placeholder_generator(text: str, output_path: FilePath) -> FilePath:
    print(f"Generating image for text: {text}")
    image_filename = f"generated_image_{hash(text)}.png"
    full_path = os.path.join(output_path, image_filename)
    with open(full_path, "w") as f:
        f.write("Placeholder for generated image")
    return Path(full_path)


# Usage example:
# generator = TextToImageGenerator(generator_func=placeholder_generator)
# You can replace placeholder_generator with any other implementation
# For example: generator = TextToImageGenerator(generator_func=stable_diffusion_generator)
