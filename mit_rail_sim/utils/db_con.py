import os
import warnings
from dotenv import find_dotenv, load_dotenv
from sqlalchemy import create_engine, text


class DummyEngine:
    def connect(self):
        raise ConnectionError("Database connection is not available.")


try:
    load_dotenv(find_dotenv(raise_error_if_not_found=True))

    USERNAME = os.environ["USERNAME"]
    PASSWORD = os.environ["PASSWORD"]
    HOST = os.environ["HOST"]
    PORT = os.environ["PORT"]
    DATABASE = os.environ["DATABASE"]

    engine = create_engine(
        f"postgresql://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"
    )
except (FileNotFoundError, KeyError, ValueError, OSError, IOError):
    warnings.warn(
        "Database connection is not available. Some features like CTA String Chart dashboards will not work. Please provide a .env file with correct credentials."
    )
    engine = DummyEngine()
