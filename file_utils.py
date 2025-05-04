import logging
import os
import time
import zipfile

import requests
from pdf2image import convert_from_path

# Setup logging
logger = logging.getLogger(__name__)


def search_and_extract(zip_filepath, target_files, extract_to):
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
                print(f"File {filename} extracted to {extract_to}")
                extracted_files.append(extract_to + "/" + os.path.basename(filename))
    return extracted_files


def ppt_preview(ppt_file_path, preview_file_path):
    # Check the file extension
    if not ppt_file_path.endswith((".ppt", ".pptx")):
        raise ValueError("File must be a .ppt or .pptx file")

    # Generate a temporary pdf path
    pdf_file_path = os.path.splitext(ppt_file_path)[0] + ".pdf"
    logger.info(f"Converting {ppt_file_path} to {pdf_file_path}")

    # Unoserver REST API settings
    unoserver_url = os.getenv("UNOSERVER_URL", "http://unoserver:2004")
    max_retries = 5
    retry_delay = 2  # starting delay in seconds

    # Convert PowerPoint to PDF using unoserver REST API with retry logic
    pdf_data = None
    last_error = None

    for attempt in range(max_retries):
        try:
            logger.info(f"Unoserver connection attempt {attempt + 1}/{max_retries}")
            with open(ppt_file_path, "rb") as f:
                resp = requests.post(
                    f"{unoserver_url}/request",
                    files={"file": f},
                    data={"convert-to": "pdf"},
                    timeout=60,
                )

            if resp.status_code != 200:
                error_msg = (
                    f"Unoserver conversion failed with status {resp.status_code}"
                )
                logger.error(f"{error_msg}: {resp.text}")
                last_error = ValueError(error_msg)
                # Retry with backoff
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue

            # Save PDF content to file
            with open(pdf_file_path, "wb") as f:
                f.write(resp.content)
            logger.info(f"Conversion successful, saved to {pdf_file_path}")
            break  # Success, exit retry loop

        except requests.RequestException as e:
            logger.warning(
                f"Request to Unoserver failed (attempt {attempt + 1}): {str(e)}"
            )
            last_error = e
            # Retry with backoff
            time.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff

    # If all retries failed
    if not os.path.exists(pdf_file_path):
        logger.error(f"All {max_retries} connection attempts to Unoserver failed")
        raise last_error or ValueError("Failed to connect to Unoserver service")

    # Convert PDF to list of images
    images = convert_from_path(pdf_file_path)

    preview_file_paths = []
    for i, image in enumerate(images):
        fname = os.path.splitext(preview_file_path)[0] + f"-{i}.jpg"
        image.save(fname, "JPEG")
        preview_file_paths.append(fname)

    return preview_file_paths
