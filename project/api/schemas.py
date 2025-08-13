from pydantic import BaseModel, validator, root_validator
import ipaddress
from typing import Optional, List, Dict, Any
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
    ip_address: Optional[str] = None
    mac_address: str
    hostname: Optional[str] = None
    status: Optional[str] = None
    port: Optional[str] = None
    os_info: Optional[str] = None

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
    last_seen: Optional[datetime] = None
    vendor: Optional[str] = None
    network_distance: Optional[str] = None
    latency: Optional[str] = None
    os_details: Optional[Dict[str, Any]] = None
    scan_summary: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

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
    file_size: Optional[int] = None
    description: Optional[str] = None

class CaptureCreate(CaptureBase):
    """
    Schema for creating a new capture.
    Inherits all fields from CaptureBase.
    """
    experiment_id: Optional[int] = None

class CaptureRead(CaptureBase):
    """
    Schema for reading capture information from the database.

    Attributes:
        id (int): Unique identifier for the capture.
    """
    id: int
    created_at: datetime
    experiment_id: Optional[int] = None

    class Config:
        from_attributes = True

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
        port (Optional[int]): Target port for the attack (default: 55443).
        status (Optional[str]): Current status of the experiment.
        start_time (Optional[datetime]): Start time of the experiment.
        end_time (Optional[datetime]): End time of the experiment.
        result (Optional[str]): Result or summary of the experiment.
        capture_id (Optional[int]): Associated capture ID.
        duration_sec (Optional[int]): Duration of the experiment in seconds.
    """
    name: str
    attack_type: str
    target_ip: str
    port: Optional[int] = 55443
    duration_sec: Optional[int] = None

    @validator('target_ip')
    def validate_target_ip(cls, v):
        try:
            ipaddress.IPv4Address(v)
        except Exception:
            raise ValueError('target_ip must be a valid IPv4 address')
        return v

    @validator('duration_sec')
    def validate_duration_sec(cls, v):
        if v is None or v <= 0:
            raise ValueError('duration_sec must be a positive integer')
        return v

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
    status: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    result: Optional[str] = None
    capture_id: Optional[int] = None

    class Config:
        from_attributes = True

# V2 Experiment schemas for Attack Engine V2
class ExperimentCreateV2(ExperimentBase):
    """
    V2 Schema for creating a new experiment with Attack Engine V2 features.
    
    Additional fields:
        interface (str): Network interface to use for attack (wlan0, eth0, any)
        attack_mode (str): Attack mode - 'single' or 'cyclic'
        cycles (int): Number of attack cycles for cyclic mode
        settle_time_sec (int): Settle time between cycles in seconds
    """
    interface: str = "wlan0"
    attack_mode: str = "single"  # 'single' or 'cyclic'
    cycles: int = 1
    settle_time_sec: int = 30

    @validator('attack_mode')
    def validate_attack_mode(cls, v):
        if v not in ['single', 'cyclic']:
            raise ValueError('attack_mode must be either "single" or "cyclic"')
        return v

    @validator('cycles')
    def validate_cycles(cls, v):
        if v < 1:
            raise ValueError('cycles must be at least 1')
        return v

    @validator('settle_time_sec')
    def validate_settle_time_sec(cls, v):
        if v < 0:
            raise ValueError('settle_time_sec must be non-negative')
        return v

class ExperimentReadV2(ExperimentBase):
    """
    V2 Schema for reading experiment information with Attack Engine V2 fields.
    """
    id: int
    status: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    result: Optional[str] = None
    capture_id: Optional[int] = None
    interface: Optional[str] = None
    attack_mode: Optional[str] = None
    cycles: Optional[int] = None
    settle_time_sec: Optional[int] = None
    current_cycle: Optional[int] = None
    total_cycles: Optional[int] = None
    attack_results: Optional[str] = None  # JSON string

    class Config:
        from_attributes = True

class ExperimentStatusV2(BaseModel):
    """
    V2 Schema for experiment status response.
    """
    id: int
    name: str
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    result: Optional[str] = None
    attack_mode: Optional[str] = None
    current_cycle: Optional[int] = None
    total_cycles: Optional[int] = None
    progress_percentage: Optional[float] = None
    estimated_remaining_time: Optional[int] = None  # in seconds

class ScanResultBase(BaseModel):
    scan_type: str  # 'port_scan' or 'os_scan'
    target_ip: str
    scan_duration: Optional[int] = None
    ports: Optional[List[Dict[str, Any]]] = None
    os_guesses: Optional[List[str]] = None
    os_details: Optional[Dict[str, Any]] = None
    raw_output: Optional[str] = None
    command: Optional[str] = None
    error: Optional[str] = None
    status: str = 'success'

class ScanResultCreate(ScanResultBase):
    device_id: int

class ScanResultRead(ScanResultBase):
    id: int
    device_id: int
    scan_time: datetime

    class Config:
        from_attributes = True

class PortInfoBase(BaseModel):
    port_number: int
    protocol: str  # 'tcp' or 'udp'
    state: str  # 'open', 'closed', 'filtered'
    service: Optional[str] = None
    version: Optional[str] = None

class PortInfoCreate(PortInfoBase):
    scan_result_id: int

class PortInfoRead(PortInfoBase):
    id: int
    scan_result_id: int

    class Config:
        from_attributes = True 