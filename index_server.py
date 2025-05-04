from app.config import Config
from app.core.indexing import run_index_server

if __name__ == "__main__":
    Config.validate()
    print("Starting index server...")
    run_index_server()
    print("Index server has started.")
