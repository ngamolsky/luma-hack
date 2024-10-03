import os

import boto3
from botocore.client import Config

ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID")
ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID")
SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY")
BUCKET_NAME = os.environ.get("R2_BUCKET_NAME")
CLOUDFLARE_BUCKET_PUBLIC_URL = os.environ.get(
    "R2_BUCKET_PUBLIC_URL", "https://pub-2576bbab2f764a5a9c3fdc59f470ef1a.r2.dev"
)

s3_client = boto3.client(
    "s3",
    endpoint_url=f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=ACCESS_KEY_ID,
    aws_secret_access_key=SECRET_ACCESS_KEY,
    config=Config(signature_version="s3v4"),
)


async def upload_to_cloudflare(image_path):
    try:
        with open(image_path, "rb") as file:
            object_name = os.path.basename(image_path)
            s3_client.upload_fileobj(file, BUCKET_NAME, object_name)

            file_name = image_path.split("/")[-1]
            cloudflare_url = f"{CLOUDFLARE_BUCKET_PUBLIC_URL}/{file_name}"
            return cloudflare_url
    except Exception as e:
        print(f"Error uploading to Cloudflare R2: {str(e)}")
        return None
