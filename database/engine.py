import os
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from database.models import Base
from database.orm_query import orm_add_banner_description

from tg_bot.command.texts_for_db import description_for_info

engine = create_async_engine(os.getenv('DB_URL'), echo=True)

session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def create_db():
    async with engine.connect() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.commit()

    async with session_maker() as session:
        await orm_add_banner_description(session, description_for_info)


async def drop_db():
    async with engine.connect() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.commit()
