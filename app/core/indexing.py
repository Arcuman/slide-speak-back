import hashlib
import logging
import os
import time
from multiprocessing.managers import BaseManager
from queue import Queue
from threading import Thread

import boto3
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
from llama_index import ServiceContext, VectorStoreIndex, download_loader
from llama_index.callbacks import CallbackManager, LlamaDebugHandler
from llama_index.llm_predictor.chatgpt import LLMPredictor
from llama_index.node_parser import SimpleNodeParser

from app.config import Config
from app.storage.vector_storage import (
    get_document_store,
    get_pinecone_client,
    get_storage_context,
)

# Setup logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Setup logging for boto
boto3.set_stream_logger("botocore", level="DEBUG")


# Auth key management for BaseManager
def get_auth_key():
    """Get authentication key for BaseManager from environment variable"""
    # First, try to get the key from environment variable
    env_key = os.environ.get("INDEX_SERVER_AUTH_KEY")
    if env_key:
        # Convert string to bytes for BaseManager
        return hashlib.md5(env_key.encode()).digest()

    # Fallback to a static key derived from host and port
    logger.warning(
        "INDEX_SERVER_AUTH_KEY not set in environment, using fallback authentication"
    )
    host = getattr(Config, "INDEX_SERVER_HOST", "127.0.0.1")
    port = getattr(Config, "INDEX_SERVER_PORT", 5602)
    static_seed = f"{host}:{port}:slidespeak-auth-key"
    return hashlib.sha256(static_seed.encode()).digest()


class IndexManager:
    """Class to manage document indexing and querying"""

    def __init__(self):
        # Initialize Pinecone
        self.pc = get_pinecone_client()

        # Initialize OpenAI
        import openai

        openai.api_key = Config.OPENAI_API_KEY

        # Initialize variables
        self.index = None
        self.stored_docs = {}
        self.docstore = get_document_store()

        # Setup debug handler
        llama_debug = LlamaDebugHandler(print_trace_on_end=True)
        self.callback_manager = CallbackManager([llama_debug])

        # Load document reader
        PptxReader = download_loader("PptxReader")
        self.loader = PptxReader()

    def worker(self, queue, query_text, doc_id, initialize_index=None):
        """Worker process to handle querying the index asynchronously"""
        try:
            # If initialize_index is provided, use it to initialize the index
            if initialize_index:
                initialize_index(doc_id)

            # Use streaming query engine
            streaming_response = self.index.as_query_engine(
                streaming=True, similarity_top_k=1
            ).query(query_text)

            # Process text chunks as they arrive
            for text in streaming_response.response_gen:
                print(text)
                queue.put(text)  # Put the text into the queue

            # Signal completion
            queue.put(None)

        except Exception as e:
            logger.error(f"Error in worker: {str(e)}", exc_info=True)
            queue.put(f"Error: {str(e)}")
            queue.put(None)  # Always signal completion

    def initialize_index(self, namespace):
        """Create a new index for the specified namespace"""
        logger.info(f"Initializing index for namespace: {namespace}")

        llm_predictor = LLMPredictor(
            llm=ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo", streaming=True)
        )
        service_context = ServiceContext.from_defaults(
            chunk_size_limit=512,
            llm_predictor=llm_predictor,
            callback_manager=self.callback_manager,
        )

        # Get storage context using the centralized function
        storage_context = get_storage_context(namespace)

        self.index = VectorStoreIndex.from_documents(
            [], storage_context=storage_context, service_context=service_context
        )
        logger.info("Index initialized successfully")

    def start_worker(self, query_text, name):
        """Start a worker thread for processing queries"""
        logger.info(f"Starting worker for namespace: {name} with query: {query_text}")
        queue = Queue()
        t = Thread(
            target=self.worker, args=(queue, query_text, name, self.initialize_index)
        )
        t.start()
        return queue

    def query_index(self, query_text, name):
        """Query the index"""
        logger.info(f"Querying index for namespace: {name} with query: {query_text}")
        response = self.index.as_query_engine().query(query_text)
        return response

    def insert_into_index(self, doc_file_path, doc_id=None):
        """Insert new document into index"""
        logger.info(f"Inserting document into index: {doc_file_path} with ID: {doc_id}")
        self.initialize_index(doc_id)
        document = self.loader.load_data(file=doc_file_path)[0]

        # Create parser and parse document into nodes
        parser = SimpleNodeParser()
        nodes = parser.get_nodes_from_documents([document])
        self.docstore.add_documents(nodes)

        if doc_id is not None:
            document.doc_id = doc_id

        self.index.insert(document)

        # Create a better document preview/summary
        try:
            # Extract document title if available, or use filename as fallback
            doc_title = getattr(document, "title", None) or doc_file_path.split("/")[-1]

            # Generate a meaningful preview - either use LLM summarization for longer docs
            # or take a smart excerpt for shorter ones
            if document.text and len(document.text) > 500:
                # Option 1: Use your existing LLM to generate a summary
                llm_predictor = LLMPredictor(
                    llm=ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo")
                )
                summary = llm_predictor.predict(
                    f"Summarize this document in 2-3 sentences: {document.text[:2000]}"
                )
                preview = summary[:200]  # Limit summary length
            else:
                # Option 2: For shorter documents, take a clean excerpt
                preview = (
                    document.text[:200]
                    if document.text
                    else "No text content available"
                )
                # Avoid cutting in the middle of words
                if len(document.text) > 200 and not preview.endswith(" "):
                    preview = preview.rsplit(" ", 1)[0] + "..."

            # Store more useful document metadata
            self.stored_docs[document.doc_id] = {
                "title": doc_title,
                "preview": preview,
                "length": len(document.text) if document.text else 0,
                "filename": doc_file_path.split("/")[-1],
            }
        except Exception as e:
            logger.warning(f"Error creating document preview: {str(e)}")
            # Fallback to the original approach if something goes wrong
            self.stored_docs[document.doc_id] = (
                document.text[:200] if document.text else "No preview available"
            )

        return

    def get_documents_list(self):
        """Get the list of currently stored documents"""
        documents_list = []
        for doc_id, doc_metadata in self.stored_docs.items():
            documents_list.append(
                {
                    "id": doc_id,
                    "title": doc_metadata.get("title", "Unknown"),
                    "preview": doc_metadata.get("preview", "No preview available"),
                    "length": doc_metadata.get("length", 0),
                    "filename": doc_metadata.get("filename", "Unknown"),
                }
            )
        return documents_list


