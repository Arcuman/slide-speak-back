import logging
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

from werkzeug.utils import secure_filename

from app.config import Config
from app.storage.s3_storage import upload_file_to_s3
from app.utils.file_utils import ppt_preview

# Setup logging
logger = logging.getLogger(__name__)

# Create a dedicated thread pool for document processing
document_executor = ThreadPoolExecutor(max_workers=4)


class DocumentService:
    """Service for handling document operations"""

    @staticmethod
    def save_uploaded_file(uploaded_file, documents_dir=None):
        """
        Save uploaded file to disk

        Args:
            uploaded_file: File from request
            documents_dir: Directory to save file to (default: Config.DOCUMENTS_DIR)

        Returns:
            tuple: (filepath, filename, generated_uuid)
        """
        if documents_dir is None:
            documents_dir = Config.DOCUMENTS_DIR

        generated_uuid = str(uuid.uuid4())
        filename = secure_filename(str(uuid.uuid4()) + ".pptx")

        # Create directory if it doesn't exist
        if not os.path.exists(documents_dir):
            os.makedirs(documents_dir)

        filepath = os.path.join(documents_dir, os.path.basename(filename))

        start_time = time.time()
        uploaded_file.save(filepath)
        logger.info(f"File saved to {filepath} in {time.time() - start_time:.2f}s")

        return filepath, filename, generated_uuid

    @staticmethod
    def generate_previews(filepath, preview_dir=None, doc_uuid=None):
        """
        Generate preview images for document

        Args:
            filepath: Path to document file
            preview_dir: Directory to save previews (default: Config.PREVIEW_DIR)
            doc_uuid: UUID to use for preview filenames

        Returns:
            list: Paths to generated preview images
        """
        if preview_dir is None:
            preview_dir = Config.PREVIEW_DIR

        if doc_uuid is None:
            doc_uuid = str(uuid.uuid4())

        # Create directory if it doesn't exist
        if not os.path.exists(preview_dir):
            os.makedirs(preview_dir)

        start_time = time.time()
        preview_file_paths = ppt_preview(
            filepath, os.path.join(preview_dir, doc_uuid + ".jpg")
        )
        logger.info(f"Preview generation completed in {time.time() - start_time:.2f}s")

        return preview_file_paths

    @staticmethod
    def upload_previews_to_s3(preview_file_paths, bucket_name=None):
        """
        Upload preview images to S3

        Args:
            preview_file_paths: List of paths to preview images
            bucket_name: S3 bucket name (default: Config.S3_BUCKET)

        Returns:
            list: URLs of uploaded previews in order
        """
        if bucket_name is None:
            bucket_name = Config.S3_BUCKET

        preview_urls_dict = {}

        if not preview_file_paths:
            return []

        # Make a list of all futures for the uploads
        future_to_preview = {
            document_executor.submit(
                upload_file_to_s3,
                preview_file_path,
                bucket_name,
                "preview-images/" + os.path.basename(preview_file_path),
            ): preview_file_path
            for preview_file_path in preview_file_paths
        }

        start_time = time.time()
        for future in as_completed(future_to_preview):
            preview_file_path = future_to_preview[future]
            try:
                preview_url = future.result()
                index = preview_file_paths.index(preview_file_path)
                preview_urls_dict[index] = preview_url

                # Delete local file after successful upload
                if os.path.exists(preview_file_path):
                    os.remove(preview_file_path)
            except Exception as exc:
                logger.error(f"{preview_file_path} generated an exception: {exc}")

        logger.info(f"S3 upload completed in {time.time() - start_time:.2f}s")

        # Convert dict to list in correct order
        return [preview_urls_dict[i] for i in sorted(preview_urls_dict.keys())]

    @staticmethod
    def process_document(file, use_filename=False, index_service=None):
        """
        Process uploaded document end-to-end

        Args:
            file: Uploaded file object
            use_filename: Whether to use filename as document ID
            index_service: Service for indexing documents

        Returns:
            dict: Response data with UUID and preview URLs
        """
        filepath = None
        try:
            # Save uploaded file
            filepath, filename, generated_uuid = DocumentService.save_uploaded_file(
                file
            )

            # Index the document
            if index_service:
                doc_id = filename if use_filename else generated_uuid
                index_service.index_document(filepath, doc_id, use_filename)

            # Upload original file to S3
            start_time = time.time()
            s3_future = document_executor.submit(
                upload_file_to_s3,
                filepath,
                Config.S3_BUCKET,
                generated_uuid + os.path.splitext(filepath)[1],
            )
            logger.info(f"S3 upload started, will take {time.time() - start_time:.2f}s")

            # Generate and upload previews
            preview_file_paths = DocumentService.generate_previews(
                filepath, doc_uuid=generated_uuid
            )
            preview_urls = DocumentService.upload_previews_to_s3(preview_file_paths)

            # Clean up original file after S3 upload completes
            s3_future.add_done_callback(
                lambda _: os.remove(filepath) if os.path.exists(filepath) else None
            )

            return {"uuid": generated_uuid, "previewUrls": preview_urls}

        except Exception as e:
            logger.error(f"Error processing document: {str(e)}", exc_info=True)
            # Clean up temp file if it exists
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
            raise
