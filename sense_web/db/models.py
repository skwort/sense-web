from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class Device(Base):
    """
    Represents a SENSE Core device with the system.

    Attributes:
        id (int): The primary key of the device.
        imei (str): The International Mobile Equipment Identity used to
            uniquely identify the device hardware.
        uuid (str): The UUID assigned to the device during registration.
            This is used for routing, resource identification, and device
            lookups.
    """

    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    imei: Mapped[str] = mapped_column(String, unique=True, index=True)
    uuid: Mapped[str] = mapped_column(Uuid(), unique=True, index=True)
    name: Mapped[str] = mapped_column(String)

    def __repr__(self) -> str:
        return (
            f"Device(\n"
            f"  id={self.id!r}),\n"
            f"  imei={self.imei!r},\n"
            f"  uuid={self.uuid!r}\n"
            f"  name={self.name!r}\n"
            f")"
        )
