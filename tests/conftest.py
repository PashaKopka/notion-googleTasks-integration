import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from config import SQLALCHEMY_TEST_DATABASE_URL
from models.models import BaseModel


@pytest.fixture(scope="session")
def engine():
    engine = create_async_engine(SQLALCHEMY_TEST_DATABASE_URL, poolclass=NullPool)
    yield engine
    engine.sync_engine.dispose()


@pytest.fixture(scope="session", autouse=True)
async def create(engine):
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.drop_all)

@pytest.fixture(scope="session")
async def sessionmanager(engine):
    yield async_sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        expire_on_commit=False,
    )


@pytest.fixture(scope="function")
async def db(sessionmanager):
    async with sessionmanager() as session:
        try:
            await session.begin()
            yield session
        finally:
            await session.rollback()


# @pytest.fixture(scope="session")
# def event_loop(request):
#     loop = asyncio.get_event_loop_policy().new_event_loop()
#     yield loop
#     loop.close()


@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()
