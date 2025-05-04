import sys
import time
from multiprocessing import Process

from app.config import Config
from app.core.indexing import run_index_server
from app.main import create_app


def start_index():
    print("▶️ Index server starting…")
    run_index_server()  # this will block, serving forever


def start_flask():
    print("▶️ Flask app starting…")
    app = create_app()

    # NOTE: Flask's built-in server is only suitable for development
    # For production, use Gunicorn, uWSGI, or another WSGI server
    # The warning you see is expected and can be ignored during development
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG, use_reloader=False)


if __name__ == "__main__":
    Config.validate()

    # spawn index server as a separate OS process
    idx_proc = Process(target=start_index, name="index-server", daemon=True)
    idx_proc.start()

    # give it a moment to bind its port
    time.sleep(2)

    # now run flask in the main process
    try:
        start_flask()
    except KeyboardInterrupt:
        print("🔌 Shutting down…")
    finally:
        idx_proc.terminate()
        idx_proc.join()
        sys.exit(0)
