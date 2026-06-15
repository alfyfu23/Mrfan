import json
from typing import Optional


# Load data of req body. Asserts json. Return None if failed.
def load_body(req) -> Optional[dict]:
    try:
        data = json.loads(req.body)
    except Exception:
        return None
    return data


# get jwt token, returns None if failed
def get_jwt_token(req) -> str:
    try:
        jwt_token = req.headers['Authorization']
        assert jwt_token.startswith('Bearer ')
        jwt_token = jwt_token.replace('Bearer ', '')
    except Exception:
        jwt_token = None
    return jwt_token
