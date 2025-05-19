import uuid
from typing import List, Optional
from sqlalchemy import select
from sense_web.exceptions import DeviceAlreadyExists
from sense_web.db.models import Device
from sense_web.db.session import sessionmanager
from sense_web.dto.device import DeviceDTO


async def register_device(imei: str) -> DeviceDTO:
    async with sessionmanager.session() as session:
        stmt = select(Device).where(Device.imei == imei)
        existing = (await session.execute(stmt)).scalars().first()
        if existing is not None:
            raise DeviceAlreadyExists(
                f"Device with IMEI {imei} already exists."
            )
        device_uuid = uuid.uuid4()
        device = Device(imei=imei, uuid=device_uuid)
        device_dto = DeviceDTO.model_validate(device)
        session.add(device)
        await session.commit()
        return device_dto


async def get_device_by_uuid(uuid: uuid.UUID) -> Optional[DeviceDTO]:
    async with sessionmanager.session() as session:
        stmt = select(Device).where(Device.uuid == uuid)
        result = (await session.execute(stmt)).scalars().one_or_none()
        if result is None:
            return None
        return DeviceDTO.model_validate(result)


async def get_device_by_imei(imei: str) -> Optional[DeviceDTO]:
    async with sessionmanager.session() as session:
        stmt = select(Device).where(Device.imei == imei)
        result = (await session.execute(stmt)).scalars().one_or_none()
        if result is None:
            return None
        return DeviceDTO.model_validate(result)


async def list_devices() -> List[DeviceDTO]:
    async with sessionmanager.session() as session:
        result = await session.execute(select(Device))
        return [DeviceDTO.model_validate(r) for r in result.scalars().all()]
