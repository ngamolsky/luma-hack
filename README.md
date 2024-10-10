# LumaGen

Generate a youtube short from anything (well for now just text)!

## Installation

1. Ensure you have Python 3.10 or higher installed.

2. Install system dependencies:

   - ImageMagick: You can install this using Homebrew on macOS:
     ```
     brew install imagemagick
     ```
     For other operating systems, please refer to the [ImageMagick installation guide](https://imagemagick.org/script/download.php).

3. Clone this repository:
   ```
   git clone https://github.com/ngamolsky/lumagen.git
   cd lumagen
   ```
4. Install the required dependencies:
   ```
   pip install -e .
   ```

## Usage

LumaGen provides several commands to manage and generate content:

- `lumagen run --project-name "project_name" --source "path/to/source.md" [--duration DURATION] [--debug]`: Run the Lumagen workflow.
- `lumagen clear --project-name "project_name"`: Clear the state of the project.
- `lumagen load_source --project-name "project_name" --source "path/to/source.md" [--overwrite]`: Load source material from a file or URL.
- `lumagen process_scene --project-name "project_name" --scene-id "scene_id" [--debug]`: Process a specific scene by ID.

The debug flag will set a much more verbose logger, and will prevent the temp files from being deleted after a successful run.

## State Management System

The LumaGen system is complex and error prone as it relies on a lot of GenAI calls and steps.

For this reason, Lumagen uses a robust state management system to handle the various stages of content generation and processing. The core of this system is implemented in the `StateManager` class.

The state is saved as the process is runnning, in a specific JSON file for the project. You can inspect the state at any point by looking at the JSON file, and retry steps by removing the appopriate state variable from the JSON file.

The Logger output should give you a sense of what state has been reached.

## Gen AI Models

The Gen AI models are defined in the `models` directory. This allows for easy swapping out of models, or integration of new models as the improve. The types of models supported and their implementations currently are:

- `text—model`: Used for text generation
  - `openai_llm`: OpenAI LLM model
- `tts`: Used for generating audio from text
  - `cartesia_tts`: Cartesia TTS model
- `text_to_image`: Used for generating images from text
  - `fal_t2i`: Fal text to image
  - `ideogram_t2i`: Ideogram text to image
- `text_to_video`: Used for generating video from text
  - `luma_ai`: Luma AI text (or image) to video model

## Source Loader

The SourceLoader class is used to load source material from a file or URL. It supports both local files and URLs. The source material is loaded into a markdown file, which is then used for generating everything else.

It will attempt to load the source as markdown, and save it in the src/data/source directory.

## Supported Scene Types

To generate the video, we generate a storyboard, which is a series of scenes. We currently support the following scene types:

- `meme_scene`: A scene with an animated meme, relevant to the script.
- `generic_scene`: A scene that creates a generic video based on the script chunk
- `twitter_scene`: A static scene with a screenshot of a tween (using TweetCapture)

## Required API Keys

To use LumaGen, you need to set up the following API keys in your environment:

- `LUMAAI_API_KEY`: API key for Luma AI text-to-video model
- `OPENAI_API_KEY`: API key for OpenAI's language models
- `IDEOGRAM_API_KEY`: API key for Ideogram text-to-image model
- `CLOUDFLARE_API_KEY`: API key for Cloudflare services
- `AIRTABLE_API_KEY`: API key for Airtable
- `CARTESIA_API_KEY`: API key for Cartesia TTS model
- `FAL_KEY`: API key for Fal.ai services
- `CLOUDFLARE_KEYS`:
  - `R2_ACCOUNT_ID`: Cloudflare R2 account ID
  - `R2_ACCESS_KEY_ID`: Access key ID for Cloudflare R2
  - `R2_SECRET_ACCESS_KEY`: Secret access key for Cloudflare R2
  - `R2_BUCKET_NAME`: Name of your R2 bucket
  - `R2_BUCKET_PUBLIC_URL`: Public URL for your R2 bucket

You can set these environment variables in a `.env` file in the root directory of your project. The application will automatically load these variables from the `.env` file when it runs.

## Future Work

### Source processing improvements

Should be able to make this multimodal to understand images and video natively. Should test with other source text.

### Audio / Video / Captions sync

Currently audio is process separately, and captions are generated from script chunks in scenes so they don't always match up. Duration fo reach scene is calculated from word count which isn't ideal.

### New scene types

Should be decently easy to add new scene types for more creative video.

### More Robust Twitter Scene

Currently uses TweetCapture, which fails a decent amount. We could write our own scraper, which could also fetch the tweet text so we could make the duration more accurate.
