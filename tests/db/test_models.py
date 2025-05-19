import pytest
import uuid
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sense_web.db.base import Base
from sense_web.db.models import Device
from sqlalchemy.exc import IntegrityError


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()


def test_create_device(db_session: Session) -> None:
    imei = "123456789012345"
    device_uuid = uuid.uuid4()
    device = Device(imei=imei, uuid=device_uuid)

    db_session.add(device)
    db_session.commit()

    assert device.id is not None
    assert device.imei == imei
    assert str(device.uuid) == str(device_uuid)


def test_unique_imei_constraint(db_session: Session) -> None:
    device1 = Device(imei="123456789012345", uuid=uuid.uuid4())
    device2 = Device(imei="123456789012345", uuid=uuid.uuid4())

    db_session.add(device1)
    db_session.commit()

    db_session.add(device2)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_unique_uuid_constraint(db_session: Session) -> None:
    fixed_uuid = uuid.uuid4()
    device1 = Device(imei="123456789012345", uuid=fixed_uuid)
    device2 = Device(imei="543210987654321", uuid=fixed_uuid)

    db_session.add(device1)
    db_session.commit()

    db_session.add(device2)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_missing_imei_raises(db_session: Session) -> None:
    device = Device(imei=None, uuid=uuid.uuid4())
    db_session.add(device)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_get_device_by_imei(db_session: Session) -> None:
    imei = "123456789012345"
    device = Device(imei=imei, uuid=uuid.uuid4())
    db_session.add(device)
    db_session.commit()

    fetched = db_session.query(Device).filter_by(imei=imei).one_or_none()
    assert fetched is not None
    assert fetched.imei == imei


def test_get_device_by_uuid(db_session: Session) -> None:
    device_uuid = uuid.uuid4()
    device = Device(imei="123456789012345", uuid=device_uuid)
    db_session.add(device)
    db_session.commit()

    fetched = (
        db_session.query(Device).filter_by(uuid=device_uuid).one_or_none()
    )
    assert fetched is not None
    assert str(fetched.uuid) == str(device_uuid)


def test_update_device_imei(db_session: Session) -> None:
    device = Device(imei="123456789012345", uuid=uuid.uuid4())
    db_session.add(device)
    db_session.commit()

    device.imei = "543210987654321"
    db_session.commit()

    updated = db_session.query(Device).filter_by(id=device.id).one()
    assert updated.imei == "543210987654321"


def test_delete_device(db_session: Session) -> None:
    device = Device(imei="123456789012345", uuid=uuid.uuid4())
    db_session.add(device)
    db_session.commit()

    db_session.delete(device)
    db_session.commit()

    deleted = db_session.query(Device).filter_by(id=device.id).one_or_none()
    assert deleted is None
