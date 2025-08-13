import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, Float, UniqueConstraint
from sqlalchemy.orm import relationship
from .base import Base

class Device(Base):
    """
    Device model representing a discovered IoT device in the lab.

    Fields:
        id: Primary key.
        ip_address: IP address of the device (unique, nullable for offline devices).
        mac_address: MAC address of the device (unique).
        hostname: Device name.
        status: Current status (e.g., online, offline).
        port: Port information (e.g., "55443", "8080").
        os_info: Operating system information.
        last_seen: Timestamp of last discovery (optional).
    """
    __tablename__ = 'devices'
    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String, index=True, nullable=True, unique=True)  # 允许NULL，但保持唯一性
    mac_address = Column(String, index=True, nullable=False, unique=True) # unique
    hostname = Column(String)
    status = Column(String)
    port = Column(String, nullable=True)
    os_info = Column(String, nullable=True)
    last_seen = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Extended fields from scan results
    vendor = Column(String, nullable=True)  # Vendor information
    network_distance = Column(String, nullable=True)  # Network distance
    latency = Column(String, nullable=True)  # Latency
    os_details = Column(JSON, nullable=True)  # Detailed OS information
    scan_summary = Column(JSON, nullable=True)  # Scan summary information

class Capture(Base):
    """
    Capture model representing a PCAP file generated from an experiment.

    Fields:
        id: Primary key.
        file_name: Name of the PCAP file.
        file_path: Path to the PCAP file.
        created_at: Timestamp when the capture was created.
        experiment_id: Foreign key to the related experiment.
        file_size: Size of the PCAP file in bytes.
        description: Optional description of the capture.
    """
    __tablename__ = 'captures'
    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    experiment_id = Column(Integer, ForeignKey('experiments.id'))
    file_size = Column(Integer)
    description = Column(String)

class Experiment(Base):
    """
    Experiment model representing a flooding attack experiment.

    Fields:
        id: Primary key.
        name: Name of the experiment.
        attack_type: Type of attack (e.g., SYN, UDP, ICMP).
        target_ip: Target IP address for the attack.
        port: Target port for the attack (default: 55443).
        status: Current status of the experiment (e.g., pending, running, completed).
        start_time: Timestamp when the experiment started.
        end_time: Timestamp when the experiment ended.
        result: Result or summary of the experiment.
        capture_id: Foreign key to the main capture file.
        capture: ORM relationship to the main Capture.
        captures: ORM relationship to all related captures.
        
        # New fields for Attack Engine V2
        interface: Network interface to use for attack.
        duration_sec: Duration of each attack cycle in seconds.
        settle_time_sec: Settle time between cycles in seconds.
        cycles: Number of attack cycles to perform.
        attack_mode: Attack mode (single/cyclic).
        current_cycle: Current cycle number during execution.
        total_cycles: Total number of cycles for this experiment.
        attack_results: JSON field storing detailed attack results.
    """
    __tablename__ = 'experiments'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    attack_type = Column(String)
    target_ip = Column(String, nullable=False)
    port = Column(Integer, default=55443)
    status = Column(String)
    start_time = Column(DateTime, default=datetime.datetime.utcnow)
    end_time = Column(DateTime)
    result = Column(Text)
    duration_sec = Column(Integer, nullable=True)
    capture_id = Column(Integer, ForeignKey('captures.id'))
    
    # New fields for Attack Engine V2
    interface = Column(String, default="wlan0")
    settle_time_sec = Column(Integer, default=30)
    cycles = Column(Integer, default=1)
    attack_mode = Column(String, default="single")  # single/cyclic
    current_cycle = Column(Integer, default=0)
    total_cycles = Column(Integer, default=1)
    attack_results = Column(Text)  # JSON field for storing detailed results

    # ORM relationships
    capture = relationship('Capture', foreign_keys=[capture_id])
    captures = relationship('Capture', backref='experiment', foreign_keys=[Capture.experiment_id])

