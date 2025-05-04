import functools
import logging
import os
import time
import zipfile

import requests
from pdf2image import convert_from_path

# Setup logging
logger = logging.getLogger(__name__)


def search_and_extract(zip_filepath, target_files, extract_to):
    """
    Search for and extract specific files from a zip archive

    Args:
        zip_filepath: Path to the zip file
        target_files: List of filenames to extract
        extract_to: Directory to extract files to

    Returns:
        List of paths to extracted files
    """
    # Ensure the target directory exists
    if not os.path.exists(extract_to):
        os.makedirs(extract_to)

    extracted_files = []

    # Open the zip file in read mode
    with zipfile.ZipFile(zip_filepath, "r") as zip_ref:
        # Loop over the files in the zip file
        for filename in zip_ref.namelist():
            # Check the filename part after the last slash
            if os.path.basename(filename) in target_files:
                # Extract the file
                zip_ref.extract(filename, extract_to)
                logger.info(f"File {filename} extracted to {extract_to}")
                extracted_files.append(
                    os.path.join(extract_to, os.path.basename(filename))
                )
    return extracted_files


def retry_with_backoff(max_retries=5, initial_delay=2):
    """
    Decorator for retrying a function with exponential backoff.

    Args:
        max_retries: Maximum number of retries
        initial_delay: Initial delay in seconds
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_error = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except requests.RequestException as e:
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}/{max_retries}): {str(e)}"
                    )
                    last_error = e
                    # Sleep with backoff
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff

            # If we get here, all retries failed
            logger.error(f"All {max_retries} attempts failed")
            raise last_error or ValueError(f"Failed after {max_retries} attempts")

        return wrapper

    return decorator


@retry_with_backoff()
def convert_ppt_to_pdf(ppt_file_path, pdf_file_path):
    """
    Convert PowerPoint to PDF using unoserver REST API.

    Args:
        ppt_file_path: Path to PowerPoint file
        pdf_file_path: Path where PDF should be saved

    Returns:
        Path to the PDF file

    Raises:
        ValueError: If conversion fails
        requests.RequestException: On connection error
    """
    unoserver_url = os.getenv("UNOSERVER_URL", "http://unoserver:2004")

    logger.info(f"Converting {ppt_file_path} to {pdf_file_path} using {unoserver_url}")
    with open(ppt_file_path, "rb") as f:
        resp = requests.post(
            f"{unoserver_url}/request",
            files={"file": f},
            data={"convert-to": "pdf"},
            timeout=60,
        )

    if resp.status_code != 200:
        error_msg = f"Unoserver conversion failed with status {resp.status_code}"
        logger.error(f"{error_msg}: {resp.text}")
        raise ValueError(error_msg)

    # Save PDF content to file
    with open(pdf_file_path, "wb") as f:
        f.write(resp.content)
    logger.info(f"Conversion successful, saved to {pdf_file_path}")
    return pdf_file_path


def ppt_preview(ppt_file_path, preview_file_path):
    """
    Generate preview images from a PowerPoint file

    Args:
        ppt_file_path: Path to the PowerPoint file
        preview_file_path: Base path for preview images

    Returns:
        List of paths to generated preview images
    """
    # Check the file extension
    if not ppt_file_path.endswith((".ppt", ".pptx")):
        raise ValueError("File must be a .ppt or .pptx file")

    # Generate a temporary pdf path
    pdf_file_path = os.path.splitext(ppt_file_path)[0] + ".pdf"

    try:
        # Convert PowerPoint to PDF using unoserver REST API with retry logic
        convert_ppt_to_pdf(ppt_file_path, pdf_file_path)

        # Convert PDF to list of images
        images = convert_from_path(pdf_file_path)

        preview_file_paths = []
        for i, image in enumerate(images):
            fname = os.path.splitext(preview_file_path)[0] + f"-{i}.jpg"
            image.save(fname, "JPEG")
            preview_file_paths.append(fname)

        return preview_file_paths
    finally:
        # Clean up PDF file
        if os.path.exists(pdf_file_path):
            os.remove(pdf_file_path)
