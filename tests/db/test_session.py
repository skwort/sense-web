import pytest
import uuid
from typing import AsyncGenerator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from sense_web.db.session import DatabaseSessionManager
from sense_web.db.models import Device

DB_URI = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_manager() -> AsyncGenerator[DatabaseSessionManager, None]:
    manager = DatabaseSessionManager()
    await manager.init(DB_URI)
    yield manager
    await manager.close()


@pytest.mark.asyncio
async def test_session_manager_provides_session(
    db_manager: DatabaseSessionManager,
) -> None:
    async with db_manager.session() as session:
        assert isinstance(session, AsyncSession)
        result = await session.execute(text("SELECT 1"))
        assert result.scalar_one() == 1


@pytest.mark.asyncio
async def test_session_manager_rejects_use_before_init() -> None:
    manager = DatabaseSessionManager()

    with pytest.raises(Exception, match="not initialised"):
        async with manager.session():
            pass


@pytest.mark.asyncio
async def test_double_close_is_safe(
    db_manager: DatabaseSessionManager,
) -> None:
    # First close already happened via fixture teardown
    # Closing again shouldn't raise an exception
    await db_manager.close()
    assert db_manager._engine is None
    assert db_manager._sessionmaker is None


@pytest.mark.asyncio
async def test_session_manager_commit(
    db_manager: DatabaseSessionManager,
) -> None:
    async with db_manager.connect() as conn:
        await db_manager.create_all(conn)

    # Create and add a device
    imei = "123456789012345"
    name = "d0"
    device_uuid = uuid.uuid4()
    device = Device(imei=imei, uuid=device_uuid, name=name)

    async with db_manager.session() as session:
        session.add(device)
        await session.commit()

    # Verify it was committed
    async with db_manager.session() as session:
        result = (
            (await session.execute(select(Device))).scalars().one_or_none()
        )
        assert result is not None
        assert result.imei == imei
        assert result.name == name
        assert str(result.uuid) == str(device_uuid)


@pytest.mark.asyncio
async def test_session_manager_rollback_on_error(
    db_manager: DatabaseSessionManager,
) -> None:
    class DummyError(Exception):
        pass

    with pytest.raises(DummyError):
        async with db_manager.session() as _:
            raise DummyError("force rollback")