class ScanResult(Base):
    """
    ScanResult model representing port scan and OS scan results.

    Fields:
        id: Primary key.
        device_id: Foreign key to the related device.
        scan_type: Type of scan (port_scan, os_scan).
        target_ip: Target IP address for the scan (unique).
        scan_time: Timestamp when the scan was performed.
        scan_duration: Duration of the scan in seconds.
        ports: JSON field containing port scan results.
        os_guesses: JSON field containing OS detection results.
        os_details: JSON field containing detailed OS information.
        raw_output: Raw scan output from nmap.
        command: The nmap command that was executed.
        error: Error message if scan failed.
        status: Scan status (success, failed, running).
    """
    __tablename__ = 'scan_results'
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey('devices.id'))
    scan_type = Column(String, nullable=False)  # 'port_scan' or 'os_scan'
    target_ip = Column(String, nullable=False)  # IP地址字段，允许多个扫描类型使用同一IP
    scan_time = Column(DateTime, default=datetime.datetime.utcnow)
    scan_duration = Column(Integer)  # Duration in seconds
    ports = Column(JSON, nullable=True)  # Port scan results
    os_guesses = Column(JSON, nullable=True)  # OS detection guesses
    os_details = Column(JSON, nullable=True)  # Detailed OS information
    raw_output = Column(Text, nullable=True)  # Raw nmap output
    command = Column(String, nullable=True)  # The nmap command executed
    error = Column(Text, nullable=True)  # Error message if failed
    status = Column(String, default='success')  # success, failed, running
    
    # Table constraints - ensure one scan result per device per scan type
    __table_args__ = (
        UniqueConstraint('device_id', 'scan_type', name='uq_device_scan_type'),
    )
    
    # ORM relationships
    device = relationship('Device', backref='scan_results')

class PortInfo(Base):
    """
    PortInfo model representing individual port information from port scans.

    Fields:
        id: Primary key.
        scan_result_id: Foreign key to the related scan result.
        port_number: Port number.
        protocol: Protocol (tcp, udp).
        state: Port state (open, closed, filtered).
        service: Service name if detected.
        version: Service version if detected.
    """
    __tablename__ = 'port_info'
    id = Column(Integer, primary_key=True, index=True)
    scan_result_id = Column(Integer, ForeignKey('scan_results.id'))
    port_number = Column(Integer, nullable=False)
    protocol = Column(String, nullable=False)  # 'tcp' or 'udp'
    state = Column(String, nullable=False)  # 'open', 'closed', 'filtered'
    service = Column(String, nullable=True)
    version = Column(String, nullable=True)
    
    # ORM relationships
    scan_result = relationship('ScanResult', backref='port_details') 

class ShellScript(Base):
    """Shell脚本模型"""
    __tablename__ = 'shell_scripts'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text)
    script_content = Column(Text, nullable=False)
    parameters_schema = Column(JSON)  # 解析出的参数结构
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    status = Column(String, default='active')  # active, inactive, deprecated
    created_by = Column(String, default='system')  # 创建者
    tags = Column(JSON)  # 标签数组
    version = Column(String, default='1.0.0')  # 脚本版本

class ScriptExecution(Base):
    """脚本执行记录"""
    __tablename__ = 'script_executions'
    id = Column(Integer, primary_key=True, index=True)
    script_id = Column(Integer, ForeignKey('shell_scripts.id'))
    script_name = Column(String)  # 冗余字段，便于查询
    parameters = Column(JSON)  # 用户填写的参数
    status = Column(String, default='pending')  # pending, running, completed, failed, cancelled
    start_time = Column(DateTime, default=datetime.datetime.utcnow)
    end_time = Column(DateTime)
    output = Column(Text)
    error = Column(Text)
    return_code = Column(Integer)
    task_id = Column(String, index=True)  # Celery任务ID
    execution_time_sec = Column(Float)  # 执行时长(秒)
    created_by = Column(String, default='system')  # 执行者
    
    # ORM relationships
    script = relationship('ShellScript', backref='executions') 