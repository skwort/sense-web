from sqlalchemy import (
    String,
    Uuid,
    Index,
    ForeignKey,
    DateTime,
    Float,
    CheckConstraint,
)
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
        name (str): The user-assigned name of the device.
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


class DataPoint(Base):
    """
    Represents a single sensor reading or message reported by a SENSE
    Core device.

    Attributes:
        id (int): The primary key of the data point.
        uuid (str): A globally unique identifier for the data point.
        device_uuid (str): The UUID of the device that reported the
            data point.
        timestamp (datetime): The device-local timestamp when the data
            was recorded.
        sensor (str): A short string identifier for the sensor or data
            source (e.g., "gps_lat", "temp", "rs232_msg").
        val_float (float, optional): A numeric value, if applicable
            for the sensor.
        val_str (str, optional): A string value, for cases like serial
            input or textual messages.
        val_units (str, optional): The unit of measurement for
            `val_float`, if any (e.g., "degrees", "V", "ppm").
    """

    __tablename__ = "data_points"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(Uuid(), unique=True, index=True)

    device_uuid: Mapped[str] = mapped_column(
        ForeignKey("devices.uuid"), nullable=False
    )

    sensor: Mapped[str] = mapped_column(String(30), nullable=False)

    timestamp: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    val_float: Mapped[float] = mapped_column(Float, nullable=True)
    val_str: Mapped[str] = mapped_column(String, nullable=True)
    val_units: Mapped[str] = mapped_column(String, nullable=True)

    __table_args__ = (
        Index("idx_sensor_time", "sensor", "timestamp"),
        Index("idx_device_sensor", "device_uuid", "sensor"),
        CheckConstraint(
            "(val_float IS NOT NULL) OR (val_str IS NOT NULL)",
            name="check_value_present",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"DataPoint(\n"
            f"  id={self.id!r}),\n"
            f"  uuid={self.uuid!r}\n"
            f"  device_uuid={self.device_uuid!r}\n"
            f"  sensor={self.sensor!r}\n"
            f"  timestamp={self.timestamp!r}\n"
            f"  val_float={self.val_float!r}\n"
            f"  val_str={self.val_str!r}\n"
            f"  val_units={self.val_units!r}\n"
            f")"
        )
