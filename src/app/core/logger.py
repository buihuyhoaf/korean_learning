import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE_PATH = os.path.join(LOG_DIR, "app.log")

LOGGING_LEVEL = logging.DEBUG  # Changed to DEBUG for detailed logging
LOGGING_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Configure root logger
logging.basicConfig(
    level=LOGGING_LEVEL, 
    format=LOGGING_FORMAT,
    handlers=[
        logging.StreamHandler(),  # Console handler
        RotatingFileHandler(LOG_FILE_PATH, maxBytes=10485760, backupCount=5)
    ]
)

# Set specific loggers to DEBUG level
logging.getLogger("app.core.google_auth").setLevel(logging.DEBUG)
logging.getLogger("app.api.v1.google_auth").setLevel(logging.DEBUG)
logging.getLogger("app.core").setLevel(logging.DEBUG)
logging.getLogger("app.api").setLevel(logging.DEBUG)
