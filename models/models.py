import asyncio
from abc import abstractmethod
from uuid import uuid4

from sqlalchemy import ForeignKey, event, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.pool import NullPool

from config import SQLALCHEMY_DATABASE_URL
from logger import get_logger
from schemas.services_auth_data import GoogleAuthData, NotionAuthData
from schemas.Item import Item
from utils.crypt_utils import create_password, decode_dict, decode_str, encode

engine = create_async_engine(SQLALCHEMY_DATABASE_URL, poolclass=NullPool)
SessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)
logger = get_logger(__name__)


async def get_db():
    async with SessionLocal() as session:
        yield session


class BaseModel(DeclarativeBase):
    __abstract__ = True

    async def save(self, db: AsyncSession):
        if not db:
            raise ValueError("Database session is required")

        if not self.id:
            self.id = str(uuid4())
        db.add(self)
        await db.commit()
        await db.refresh(self)

        return self

    async def delete(self, db: AsyncSession):
        if not db:
            raise ValueError("Database session is required")

        await db.delete(self)
        await db.commit()


class User(BaseModel):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    password: Mapped[str] = mapped_column()

    syncing_services: Mapped[list["SyncingService"]] = relationship(
        back_populates="user",
        cascade="all, delete",
        lazy="selectin",
    )

    async def save(self, db: AsyncSession = None):
        self.password = create_password(self.password)
        return await super().save(db)

    @classmethod
    async def get_by_id(cls, id_: str, db: AsyncSession) -> "User":
        result = await db.execute(select(User).where(User.id == id_))
        user = result.scalars().first()

        if user is not None:
            await db.refresh(user)

        return user

    @classmethod
    async def get_by_email(cls, email: str, db: AsyncSession) -> "User":
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalars().first()

        if user is not None:
            await db.refresh(user)

        return user


class Data(BaseModel):
    __abstract__ = True

    @abstractmethod
    def create_from_auth_data(cls, data, syncing_service_id: str) -> "Data":
        raise NotImplementedError

    @classmethod
    async def get_by_syncing_service_id(cls, syncing_service_id: str, db: AsyncSession):
        result = await db.execute(
            select(cls).where(cls.syncing_service_id == syncing_service_id)
        )
        data = result.scalars().first()

        if data is not None:
            await db.refresh(data)

        return data


class NotionData(Data):
    __tablename__ = "notion_datas"

    __encode_sensitive_fields__ = [
        "access_token",
        "duplicated_template_id",
    ]
    __encode_sensitive_dict_fields__ = ["data"]

    id: Mapped[str] = mapped_column(primary_key=True, index=True)
    access_token: Mapped[str] = mapped_column()
    duplicated_template_id: Mapped[str] = mapped_column()
    title_prop_name: Mapped[str] = mapped_column(nullable=True)
    data: Mapped[str] = mapped_column()

    syncing_service_id: Mapped[str] = mapped_column(ForeignKey("syncing_services.id"))
    syncing_service: Mapped["SyncingService"] = relationship(
        back_populates="notion_data",
        lazy="selectin",
    )

    @classmethod
    def create_from_auth_data(
        cls,
        data: NotionAuthData,
        syncing_service_id: str,
    ) -> "NotionData":
        return cls(
            access_token=data.access_token,
            duplicated_template_id=data.duplicated_template_id,
            data=data.data,
            syncing_service_id=syncing_service_id,
        )


class GoogleTasksData(Data):
    __tablename__ = "google_tasks_datas"

    __encode_sensitive_fields__ = [
        "token",
        "refresh_token",
        "token_uri",
        "client_id",
        "client_secret",
    ]
    __encode_sensitive_dict_fields__ = ["data"]

    id: Mapped[str] = mapped_column(primary_key=True, index=True)
    token: Mapped[str] = mapped_column()
    refresh_token: Mapped[str] = mapped_column()
    token_uri: Mapped[str] = mapped_column()
    client_id: Mapped[str] = mapped_column()
    client_secret: Mapped[str] = mapped_column()
    tasks_list_id: Mapped[str] = mapped_column(nullable=True)
    data: Mapped[str] = mapped_column()

    syncing_service_id: Mapped[str] = mapped_column(ForeignKey("syncing_services.id"))
    syncing_service: Mapped["SyncingService"] = relationship(
        back_populates="google_tasks_data",
        lazy="selectin",
    )

    @classmethod
    def create_from_auth_data(
        cls,
        data: GoogleAuthData,
        syncing_service_id: str,
    ) -> "GoogleTasksData":
        return cls(
            token=data.token,
            refresh_token=data.refresh_token,
            token_uri=data.token_uri,
            client_id=data.client_id,
            client_secret=data.client_secret,
            data=data.data,
            syncing_service_id=syncing_service_id,
        )


