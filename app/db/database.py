from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from ..core.config import get_settings

settings = get_settings()


engine = create_async_engine(
    settings.database_url,
)


async def get_session():

    async with AsyncSession(engine) as session:
        yield session
