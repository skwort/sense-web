import contextlib
import os
from typing import AsyncIterator
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from .base import Base
import logging as log

log.basicConfig(level=log.INFO)


class DatabaseSessionManager:
    """
    Manages the lifecycle of the SQLAlchemy async engine and session
    factory.

    Use `init()` to initialise the engine and sessionmaker. Use
    `session()` to get an async session context manager. Use `connect()`
    if you need direct access to a lower-level connection.
    """

    def __init__(self) -> None:
        self._engine: AsyncEngine | None = None
        self._sessionmaker: async_sessionmaker[AsyncSession] | None = None

    async def init(self, db_uri: str) -> None:
        self._engine = create_async_engine(db_uri)
        self._sessionmaker = async_sessionmaker(
            autocommit=False, bind=self._engine
        )

        if db_uri.startswith("sqlite+aiosqlite:///"):
            path = db_uri.split(":///")[-1]
            if not os.path.exists(path) and not path == ":memory:":
                async with self.connect() as connection:
                    log.info(f"Creating database: {path}")
                    await self.create_all(connection)

    async def close(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
        self._sessionmaker = None

    @contextlib.asynccontextmanager
    async def connect(self) -> AsyncIterator[AsyncConnection]:
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialised")

        async with self._engine.begin() as connection:
            try:
                yield connection
            except Exception:
                await connection.rollback()
                raise

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if self._sessionmaker is None:
            raise Exception("DatabaseSessionManager is not initialised")

        session = self._sessionmaker()

        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def create_all(self, connection: AsyncConnection) -> None:
        await connection.run_sync(Base.metadata.create_all)

    async def drop_all(self, connection: AsyncConnection) -> None:
        await connection.run_sync(Base.metadata.drop_all)


sessionmanager: DatabaseSessionManager = DatabaseSessionManager()
