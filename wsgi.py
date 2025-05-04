from app.config import Config
from app.main import create_app

# ensure config is valid before serving
Config.validate()
app = create_app()