# Create a singleton instance
index_manager = IndexManager()


def create_index_manager():
    """Create and return a BaseManager connected to the index server"""
    host = (
        Config.INDEX_SERVER_HOST
        if hasattr(Config, "INDEX_SERVER_HOST")
        else "127.0.0.1"
    )
    port = Config.INDEX_SERVER_PORT if hasattr(Config, "INDEX_SERVER_PORT") else 5602

    # Create a BaseManager with secure configuration
    manager = BaseManager((host, port), get_auth_key())
    manager.register("query_index", index_manager.query_index)
    manager.register("insert_into_index", index_manager.insert_into_index)
    manager.register("get_documents_list", index_manager.get_documents_list)
    manager.register("initialize_index", index_manager.initialize_index)
    manager.register("start_worker", index_manager.start_worker)

    # Try to connect multiple times
    max_retries = (
        Config.INDEX_SERVER_MAX_RETRIES
        if hasattr(Config, "INDEX_SERVER_MAX_RETRIES")
        else 10
    )
    retry_interval = (
        Config.INDEX_SERVER_RETRY_INTERVAL
        if hasattr(Config, "INDEX_SERVER_RETRY_INTERVAL")
        else 3
    )

    for attempt in range(max_retries):
        try:
            manager.connect()
            logger.info("Connected to index server successfully")
            return manager
        except ConnectionRefusedError:
            logger.warning(
                f"Connecting to index server failed (attempt {attempt+1}/{max_retries}), "
                f"waiting {retry_interval} seconds before retrying..."
            )
            time.sleep(retry_interval)
        except Exception as e:
            logger.error(f"Unexpected error connecting to index server: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_interval)
                continue
            else:
                raise

    raise ConnectionError(
        f"Could not connect to index server after {max_retries} attempts"
    )


def run_index_server():
    """Run the index server"""
    host = (
        Config.INDEX_SERVER_HOST
        if hasattr(Config, "INDEX_SERVER_HOST")
        else "127.0.0.1"
    )
    port = Config.INDEX_SERVER_PORT if hasattr(Config, "INDEX_SERVER_PORT") else 5602

    logger.info(f"Starting index server on {host}:{port}...")

    # Create a BaseManager with secure configuration
    manager = BaseManager((host, port), get_auth_key())
    manager.register("query_index", index_manager.query_index)
    manager.register("insert_into_index", index_manager.insert_into_index)
    manager.register("get_documents_list", index_manager.get_documents_list)
    manager.register("initialize_index", index_manager.initialize_index)
    manager.register("start_worker", index_manager.start_worker)

    server = manager.get_server()
    logger.info("Index server started and ready to accept connections")
    server.serve_forever()
