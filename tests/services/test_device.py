import pytest
import uuid
from typing import AsyncGenerator

from sense_web.exceptions import DeviceAlreadyExists
from sense_web.db.session import DatabaseSessionManager, sessionmanager
from sense_web.services.device import (
    register_device,
    get_device_by_imei,
    get_device_by_uuid,
    list_devices,
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
async def test_register_and_get_device(
    db_manager: DatabaseSessionManager,
) -> None:
    imei = "123456789012345"
    await register_device(imei)

    device = await get_device_by_imei(imei)
    assert device is not None
    assert device.imei == imei

    device_by_uuid = await get_device_by_uuid(device.uuid)
    assert device_by_uuid is not None
    assert device_by_uuid.uuid == device.uuid


@pytest.mark.asyncio
async def test_register_twice_fail(
    db_manager: DatabaseSessionManager,
) -> None:
    imei = "123456789012345"
    await register_device(imei)

    device = await get_device_by_imei(imei)
    assert device is not None
    assert device.imei == imei

    with pytest.raises(DeviceAlreadyExists):
        await register_device(imei)


@pytest.mark.asyncio
async def test_list_devices(db_manager: DatabaseSessionManager) -> None:
    imeis = ["111", "222", "333"]
    for imei in imeis:
        await register_device(imei)

    devices = await list_devices()
    assert len(devices) == len(imeis)
    fetched_imeis = [d.imei for d in devices]
    for imei in imeis:
        assert imei in fetched_imeis


@pytest.mark.asyncio
async def test_get_device_by_imei_not_found(
    db_manager: DatabaseSessionManager,
) -> None:
    device = await get_device_by_imei("nonexistent-imei")
    assert device is None


@pytest.mark.asyncio
async def test_get_device_by_uuid_not_found(
    db_manager: DatabaseSessionManager,
) -> None:
    random_uuid = uuid.uuid4()
    device = await get_device_by_uuid(random_uuid)
    assert device is None
