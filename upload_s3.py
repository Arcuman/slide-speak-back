import os
from urllib.parse import urlparse

import boto3

# Check if we're in a local development environment using environment variable
IS_LOCAL = os.environ.get("USE_MINIO", "false").lower() == "true"

# MinIO configuration
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")


# Initialize S3 client based on environment
def get_s3_client():
    if IS_LOCAL:
        # Use MinIO for local development
        return boto3.client("s3", endpoint_url=MINIO_ENDPOINT)
    else:
        # Use AWS S3 for production
        return boto3.client("s3")


def upload_file_to_s3(file_path, bucket_name, object_name=None):
    # Get appropriate S3 client
    s3 = get_s3_client()

    # Specify the S3 bucket and object name
    if object_name is None:
        object_name = os.path.basename(file_path)

    # Create bucket if it doesn't exist (for MinIO)
    if IS_LOCAL:
        try:
            s3.head_bucket(Bucket=bucket_name)
        except:
            s3.create_bucket(Bucket=bucket_name)

    # Upload the file to S3
    try:
        s3.upload_file(file_path, bucket_name, object_name)

        # Construct the URL differently depending on environment
        if IS_LOCAL:
            parsed_url = urlparse(MINIO_ENDPOINT)
            file_url = (
                f"{parsed_url.scheme}://localhost:9000/{bucket_name}/{object_name}"
            )
        else:
            file_url = f"https://{bucket_name}.s3.amazonaws.com/{object_name}"

        print("File uploaded successfully.")
        print(file_url)
        return file_url
    except Exception as e:
        print("Error uploading file:", str(e))
        return None


def delete_file_by_path(filepath):
    if filepath is not None and os.path.exists(filepath):
        os.remove(filepath)
