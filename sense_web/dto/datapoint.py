import datetime
from pydantic import BaseModel, ConfigDict
from uuid import UUID


class DataPointDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    device_uuid: UUID
    timestamp: datetime.datetime
    sensor: str
    val_float: float | None = None
    val_str: str | None = None
    val_units: str | None = None
