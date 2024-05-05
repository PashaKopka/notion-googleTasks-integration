from uuid import uuid4

from databases import Database
from sqlalchemy import JSON, Boolean, Column, ForeignKey, String, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from config import SQLALCHEMY_DATABASE_URL
from services.service import Item

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
database = Database(SQLALCHEMY_DATABASE_URL)


class BaseModel(Base):
    __abstract__ = True

    def save(self):
        self.id = str(uuid4())
        db = SessionLocal()
        db.add(self)
        db.commit()
        db.refresh(self)
        db.close()
        return self


class User(BaseModel):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)

    def save(self):
        from utils.crypt_utils import create_password  # TODO up this string if possible

        self.password = create_password(self.password)
        return super().save()

    @classmethod
    def get_by_id(cls, id_: str) -> "User":
        db = SessionLocal()
        user = db.query(User).filter(User.id == id_).first()
        db.close()
        return user

    @classmethod
    def get_by_email(cls, email: str) -> "User":
        db = SessionLocal()
        user = db.query(User).filter(User.email == email).first()
        db.close()
        return user


class SyncingServices(BaseModel):
    __tablename__ = "syncing_services"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    service_notion_data = Column(JSON, nullable=True)
    service_google_tasks_data = Column(JSON, nullable=True)
    ready = Column(Boolean, default=False)
    is_active = Column(Boolean, default=False)
    task_id = Column(String, nullable=True)

    user = relationship("User", back_populates="syncing_services")

    def update(self):
        db = SessionLocal()
        db.query(SyncingServices).filter(
            SyncingServices.user_id == self.user_id
        ).update(
            {
                "service_notion_data": self.service_notion_data,
                "service_google_tasks_data": self.service_google_tasks_data,
                "ready": self.ready,
                "is_active": self.is_active,
                "task_id": self.task_id,
            }
        )
        db.commit()
        db.close()

    def save(self):
        db = SessionLocal()
        # if service already exists we update it
        service = (
            db.query(SyncingServices)
            .filter(SyncingServices.user_id == self.user_id)
            .first()
        )
        if service:
            # We update
            if not service.service_google_tasks_data:
                service.service_google_tasks_data = self.service_google_tasks_data
            if not service.service_notion_data:
                service.service_notion_data = self.service_notion_data
            service.update()
            return service

        db.close()
        return super().save()

    @classmethod
    def get_ready_services(cls) -> list["SyncingServices"]:
        db = SessionLocal()
        services = db.query(SyncingServices).filter(SyncingServices.ready == True).all()
        db.close()
        return services

    @classmethod
    def get_service_by_user_id(cls, user_id: str) -> "SyncingServices":
        db = SessionLocal()
        service = (
            db.query(SyncingServices).filter(SyncingServices.user_id == user_id).first()
        )
        db.close()
        return service

    def ready_to_start_sync(self) -> bool:
        if not self.service_google_tasks_data or not self.service_notion_data:
            return False

        if not self.service_google_tasks_data.get("tasks_list_id"):
            return False

        if not self.service_notion_data.get("duplicated_template_id"):
            return False

        if not self.service_notion_data.get("title_prop_name"):
            return False

        self.ready = True
        self.update()

        return True


class SyncedItem(BaseModel):
    __tablename__ = "synced_item"

    id = Column(String, primary_key=True, index=True)
    notion_id = Column(String)
    google_task_id = Column(String)

    syncing_service_id = Column(String, ForeignKey("syncing_services.id"))
    syncing_service = relationship("SyncingServices")

    @classmethod
    def get_by_sync_id(cls, **kwargs) -> "SyncedItem":
        if not kwargs:
            raise ValueError("At least one argument is required")

        filters = [
            cls.get_column_by_name(key) == value for key, value in kwargs.items()
        ]

        db = SessionLocal()
        item = db.query(SyncedItem).filter(*filters).first()
        db.close()
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


User.syncing_services = relationship("SyncingServices", back_populates="user")


def create_tables():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
