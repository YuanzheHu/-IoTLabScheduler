from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from db.base import SessionLocal
from db.models import Device
from core.device_discovery import DeviceDiscovery
import os
from core.scan_engine import ScanEngine
import ipaddress
import asyncio

router = APIRouter(prefix="/devices", tags=["devices"])

def get_db():
    """Provides a SQLAlchemy database session.

    Yields:
        Session: SQLAlchemy database session.

    Closes:
        The session after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/scan", response_model=List[Dict[str, Any]])
def scan_subnet(subnet: str, db: Session = Depends(get_db)):
    """Scans a subnet for devices and returns device information.

    Args:
        subnet (str): Subnet to scan (e.g., "10.12.0.0/24").
        db (Session): Database session.

    Returns:
        List[Dict[str, Any]]: List of devices with Category, Name, MAC address, Phone, Email, Password.

    Raises:
        HTTPException: If the scan fails.
    """
    try:
        clean_file = os.path.join(os.path.dirname(__file__), "../data/clean_devices.csv")
        discovery = DeviceDiscovery(clean_file)
        devices = discovery.discover(subnet)
        identified_devices = discovery.identify(devices)
        for device_info in identified_devices:
            existing_device = db.query(Device).filter(
                Device.mac_address == device_info['MAC']
            ).first()
            if existing_device:
                existing_device.ip_address = device_info['IP']
                existing_device.hostname = device_info['Name']
                existing_device.device_type = device_info['Category']
                existing_device.status = "online"
                existing_device.password = device_info.get('Password', None)
                existing_device.port = None
                existing_device.os_info = None
                existing_device.phone = device_info.get('Phone', None)
                existing_device.email = device_info.get('Email', None)
            else:
                new_device = Device(
                    ip_address=device_info['IP'],
                    mac_address=device_info['MAC'],
                    hostname=device_info['Name'],
                    device_type=device_info['Category'],
                    status="online",
                    password=device_info.get('Password', None),
                    port=None,
                    os_info=None,
                    phone=device_info.get('Phone', None),
                    email=device_info.get('Email', None)
                )
                db.add(new_device)
        db.commit()
        return identified_devices
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")

@router.get("/", response_model=List[Dict[str, Any]])
def list_devices(db: Session = Depends(get_db)):
    """Retrieves all devices from the database.

    Args:
        db (Session): Database session.

    Returns:
        List[Dict[str, Any]]: List of all devices.
    """
    devices = db.query(Device).all()
    result = []
    for device in devices:
        result.append({
            "IP": device.ip_address,
            "Category": device.device_type or "Unknown",
            "Name": device.hostname or "Unknown",
            "MAC address": device.mac_address,
            "Phone": device.phone,
            "Email": device.email,
            "Password": device.password,
            "Port": device.port,
            "Status": device.status,
            "Last Seen": device.last_seen.isoformat() if device.last_seen else None,
            "OS Info": device.os_info
        })
    return result

@router.get("/{device_id}", response_model=Dict[str, Any])
def get_device(device_id: int, db: Session = Depends(get_db)):
    """Retrieves a specific device by ID.

    Args:
        device_id (int): Device ID.
        db (Session): Database session.

    Returns:
        Dict[str, Any]: Device information.

    Raises:
        HTTPException: If the device is not found.
    """
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return {
        "id": device.id,
        "IP": device.ip_address,
        "Category": device.device_type or "Unknown",
        "Name": device.hostname or "Unknown",
        "MAC address": device.mac_address,
        "Phone": device.phone,
        "Email": device.email,
        "Password": device.password,
        "Port": device.port,
        "Status": device.status,
        "Last Seen": device.last_seen.isoformat() if device.last_seen else None,
        "OS Info": device.os_info
    }

@router.delete("/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db)):
    """Deletes a device by ID.

    Args:
        device_id (int): Device ID.
        db (Session): Database session.

    Returns:
        Dict[str, str]: Success message.

    Raises:
        HTTPException: If the device is not found.
    """
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    db.delete(device)
    db.commit()
    return {"message": "Device deleted successfully"}

@router.get("/{ip}/portscan", response_model=dict)
async def port_scan_device(
    ip: str,
    ports: str = "-",
    fast_scan: bool = True,
    db: Session = Depends(get_db)
):
    """Performs a port scan on the given device IP using nmap.

    Args:
        ip (str): Target device IP address.
        ports (str, optional): Ports to scan (default: all ports).
        fast_scan (bool, optional): Use fast scan options.
        db (Session): Database session.

    Returns:
        dict: Port scan results.

    Raises:
        HTTPException: If the IP address is invalid.
    """
    try:
        ipaddress.IPv4Address(ip)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid IPv4 address")
    engine = ScanEngine()
    result = await engine.port_scan(ip, ports=ports, fast_scan=fast_scan)
    device = db.query(Device).filter(Device.ip_address == ip).first()
    if device:
        port_list = [p['port'].split('/')[0] for p in result.get('ports', [])]
        device.port = ','.join(port_list)
        db.commit()
    return result

@router.get("/{ip}/oscan", response_model=dict)
async def os_fingerprint_device(
    ip: str,
    fast_scan: bool = True,
    ports: str = "22,80,443",
    db: Session = Depends(get_db)
):
    """Performs OS fingerprinting on the given device IP using nmap.

    Args:
        ip (str): Target device IP address.
        fast_scan (bool, optional): Use fast scan options.
        ports (str, optional): Ports to scan for OS fingerprinting.
        db (Session): Database session.

    Returns:
        dict: OS fingerprint results.

    Raises:
        HTTPException: If the IP address is invalid.
    """
    try:
        ipaddress.IPv4Address(ip)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid IPv4 address")
    engine = ScanEngine()
    result = await engine.os_fingerprint(ip, fast_scan=fast_scan, ports=ports)
    device = db.query(Device).filter(Device.ip_address == ip).first()
    if device:
        guesses = result.get('os_guesses', [])
        device.os_info = guesses[0] if guesses else None
        db.commit()
    return result