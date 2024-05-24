import pytest

from utils.crypt_utils import (
    create_password,
    decode_dict,
    encode,
    generate_access_token,
    validate_token,
    verify_password,
)


def test_encode_dict():
    result = encode({"key": "value"})
    assert result == "eyJrZXkiOiAidmFsdWUifQ=="


def test_encode_str():
    result = encode("value")
    assert result == "dmFsdWU="


def test_decode_dict():
    result = decode_dict("eyJrZXkiOiAidmFsdWUifQ==")
    assert result == {"key": "value"}


def test_generate_access_token():
    # TODO Implement this test
    pass


def test_validate_token():
    # TODO Implement this test
    pass


def test_create_password():
    result = create_password("password")
    assert result == "5c9646af43907a512a8a4251189ba3600a0b657d931386618216e45772eef811"


def test_verify_password():
    result = verify_password(
        "password",
        "5c9646af43907a512a8a4251189ba3600a0b657d931386618216e45772eef811",
    )
    assert result is True
