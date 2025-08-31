import os
from dotenv import load_dotenv
from redis import Redis
from datetime import timedelta

load_dotenv()


class Config:
    # Flask Configuration Key
    SECRET_KEY = os.urandom(24)

    # Base Site Configuration
    REDIRECT_URI = os.getenv('REDIRECT_URI')
    LOGOUT_REDIRECT_URL = os.getenv('LOGOUT_REDIRECT_URL')
    DOMAIN = os.getenv('DOMAIN')

    # Redis Configuration (dependency for Flask-Session)
    SESSION_TYPE = 'redis'
    SESSION_REDIS = Redis(host='localhost', port=6379)
    SESSION_KEY_PREFIX = 'project_session:'
    SESSION_COOKIE_SAMESITE = 'None'
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=6)
