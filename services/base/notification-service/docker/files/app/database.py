from app.config import settings
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

async_engine = create_async_engine(settings.DATABASE_URL)
async_session = sessionmaker(bind=async_engine, expire_on_commit=False, class_=AsyncSession)
