import logging
import time

from app.core.indexing import create_index_manager
from app.utils.retry import retry_with_backoff

# Setup logging
logger = logging.getLogger(__name__)


class IndexService:
    """Service for handling index operations"""

    def __init__(self):
        self._manager = None
        self._connect_to_index_manager()

    @retry_with_backoff(max_retries=5, initial_delay=2)
    def _connect_to_index_manager(self):
        """Establish connection to index manager with retry"""
        try:
            logger.info("Connecting to index manager...")
            self._manager = create_index_manager()
            logger.info("Successfully connected to index manager")
        except Exception as e:
            logger.error(f"Failed to connect to index manager: {str(e)}")
            raise

    @property
    def manager(self):
        """Get the index manager, reconnecting if necessary"""
        if self._manager is None:
            self._connect_to_index_manager()
        return self._manager

    def initialize_index(self, doc_id):
        """
        Initialize index for a document

        Args:
            doc_id: Document ID
        """
        try:
            self.manager.initialize_index(doc_id)
        except Exception as e:
            logger.error(f"Error initializing index: {str(e)}")
            # Attempt to reconnect and retry once
            self._connect_to_index_manager()
            self.manager.initialize_index(doc_id)

    def index_document(self, filepath, doc_id, use_filename=False):
        """
        Index a document

        Args:
            filepath: Path to document
            doc_id: Document ID
            use_filename: Whether to use filename as document ID
        """
        start_time = time.time()
        try:
            if use_filename:
                self.manager.insert_into_index(filepath, doc_id=doc_id)
            else:
                self.manager.insert_into_index(filepath, doc_id)
            logger.info(f"Document indexed in {time.time() - start_time:.2f}s")
        except Exception as e:
            logger.error(f"Error indexing document: {str(e)}")
            # Attempt to reconnect and retry once
            self._connect_to_index_manager()
            if use_filename:
                self.manager.insert_into_index(filepath, doc_id=doc_id)
            else:
                self.manager.insert_into_index(filepath, doc_id)

    def query_index(self, query_text, doc_id):
        """
        Query the index

        Args:
            query_text: Query text
            doc_id: Document ID

        Returns:
            Query response
        """
        try:
            return self.manager.query_index(query_text, doc_id)._getvalue()
        except Exception as e:
            logger.error(f"Error querying index: {str(e)}")
            # Attempt to reconnect and retry once
            self._connect_to_index_manager()
            return self.manager.query_index(query_text, doc_id)._getvalue()

    def start_worker(self, query_text, doc_id):
        """
        Start a worker for streaming query results

        Args:
            query_text: Query text
            doc_id: Document ID

        Returns:
            Queue for receiving streaming results
        """
        try:
            return self.manager.start_worker(query_text, doc_id)
        except Exception as e:
            logger.error(f"Error starting worker: {str(e)}")
            # Attempt to reconnect and retry once
            self._connect_to_index_manager()
            return self.manager.start_worker(query_text, doc_id)

    def get_documents_list(self):
        """
        Get list of indexed documents

        Returns:
            List of documents
        """
        try:
            return self.manager.get_documents_list()._getvalue()
        except Exception as e:
            logger.error(f"Error getting documents list: {str(e)}")
            # Attempt to reconnect and retry once
            self._connect_to_index_manager()
            return self.manager.get_documents_list()._getvalue()


# Create a singleton instance
index_service = IndexService()
