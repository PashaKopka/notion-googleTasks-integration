import pytest

from models.models import User


@pytest.fixture
async def user(db):
    user = User(email="test_user_model@test.com", password="password")
    yield await user.save(db)
    await user.delete(db)


async def test_user_get_by_id(user, db):
    user_db = await User.get_by_id(user.id, db)
    assert user is not None
    assert user_db.id == user.id


async def test_user_get_by_email(user, db):
    user_db = await User.get_by_email(user.email, db)
    assert user is not None
    assert user_db.email == user.email
