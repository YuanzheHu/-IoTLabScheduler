from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON
from .base import Base
import datetime

class Device(Base):
    """
    Device model representing a discovered IoT device in the lab.

    Fields:
        id: Primary key.
        ip_address: IP address of the device.
        mac_address: MAC address of the device.
        hostname: Hostname of the device.
        device_type: Type/category of the device (e.g., Camera, Sensor).
        os_info: Operating system information.
        status: Current status (e.g., online, offline).
        last_seen: Timestamp of last discovery.
        extra_info: Additional information (JSON/text).
    """
    __tablename__ = 'devices'
    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String, index=True, nullable=False, unique=True)
    mac_address = Column(String, index=True, nullable=False, unique=True)
    hostname = Column(String)
    device_type = Column(String)
    os_info = Column(String)
    status = Column(String)
    last_seen = Column(DateTime, default=datetime.datetime.utcnow)
    extra_info = Column(Text)

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
        status: Current status of the experiment (e.g., pending, running, completed).
        start_time: Timestamp when the experiment started.
        end_time: Timestamp when the experiment ended.
        result: Result or summary of the experiment.
        capture_id: Foreign key to the main capture file.
        capture: ORM relationship to the main Capture.
        captures: ORM relationship to all related captures.
    """
    __tablename__ = 'experiments'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    attack_type = Column(String)
    target_ip = Column(String, nullable=False)
    status = Column(String)
    start_time = Column(DateTime, default=datetime.datetime.utcnow)
    end_time = Column(DateTime)
    result = Column(Text)
    capture_id = Column(Integer, ForeignKey('captures.id'))

    # ORM relationships
    capture = relationship('Capture', foreign_keys=[capture_id])
    captures = relationship('Capture', backref='experiment', foreign_keys=[Capture.experiment_id]) 