from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from db.base import SessionLocal
from db.models import ScanResult, PortInfo, Device
from .schemas import ScanResultCreate, ScanResultRead, PortInfoCreate, PortInfoRead
import datetime
from sqlalchemy import text

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

def update_or_create_scan_result(scan_result: ScanResultCreate, db: Session):
    """
    Update existing scan result for a device or create new one if none exists.
    This ensures one device has only one scan result per scan type.
    """
    try:
        # 查找该设备是否已有相同类型的扫描结果
        existing_result = db.query(ScanResult).filter(
            ScanResult.device_id == scan_result.device_id,
            ScanResult.scan_type == scan_result.scan_type
        ).first()
        
        if existing_result:
            # 更新现有记录
            existing_result.target_ip = scan_result.target_ip
            existing_result.scan_duration = scan_result.scan_duration
            existing_result.ports = scan_result.ports
            existing_result.os_guesses = scan_result.os_guesses
            existing_result.os_details = scan_result.os_details
            existing_result.raw_output = scan_result.raw_output
            existing_result.command = scan_result.command
            existing_result.error = scan_result.error
            existing_result.status = scan_result.status
            existing_result.scan_time = datetime.datetime.utcnow()  # 更新时间戳
            
            db.commit()
            db.refresh(existing_result)
            return existing_result
        else:
            # 创建新记录
            return create_scan_result_internal(scan_result, db)
            
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update/create scan result: {str(e)}")

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
    scan_type: str = Query(..., description="Scan type (port_scan, os_scan)"),
    db: Session = Depends(get_db)
):
    """Get the latest scan result for a specific device and scan type."""
    try:
        result = db.query(ScanResult).filter(
            ScanResult.device_id == device_id,
            ScanResult.scan_type == scan_type
        ).order_by(ScanResult.scan_time.desc()).first()
        
        if not result:
            raise HTTPException(status_code=404, detail="No scan result found for this device and scan type")
        
        return {
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
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get latest scan result: {str(e)}")

@router.delete("/cleanup-duplicates")
def cleanup_duplicate_scan_results(db: Session = Depends(get_db)):
    """
    Clean up duplicate scan results, keeping only the latest one for each device and scan type.
    This ensures one device has only one scan result per scan type.
    """
    try:
        # 查找所有重复的扫描结果
        duplicates = db.execute("""
            WITH ranked_results AS (
                SELECT 
                    id,
                    device_id,
                    scan_type,
                    ROW_NUMBER() OVER (
                        PARTITION BY device_id, scan_type 
                        ORDER BY scan_time DESC
                    ) as rn
                FROM scan_results
            )
            SELECT id FROM ranked_results WHERE rn > 1
        """).fetchall()
        
        if not duplicates:
            return {"message": "No duplicate scan results found", "deleted_count": 0}
        
        # 删除重复的记录
        duplicate_ids = [row[0] for row in duplicates]
        deleted_count = db.query(ScanResult).filter(ScanResult.id.in_(duplicate_ids)).delete()
        db.commit()
        
        return {
            "message": f"Successfully cleaned up {deleted_count} duplicate scan results",
            "deleted_count": deleted_count,
            "deleted_ids": duplicate_ids
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to cleanup duplicate scan results: {str(e)}")

@router.get("/stats/summary")
def get_scan_results_summary(db: Session = Depends(get_db)):
    """Get summary statistics of scan results."""
    try:
        # 总扫描结果数
        total_results = db.query(ScanResult).count()
        
        # 按扫描类型统计
        type_stats = db.execute(text("""
            SELECT 
                scan_type,
                COUNT(*) as count,
                COUNT(DISTINCT device_id) as unique_devices
            FROM scan_results 
            GROUP BY scan_type
        """)).fetchall()
        
        # 按设备统计
        device_stats = db.execute(text("""
            SELECT 
                device_id,
                COUNT(*) as scan_count,
                MAX(scan_time) as last_scan_time
            FROM scan_results 
            GROUP BY device_id
            ORDER BY scan_count DESC
        """)).fetchall()
        
        return {
            "total_scan_results": total_results,
            "scan_type_distribution": [
                {
                    "scan_type": row[0],
                    "count": row[1],
                    "unique_devices": row[2]
                }
                for row in type_stats
            ],
            "device_scan_summary": [
                {
                    "device_id": row[0],
                    "scan_count": row[1],
                    "last_scan_time": row[2].isoformat() if row[2] and hasattr(row[2], 'isoformat') else str(row[2]) if row[2] else None
                }
                for row in device_stats
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get scan results summary: {str(e)}") 