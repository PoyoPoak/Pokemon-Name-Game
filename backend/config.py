import os
from dotenv import load_dotenv
from datetime import timedelta

# Optional import for redis (only needed if SESSION_TYPE=redis)
try:  
    from redis import Redis 
except ImportError:  
    Redis = None

load_dotenv()

class Config:
    # Flask secret key (provide stable SECRET_KEY via env in production)
    SECRET_KEY = os.getenv("SECRET_KEY") or os.urandom(24)

    # Base Site Configuration (use REDIRECT_URL consistently; expose as REDIRECT_URL)
    REDIRECT_URL = os.getenv('REDIRECT_URL')
    LOGOUT_REDIRECT_URL = os.getenv('LOGOUT_REDIRECT_URL')
    DOMAIN = os.getenv('DOMAIN')

    # Session settings (default = signed cookies). Set SESSION_TYPE=redis to enable server-side.
    SESSION_TYPE = os.getenv('SESSION_TYPE') or None
    SESSION_COOKIE_SAMESITE = 'None'
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=6)

    if SESSION_TYPE == 'redis':
        if Redis is None:  
            raise RuntimeError("SESSION_TYPE=redis but 'redis' package not installed")
        SESSION_REDIS = Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            password=os.getenv('REDIS_PASSWORD') or None,
            ssl=bool(int(os.getenv('REDIS_SSL', '0')))
        )
        SESSION_KEY_PREFIX = os.getenv('SESSION_KEY_PREFIX', 'project_session:')
