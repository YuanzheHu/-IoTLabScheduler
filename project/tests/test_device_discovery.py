#!/usr/bin/env python3
"""
Test script for device discovery functionality
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from core.device_discovery import DeviceDiscovery

def test_device_discovery():
    """Test device discovery functionality"""
    print("Testing device discovery...")
    
    # Initialize device discovery
    clean_file = os.path.join(os.path.dirname(__file__), "data/clean_devices.csv")
    discovery = DeviceDiscovery(clean_file)
    
    # Test subnet scanning
    subnet = "10.12.0.0/24"
    print(f"Scanning subnet: {subnet}")
    
    try:
        # Discover devices
        devices = discovery.discover(subnet)
        print(f"Discovered {len(devices)} devices")
        
        # Identify devices
        identified = discovery.identify(devices)
        print(f"Identified {len(identified)} devices")
        
        # Print results
        for i, device in enumerate(identified):
            print(f"Device {i+1}:")
            print(f"  IP: {device['IP']}")
            print(f"  Category: {device['Category']}")
            print(f"  Name: {device['Name']}")
            print(f"  MAC: {device['MAC']}")
            print(f"  Phone: {device['Phone']}")
            print(f"  Email: {device['Email']}")
            print(f"  Password: {device['Password']}")
            print()
        
        return identified
        
    except Exception as e:
        print(f"Error during device discovery: {e}")
        return []

if __name__ == "__main__":
    test_device_discovery() 