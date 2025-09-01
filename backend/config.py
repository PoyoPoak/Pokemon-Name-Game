import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()


class Config:
    # Flask secret key (provide stable SECRET_KEY via env in production)
    SECRET_KEY = os.getenv("SECRET_KEY") or os.urandom(24)

    # Base Site Configuration
    REDIRECT_URI = os.getenv('REDIRECT_URI')
    LOGOUT_REDIRECT_URL = os.getenv('LOGOUT_REDIRECT_URL')
    DOMAIN = os.getenv('DOMAIN')

    # Using default secure cookie sessions (Redis removed).
    # If you later need server-side sessions, add Flask-Session and set:
    #   SESSION_TYPE=redis  and configure SESSION_REDIS, etc.
    SESSION_COOKIE_SAMESITE = 'None'
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=6)