class SyncingService(BaseModel):
    __tablename__ = "syncing_services"

    id: Mapped[str] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    ready: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=False)

    user: Mapped["User"] = relationship(
        back_populates="syncing_services", lazy="selectin"
    )
    notion_data: Mapped["NotionData"] = relationship(
        back_populates="syncing_service", lazy="selectin"
    )
    google_tasks_data: Mapped["GoogleTasksData"] = relationship(
        back_populates="syncing_service", lazy="selectin"
    )

    @classmethod
    async def update(
        self,
        user_id: str,
        values: dict,
        db: AsyncSession,
    ) -> "SyncingService":
        query = select(SyncingService).where(SyncingService.user_id == user_id)
        result = await db.execute(query)
        service = result.scalars().first()

        if not service:
            raise ValueError("Service not found")

        stmt = (
            update(SyncingService)
            .where(SyncingService.user_id == user_id)
            .values(**values)
            .execution_options(synchronize_session="fetch")
        )

        result = await db.execute(stmt)
        await db.commit()

        return service

    @classmethod
    async def get_ready_services(cls, db: AsyncSession) -> list["SyncingService"]:
        results = await db.execute(
            select(SyncingService).where(SyncingService.ready == True)
        )
        services = results.scalars().all()

        if services:
            for service in services:
                await db.refresh(service)

        return services

    @classmethod
    async def get_service_by_user_id(
        cls, user_id: str, db: AsyncSession
    ) -> "SyncingService":
        result = await db.execute(
            select(SyncingService).where(SyncingService.user_id == user_id)
        )
        service = result.scalars().first()

        if service is not None:
            await db.refresh(service)

        return service

    async def ready_to_start_sync(self, db: AsyncSession) -> bool:
        if not self.google_tasks_data or not self.notion_data:
            return False

        if not self.google_tasks_data.tasks_list_id:
            return False

        if not self.notion_data.duplicated_template_id:
            return False

        if not self.notion_data.title_prop_name:
            return False

        if not self.ready:
            self.ready = True
            await self.save(db)

        return True


class SyncedItem(BaseModel):
    __tablename__ = "synced_item"

    id: Mapped[str] = mapped_column(primary_key=True, index=True)
    notion_id: Mapped[str] = mapped_column()
    google_task_id: Mapped[str] = mapped_column()
    syncing_service_id: Mapped[str] = mapped_column(ForeignKey("syncing_services.id"))

    syncing_service: Mapped["SyncingService"] = relationship(lazy="selectin")

    @classmethod
    async def get_by_sync_id(cls, db: AsyncSession, **kwargs) -> "SyncedItem":
        if not kwargs:
            raise ValueError("At least one argument is required")

        filters = [
            cls.get_column_by_name(key) == value for key, value in kwargs.items()
        ]

        result = await db.execute(select(SyncedItem).filter(*filters))
        item = result.scalars().first()

        if item is not None:
            await db.refresh(item)

        return item

    @classmethod
    def get_column_by_name(cls, column_name: str):
        return SyncedItem.__table__.columns[column_name]

    @classmethod
    def create_from_item(cls, item: Item, syncing_service_id: str) -> "SyncedItem":
        return cls(
            notion_id=item.notion_id,
            google_task_id=item.google_task_id,
            syncing_service_id=syncing_service_id,
        )


@event.listens_for(Data, "before_insert", propagate=True)
@event.listens_for(Data, "before_update", propagate=True)
def encode_sensitive_fields(mapper, connection, target):
    fields_to_encode = getattr(target, "__encode_sensitive_fields__", [])
    fields_to_encode_dict = getattr(target, "__encode_sensitive_dict_fields__", [])

    for field_name in fields_to_encode + fields_to_encode_dict:
        field_value = getattr(target, field_name)
        encoded_value = encode(field_value)
        setattr(target, field_name, encoded_value)

    logger.info(
        f"Encoded fields for {target.__class__.__name__}: {fields_to_encode + fields_to_encode_dict}"
    )


@event.listens_for(Data, "refresh", propagate=True)
@event.listens_for(Data, "load", propagate=True)
def decode_sensitive_fields(target, *args, **kwargs):
    if isinstance(target.data, dict):
        # Already decoded
        return

    fields_to_decode = getattr(target, "__encode_sensitive_fields__", [])
    for field_name in fields_to_decode:
        field_value = getattr(target, field_name)
        decoded_value = decode_str(field_value)
        setattr(target, field_name, decoded_value)

    fields_to_decode_dict = getattr(target, "__encode_sensitive_dict_fields__", [])
    for field_name in fields_to_decode_dict:
        field_value = getattr(target, field_name)
        decoded_value = decode_dict(field_value)
        setattr(target, field_name, decoded_value)


async def create_all_tables():
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)
