import os
from cryptography.fernet import Fernet

key = os.environ.get("FERNET_KEY")

if not key:
    raise RuntimeError("FERNET_KEY not set in environment")

fernet = Fernet(key)
