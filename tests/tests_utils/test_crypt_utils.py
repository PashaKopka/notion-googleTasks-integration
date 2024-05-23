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
    assert (
        result
        == b"\\\x96F\xafC\x90zQ*\x8aBQ\x18\x9b\xa3`\n\x0be}\x93\x13\x86a\x82\x16\xe4Wr\xee\xf8\x11"
    )


def test_verify_password():
    result = verify_password(
        "password",
        b"\\\x96F\xafC\x90zQ*\x8aBQ\x18\x9b\xa3`\n\x0be}\x93\x13\x86a\x82\x16\xe4Wr\xee\xf8\x11",
    )
    assert result is True
