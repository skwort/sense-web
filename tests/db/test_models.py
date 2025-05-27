import datetime
import pytest
import uuid
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sense_web.db.base import Base
from sense_web.db.models import Device, DataPoint
from sqlalchemy.exc import IntegrityError


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()


def test_device_create(db_session: Session) -> None:
    imei = "123456789012345"
    device_uuid = uuid.uuid4()
    name = "device_name"
    device = Device(imei=imei, uuid=device_uuid, name=name)

    db_session.add(device)
    db_session.commit()

    assert device.id is not None
    assert device.imei == imei
    assert str(device.uuid) == str(device_uuid)
    assert device.name == name


def test_device_unique_imei_constraint(db_session: Session) -> None:
    device1 = Device(imei="123456789012345", uuid=uuid.uuid4(), name="d1")
    device2 = Device(imei="123456789012345", uuid=uuid.uuid4(), name="d2")

    db_session.add(device1)
    db_session.commit()

    db_session.add(device2)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_device_unique_uuid_constraint(db_session: Session) -> None:
    fixed_uuid = uuid.uuid4()
    device1 = Device(imei="123456789012345", uuid=fixed_uuid, name="d1")
    device2 = Device(imei="543210987654321", uuid=fixed_uuid, name="d2")

    db_session.add(device1)
    db_session.commit()

    db_session.add(device2)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_device_missing_imei_raises(db_session: Session) -> None:
    device = Device(imei=None, uuid=uuid.uuid4(), name="d1")
    db_session.add(device)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_device_get_by_imei(db_session: Session) -> None:
    imei = "123456789012345"
    device = Device(imei=imei, uuid=uuid.uuid4(), name="d1")
    db_session.add(device)
    db_session.commit()

    fetched = db_session.query(Device).filter_by(imei=imei).one_or_none()
    assert fetched is not None
    assert fetched.imei == imei


def test_device_get_by_uuid(db_session: Session) -> None:
    device_uuid = uuid.uuid4()
    device = Device(imei="123456789012345", uuid=device_uuid, name="d1")
    db_session.add(device)
    db_session.commit()

    fetched = (
        db_session.query(Device).filter_by(uuid=device_uuid).one_or_none()
    )
    assert fetched is not None
    assert str(fetched.uuid) == str(device_uuid)


def test_device_update_imei(db_session: Session) -> None:
    device = Device(imei="123456789012345", uuid=uuid.uuid4(), name="d1")
    db_session.add(device)
    db_session.commit()

    device.imei = "543210987654321"
    db_session.commit()

    updated = db_session.query(Device).filter_by(id=device.id).one()
    assert updated.imei == "543210987654321"


def test_device_delete(db_session: Session) -> None:
    device = Device(imei="123456789012345", uuid=uuid.uuid4(), name="d1")
    db_session.add(device)
    db_session.commit()

    db_session.delete(device)
    db_session.commit()

    deleted = db_session.query(Device).filter_by(id=device.id).one_or_none()
    assert deleted is None


def make_device(
    db_session: Session, imei: str = "123456789012345", name: str = "device"
) -> Device:
    device = Device(imei=imei, uuid=uuid.uuid4(), name=name)
    db_session.add(device)
    db_session.commit()
    return device


def test_datapoint_create(db_session: Session) -> None:
    device = make_device(db_session)
    dp = DataPoint(
        uuid=uuid.uuid4(),
        device_uuid=device.uuid,
        timestamp=datetime.datetime.now(datetime.UTC),
        sensor="gps_lat",
        val_float=37.7749,
        val_units="degrees",
    )

    db_session.add(dp)
    db_session.commit()

    assert dp.id is not None
    assert dp.val_float == 37.7749
    assert dp.val_units == "degrees"
    assert dp.val_str is None


