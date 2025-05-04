import logging

# Setup logging
logger = logging.getLogger(__name__)


def worker(queue, query_text, doc_id, initialize_index=None):
    """Worker process to handle querying the index asynchronously"""
    try:
        # Import index_manager inside function to avoid circular import
        from app.core.indexing import index_manager

        # If initialize_index is provided, use it to initialize the index
        if initialize_index:
            initialize_index(doc_id)

        # Use streaming query engine
        streaming_response = index_manager.index.as_query_engine(
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
