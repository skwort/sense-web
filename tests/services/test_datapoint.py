import datetime
from typing import AsyncGenerator
import pytest

from sense_web.db.session import DatabaseSessionManager, sessionmanager
from sense_web.services.device import register_device
from sense_web.services.datapoint import (
    create_datapoint,
    get_datapoints_by_device_uuid,
)

DB_URI = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_manager() -> AsyncGenerator[DatabaseSessionManager, None]:
    await sessionmanager.init(DB_URI)
    async with sessionmanager.connect() as conn:
        await sessionmanager.create_all(conn)
    yield sessionmanager
    await sessionmanager.close()


@pytest.mark.asyncio
async def test_create_datapoint(db_manager: DatabaseSessionManager) -> None:
    device = await register_device("12345", "device1")

    timestamp = datetime.datetime.now(datetime.UTC)
    dp = await create_datapoint(
        device_uuid=device.uuid,
        timestamp=timestamp,
        sensor="temp",
        val_float=22.5,
        val_units="C",
    )

    assert dp is not None
    assert dp.device_uuid == device.uuid
    assert dp.sensor == "temp"
    assert dp.val_float == 22.5
    assert dp.val_units == "C"
    assert dp.val_str is None


@pytest.mark.asyncio
async def test_get_datapoints_by_device_uuid(
    db_manager: DatabaseSessionManager,
) -> None:
    device = await register_device("12345", "device1")

    await create_datapoint(
        device_uuid=device.uuid,
        timestamp=datetime.datetime.now(datetime.UTC),
        sensor="humidity",
        val_float=55.2,
        val_units="%",
    )
    await create_datapoint(
        device_uuid=device.uuid,
        timestamp=datetime.datetime.now(datetime.UTC),
        sensor="status",
        val_str="OK",
    )

    points = await get_datapoints_by_device_uuid(device.uuid)

    assert len(points) == 2
    sensors = {p.sensor for p in points}
    assert "humidity" in sensors
    assert "status" in sensors


@pytest.mark.asyncio
async def test_get_datapoints_by_device_uuid_none_exist(
    db_manager: DatabaseSessionManager,
) -> None:
    device = await register_device("12345", "device1")

    points = await get_datapoints_by_device_uuid(device.uuid)

    assert points is not None
    assert len(points) == 0
