import logging

from flask import Blueprint, Response, jsonify, make_response, request

from app.services.document_service import DocumentService
from app.services.index_service import index_service

# Setup logging
logger = logging.getLogger(__name__)

# Create main API blueprint with no prefix to keep original route structure
api_bp = Blueprint("api", __name__)


@api_bp.route("/uploadFile", methods=["POST"])
def upload_file():
    """Handle document upload with new service structure but original endpoint path"""
    if "file" not in request.files:
        return "Please send a POST request with a file", 400

    try:
        # Check if we should use filename as document ID
        use_filename = request.form.get("filename_as_doc_id", None) is not None

        # Process the document
        result = DocumentService.process_document(
            request.files["file"],
            use_filename=use_filename,
            index_service=index_service,
        )

        return make_response(jsonify(result), 200)

    except Exception as e:
        logger.error(f"Error in upload_file: {str(e)}", exc_info=True)
        # Clean up any temporary files
        return f"Error: {str(e)}", 500


@api_bp.route("/getDocuments", methods=["GET"])
def get_documents():
    """Get list of all documents with original endpoint path"""
    try:
        document_list = index_service.get_documents_list()
        return make_response(jsonify(document_list)), 200
    except Exception as e:
        logger.error(f"Error in get_documents: {str(e)}", exc_info=True)
        return f"Error: {str(e)}", 500


# TODO: Can we delete this route? <-- Deprecate
@api_bp.route("/query", methods=["GET"])
def query_index():
    """Query the index with original endpoint path"""
    query_text = request.args.get("text", None)
    query_doc_id = request.args.get("doc_id", None)
    uuid_id = request.args.get("uuid", None)

    if query_text is None:
        return "No text found, please include a ?text=blah parameter in the URL", 400
    if uuid_id is None:
        return "No UUID found, please include a uuid in the URL", 400

    try:
        # Initialize index and query
        index_service.initialize_index(uuid_id)
        response = index_service.query_index(query_text, query_doc_id or uuid_id)

        response_json = {
            "text": str(response),
        }
        return make_response(jsonify(response_json)), 200

    except Exception as e:
        logger.error(f"Error in query_index: {str(e)}", exc_info=True)
        return f"Error: {str(e)}", 500


@api_bp.route("/stream", methods=["GET"])
def stream():
    """Stream query results with original endpoint path"""
    query_text = request.args.get("text", None)
    uuid_id = request.args.get("uuid", None)

    if query_text is None:
        return "No text found, please include a ?text=blah parameter in the URL", 400

    if uuid_id is None:
        return "No UUID found, please include a ?uuid=blah parameter in the URL", 400

    try:
        # Initialize index and start worker
        index_service.initialize_index(uuid_id)
        queue = index_service.start_worker(query_text, uuid_id)

        def generate():
            while True:
                response = queue.get()
                if response is None:  # If we get None, that means the stream is done
                    break
                yield str(response)

        return Response(generate(), mimetype="text/event-stream")

    except Exception as e:
        logger.error(f"Error in stream: {str(e)}", exc_info=True)
        return f"Error: {str(e)}", 500
