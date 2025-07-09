from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Device schemas
class DeviceBase(BaseModel):
    """
    Base schema for IoT devices.

    Attributes:
        ip_address (str): IP address of the device.
        mac_address (str): MAC address of the device.
        hostname (Optional[str]): Hostname of the device.
        device_type (Optional[str]): Type/category of the device.
        os_info (Optional[str]): Operating system information.
        status (Optional[str]): Current status (e.g., online/offline).
        last_seen (Optional[datetime]): Last time the device was seen.
        extra_info (Optional[str]): Any additional information.
    """
    ip_address: str
    mac_address: str
    hostname: Optional[str] = None
    device_type: Optional[str] = None
    os_info: Optional[str] = None
    status: Optional[str] = None
    last_seen: Optional[datetime] = None
    extra_info: Optional[str] = None

class DeviceCreate(DeviceBase):
    """
    Schema for creating a new device.
    Inherits all fields from DeviceBase.
    """
    pass

class DeviceRead(DeviceBase):
    """
    Schema for reading device information from the database.

    Attributes:
        id (int): Unique identifier for the device.
    """
    id: int
    class Config:
        orm_mode = True

# Capture schemas
class CaptureBase(BaseModel):
    """
    Base schema for packet capture (PCAP) files.

    Attributes:
        file_name (str): Name of the PCAP file.
        file_path (str): Filesystem path to the PCAP file.
        created_at (Optional[datetime]): Timestamp when the capture was created.
        experiment_id (Optional[int]): Associated experiment ID.
        file_size (Optional[int]): Size of the file in bytes.
        description (Optional[str]): Description or notes about the capture.
    """
    file_name: str
    file_path: str
    created_at: Optional[datetime] = None
    experiment_id: Optional[int] = None
    file_size: Optional[int] = None
    description: Optional[str] = None

class CaptureCreate(CaptureBase):
    """
    Schema for creating a new capture.
    Inherits all fields from CaptureBase.
    """
    pass

class CaptureRead(CaptureBase):
    """
    Schema for reading capture information from the database.

    Attributes:
        id (int): Unique identifier for the capture.
    """
    id: int
    class Config:
        orm_mode = True

class CaptureDeleteResponse(BaseModel):
    """
    Response schema for capture deletion.

    Attributes:
        ok (bool): Whether the deletion was successful.
        detail (str): Additional details or error messages.
    """
    ok: bool
    detail: str = ""

# Experiment schemas
class ExperimentBase(BaseModel):
    """
    Base schema for experiments.

    Attributes:
        name (str): Name of the experiment.
        attack_type (Optional[str]): Type of attack (e.g., SYN, UDP, ICMP).
        target_ip (str): Target IP address for the experiment.
        status (Optional[str]): Current status of the experiment.
        start_time (Optional[datetime]): Start time of the experiment.
        end_time (Optional[datetime]): End time of the experiment.
        result (Optional[str]): Result or summary of the experiment.
        capture_id (Optional[int]): Associated capture ID.
        duration_sec (Optional[int]): Duration of the experiment in seconds.
    """
    name: str
    attack_type: Optional[str] = None
    target_ip: str
    status: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    result: Optional[str] = None
    capture_id: Optional[int] = None
    duration_sec: Optional[int] = 60

class ExperimentCreate(ExperimentBase):
    """
    Schema for creating a new experiment.
    Inherits all fields from ExperimentBase.
    """
    pass

class ExperimentRead(ExperimentBase):
    """
    Schema for reading experiment information from the database.

    Attributes:
        id (int): Unique identifier for the experiment.
        capture (Optional[CaptureRead]): Associated capture object.
        captures (Optional[List[CaptureRead]]): List of related captures.
    """
    id: int
    capture: Optional[CaptureRead] = None
    captures: Optional[List[CaptureRead]] = None
    class Config:
        orm_mode = True 