def test_datapoint_with_val_str(db_session: Session) -> None:
    device = make_device(db_session)
    dp = DataPoint(
        uuid=uuid.uuid4(),
        device_uuid=device.uuid,
        timestamp=datetime.datetime.now(datetime.UTC),
        sensor="raw_rs232",
        val_str="OK",
        val_units=None,
    )

    db_session.add(dp)
    db_session.commit()

    assert dp.id is not None
    assert dp.val_str == "OK"
    assert dp.val_float is None


def test_datapoint_missing_required_fields(db_session: Session) -> None:
    device = make_device(db_session)
    dp = DataPoint(
        uuid=uuid.uuid4(),
        device_uuid=device.uuid,
        timestamp=datetime.datetime.now(datetime.UTC),
        sensor=None,
    )
    db_session.add(dp)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_datapoint_uuid_uniqueness(db_session: Session) -> None:
    device = make_device(db_session)
    fixed_uuid = uuid.uuid4()
    dp1 = DataPoint(
        uuid=fixed_uuid,
        device_uuid=device.uuid,
        timestamp=datetime.datetime.now(datetime.UTC),
        sensor="s1",
        val_float=1.0,
    )
    dp2 = DataPoint(
        uuid=fixed_uuid,
        device_uuid=device.uuid,
        timestamp=datetime.datetime.now(datetime.UTC),
        sensor="s2",
        val_float=2.0,
    )

    db_session.add(dp1)
    db_session.commit()

    db_session.add(dp2)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_datapoint_query_by_sensor(db_session: Session) -> None:
    device = make_device(db_session)
    for i in range(3):
        dp = DataPoint(
            uuid=uuid.uuid4(),
            device_uuid=device.uuid,
            timestamp=datetime.datetime.now(datetime.UTC),
            sensor="temp_sensor",
            val_float=20 + i,
            val_units="C",
        )
        db_session.add(dp)
    db_session.commit()

    results = db_session.query(DataPoint).filter_by(sensor="temp_sensor").all()
    assert len(results) == 3


def test_datapoint_val_float_and_str_can_coexist(db_session: Session) -> None:
    device = make_device(db_session)
    dp = DataPoint(
        uuid=uuid.uuid4(),
        device_uuid=device.uuid,
        timestamp=datetime.datetime.now(datetime.UTC),
        sensor="weird_sensor",
        val_float=3.14,
        val_str="3.14",
        val_units="units",
    )
    db_session.add(dp)
    db_session.commit()

    assert dp.val_float == 3.14
    assert dp.val_str == "3.14"


def test_datapoint_filter_by_time_range(db_session: Session) -> None:
    device = make_device(db_session)
    now = datetime.datetime.now(datetime.UTC)

    old_dp = DataPoint(
        uuid=uuid.uuid4(),
        device_uuid=device.uuid,
        timestamp=now.replace(year=2024),
        sensor="humidity",
        val_float=50.0,
    )
    new_dp = DataPoint(
        uuid=uuid.uuid4(),
        device_uuid=device.uuid,
        timestamp=now,
        sensor="humidity",
        val_float=55.0,
    )
    db_session.add_all([old_dp, new_dp])
    db_session.commit()

    results = (
        db_session.query(DataPoint)
        .filter(DataPoint.timestamp >= now.replace(year=2025))
        .all()
    )
    assert len(results) == 1
    assert results[0].val_float == 55.0


def test_datapoint_missing_device_uuid_raises(db_session: Session) -> None:
    dp = DataPoint(
        uuid=uuid.uuid4(),
        device_uuid=None,
        timestamp=datetime.datetime.now(datetime.UTC),
        sensor="temp",
        val_float=25.0,
    )
    db_session.add(dp)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_val_units_can_be_null(db_session: Session) -> None:
    device = make_device(db_session)
    dp = DataPoint(
        uuid=uuid.uuid4(),
        device_uuid=device.uuid,
        timestamp=datetime.datetime.now(datetime.UTC),
        sensor="custom_sensor",
        val_float=42.0,
    )
    db_session.add(dp)
    db_session.commit()
    assert dp.val_units is None
