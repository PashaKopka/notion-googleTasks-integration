from uuid import uuid4
from sqlalchemy import create_engine, Column, String, JSON, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from databases import Database

from config import SQLALCHEMY_DATABASE_URL

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


class SyncingServices(BaseModel):
    __tablename__ = "syncing_services"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    service_1_data = Column(JSON)
    service_2_data = Column(JSON)

    user = relationship("User", back_populates="syncing_services")


class SyncedItem(BaseModel):
    __tablename__ = "synced_item"

    id = Column(String, primary_key=True, index=True)
    service_1_id = Column(String)
    service_2_id = Column(String)

    syncing_service_id = Column(String, ForeignKey("syncing_services.id"))
    syncing_service = relationship("SyncingServices")

    @staticmethod
    def get_by_sync_id(service_1_id: str = None, service_2_id: str = None):
        if not service_1_id and not service_2_id:
            return None

        filters = []
        if service_1_id:
            filters.append(SyncedItem.service_1_id == service_1_id)
        if service_2_id:
            filters.append(SyncedItem.service_2_id == service_2_id)

        db = SessionLocal()
        item = db.query(SyncedItem).filter(*filters).first()
        db.close()
        return item


User.syncing_services = relationship("SyncingServices", back_populates="user")


def create_tables():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
