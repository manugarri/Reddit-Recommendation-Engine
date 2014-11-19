import logging
logging.basicConfig(level=logging.INFO)

from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL

from reddit_recommender import app

def db_connect():
    """
    Performs database connection using database settings from settings.py.
    Returns sqlalchemy engine instance
    """
    DB_SETTINGS = app.config['DB_SETTINGS']
    engine =  create_engine(URL(**DB_SETTINGS))
    connection = engine.connect()
    return connection

def db_close(connection):
    connection.close()
