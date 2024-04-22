import base64
import datetime
import json

import jwt
from fastapi import HTTPException, Security
from fastapi.security import OAuth2PasswordBearer
from jwt import ExpiredSignatureError, InvalidTokenError, decode

from config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY
from utils.user_utils import User, get_user

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def encode(data: str | dict) -> str:
    if isinstance(data, dict):
        data = json.dumps(data)
        encoded_data = data.encode("utf-8")
    elif isinstance(data, str):
        encoded_data = data.encode("utf-8")

    b64_encoded_data = base64.b64encode(encoded_data)
    return b64_encoded_data.decode("utf-8")


def decode_dict(data: str) -> dict:
    utf_8_encoded_data = data.encode("utf-8")
    b64_decoded_data = base64.b64decode(utf_8_encoded_data)
    decoded_data = b64_decoded_data.decode("utf-8")
    return json.loads(decoded_data)


def generate_access_token(user: User) -> str:
    payload = {
        "sub": user.email,
        "exp": datetime.datetime.now(datetime.UTC)
        + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


def validate_token(token: str = Security(oauth2_scheme)) -> User:
    try:
        payload = decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        expiration = payload.get("exp")

        expiration_datetime = datetime.datetime.fromtimestamp(expiration)
        current_datetime = datetime.datetime.now(expiration_datetime.tzinfo)
        if email and expiration and current_datetime < expiration_datetime:
            user = get_user(email=email)
            if user:
                return user
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    raise HTTPException(status_code=401, detail="Invalid credentials")