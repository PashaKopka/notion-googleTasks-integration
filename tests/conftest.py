import asyncio
from contextlib import ExitStack

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from config import SQLALCHEMY_TEST_DATABASE_URL
from main import app as actual_app
from models.models import BaseModel, get_db


@pytest.fixture(scope="session")
def engine():
    engine = create_async_engine(SQLALCHEMY_TEST_DATABASE_URL, poolclass=NullPool)
    yield engine
    engine.sync_engine.dispose()


@pytest.fixture(scope="session", autouse=True)
async def create(engine):
    async with engine.begin() as conn:
        # drop all tables in case previous test run failed
        await conn.run_sync(BaseModel.metadata.drop_all)

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


@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture()
def app(sessionmanager):
    async def override_get_db():
        async with sessionmanager() as db:
            yield db

    actual_app.dependency_overrides[get_db] = override_get_db
    with ExitStack():
        yield actual_app


@pytest.fixture()
def client(app):
    with TestClient(app) as c:
        yield c
