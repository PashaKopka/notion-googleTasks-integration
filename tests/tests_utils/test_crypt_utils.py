import datetime

import pytest

from models.models import User
from utils.crypt_utils import create_password, decode_dict, encode, verify_password
from utils.db_utils import generate_access_token, validate_token


@pytest.fixture
async def user(db):
    user = User(email="test_crypt_utils@test.com", password="password")
    yield await user.save(db)
    await user.delete(db)


def test_encode_dict():
    result = encode({"key": "value"})
    assert result == "eyJrZXkiOiAidmFsdWUifQ=="


def test_encode_str():
    result = encode("value")
    assert result == "dmFsdWU="


def test_decode_dict():
    result = decode_dict("eyJrZXkiOiAidmFsdWUifQ==")
    assert result == {"key": "value"}


def test_generate_access_token(user):
    access_token = generate_access_token(user)
    assert access_token is not None
    assert access_token[0] is not None
    assert isinstance(access_token[1], datetime.datetime)


async def test_validate_token(user, db):
    access_token = generate_access_token(user)
    result = await validate_token(access_token[0], db)
    assert result is not None
    assert result.email == user.email


def test_create_password():
    result = create_password("password")
    assert result == "5c9646af43907a512a8a4251189ba3600a0b657d931386618216e45772eef811"


def test_verify_password():
    result = verify_password(
        "password",
        "5c9646af43907a512a8a4251189ba3600a0b657d931386618216e45772eef811",
    )
    assert result is True
