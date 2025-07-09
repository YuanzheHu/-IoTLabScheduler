"""
Device Discovery Module

This module provides functionality for:
- Network device scanning
- Device fingerprinting
- Status monitoring
"""

import subprocess
import re
import csv
from typing import List, Dict, Optional

CLEAN_FIELDS = [
    'Category', 'Name', 'MAC address', 'Phone', 'Email', 'Password'
]

class DeviceDiscovery:
    def __init__(self, clean_file: Optional[str] = None):
        self.clean_file = clean_file
        self.clean_mapping = self.load_clean_mapping(clean_file) if clean_file else {}

    def discover(self, subnet: str) -> List[Dict]:
        """
        Use nmap -sn to scan the subnet and return a list of active hosts (ip, mac).
        """
        print(f"Scanning subnet {subnet} with nmap...")
        result = subprocess.run(
            ['nmap', '-sn', subnet], capture_output=True, text=True
        )
        hosts = []
        current_ip = None
        for line in result.stdout.splitlines():
            if line.startswith('Nmap scan report for'):
                current_ip = line.split()[-1]
            elif 'MAC Address:' in line and current_ip:
                match = re.search(r'([0-9A-Fa-f:]{17})', line)
                if match:
                    mac = match.group(1).lower()
                    hosts.append({'IP': current_ip, 'MAC': mac})
                current_ip = None
        return hosts

    @staticmethod
    def load_devices(input_file: str) -> List[Dict]:
        """
        Read each row's IP and MAC from the CSV file.
        """
        devices = []
        with open(input_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ip = row.get('IP') or row.get('Ip') or row.get('ip')
                mac = row.get('MAC') or row.get('Mac') or row.get('mac')
                if ip and mac:
                    devices.append({'IP': ip, 'MAC': mac.lower()})
        return devices

    @staticmethod
    def load_clean_mapping(clean_file: Optional[str]) -> Dict[str, Dict]:
        """
        Read MAC-to-all-fields mapping from clean_devices.csv.
        """
        if not clean_file:
            return {}
            
        mapping = {}
        with open(clean_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                mac = row.get('MAC address')
                if mac:
                    mapping[mac.strip().lower()] = {field: row.get(field, 'Unknown').strip() for field in CLEAN_FIELDS}
        return mapping

    def identify(self, devices: List[Dict]) -> List[Dict]:
        """
        Fully match MAC addresses with clean_devices.csv, return identified list with all fields.
        """
        mapping = self.clean_mapping
        identified = []
        for d in devices:
            info = mapping.get(d['MAC'], None)
            if info:
                identified.append({
                    'IP': d['IP'],
                    'Category': info['Category'],
                    'Name': info['Name'],
                    'MAC': info['MAC address'],
                    'Phone': info['Phone'],
                    'Email': info['Email'],
                    'Password': info['Password']
                })
            else:
                identified.append({
                    'IP': d['IP'],
                    'Category': 'Unknown',
                    'Name': 'Unknown',
                    'MAC': d['MAC'],
                    'Phone': 'Unknown',
                    'Email': 'Unknown',
                    'Password': 'Unknown'
                })
        return identified

if __name__ == '__main__':
    # Example usage
    clean_file = '../data/clean_devices.csv'
    subnet = '10.12.0.0/24'  # Change as needed
    dd = DeviceDiscovery(clean_file)
    devices = dd.discover(subnet)
    print(f"Discovered devices: {devices}")
    identified = dd.identify(devices)
    print(f"Identified devices: {identified}")

    # Save scan result
    scan_result_file = '../data/scan_result.csv'
    with open(scan_result_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['IP', 'MAC'])
        writer.writeheader()
        writer.writerows(devices)
    print(f"Scan result saved to {scan_result_file}")

    # Save identified result (sorted by Category)
    identified_result_file = '../data/identified_result.csv'
    identified_sorted = sorted(identified, key=lambda x: x['Category'])
    with open(identified_result_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['IP', 'Category', 'Name', 'MAC', 'Phone', 'Email', 'Password'])
        writer.writeheader()
        writer.writerows(identified_sorted)
    print(f"Identified result saved to {identified_result_file}")

 