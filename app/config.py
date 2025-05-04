import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Central configuration class for the application"""

    # AWS S3 configuration
    IS_LOCAL = os.environ.get("USE_MINIO", "false").lower() == "true"
    MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")
    AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
    S3_BUCKET = os.environ.get("S3_BUCKET", "slidespeak-files")

    # MongoDB configuration
    MONGO_DB_URL = os.environ.get("MONGO_DB_URL")

    # Pinecone configuration
    PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
    PINECONE_REGION = os.environ.get("PINECONE_REGION", "us-east-1")
    PINECONE_INDEX = os.environ.get("PINECONE_INDEX", "pptx-index")

    # OpenAI configuration
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

    # Server settings
    DEBUG = os.environ.get("DEBUG", "False").lower() == "true"
    PORT = int(os.environ.get("PORT", 5601))

    # File storage
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "documents")

    # Unoserver
    UNOSERVER_URL = os.environ.get("UNOSERVER_URL", "http://unoserver:2004")

    # Index server settings
    INDEX_SERVER_HOST = os.getenv(
        "INDEX_SERVER_HOST", "127.0.0.1"
    )  # Default to localhost for security
    INDEX_SERVER_PORT = int(os.getenv("INDEX_SERVER_PORT", "5602"))
    INDEX_SERVER_MAX_RETRIES = int(os.getenv("INDEX_SERVER_MAX_RETRIES", "10"))
    INDEX_SERVER_RETRY_INTERVAL = int(os.getenv("INDEX_SERVER_RETRY_INTERVAL", "3"))

    # Directory paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DOCUMENTS_DIR = os.path.join(BASE_DIR, UPLOAD_FOLDER)
    PREVIEW_DIR = os.path.join(BASE_DIR, "preview_images")

    @classmethod
    def validate(cls):
        """Validate critical configuration is present"""
        missing = []

        if not cls.MONGO_DB_URL:
            missing.append("MONGO_DB_URL")

        if not cls.PINECONE_API_KEY:
            missing.append("PINECONE_API_KEY")

        if not cls.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")

        if not cls.AWS_ACCESS_KEY_ID:
            missing.append("AWS_ACCESS_KEY_ID")

        if not cls.AWS_SECRET_ACCESS_KEY:
            missing.append("AWS_SECRET_ACCESS_KEY")

        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

        # Create required directories
        os.makedirs(cls.DOCUMENTS_DIR, exist_ok=True)
        os.makedirs(cls.PREVIEW_DIR, exist_ok=True)

        return True
