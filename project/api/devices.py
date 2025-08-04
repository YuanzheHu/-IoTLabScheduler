from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from db.base import SessionLocal
from db.models import Device
from core.device_discovery import DeviceDiscovery
import os
from core.scan_engine import ScanEngine, ScanType
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
    
    # 手动构建返回字典，确保Pydantic可以正确序列化
    return {
        "id": device.id,
        "ip_address": device.ip_address,
        "mac_address": device.mac_address,
        "hostname": device.hostname,
        "status": device.status,
        "port": device.port,
        "os_info": device.os_info,
        "last_seen": device.last_seen
    }

@router.get("/{ip}/portscan")
async def port_scan_device(ip: str, ports: str = None, fast_scan: bool = True, save_to_db: bool = True, db: Session = Depends(get_db)):
    """执行端口扫描
    
    Args:
        ip: 目标IP地址
        ports: 要扫描的端口（可选，默认扫描常用端口）
        fast_scan: 是否使用快速扫描模式
        save_to_db: 是否保存结果到数据库
        db: 数据库会话
        
    Returns:
        Dict: 扫描结果
    """
    try:
        # 验证IP地址格式
        ipaddress.ip_address(ip)
        
        # 查找对应的设备
        device = db.query(Device).filter(Device.ip_address == ip).first()
        
        # 如果设备不存在，创建一个临时设备记录
        if not device:
            device = Device(
                ip_address=ip,
                mac_address=f"temp_{ip.replace('.', '_')}",
                hostname=f"External Device {ip}",
                status="online"
            )
            db.add(device)
            db.commit()
            db.refresh(device)
        
        device_id = device.id if device else None
        
        # 创建扫描引擎
        scan_engine = ScanEngine()
        
        # 执行端口扫描
        result = await scan_engine.scan_single_device(
            target_ip=ip,
            device_name=f"Device {ip}",
            scan_type=ScanType.PORT_SCAN
        )
        
        if result.error:
            raise HTTPException(status_code=500, detail=f"Port scan failed: {result.error}")
        
        # 准备返回结果
        scan_result = {
            "ports": result.tcp_ports + result.udp_ports,
            "raw_output": result.raw_output,
            "scan_duration": result.scan_duration,
            "total_tcp_ports": len(result.tcp_ports),
            "total_udp_ports": len(result.udp_ports)
        }
        
        # 保存到数据库
        if save_to_db and device_id:
            try:
                from .scan_results import create_scan_result_internal
                from .schemas import ScanResultCreate
                
                scan_result_data = ScanResultCreate(
                    device_id=device_id,
                    scan_type="port_scan",
                    target_ip=ip,
                    scan_duration=int(result.scan_duration),
                    ports=scan_result["ports"],
                    raw_output=result.raw_output,
                    command=result.command,
                    status="success"
                )
                
                create_scan_result_internal(scan_result_data, db)
            except Exception as e:
                # 如果保存失败，记录错误但不影响扫描结果返回
                print(f"Warning: Failed to save scan result to database: {e}")
        
        return scan_result
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid IP address format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Port scan failed: {str(e)}")

@router.get("/{ip}/oscan")
async def os_scan_device(ip: str, ports: str = "22,80,443", fast_scan: bool = True, save_to_db: bool = True, db: Session = Depends(get_db)):
    """执行OS指纹识别
    
    Args:
        ip: 目标IP地址
        ports: 用于OS指纹识别的端口（默认：22,80,443）
        fast_scan: 是否使用快速扫描模式
        save_to_db: 是否保存结果到数据库
        db: 数据库会话
        
    Returns:
        Dict: OS扫描结果
    """
    try:
        # 验证IP地址格式
        ipaddress.ip_address(ip)
        
        # 查找对应的设备
        device = db.query(Device).filter(Device.ip_address == ip).first()
        
        # 如果设备不存在，创建一个临时设备记录
        if not device:
            device = Device(
                ip_address=ip,
                mac_address=f"temp_{ip.replace('.', '_')}",
                hostname=f"External Device {ip}",
                status="online"
            )
            db.add(device)
            db.commit()
            db.refresh(device)
        
        device_id = device.id if device else None
        
        # 创建扫描引擎
        scan_engine = ScanEngine()
        
        # 执行OS扫描
        result = await scan_engine.scan_single_device(
            target_ip=ip,
            device_name=f"Device {ip}",
            scan_type=ScanType.OS_SCAN
        )
        
        if result.error:
            raise HTTPException(status_code=500, detail=f"OS scan failed: {result.error}")
        
        # 准备返回结果
        scan_result = {
            "os_guesses": result.os_info.get("os_guesses", []),
            "os_details": result.os_info.get("os_details", {}),
            "raw_output": result.raw_output,
            "scan_duration": result.scan_duration
        }
        
        # 保存到数据库
        if save_to_db and device_id:
            try:
                from .scan_results import create_scan_result_internal
                from .schemas import ScanResultCreate
                
                scan_result_data = ScanResultCreate(
                    device_id=device_id,
                    scan_type="os_scan",
                    target_ip=ip,
                    scan_duration=int(result.scan_duration),
                    os_guesses=scan_result["os_guesses"],
                    os_details=scan_result["os_details"],
                    raw_output=result.raw_output,
                    command=result.command,
                    status="success"
                )
                
                create_scan_result_internal(scan_result_data, db)
            except Exception as e:
                # 如果保存失败，记录错误但不影响扫描结果返回
                print(f"Warning: Failed to save scan result to database: {e}")
        
        return scan_result
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid IP address format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OS scan failed: {str(e)}")
