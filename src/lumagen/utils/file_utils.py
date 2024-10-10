import os
from pathlib import Path

import boto3
from botocore.client import Config
from pydantic import FilePath

from lumagen.utils.logger import WorkflowLogger

logger = WorkflowLogger()

# Cloudflare R2 configuration
ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID")
ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID")
SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY")
BUCKET_NAME = os.environ.get("R2_BUCKET_NAME")
CLOUDFLARE_BUCKET_PUBLIC_URL = os.environ.get("R2_BUCKET_PUBLIC_URL")

# Initialize S3 client for Cloudflare R2
s3_client = boto3.client(
    "s3",
    endpoint_url=f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=ACCESS_KEY_ID,
    aws_secret_access_key=SECRET_ACCESS_KEY,
    config=Config(signature_version="s3v4"),
)


def save_bytes_to_file(data: bytes, filepath: str) -> FilePath:
    """
    Save bytes data to a file with the given filepath and extension.

    Args:
        data (bytes): The bytes data to be saved.
        filepath (str): The full path of the file without extension.
        extension (str): The file extension (without the dot).

    Returns:
        FilePath: The full path of the saved file.
    """
    logger.debug(f"Saving bytes to file: {filepath}")

    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    # Write the bytes data to the file
    with open(filepath, "wb") as file:
        file.write(data)

    logger.debug(f"Successfully saved file: {filepath}")
    return Path(filepath)


def upload_to_cloudflare(file_path: str) -> str:
    """
    Upload a file to Cloudflare R2 bucket and return the public URL.

    Args:
        file_path (str): The path to the file to be uploaded.

    Returns:
        str: The public URL of the uploaded file.
    """

    with open(file_path, "rb") as file:
        # Print the type of file
        object_name = os.path.basename(file_path)
        s3_client.upload_fileobj(file, BUCKET_NAME, object_name)

    logger.debug(
        f"Successfully uploaded file. Public URL: {CLOUDFLARE_BUCKET_PUBLIC_URL}/{object_name}"
    )
    return f"{CLOUDFLARE_BUCKET_PUBLIC_URL}/{object_name}"


def delete_from_cloudflare(file_path: str) -> None:
    """
    Delete a file from Cloudflare R2 bucket.

    Args:
        file_path (str): The path to the file to be deleted.
    """
    logger.debug(f"Deleting file from Cloudflare R2: {file_path}")
    try:
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=file_path)
        logger.debug(f"Successfully deleted file: {file_path}")
    except Exception as e:
        logger.error(f"Error deleting file from Cloudflare R2: {str(e)}")
