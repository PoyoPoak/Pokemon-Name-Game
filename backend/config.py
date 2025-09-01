import os
from dotenv import load_dotenv
from redis import Redis
from datetime import timedelta

load_dotenv()


class Config:
    # Flask Configuration Key (provide stable SECRET_KEY via env in production)
    SECRET_KEY = os.getenv("SECRET_KEY", None) or os.urandom(24)

    # Base Site Configuration
    REDIRECT_URI = os.getenv('REDIRECT_URI')
    LOGOUT_REDIRECT_URL = os.getenv('LOGOUT_REDIRECT_URL')
    DOMAIN = os.getenv('DOMAIN')

    # Redis Configuration (dependency for Flask-Session)
    # In Railway, create/provision a Redis service and set env vars:
    #   REDIS_HOST, REDIS_PORT, REDIS_PASSWORD (optional if no auth)
    SESSION_TYPE = 'redis'
    SESSION_REDIS = Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', '6379')),
        password=os.getenv('REDIS_PASSWORD') or None,
        ssl=bool(int(os.getenv('REDIS_SSL', '0')))
    )
    SESSION_KEY_PREFIX = 'project_session:'
    SESSION_COOKIE_SAMESITE = 'None'
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=6)
