from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from db.base import SessionLocal
from db.models import ScanResult, PortInfo, Device
from .schemas import ScanResultCreate, ScanResultRead, PortInfoCreate, PortInfoRead
import datetime

router = APIRouter(prefix="/scan-results", tags=["scan-results"])

def get_db():
    """Provides a SQLAlchemy database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_scan_result_internal(scan_result: ScanResultCreate, db: Session):
    """Internal function to create a scan result."""
    try:
        # 验证设备是否存在
        device = db.query(Device).filter(Device.id == scan_result.device_id).first()
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        # 创建扫描结果
        db_scan_result = ScanResult(
            device_id=scan_result.device_id,
            scan_type=scan_result.scan_type,
            target_ip=scan_result.target_ip,
            scan_duration=scan_result.scan_duration,
            ports=scan_result.ports,
            os_guesses=scan_result.os_guesses,
            os_details=scan_result.os_details,
            raw_output=scan_result.raw_output,
            command=scan_result.command,
            error=scan_result.error,
            status=scan_result.status
        )
        
        db.add(db_scan_result)
        db.commit()
        db.refresh(db_scan_result)
        
        return db_scan_result
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create scan result: {str(e)}")

@router.post("/", response_model=ScanResultRead)
def create_scan_result(scan_result: ScanResultCreate, db: Session = Depends(get_db)):
    """Create a new scan result."""
    return create_scan_result_internal(scan_result, db)

@router.get("/", response_model=List[ScanResultRead])
def get_scan_results(
    device_id: Optional[int] = Query(None, description="Filter by device ID"),
    scan_type: Optional[str] = Query(None, description="Filter by scan type (port_scan, os_scan)"),
    target_ip: Optional[str] = Query(None, description="Filter by target IP"),
    limit: int = Query(100, description="Maximum number of results to return"),
    offset: int = Query(0, description="Number of results to skip"),
    db: Session = Depends(get_db)
):
    """Get scan results with optional filtering."""
    try:
        query = db.query(ScanResult)
        
        # 应用过滤器
        if device_id:
            query = query.filter(ScanResult.device_id == device_id)
        if scan_type:
            query = query.filter(ScanResult.scan_type == scan_type)
        if target_ip:
            query = query.filter(ScanResult.target_ip == target_ip)
        
        # 按时间倒序排列
        query = query.order_by(ScanResult.scan_time.desc())
        
        # 应用分页
        results = query.offset(offset).limit(limit).all()
        
        # 手动构建响应，处理JSON字段
        response_results = []
        for result in results:
            response_results.append({
                "id": result.id,
                "device_id": result.device_id,
                "scan_type": result.scan_type,
                "target_ip": result.target_ip,
                "scan_time": result.scan_time,
                "scan_duration": result.scan_duration,
                "ports": result.ports,
                "os_guesses": result.os_guesses,
                "os_details": result.os_details,
                "raw_output": result.raw_output,
                "command": result.command,
                "error": result.error,
                "status": result.status
            })
        
        return response_results
    except Exception as e:
        import traceback
        print(f"Error in get_scan_results: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to get scan results: {str(e)}")

@router.get("/{scan_result_id}", response_model=ScanResultRead)
def get_scan_result(scan_result_id: int, db: Session = Depends(get_db)):
    """Get a specific scan result by ID."""
    try:
        scan_result = db.query(ScanResult).filter(ScanResult.id == scan_result_id).first()
        if not scan_result:
            raise HTTPException(status_code=404, detail="Scan result not found")
        return scan_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get scan result: {str(e)}")

@router.get("/device/{device_id}", response_model=List[ScanResultRead])
def get_device_scan_results(
    device_id: int,
    scan_type: Optional[str] = Query(None, description="Filter by scan type"),
    limit: int = Query(50, description="Maximum number of results to return"),
    db: Session = Depends(get_db)
):
    """Get all scan results for a specific device."""
    try:
        # 验证设备是否存在
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        query = db.query(ScanResult).filter(ScanResult.device_id == device_id)
        
        if scan_type:
            query = query.filter(ScanResult.scan_type == scan_type)
        
        # 按时间倒序排列
        results = query.order_by(ScanResult.scan_time.desc()).limit(limit).all()
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get device scan results: {str(e)}")

@router.get("/device/{device_id}/latest", response_model=ScanResultRead)
def get_latest_scan_result(
    device_id: int,
    scan_type: str = Query(..., description="Scan type (port_scan or os_scan)"),
    db: Session = Depends(get_db)
):
    """Get the latest scan result for a specific device and scan type."""
    try:
        # 验证设备是否存在
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        scan_result = db.query(ScanResult).filter(
            ScanResult.device_id == device_id,
            ScanResult.scan_type == scan_type
        ).order_by(ScanResult.scan_time.desc()).first()
        
        if not scan_result:
            raise HTTPException(status_code=404, detail="No scan result found for this device and scan type")
        
        # 手动构建返回字典，确保Pydantic可以正确序列化
        return {
            "id": scan_result.id,
            "device_id": scan_result.device_id,
            "scan_type": scan_result.scan_type,
            "target_ip": scan_result.target_ip,
            "scan_time": scan_result.scan_time,
            "scan_duration": scan_result.scan_duration,
            "ports": scan_result.ports,
            "os_guesses": scan_result.os_guesses,
            "os_details": scan_result.os_details,
            "raw_output": scan_result.raw_output,
            "command": scan_result.command,
            "error": scan_result.error,
            "status": scan_result.status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get latest scan result: {str(e)}")

@router.delete("/{scan_result_id}")
def delete_scan_result(scan_result_id: int, db: Session = Depends(get_db)):
    """Delete a scan result."""
    try:
        scan_result = db.query(ScanResult).filter(ScanResult.id == scan_result_id).first()
        if not scan_result:
            raise HTTPException(status_code=404, detail="Scan result not found")
        
        db.delete(scan_result)
        db.commit()
        
        return {"message": "Scan result deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete scan result: {str(e)}")

@router.get("/stats/summary")
def get_scan_stats(db: Session = Depends(get_db)):
    """Get scan statistics summary."""
    try:
        # 总扫描次数
        total_scans = db.query(ScanResult).count()
        
        # 按类型统计
        port_scans = db.query(ScanResult).filter(ScanResult.scan_type == "port_scan").count()
        os_scans = db.query(ScanResult).filter(ScanResult.scan_type == "os_scan").count()
        
        # 按状态统计
        successful_scans = db.query(ScanResult).filter(ScanResult.status == "success").count()
        failed_scans = db.query(ScanResult).filter(ScanResult.status == "failed").count()
        
        # 平均扫描时间
        avg_duration = db.query(ScanResult.scan_duration).filter(
            ScanResult.scan_duration.isnot(None)
        ).all()
        avg_duration = sum([d[0] for d in avg_duration]) / len(avg_duration) if avg_duration else 0
        
        # 最近24小时的扫描
        yesterday = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        recent_scans = db.query(ScanResult).filter(ScanResult.scan_time >= yesterday).count()
        
        return {
            "total_scans": total_scans,
            "port_scans": port_scans,
            "os_scans": os_scans,
            "successful_scans": successful_scans,
            "failed_scans": failed_scans,
            "avg_duration_seconds": round(avg_duration, 2),
            "recent_24h_scans": recent_scans
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get scan stats: {str(e)}") 