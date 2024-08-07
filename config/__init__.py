import os

NOTION_OAUTH_CLIENT_ID = os.getenv("NOTION_OAUTH_CLIENT_ID")
NOTION_OAUTH_CLIENT_SECRET = os.getenv("NOTION_OAUTH_CLIENT_SECRET")
NOTION_AUTHORIZATION_URL = os.getenv("NOTION_AUTHORIZATION_URL")
NOTION_TOKEN_URL = os.getenv("NOTION_TOKEN_URL")

GOOGLE_CLIENT_SECRET_FILE = os.getenv("GOOGLE_CLIENT_SECRET_FILE")
GOOGLE_API_SCOPES = os.getenv("GOOGLE_API_SCOPES")
NOTION_TITLE_PROP_NAME = os.getenv("NOTION_TITLE_PROP_NAME")
NOTION_VERSION = os.getenv("NOTION_VERSION") or "2022-02-22"

SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")
SQLALCHEMY_TEST_DATABASE_URL = os.getenv("SQLALCHEMY_TEST_DATABASE_URL")
HOST = os.getenv("HOST")
FRONT_END_HOST = os.getenv("FRONT_END_HOST")

ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES") or 90
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM") or "HS256"
SALT = os.getenv("SALT").encode("utf-8")
ENCODING_ITERATIONS = os.getenv("ENCODING_ITERATIONS") or 100000

SYNC_WAIT_TIME = os.getenv("SYNC_WAIT_TIME") or 10

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

TESTING = os.getenv("TESTING") == "True"
