from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Device schemas
class DeviceBase(BaseModel):
    ip_address: str
    mac_address: str
    hostname: Optional[str] = None
    device_type: Optional[str] = None
    os_info: Optional[str] = None
    status: Optional[str] = None
    last_seen: Optional[datetime] = None
    extra_info: Optional[str] = None

class DeviceCreate(DeviceBase):
    pass

class DeviceRead(DeviceBase):
    id: int
    class Config:
        orm_mode = True

# Capture schemas
class CaptureBase(BaseModel):
    file_name: str
    file_path: str
    created_at: Optional[datetime] = None
    experiment_id: Optional[int] = None
    file_size: Optional[int] = None
    description: Optional[str] = None

class CaptureCreate(CaptureBase):
    pass

class CaptureRead(CaptureBase):
    id: int
    class Config:
        orm_mode = True

# Experiment schemas
class ExperimentBase(BaseModel):
    name: str
    attack_type: Optional[str] = None
    target_ip: str
    status: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    result: Optional[str] = None
    capture_id: Optional[int] = None

class ExperimentCreate(ExperimentBase):
    pass

class ExperimentRead(ExperimentBase):
    id: int
    capture: Optional[CaptureRead] = None
    captures: Optional[List[CaptureRead]] = None
    class Config:
        orm_mode = True 