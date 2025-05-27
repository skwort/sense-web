import uuid
from typing import List
from datetime import datetime

from sqlalchemy import select
from sense_web.db.models import DataPoint
from sense_web.db.session import sessionmanager
from sense_web.dto.datapoint import DataPointDTO


async def create_datapoint(
    device_uuid: uuid.UUID,
    timestamp: datetime,
    sensor: str,
    val_float: float | None = None,
    val_str: str | None = None,
    val_units: str | None = None,
) -> DataPointDTO:
    async with sessionmanager.session() as session:
        dp = DataPoint(
            uuid=uuid.uuid4(),
            device_uuid=device_uuid,
            timestamp=timestamp,
            sensor=sensor,
            val_float=val_float,
            val_str=val_str,
            val_units=val_units,
        )
        dp_dto = DataPointDTO.model_validate(dp)
        session.add(dp)
        await session.commit()
        return dp_dto


async def get_datapoints_by_device_uuid(
    device_uuid: uuid.UUID, sort_descending: bool = True
) -> List[DataPointDTO]:
    async with sessionmanager.session() as session:
        stmt = select(DataPoint).where(DataPoint.device_uuid == device_uuid)
        result = await session.execute(stmt)
        if result is None:
            return []

        datapoint_list = [
            DataPointDTO.model_validate(dp) for dp in result.scalars().all()
        ]

        if len(datapoint_list) > 1 and sort_descending:
            datapoint_list.sort(key=lambda dp: dp.timestamp, reverse=True)

        return datapoint_list
