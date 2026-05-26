"""PostgreSQL (async) + Redis connection management."""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from redis.asyncio import Redis
from .config import settings

engine = create_async_engine(settings.database_url, echo=False, pool_size=10, max_overflow=20)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# Redis async connection
redis_client: Redis = Redis.from_url(settings.redis_url, decode_responses=True)


async def get_db() -> AsyncSession:
    """FastAPI dependency that yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_redis() -> Redis:
    """FastAPI dependency that yields the Redis client."""
    return redis_client


async def check_db_connection() -> bool:
    """Check if the database is reachable."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"[DB_CHECK] Connection failed: {type(e).__name__}: {e}")
        return False


async def check_redis_connection() -> bool:
    """Check if Redis is reachable."""
    try:
        await redis_client.ping()
        return True
    except Exception:
        return False
