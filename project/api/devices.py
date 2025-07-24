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
import datetime
from pydantic import BaseModel
from .schemas import DeviceRead

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

class ScanRequest(BaseModel):
    subnet: str

@router.post("/scan", response_model=List[Dict[str, str]])
def scan_subnet(request: ScanRequest, db: Session = Depends(get_db)):
    """Scans a subnet for devices and returns device information (online and offline).

    Args:
        request (ScanRequest): Request body containing subnet.
        db (Session): Database session.

    Returns:
        List[Dict[str, str]]: List of devices with MAC, Name, IP, Status.
    """
    try:
        subnet = request.subnet
        devices_txt = os.path.join(os.path.dirname(__file__), "../data/devices.txt")
        discovery = DeviceDiscovery(devices_txt)
        scanned = discovery.discover(subnet)
        identified_devices = discovery.identify(scanned)

        # 1. Ensure all known devices from devices.txt exist in DB
        mac_to_device = {d.mac_address: d for d in db.query(Device).all()}
        for dev in discovery.mac_name_mapping.items():
            mac, name = dev
            # Ensure MAC is properly normalized
            normalized_mac = DeviceDiscovery.normalize_mac(mac)
            if normalized_mac not in mac_to_device:
                db.add(Device(mac_address=normalized_mac, hostname=name, status='offline', ip_address=''))
        db.commit()

        # 2. Update DB: set all known devices offline by default
        for device in db.query(Device).all():
            device.status = 'offline'
            device.ip_address = ''
        db.commit()

        # 3. Update DB: set scanned/online devices
        for device_info in identified_devices:
            if not device_info['IP']:
                continue  # Only update online devices here
            # Ensure MAC is properly normalized for comparison
            normalized_mac = DeviceDiscovery.normalize_mac(device_info['MAC'])
            device = db.query(Device).filter(Device.mac_address == normalized_mac).first()
            if device:
                device.ip_address = device_info['IP']
                device.hostname = device_info['Name']
                device.status = 'online'
                device.last_seen = datetime.datetime.utcnow()
            else:
                db.add(Device(
                    ip_address=device_info['IP'],
                    mac_address=normalized_mac,
                    hostname=device_info['Name'],
                    status='online',
                    last_seen=datetime.datetime.utcnow()
                ))
        db.commit()

        # 4. Return all devices (online and offline)
        all_devices = db.query(Device).all()
        result = []
        for d in all_devices:
            result.append({
                'mac_address': d.mac_address,
                'hostname': d.hostname,
                'ip_address': d.ip_address or '',
                'status': d.status
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")

@router.get("/", response_model=List[Dict[str, str]])
def get_devices(db: Session = Depends(get_db)):
    """Get all devices from database.

    Returns:
        List[Dict[str, str]]: List of devices with MAC, Name, IP, Status.
    """
    try:
        devices = db.query(Device).all()
        result = []
        for d in devices:
            result.append({
                'mac_address': d.mac_address,
                'hostname': d.hostname,
                'ip_address': d.ip_address or '',
                'status': d.status
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get devices: {str(e)}")

@router.get("/mac/{mac_address}", response_model=DeviceRead)
def get_device_by_mac(mac_address: str, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.mac_address == mac_address).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device

@router.get("/ip/{ip}/portscan", response_model=dict)
async def port_scan_device(
    ip: str,
    ports: str = "-",
    fast_scan: bool = True,
    db: Session = Depends(get_db)
):
    """Performs a port scan on the given device IP using nmap."""
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

@router.get("/ip/{ip}/oscan", response_model=dict)
async def os_fingerprint_device(
    ip: str,
    fast_scan: bool = True,
    ports: str = "22,80,443",
    db: Session = Depends(get_db)
):
    """Performs OS fingerprinting on the given device IP using nmap."""
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