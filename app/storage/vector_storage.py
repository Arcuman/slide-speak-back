from llama_index import StorageContext
from llama_index.storage.docstore import MongoDocumentStore
from llama_index.storage.index_store import MongoIndexStore
from llama_index.vector_stores.pinecone import PineconeVectorStore
from pinecone import Pinecone

from app.config import Config


def get_pinecone_client():
    """
    Initialize and return a Pinecone client

    Returns:
        An initialized Pinecone client
    """
    return Pinecone(api_key=Config.PINECONE_API_KEY)


def get_vector_store(namespace):
    """
    Initialize and return a configured vector store

    Args:
        namespace: Namespace to use for the vector store

    Returns:
        An initialized vector store
    """
    # Initialize Pinecone
    pc = get_pinecone_client()

    # Get the Pinecone index
    pinecone_index = pc.Index(Config.PINECONE_INDEX)

    # Create the vector store with the specified namespace
    return PineconeVectorStore(
        pinecone_index=pinecone_index,
        namespace=namespace,
    )


def get_document_store():
    """
    Initialize and return a configured document store

    Returns:
        An initialized document store
    """
    return MongoDocumentStore.from_uri(uri=Config.MONGO_DB_URL)


def get_index_store():
    """
    Initialize and return a configured index store

    Returns:
        An initialized index store
    """
    return MongoIndexStore.from_uri(uri=Config.MONGO_DB_URL)


def get_storage_context(namespace) -> StorageContext:
    """
    Initialize and return a complete storage context with all components

    Args:
        namespace: Namespace to use for the vector store

    Returns:
        A fully initialized StorageContext
    """
    vector_store = get_vector_store(namespace)
    docstore = get_document_store()
    index_store = get_index_store()

    return StorageContext.from_defaults(
        docstore=docstore,
        index_store=index_store,
        vector_store=vector_store,
    )
