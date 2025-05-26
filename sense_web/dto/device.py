from pydantic import BaseModel, ConfigDict
from uuid import UUID


class DeviceDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    imei: str
    name: str
