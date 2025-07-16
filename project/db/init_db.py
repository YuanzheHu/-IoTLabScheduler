from project.db.base import engine, Base, SessionLocal
from project.db.models import Device, Experiment, Capture
from sqlalchemy import MetaData

# Drop all tables (reset database)
Base.metadata.drop_all(bind=engine)
# Create all tables
Base.metadata.create_all(bind=engine)

# Simple insert/query test
if __name__ == '__main__':
    db = SessionLocal()
    try:
        # Insert a test device
        device = Device(
            ip_address='10.12.0.100',
            mac_address='00:11:22:33:44:55',
            hostname='test-device',
            device_type='Camera',
            os_info='Linux',
            status='online'
        )
        db.add(device)
        db.commit()
        db.refresh(device)
        print(f"Inserted device: {device.id}, {device.ip_address}")

        # Query all devices
        devices = db.query(Device).all()
        print(f"All devices: {[d.ip_address for d in devices]}")

        # Delete the test device
        db.delete(device)
        db.commit()
    finally:
        db.close()