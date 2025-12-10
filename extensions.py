from passlib.context import CryptContext
from pymongo import MongoClient
import certifi
import os
from dotenv import load_dotenv
import re
from flask import session, redirect, url_for

load_dotenv()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

MONGO_URI = os.getenv("MONGO_URI") 
if not MONGO_URI:
    raise RuntimeError("MONGO_URI environment variable is not set")

client = MongoClient(
    MONGO_URI,
    tlsCAFile=certifi.where()
)

class MongoWrapper:
    def __init__(self, client):
        self.cx = client
        self.db = client.get_database()

mongo = MongoWrapper(client)


def is_strong_password(password: str) -> bool:
    pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]{8,}$'
    return re.match(pattern, password) is not None


def user_login_required(f):
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper


def admin_login_required(f):
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper


from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per hour"]
)
