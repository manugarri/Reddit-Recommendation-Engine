import os

DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASSWORD')
DB_HOST = os.environ.get('DB_HOST')
DB_PORT = os.environ.get('DB_PORT')
DB_NAME = os.environ.get('DB_NAME')

SECRET_KEY = os.urandom(24)
CACHE_TIMEOUT = 15*60
REDDIT_CLIENT_ID = os.environ.get('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = os.environ.get('REDDIT_CLIENT_SECRET')

if os.environ.get('DEBUG') == 'yes':
    DB_SETTINGS = {'drivername': 'postgresql',
            'host': 'localhost',
            'port': '5432',
            'username': 'test',
            'password': 'test',
            'database': 'test'}
    REDDIT_REDIRECT_URI = 'http://localhost:5000/authorize_callback'

else:
    DB_SETTINGS = {'drivername': 'postgresql',
            'host': DB_HOST,
            'port': DB_PORT,
            'username': DB_USER,
            'password': DB_PASSWORD,
            'database': DB_NAME}
    REDDIT_REDIRECT_URI = os.environ.get('REDDIT_REDIRECT_URI')
