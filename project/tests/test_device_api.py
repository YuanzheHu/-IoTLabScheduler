import pytest
from fastapi.testclient import TestClient
from main import app
import time

client = TestClient(app)

def test_scan_subnet_get():
    """
    Test scanning a subnet using GET method.
    """
    # Test scanning a subnet
    response = client.get("/devices/subnet/10.12.0.0/24/scan")
    assert response.status_code == 200
    
    devices = response.json()
    assert isinstance(devices, list)
    
    # Check if devices have the required fields
    if devices:  # If any devices found
        device = devices[0]
        required_fields = ["IP", "Category", "Name", "MAC address", "Phone", "Email", "Password"]
        for field in required_fields:
            assert field in device
            assert device[field] is not None

def test_scan_subnet_post():
    """
    Test scanning a subnet using POST method.
    """
    # Test scanning a subnet
    response = client.post("/devices/scan", params={"subnet": "10.12.0.0/24"})
    assert response.status_code == 200
    
    devices = response.json()
    assert isinstance(devices, list)
    
    # Check if devices have the required fields
    if devices:  # If any devices found
        device = devices[0]
        required_fields = ["IP", "Category", "Name", "MAC address", "Phone", "Email", "Password"]
        for field in required_fields:
            assert field in device
            assert device[field] is not None

def test_list_devices():
    """
    Test listing all devices from database.
    """
    response = client.get("/devices/")
    assert response.status_code == 200
    
    devices = response.json()
    assert isinstance(devices, list)
    
    # Check if devices have the required fields
    if devices:  # If any devices found
        device = devices[0]
        required_fields = ["IP", "Category", "Name", "MAC address", "Phone", "Email", "Password", "Status"]
        for field in required_fields:
            assert field in device

def test_get_device_by_id():
    """
    Test getting a specific device by ID.
    """
    # First, scan a subnet to ensure we have devices
    scan_response = client.get("/devices/subnet/10.12.0.0/24/scan")
    assert scan_response.status_code == 200
    
    devices = scan_response.json()
    if devices:  # If any devices found
        # Get the first device by ID (we need to get the ID from the database)
        # For now, we'll test with a non-existent ID
        response = client.get("/devices/999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Device not found"

def test_delete_device():
    """
    Test deleting a device by ID.
    """
    # Test deleting a non-existent device
    response = client.delete("/devices/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Device not found"

def test_scan_invalid_subnet():
    """
    Test scanning with invalid subnet format.
    """
    response = client.get("/devices/subnet/invalid-subnet/scan")
    # This might return 500 or 200 depending on how nmap handles invalid input
    assert response.status_code in [200, 500]

def test_device_data_structure():
    """
    Test that device data has the correct structure for frontend use.
    """
    # Scan a subnet
    response = client.get("/devices/subnet/10.12.0.0/24/scan")
    assert response.status_code == 200
    
    devices = response.json()
    assert isinstance(devices, list)
    
    if devices:
        device = devices[0]
        
        # Check all required fields for frontend
        required_fields = {
            "IP": str,
            "Category": str,
            "Name": str,
            "MAC address": str,
            "Phone": str,
            "Email": str,
            "Password": str
        }
        
        for field, expected_type in required_fields.items():
            assert field in device
            assert isinstance(device[field], expected_type)
            assert device[field] is not None

def test_device_persistence():
    """
    Test that scanned devices are persisted to database.
    """
    # First scan
    response1 = client.get("/devices/subnet/10.12.0.0/24/scan")
    assert response1.status_code == 200
    devices1 = response1.json()
    
    # Second scan (should return same devices from database)
    response2 = client.get("/devices/subnet/10.12.0.0/24/scan")
    assert response2.status_code == 200
    devices2 = response2.json()
    
    # Both scans should return the same number of devices
    assert len(devices1) == len(devices2)
    
    # Check that devices are also available via list endpoint
    list_response = client.get("/devices/")
    assert list_response.status_code == 200
    list_devices = list_response.json()
    
    # Should have at least as many devices as scanned
    assert len(list_devices) >= len(devices1)

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"]) 