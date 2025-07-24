"""
Device Discovery Module
"""

import subprocess
import re
import csv
import os
from typing import List, Dict, Optional

class DeviceDiscovery:
    def __init__(self, devices_txt: Optional[str] = None):
        """Initializes DeviceDiscovery with a device mapping file.

        Args:
            devices_txt: Path to devices.txt file.
        """
        self.devices_txt = devices_txt
        self.mac_name_mapping = self.load_devices_txt(devices_txt) if devices_txt else {}

    @staticmethod
    def normalize_mac(mac: str) -> str:
        """Normalize MAC address to xx:xx:xx:xx:xx:xx format.

        Args:
            mac: MAC address string.
        Returns:
            Normalized MAC address string.
        """
        if not mac:
            return ''
        
        # Handle MAC addresses that might have 'x' prefix (from devices.txt)
        mac = mac.replace('x', '0')
        
        # Split by colon and ensure each part has 2 digits
        parts = mac.lower().split(':')
        normalized_parts = []
        
        for part in parts:
            # Remove any non-hex characters and ensure 2-digit format
            clean_part = ''.join(c for c in part if c in '0123456789abcdef')
            if len(clean_part) == 1:
                normalized_parts.append('0' + clean_part)
            elif len(clean_part) == 2:
                normalized_parts.append(clean_part)
            else:
                # If more than 2 characters, take the last 2
                normalized_parts.append(clean_part[-2:])
        
        return ':'.join(normalized_parts)

    @staticmethod
    def load_devices_txt(devices_txt: str) -> Dict[str, str]:
        """Load device MAC-to-name mapping from devices.txt.

        Args:
            devices_txt: Path to devices.txt file.
        Returns:
            Dictionary mapping normalized MAC to device name.
        """
        mapping = {}
        if not devices_txt or not os.path.exists(devices_txt):
            return mapping
        with open(devices_txt, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    mac = DeviceDiscovery.normalize_mac(parts[0])
                    name = ' '.join(parts[1:])
                    mapping[mac] = name
        return mapping

    def discover(self, subnet: str) -> List[Dict]:
        """Scan the subnet and return a list of active hosts with IP and MAC.

        Args:
            subnet: Subnet to scan (e.g., '10.12.0.0/24').
        Returns:
            List of dicts with 'IP' and 'MAC' keys.
        """
        try:
            result = subprocess.run(
                ['sudo', 'nmap', '-sn', '-PR', subnet], 
                capture_output=True, text=True, timeout=120
            )
        except subprocess.TimeoutExpired:
            return []
        except FileNotFoundError:
            try:
                result = subprocess.run(
                    ['nmap', '-sn', '-PR', subnet], 
                    capture_output=True, text=True, timeout=120
                )
            except subprocess.TimeoutExpired:
                return []
        
        hosts = []
        current_ip = None
        current_mac = None
        
        for line in result.stdout.splitlines():
            if line.startswith('Nmap scan report for'):
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
        if current_ip:
            hosts.append({
                'IP': current_ip, 
                'MAC': current_mac if current_mac else 'Unknown'
            })
        return hosts

    def identify(self, scanned_devices: List[Dict]) -> List[Dict]:
        """Identify devices by matching scanned MACs to known devices.

        Args:
            scanned_devices: List of dicts with 'IP' and 'MAC'.
        Returns:
            List of dicts with 'MAC', 'Name', 'IP', 'Status'. Online devices first.
        """
        mapping = self.mac_name_mapping
        scanned_mac_ip = {self.normalize_mac(d['MAC']): d['IP'] for d in scanned_devices if d['MAC'] != 'Unknown'}
        online = []
        offline = []
        for mac, name in mapping.items():
            if mac in scanned_mac_ip:
                online.append({
                    'MAC': mac,
                    'Name': name,
                    'IP': scanned_mac_ip[mac],
                    'Status': 'online'
                })
            else:
                offline.append({
                    'MAC': mac,
                    'Name': name,
                    'IP': '',
                    'Status': 'offline'
                })
        for mac, ip in scanned_mac_ip.items():
            if mac not in mapping:
                online.append({
                    'MAC': mac,
                    'Name': 'Unknown Device',
                    'IP': ip,
                    'Status': 'online'
                })
        return online + offline

if __name__ == '__main__':
    devices_txt = '../data/devices.txt'
    subnet = '10.12.0.0/24'  # Change as needed
    dd = DeviceDiscovery(devices_txt)
    devices = dd.discover(subnet)
    identified = dd.identify(devices)
    identified_result_file = '../data/identified_devices_status.csv'
    with open(identified_result_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['MAC', 'Name', 'IP', 'Status'])
        writer.writeheader()
        writer.writerows(identified)