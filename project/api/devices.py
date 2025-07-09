from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from db.base import SessionLocal
from db.models import Device
from .schemas import DeviceCreate, DeviceRead

router = APIRouter(prefix="/devices", tags=["devices"])

def get_db():
    """
    Dependency that provides a SQLAlchemy database session.
    Closes the session after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=DeviceRead)
def create_device(device: DeviceCreate, db: Session = Depends(get_db)):
    """
    Create a new device entry in the database.

    Args:
        device (DeviceCreate): Device data to create.
        db (Session): Database session.

    Returns:
        DeviceRead: The created device object.
    """
    db_device = Device(**device.dict())
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device

@router.get("/", response_model=List[DeviceRead])
def list_devices(db: Session = Depends(get_db)):
    """
    Retrieve a list of all devices.

    Args:
        db (Session): Database session.

    Returns:
        List[DeviceRead]: List of all device objects.
    """
    return db.query(Device).all()

@router.get("/{device_id}", response_model=DeviceRead)
def get_device(device_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a device by its ID.

    Args:
        device_id (int): The ID of the device to retrieve.
        db (Session): Database session.

    Returns:
        DeviceRead: The device object if found.

    Raises:
        HTTPException: If the device is not found.
    """
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device

@router.put("/{device_id}", response_model=DeviceRead)
def update_device(device_id: int, device: DeviceCreate, db: Session = Depends(get_db)):
    """
    Update an existing device by its ID.

    Args:
        device_id (int): The ID of the device to update.
        device (DeviceCreate): Updated device data.
        db (Session): Database session.

    Returns:
        DeviceRead: The updated device object.

    Raises:
        HTTPException: If the device is not found.
    """
    db_device = db.query(Device).filter(Device.id == device_id).first()
    if not db_device:
        raise HTTPException(status_code=404, detail="Device not found")
    for key, value in device.dict().items():
        setattr(db_device, key, value)
    db.commit()
    db.refresh(db_device)
    return db_device

@router.delete("/{device_id}", response_model=dict)
def delete_device(device_id: int, db: Session = Depends(get_db)):
    """
    Delete a device by its ID.

    Args:
        device_id (int): The ID of the device to delete.
        db (Session): Database session.

    Returns:
        dict: Confirmation of deletion.

    Raises:
        HTTPException: If the device is not found.
    """
    db_device = db.query(Device).filter(Device.id == device_id).first()
    if not db_device:
        raise HTTPException(status_code=404, detail="Device not found")
    db.delete(db_device)
    db.commit()
    return {"ok": True} 