import datetime
import hashlib
import hmac
import time
import json
import base64
import os
from typing import Optional

SALT = os.environ.get("JWT_SECRET_KEY", "change-me-in-production").encode("utf-8")
EXPIRE_IN_SECONDS = 60 * 60 * 2
ALT_CHARS = "-_".encode("utf-8")

def b64url_encode(s):
    if isinstance(s, str):
        return base64.b64encode(s.encode("utf-8"), altchars=ALT_CHARS).decode("utf-8").strip("=")
    else:
        return base64.b64encode(s, altchars=ALT_CHARS).decode("utf-8").strip("=")

def b64url_decode(s: str, decode_to_str=True):
    s += "=" * (4 - len(s) % 4)
    
    if decode_to_str:
        return base64.b64decode(s, altchars=ALT_CHARS).decode("utf-8")
    else:
        return base64.b64decode(s, altchars=ALT_CHARS)

def generate_jwt_token(username: str, id: int):
    header = {
        "alg": "HS256",
        "typ": "JWT"
    }
    header_str = json.dumps(header, separators=(",", ":"))
    header_b64 = b64url_encode(header_str)
    
    payload = {
        "iat": int(time.time()),
        "exp": int(time.time()) + EXPIRE_IN_SECONDS,
        "data": {
            "username": username,
            "id": id
        }
    }
    payload_str = json.dumps(payload, separators=(",", ":"))
    payload_b64 = b64url_encode(payload_str)
    
    signature_raw = header_b64 + "." + payload_b64
    signature = hmac.new(SALT, signature_raw.encode("utf-8"), digestmod=hashlib.sha256).digest()
    signature_b64 = b64url_encode(signature)
    
    return header_b64 + "." + payload_b64 + "." + signature_b64

def parse_jwt_token(token: str) -> Optional[int]:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except Exception:
        return None

    payload_str = b64url_decode(payload_b64)
    
    signature_str_check = header_b64 + "." + payload_b64
    signature_check = hmac.new(SALT, signature_str_check.encode("utf-8"), digestmod=hashlib.sha256).digest()
    signature_b64_check = b64url_encode(signature_check)
    
    if signature_b64_check != signature_b64:
        return None
    
    payload = json.loads(payload_str)
    if payload["exp"] < time.time():
        return None
    
    return payload["data"]['id']
