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

        # 1. Ensure all known devices from devices.txt exist in DB (with deduplication)
        mac_to_device = {d.mac_address: d for d in db.query(Device).all()}
        devices_to_add = []
        processed_macs_txt = set()
        
        for dev in discovery.mac_name_mapping.items():
            mac, name = dev
            # Ensure MAC is properly normalized
            normalized_mac = DeviceDiscovery.normalize_mac(mac)
            
            # Skip if we've already processed this MAC from devices.txt
            if normalized_mac in processed_macs_txt:
                continue
            processed_macs_txt.add(normalized_mac)
            
            if normalized_mac not in mac_to_device:
                devices_to_add.append(Device(mac_address=normalized_mac, hostname=name, status='offline', ip_address=None))
        
        # Add all new devices at once
        if devices_to_add:
            db.add_all(devices_to_add)
            db.flush()  # Ensure new devices are committed to the session
        
        # 2. Update DB: set all known devices offline by default
        for device in db.query(Device).all():
            device.status = 'offline'
            device.ip_address = None
        
        # 3. Update DB: set scanned/online devices (with deduplication)
        updated_count = 0
        processed_macs = set()  # Track processed MACs to avoid duplicates
        for device_info in identified_devices:
            if not device_info['IP']:
                continue  # Only update online devices here
            # Ensure MAC is properly normalized for comparison
            normalized_mac = DeviceDiscovery.normalize_mac(device_info['MAC'])
            
            # Skip if we've already processed this MAC in this scan
            if normalized_mac in processed_macs:
                continue
            processed_macs.add(normalized_mac)
            
            device = db.query(Device).filter(Device.mac_address == normalized_mac).first()
            if device:
                device.ip_address = device_info['IP']
                device.hostname = device_info['Name']
                device.status = 'online'
                device.last_seen = datetime.datetime.utcnow()
                updated_count += 1
            else:
                # Check if device already exists in pending adds (defensive programming)
                try:
                    new_device = Device(
                        ip_address=device_info['IP'],
                        mac_address=normalized_mac,
                        hostname=device_info['Name'],
                        status='online',
                        last_seen=datetime.datetime.utcnow()
                    )
                    db.add(new_device)
                    db.flush()  # Force SQL execution to catch constraint errors early
                    updated_count += 1
                except Exception as e:
                    print(f"Warning: Could not add device {normalized_mac}: {e}")
                    db.rollback()
                    # Try to update existing device if it was created in the meantime
                    device = db.query(Device).filter(Device.mac_address == normalized_mac).first()
                    if device:
                        device.ip_address = device_info['IP']
                        device.hostname = device_info['Name']
                        device.status = 'online'
                        device.last_seen = datetime.datetime.utcnow()
                        updated_count += 1
        
        # Commit all changes at once
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
        "last_seen": device.last_seen,
        "vendor": device.vendor,
        "network_distance": device.network_distance,
        "latency": device.latency,
        "os_details": device.os_details,
        "scan_summary": device.scan_summary
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
                from .scan_results import create_scan_result_internal, update_or_create_scan_result
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
                
                # 使用更新或创建函数，确保一个设备只有一个扫描结果
                update_or_create_scan_result(scan_result_data, db)
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
            "mac_address": result.os_info.get("mac_address"),
            "vendor": result.os_info.get("vendor"),
            "network_distance": result.os_info.get("network_distance"),
            "port_info": result.os_info.get("port_info", []),
            "scan_summary": result.os_info.get("scan_summary", {}),
            "host_status": result.os_info.get("host_status"),
            "scan_statistics": result.os_info.get("scan_statistics", {}),
            "raw_output": result.raw_output,
            "scan_duration": result.scan_duration
        }
        
        # 保存到数据库
        if save_to_db and device_id:
            try:
                from .scan_results import create_scan_result_internal, update_or_create_scan_result
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
                
                # 使用更新或创建函数，确保一个设备只有一个扫描结果
                update_or_create_scan_result(scan_result_data, db)
                
                # Update device information from scan results
                if result.os_info:
                    update_device_from_scan_results(device_id, result.os_info, db)
            except Exception as e:
                # 如果保存失败，记录错误但不影响扫描结果返回
                print(f"Warning: Failed to save scan result to database: {e}")
        
        return scan_result
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid IP address format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OS scan failed: {str(e)}")

def update_device_from_scan_results(device_id: int, scan_info: dict, db: Session):
    """
    Update device information from scan results
    
    Args:
        device_id: Device ID
        scan_info: Scan information dictionary
        db: Database session
    """
    try:
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            return
            
        # Update vendor information
        if scan_info.get('vendor'):
            device.vendor = scan_info['vendor']
            
        # Update network distance
        if scan_info.get('network_distance'):
            device.network_distance = scan_info['network_distance']
            
        # Update latency information
        if scan_info.get('scan_summary', {}).get('latency'):
            device.latency = scan_info['scan_summary']['latency']
            
        # Update OS details
        if scan_info.get('os_details'):
            device.os_details = scan_info['os_details']
            
        # Update scan summary
        if scan_info.get('scan_summary'):
            device.scan_summary = scan_info['scan_summary']
            
        # Update simplified OS info
        if scan_info.get('os_guesses'):
            device.os_info = scan_info['os_guesses'][0] if scan_info['os_guesses'] else None
            
        db.commit()
        
    except Exception as e:
        print(f"Error updating device from scan results: {e}")
        db.rollback()
