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
import sys
import logging

CLEAN_FIELDS = [
    'Category', 'Name', 'MAC address', 'Phone', 'Email', 'Password'
]

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filename='logs/app.log',
    filemode='a'
)
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)
logger = logging.getLogger(__name__)

class DeviceDiscovery:
    def __init__(self, clean_file: Optional[str] = None):
        self.clean_file = clean_file
        self.clean_mapping = self.load_clean_mapping(clean_file) if clean_file else {}

    def discover(self, subnet: str) -> List[Dict]:
        """
        Use nmap -sn -PR to scan the subnet and return a list of active hosts (ip, mac).
        """
        logger.info(f"Scanning subnet {subnet} with nmap...")
        
        # Use ARP scanning to get MAC addresses
        try:
            result = subprocess.run(
                ['sudo', 'nmap', '-sn', '-PR', subnet], 
                capture_output=True, text=True, timeout=120
            )
        except subprocess.TimeoutExpired:
            logger.error("Nmap scan timed out...")
            return []
        except FileNotFoundError:
            logger.warning("nmap not found, trying without sudo...")
            try:
                result = subprocess.run(
                    ['nmap', '-sn', '-PR', subnet], 
                    capture_output=True, text=True, timeout=120
                )
            except subprocess.TimeoutExpired:
                logger.error("Nmap scan timed out...")
                return []
        
        hosts = []
        current_ip = None
        current_mac = None
        
        logger.info(f"Nmap output:\n{result.stdout}")
        
        for line in result.stdout.splitlines():
            if line.startswith('Nmap scan report for'):
                # If we have a previous IP, add it to hosts
                if current_ip:
                    hosts.append({
                        'IP': current_ip, 
                        'MAC': current_mac if current_mac else 'Unknown'
                    })
                
                current_ip = line.split()[-1]
                current_mac = None
            elif 'MAC Address:' in line and current_ip:
                match = re.search(r'([0-9A-Fa-f:]{17})', line)
                if match:
                    current_mac = match.group(1).lower()
            elif 'MAC Address:' in line and current_ip:
                # Alternative pattern for MAC address
                match = re.search(r'([0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2})', line)
                if match:
                    current_mac = match.group(1).lower()
        
        # Add the last device if we have one
        if current_ip:
            hosts.append({
                'IP': current_ip, 
                'MAC': current_mac if current_mac else 'Unknown'
            })
        
        logger.info(f"Discovered {len(hosts)} hosts: {hosts}")
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
            mac = d['MAC']
            # Try to find device info in mapping
            info = mapping.get(mac, None) if mac != 'Unknown' else None
            
            if info:
                # Device found in clean mapping
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
                # Device not found in mapping or has unknown MAC
                identified.append({
                    'IP': d['IP'],
                    'Category': 'Unknown',
                    'Name': f"Device {d['IP']}",
                    'MAC': mac,
                    'Phone': 'Unknown',
                    'Email': 'Unknown',
                    'Password': 'Unknown'
                })
        
        logger.info(f"Identified {len(identified)} devices")
        return identified

if __name__ == '__main__':
    # Example usage
    clean_file = '../data/clean_devices.csv'
    subnet = '10.12.0.0/24'  # Change as needed
    dd = DeviceDiscovery(clean_file)
    devices = dd.discover(subnet)
    logger.info(f"Discovered devices: {devices}")
    identified = dd.identify(devices)
    logger.info(f"Identified devices: {identified}")

    # Save scan result
    scan_result_file = '../data/scan_result.csv'
    with open(scan_result_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['IP', 'MAC'])
        writer.writeheader()
        writer.writerows(devices)
    logger.info(f"Scan result saved to {scan_result_file}")

    # Save identified result (sorted by Category)
    identified_result_file = '../data/identified_result.csv'
    identified_sorted = sorted(identified, key=lambda x: x['Category'])
    with open(identified_result_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['IP', 'Category', 'Name', 'MAC', 'Phone', 'Email', 'Password'])
        writer.writeheader()
        writer.writerows(identified_sorted)
    logger.info(f"Identified result saved to {identified_result_file}")

 