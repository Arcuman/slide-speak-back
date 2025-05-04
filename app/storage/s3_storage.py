import os
from urllib.parse import urlparse

import boto3

from app.config import Config


def get_s3_client():
    """
    Initialize S3 client based on environment
    Returns an S3 client configured for either MinIO (local) or AWS S3
    """
    if Config.IS_LOCAL:
        # Use MinIO for local development
        return boto3.client(
            "s3",
            endpoint_url=Config.MINIO_ENDPOINT,
            aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
        )
    else:
        # Use AWS S3 for production
        return boto3.client(
            "s3",
            aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
        )


def upload_file_to_s3(file_path, bucket_name, object_name=None):
    """
    Upload a file to S3 or MinIO

    Args:
        file_path: Path to the file to upload
        bucket_name: Name of the S3 bucket
        object_name: Name to give the object in S3 (defaults to filename)

    Returns:
        URL of the uploaded file or None if upload failed
    """
    # Get appropriate S3 client
    s3 = get_s3_client()

    # Specify the S3 bucket and object name
    if object_name is None:
        object_name = os.path.basename(file_path)

    # Create bucket if it doesn't exist (for MinIO)
    if Config.IS_LOCAL:
        try:
            s3.head_bucket(Bucket=bucket_name)
        except:
            s3.create_bucket(Bucket=bucket_name)

    # Upload the file to S3
    try:
        s3.upload_file(file_path, bucket_name, object_name)

        # Construct the URL differently depending on environment
        if Config.IS_LOCAL:
            parsed_url = urlparse(Config.MINIO_ENDPOINT)
            file_url = (
                f"{parsed_url.scheme}://localhost:9000/{bucket_name}/{object_name}"
            )
        else:
            file_url = f"https://{bucket_name}.s3.amazonaws.com/{object_name}"

        print(f"File {object_name} uploaded successfully to {bucket_name}")
        return file_url
    except Exception as e:
        print(f"Error uploading file {file_path} to S3: {str(e)}")
        return None


def delete_file_by_path(filepath):
    """
    Delete a file from the local filesystem if it exists

    Args:
        filepath: Path to the file to delete
    """
    if filepath is not None and os.path.exists(filepath):
        try:
            os.remove(filepath)
            print(f"Successfully deleted local file: {filepath}")
        except Exception as e:
            print(f"Error deleting file {filepath}: {str(e)}")
