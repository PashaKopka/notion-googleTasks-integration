import asyncio
from uuid import uuid4

from sqlalchemy import JSON, ForeignKey, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.pool import NullPool

from config import SQLALCHEMY_DATABASE_URL
from services.service import Item

engine = create_async_engine(SQLALCHEMY_DATABASE_URL, poolclass=NullPool)
SessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


async def get_db():
    async with SessionLocal() as session:
        yield session


class BaseModel(DeclarativeBase):
    __abstract__ = True

    async def save(self, db: AsyncSession):
        if not db:
            raise ValueError("Database session is required")

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

    async def save(self, db: AsyncSession = None):
        from utils.crypt_utils import create_password

        self.password = create_password(self.password)
        return await super().save(db)

    @classmethod
    async def get_by_id(cls, id_: str, db: AsyncSession) -> "User":
        result = await db.execute(select(User).where(User.id == id_))
        user = result.scalars().first()
        return user

    @classmethod
    async def get_by_email(cls, email: str, db: AsyncSession) -> "User":
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalars().first()
        return user


class SyncingServices(BaseModel):
    __tablename__ = "syncing_services"

    id: Mapped[str] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    service_notion_data: Mapped[JSON] = mapped_column(type_=JSON, nullable=True)
    service_google_tasks_data: Mapped[JSON] = mapped_column(type_=JSON, nullable=True)
    ready: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=False)
    task_id: Mapped[str] = mapped_column(nullable=True)

    user = relationship("User", back_populates="syncing_services")

    @classmethod
    async def update(
        self,
        user_id: str,
        values: dict,
        db: AsyncSession,
    ) -> "SyncingServices":
        query = select(SyncingServices).where(SyncingServices.user_id == user_id)
        result = await db.execute(query)
        service = result.scalars().first()

        if not service:
            raise ValueError("Service not found")

        stmt = (
            update(SyncingServices)
            .where(SyncingServices.user_id == user_id)
            .values(**values)
            .execution_options(synchronize_session="fetch")
        )

        result = await db.execute(stmt)
        await db.commit()

        return service

    @classmethod
    async def get_ready_services(cls, db: AsyncSession) -> list["SyncingServices"]:
        results = await db.execute(
            select(SyncingServices).where(SyncingServices.ready == True)
        )
        services = results.scalars().all()
        return services

    @classmethod
    async def get_service_by_user_id(
        cls, user_id: str, db: AsyncSession
    ) -> "SyncingServices":
        result = await db.execute(
            select(SyncingServices).where(SyncingServices.user_id == user_id)
        )
        service = result.scalars().first()
        return service

    async def ready_to_start_sync(self, db: AsyncSession) -> bool:
        if not self.service_google_tasks_data or not self.service_notion_data:
            return False

        if not self.service_google_tasks_data.get("tasks_list_id"):
            return False

        if not self.service_notion_data.get("duplicated_template_id"):
            return False

        if not self.service_notion_data.get("title_prop_name"):
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

    syncing_service = relationship("SyncingServices")

    @classmethod
    async def get_by_sync_id(cls, db: AsyncSession, **kwargs) -> "SyncedItem":
        if not kwargs:
            raise ValueError("At least one argument is required")

        filters = [
            cls.get_column_by_name(key) == value for key, value in kwargs.items()
        ]

        item = await db.execute(select(SyncedItem).filter(*filters))
        return item.scalars().first()

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


User.syncing_services = relationship(
    "SyncingServices",
    back_populates="user",
    cascade="all, delete",
)


async def create_all_tables():
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)
