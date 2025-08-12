from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from db.base import SessionLocal
from db.models import Capture, Device, Experiment
from .schemas import CaptureRead, CaptureDeleteResponse
import os

router = APIRouter(prefix="/captures", tags=["captures"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=List[CaptureRead])
def list_captures(
    experiment_id: Optional[int] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Capture)
    if experiment_id:
        query = query.filter(Capture.experiment_id == experiment_id)
    if start_time:
        query = query.filter(Capture.created_at >= start_time)
    if end_time:
        query = query.filter(Capture.created_at <= end_time)
    captures = query.order_by(Capture.created_at.desc()).all()
    
    # 手动构建返回字典，确保Pydantic可以正确序列化
    result = []
    for capture in captures:
        result.append({
            "id": capture.id,
            "file_name": capture.file_name,
            "file_path": capture.file_path,
            "file_size": capture.file_size,
            "description": capture.description,
            "created_at": capture.created_at,
            "experiment_id": capture.experiment_id
        })
    return result

@router.get("/device/{mac_address}", response_model=List[CaptureRead])
def get_device_captures(mac_address: str, db: Session = Depends(get_db)):
    """
    List all PCAP captures related to a device (by mac_address).
    """
    device = db.query(Device).filter(Device.mac_address == mac_address).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    experiments = db.query(Experiment).filter(Experiment.target_ip == device.ip_address).all()
    experiment_ids = [e.id for e in experiments]
    if not experiment_ids:
        return []
    captures = db.query(Capture).filter(Capture.experiment_id.in_(experiment_ids)).order_by(Capture.created_at.desc()).all()
    
    # 手动构建返回字典，确保Pydantic可以正确序列化
    result = []
    for capture in captures:
        result.append({
            "id": capture.id,
            "file_name": capture.file_name,
            "file_path": capture.file_path,
            "file_size": capture.file_size,
            "description": capture.description,
            "created_at": capture.created_at,
            "experiment_id": capture.experiment_id
        })
    return result

@router.get("/{capture_id}/download")
def download_capture(capture_id: int, db: Session = Depends(get_db)):
    capture = db.query(Capture).filter(Capture.id == capture_id).first()
    if not capture:
        raise HTTPException(status_code=404, detail="Capture not found")
    file_path = capture.file_path
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="PCAP file not found")
    with open(file_path, "rb") as f:
        data = f.read()
    return Response(data, media_type="application/octet-stream", headers={
        "Content-Disposition": f"attachment; filename={capture.file_name}"
    })

@router.delete("/{capture_id}/", response_model=CaptureDeleteResponse)
def delete_capture(capture_id: int, db: Session = Depends(get_db)):
    capture = db.query(Capture).filter(Capture.id == capture_id).first()
    if not capture:
        return CaptureDeleteResponse(ok=False, detail="Capture not found")
    file_path = capture.file_path
    db.delete(capture)
    db.commit()
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            return CaptureDeleteResponse(ok=True, detail=f"DB deleted, file delete failed: {e}")
    return CaptureDeleteResponse(ok=True, detail="Capture and file deleted.") 