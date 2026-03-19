import datetime
import hashlib
import hmac
import time
import json
import base64
from typing import Optional

SALT = "Team_MrFan".encode("utf-8")
EXPIRE_IN_SECONDS = 60 * 60 * 2  # 2 hours
ALT_CHARS = "-_".encode("utf-8")

def b64url_encode(s):
    if isinstance(s, str):
        return base64.b64encode(s.encode("utf-8"), altchars=ALT_CHARS).decode("utf-8").strip("=")
    else:
        return base64.b64encode(s, altchars=ALT_CHARS).decode("utf-8").strip("=")

def b64url_decode(s: str, decode_to_str=True):
    s += "=" * (4 - len(s) % 4)  # restore padding
    
    if decode_to_str:
        return base64.b64decode(s, altchars=ALT_CHARS).decode("utf-8")
    else:
        return base64.b64decode(s, altchars=ALT_CHARS)

def generate_jwt_token(username: str, id: int):
    # * header
    header = {
        "alg": "HS256",
        "typ": "JWT"
    }
    # dump to str. remove `\n` and space after `:`
    header_str = json.dumps(header, separators=(",", ":"))
    # use base64url to encode, instead of base64
    header_b64 = b64url_encode(header_str)
    
    # * payload
    payload = {
        "iat": int(time.time()),
        "exp": int(time.time()) + EXPIRE_IN_SECONDS,
        "data": {
            "username": username,
            "id": id  # 用户的id
            # And more data for your own usage
        }
    }
    payload_str = json.dumps(payload, separators=(",", ":"))
    payload_b64 = b64url_encode(payload_str)
    
    # * signature
    signature_raw = header_b64 + "." + payload_b64
    signature = hmac.new(SALT, signature_raw.encode("utf-8"), digestmod=hashlib.sha256).digest()
    signature_b64 = b64url_encode(signature)
    
    return header_b64 + "." + payload_b64 + "." + signature_b64

# return user id, returns None if failed
def parse_jwt_token(token: str) -> Optional[int]:
    # * Split token
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except Exception:
        return None

    payload_str = b64url_decode(payload_b64)
    
    # * Check signature
    signature_str_check = header_b64 + "." + payload_b64
    signature_check = hmac.new(SALT, signature_str_check.encode("utf-8"), digestmod=hashlib.sha256).digest()
    signature_b64_check = b64url_encode(signature_check)
    
    if signature_b64_check != signature_b64:
        return None
    
    # Check expire
    payload = json.loads(payload_str)
    if payload["exp"] < time.time():
        return None
    
    return payload["data"]['id']
