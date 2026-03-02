from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from contextlib import asynccontextmanager
from core.config import settings

# Create async engine
DATABASE_URL = settings.database_url
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Create sync engine for setup
sync_engine = create_engine(DATABASE_URL.replace('+aiosqlite', '').replace('sqlite', 'sqlite'))
SyncSessionLocal = sessionmaker(sync_engine)

# Import models to register them with SQLAlchemy
from database.models import Base

# Create tables
def init_db():
    Base.metadata.create_all(bind=sync_engine)

@asynccontextmanager
async def get_db_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()