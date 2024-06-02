import base64
import hashlib
import json

from fastapi.security import OAuth2PasswordBearer

from config import ENCODING_ITERATIONS, SALT

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def encode(data: str | dict) -> str:
    if isinstance(data, dict):
        data = json.dumps(data)
        encoded_data = data.encode("utf-8")
    elif isinstance(data, str):
        encoded_data = data.encode("utf-8")

    b64_encoded_data = base64.b64encode(encoded_data)
    return b64_encoded_data.decode("utf-8")


def decode_str(data: str) -> str:
    try:
        utf_8_encoded_data = data.encode("utf-8")
        b64_decoded_data = base64.b64decode(utf_8_encoded_data)
        return b64_decoded_data.decode("utf-8")
    except Exception:
        print("Error decoding data")
        return ""


def decode_dict(data: str) -> dict:
    utf_8_encoded_data = data.encode("utf-8")
    b64_decoded_data = base64.b64decode(utf_8_encoded_data)
    decoded_data = b64_decoded_data.decode("utf-8")
    return json.loads(decoded_data)


def create_password(password: str) -> str:
    hashed_password = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        SALT,
        ENCODING_ITERATIONS,
    )
    return hashed_password.hex()


def verify_password(password: str, hashed_password: str) -> bool:
    new_hashed_password = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        SALT,
        ENCODING_ITERATIONS,
    ).hex()

    return new_hashed_password == hashed_password
