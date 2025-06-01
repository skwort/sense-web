import datetime
from pydantic import BaseModel, ConfigDict, field_validator
from uuid import UUID


class DataPointDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    device_uuid: UUID
    timestamp: datetime.datetime
    sensor: str
    val_int: int | None = None
    val_float: float | None = None
    val_str: str | None = None
    val_units: str | None = None

    @field_validator("timestamp", mode="before")
    @classmethod
    def ensure_utc(cls, value: datetime.datetime) -> datetime.datetime:
        if value and value.tzinfo is None:
            # Treat naive datetimes as UTC; this is required because SQLite
            # DATETIME values lack timezones.
            return value.replace(tzinfo=datetime.timezone.utc)
        return value
