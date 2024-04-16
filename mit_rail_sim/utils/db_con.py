import os

from dotenv import find_dotenv, load_dotenv
from sqlalchemy import create_engine, text

load_dotenv(find_dotenv())

USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
HOST = os.getenv("HOST")
PORT = os.getenv("PORT")
DATABASE = os.getenv("DATABASE")

engine = create_engine(f"postgresql://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}")
