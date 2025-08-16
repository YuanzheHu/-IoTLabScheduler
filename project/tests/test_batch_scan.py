#!/usr/bin/env python3
"""
Batch Scanning Test - Three Essential Test Cases
- Subnet Discovery
- Concurrent OS Scan  
- Concurrent Port Scan
"""

import pytest
import requests
import json
import time
import concurrent.futures
import os
from typing import List, Dict
from datetime import datetime

# ==================== Configuration Parameters ====================
API_BASE_URL = "http://localhost:8000"  # API base URL
SUBNET_TO_SCAN = "10.12.0.0/24"        # Subnet to scan
FAST_SCAN = False                       # Whether to use fast scan mode
MAX_WORKERS = 5                         # Maximum concurrent scan threads
SCAN_TIMEOUT = 120                      # Timeout for each port scan (seconds)
OS_SCAN_TIMEOUT = 180                   # Timeout for each OS scan (seconds)
OS_SCAN_PORTS = "22,80,443"             # Ports for OS fingerprinting
# ================================================

class TestBatchPortScan:
    """Batch scanning test class with three main test cases"""
    
    def scan_and_get_online_devices(self) -> List[Dict]:
        """Scan subnet and get all online devices"""
        try:
            # 1. Scan subnet
            print(f"🔍 Scanning subnet: {SUBNET_TO_SCAN}")
            scan_response = requests.post(
                f"{API_BASE_URL}/devices/scan",
                json={"subnet": SUBNET_TO_SCAN},
                timeout=300
            )
            scan_response.raise_for_status()
            print(f"✅ Subnet scan completed")
            
            # 2. Get all devices (including online status)
            devices_response = requests.get(f"{API_BASE_URL}/devices/", timeout=30)
            devices_response.raise_for_status()
            devices = devices_response.json()
            
            # 3. Filter online devices
            online_devices = [
                device for device in devices 
                if (device.get("status") == "online" and 
                    device.get("ip_address") and
                    device.get("ip_address").strip() != "")
            ]
            
            print(f"✅ Found {len(online_devices)} online devices")
            
            # 4. Display all online devices
            for i, device in enumerate(online_devices, 1):
                hostname = device.get('hostname', 'Unknown Device')
                ip_address = device.get('ip_address')
                mac_address = device.get('mac_address')
                print(f"   {i}. {hostname} ({ip_address}) - {mac_address}")
            
            return online_devices
            
        except requests.RequestException as e:
            pytest.fail(f"Failed to get online devices: {e}")
    
    def port_scan_device(self, device: Dict) -> Dict:
        """Perform port scan on a single device"""
        device_ip = device.get('ip_address')
        device_name = device.get('hostname', 'Unknown Device')
        device_mac = device.get('mac_address')
        
        scan_result = {
            "device_ip": device_ip,
            "device_name": device_name,
            "device_mac": device_mac,
            "scan_start_time": datetime.now().isoformat(),
            "status": "pending",
            "scan_duration": 0,
            "open_ports": [],
            "total_ports_found": 0,
            "error": None
        }
        
        try:
            print(f"🔍 Starting port scan for device: {device_name} ({device_ip})")
            
            # Call port scan API
            scan_url = f"{API_BASE_URL}/devices/{device_ip}/portscan"
            params = {
                "fast_scan": FAST_SCAN,
                "save_to_db": True
            }
            
            start_time = time.time()
            response = requests.get(scan_url, params=params, timeout=SCAN_TIMEOUT)
            end_time = time.time()
            
            scan_duration = round(end_time - start_time, 2)
            scan_result["scan_duration"] = scan_duration
            scan_result["scan_end_time"] = datetime.now().isoformat()
            
            if response.status_code == 200:
                scan_data = response.json()
                
                # Extract port information
                ports = scan_data.get('ports', [])
                open_ports = [
                    {
                        "port": port.get('port'),
                        "state": port.get('state'),
                        "service": port.get('service', 'unknown')
                    }
                    for port in ports 
                    if port.get('state') == 'open'
                ]
                
                scan_result.update({
                    "status": "success",
                    "open_ports": open_ports,
                    "total_ports_found": len(ports),
                    "open_ports_count": len(open_ports),
                    "scan_command": scan_data.get('command', ''),
                    "raw_output": scan_data.get('raw_output', '')[:500]  # Limit output length
                })
                
                print(f"✅ {device_name} port scan completed: {len(open_ports)} open ports, took {scan_duration}s")
                
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                scan_result.update({
                    "status": "failed",
                    "error": error_msg
                })
                print(f"❌ {device_name} port scan failed: {error_msg}")
                
        except requests.exceptions.Timeout:
            scan_result.update({
                "status": "timeout",
                "error": f"Port scan timeout ({SCAN_TIMEOUT} seconds)"
            })
            print(f"⏰ {device_name} port scan timeout")
            
        except Exception as e:
            scan_result.update({
                "status": "error",
                "error": str(e)
            })
            print(f"❌ {device_name} port scan error: {e}")
        
        return scan_result

    def os_scan_device(self, device: Dict) -> Dict:
        """Perform OS scan on a single device"""
        device_ip = device.get('ip_address')
        device_name = device.get('hostname', 'Unknown Device')
        device_mac = device.get('mac_address')
        
        scan_result = {
            "device_ip": device_ip,
            "device_name": device_name,
            "device_mac": device_mac,
            "scan_start_time": datetime.now().isoformat(),
            "status": "pending",
            "scan_duration": 0,
            "os_guesses": [],
            "os_details": {},
            "vendor": None,
            "network_distance": None,
            "latency": None,
            "error": None
        }
        
        try:
            print(f"🖥️ Starting OS scan for device: {device_name} ({device_ip})")
            
            # Call OS scan API
            scan_url = f"{API_BASE_URL}/devices/{device_ip}/oscan"
            params = {
                "ports": OS_SCAN_PORTS,
                "fast_scan": FAST_SCAN,
                "save_to_db": True
            }
            
            start_time = time.time()
            response = requests.get(scan_url, params=params, timeout=OS_SCAN_TIMEOUT)
            end_time = time.time()
            
            scan_duration = round(end_time - start_time, 2)
            scan_result["scan_duration"] = scan_duration
            scan_result["scan_end_time"] = datetime.now().isoformat()
            
            if response.status_code == 200:
                scan_data = response.json()
                
                # Extract OS information
                scan_result.update({
                    "status": "success",
                    "os_guesses": scan_data.get('os_guesses', []),
                    "os_details": scan_data.get('os_details', {}),
                    "vendor": scan_data.get('vendor'),
                    "network_distance": scan_data.get('network_distance'),
                    "latency": scan_data.get('latency'),
                    "mac_address": scan_data.get('mac_address'),
                    "host_status": scan_data.get('host_status'),
                    "scan_summary": scan_data.get('scan_summary', {}),
                    "raw_output": scan_data.get('raw_output', '')[:500]  # Limit output length
                })
                
                os_guess_count = len(scan_data.get('os_guesses', []))
                print(f"✅ {device_name} OS scan completed: {os_guess_count} OS guesses, took {scan_duration}s")
                
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                scan_result.update({
                    "status": "failed",
                    "error": error_msg
                })
                print(f"❌ {device_name} OS scan failed: {error_msg}")
                
        except requests.exceptions.Timeout:
            scan_result.update({
                "status": "timeout",
                "error": f"OS scan timeout ({OS_SCAN_TIMEOUT} seconds)"
            })
            print(f"⏰ {device_name} OS scan timeout")
            
        except Exception as e:
            scan_result.update({
                "status": "error",
                "error": str(e)
            })
            print(f"❌ {device_name} OS scan error: {e}")
        
        return scan_result
    
    def test_subnet_discovery(self):
        """Test Case 1: Subnet Discovery - Scan network segment and discover devices"""
        print(f"\n🚀 Test Case 1: Subnet Discovery - {datetime.now()}")
        print("=" * 60)
        print(f"📋 Configuration:")
        print(f"   Subnet to scan: {SUBNET_TO_SCAN}")
        print(f"   API endpoint: {API_BASE_URL}")
        print("=" * 60)
        
        # Ensure output directory exists
        output_dir = "project/test"
        os.makedirs(output_dir, exist_ok=True)
        
        start_time = time.time()
        
        try:
            online_devices = self.scan_and_get_online_devices()
            discovery_duration = time.time() - start_time
            
            if not online_devices:
                pytest.skip("No online devices found during subnet discovery")
            
            print(f"\n📊 Discovery Results:")
            print(f"   ✅ Devices discovered: {len(online_devices)}")
            print(f"   ⏱️  Discovery time: {discovery_duration:.2f} seconds")
            
            # Save discovery results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            discovery_file = os.path.join(output_dir, f"subnet_discovery_{timestamp}.json")
            
            discovery_data = {
                "test_metadata": {
                    "test_name": "Subnet Discovery",
                    "execution_timestamp": datetime.now().isoformat(),
                    "subnet_scanned": SUBNET_TO_SCAN,
                    "discovery_duration_sec": round(discovery_duration, 2)
                },
                "discovery_results": {
                    "total_devices_found": len(online_devices),
                    "devices": [
                        {
                            "hostname": device.get('hostname', 'Unknown'),
                            "ip_address": device.get('ip_address'),
                            "mac_address": device.get('mac_address'),
                            "status": device.get('status')
                        }
                        for device in online_devices
                    ]
                }
            }
            
            with open(discovery_file, "w", encoding="utf-8") as f:
                json.dump(discovery_data, f, indent=2, ensure_ascii=False)
            
            print(f"   📄 Results saved to: {os.path.basename(discovery_file)}")
            
            # Test assertions
            assert len(online_devices) > 0, "Should discover at least one device"
            print(f"   ✅ Test passed: {len(online_devices)} devices discovered")
            
            return online_devices
            
        except Exception as e:
            pytest.fail(f"Subnet discovery failed: {e}")

    def test_concurrent_os_scan(self):
        """Test Case 2: Concurrent OS Scan - Perform OS fingerprinting on online devices"""
        print(f"\n🚀 Test Case 2: Concurrent OS Scan - {datetime.now()}")
        print("=" * 60)
        print(f"📋 Configuration:")
        print(f"   Fast scan mode: {FAST_SCAN}")
        print(f"   OS scan timeout: {OS_SCAN_TIMEOUT} seconds")
        print(f"   OS scan ports: {OS_SCAN_PORTS}")
        print(f"   Max concurrent workers: {MAX_WORKERS}")
        print("=" * 60)
        
        # Ensure output directory exists
        output_dir = "project/test"
        os.makedirs(output_dir, exist_ok=True)
        
        # Get online devices
        online_devices = self.scan_and_get_online_devices()
        if not online_devices:
            pytest.skip("No online devices found for OS scanning")
        
        print(f"📱 Performing OS scan on {len(online_devices)} devices")
        
        start_time = time.time()
        os_results = []
        
        # Concurrent OS scanning
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            print(f"📤 Submitting {len(online_devices)} OS scan tasks...")
            
            future_to_device = {
                executor.submit(self.os_scan_device, device): device 
                for device in online_devices
            }
            
            for i, future in enumerate(concurrent.futures.as_completed(future_to_device), 1):
                device = future_to_device[future]
                try:
                    result = future.result()
                    os_results.append(result)
                    print(f"✅ OS scan completed {i}/{len(online_devices)}: {device.get('hostname', 'Unknown')}")
                except Exception as e:
                    error_result = {
                        "device_ip": device.get('ip_address'),
                        "device_name": device.get('hostname', 'Unknown'),
                        "status": "error",
                        "error": str(e),
                        "scan_duration": 0,
                        "os_guesses": [],
                        "vendor": None
                    }
                    os_results.append(error_result)
                    print(f"❌ OS scan failed {i}/{len(online_devices)}: {device.get('hostname', 'Unknown')}")
        
        scan_duration = time.time() - start_time
        
        # Calculate statistics
        success_count = len([r for r in os_results if r["status"] == "success"])
        failed_count = len([r for r in os_results if r["status"] != "success"])
        total_os_guesses = sum(len(r.get("os_guesses", [])) for r in os_results)
        devices_with_vendor = len([r for r in os_results if r.get("vendor")])
        
        print(f"\n📊 OS Scan Results:")
        print(f"   ✅ Successful scans: {success_count}/{len(online_devices)}")
        print(f"   ❌ Failed scans: {failed_count}")
        print(f"   🖥️  Total OS guesses: {total_os_guesses}")
        print(f"   🏭 Devices with vendor info: {devices_with_vendor}")
        print(f"   ⏱️  Total scan time: {scan_duration:.2f} seconds")
        
        # Save OS scan results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        os_scan_file = os.path.join(output_dir, f"concurrent_os_scan_{timestamp}.json")
        
        os_scan_data = {
            "test_metadata": {
                "test_name": "Concurrent OS Scan",
                "execution_timestamp": datetime.now().isoformat(),
                "scan_duration_sec": round(scan_duration, 2),
                "fast_scan_mode": FAST_SCAN
            },
            "scan_configuration": {
                "os_scan_timeout": OS_SCAN_TIMEOUT,
                "os_scan_ports": OS_SCAN_PORTS,
                "max_concurrent_workers": MAX_WORKERS
            },
            "scan_statistics": {
                "total_devices": len(online_devices),
                "successful_scans": success_count,
                "failed_scans": failed_count,
                "success_rate": round((success_count / len(online_devices)) * 100, 2),
                "total_os_guesses": total_os_guesses,
                "devices_with_vendor": devices_with_vendor
            },
            "os_scan_results": os_results
        }
        
        with open(os_scan_file, "w", encoding="utf-8") as f:
            json.dump(os_scan_data, f, indent=2, ensure_ascii=False)
        
        print(f"   📄 Results saved to: {os.path.basename(os_scan_file)}")
        
        # Display top vendor information
        if devices_with_vendor > 0:
            print(f"\n🏭 Vendor Information:")
            vendor_stats = {}
            for result in os_results:
                vendor = result.get("vendor")
                if vendor and vendor != "Unknown":
                    vendor_stats[vendor] = vendor_stats.get(vendor, 0) + 1
            
            for vendor, count in sorted(vendor_stats.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"   • {vendor}: {count} devices")
        
        # Test assertions
        assert success_count > 0, "Should successfully complete at least some OS scans"
        success_rate = success_count / len(online_devices)
        assert success_rate >= 0.3, f"OS scan success rate too low: {success_rate*100:.1f}%"
        print(f"   ✅ Test passed: {success_count} successful OS scans")

    def test_concurrent_port_scan(self):
        """Test Case 3: Concurrent Port Scan - Perform port scanning on online devices"""
        print(f"\n🚀 Test Case 3: Concurrent Port Scan - {datetime.now()}")
        print("=" * 60)
        print(f"📋 Configuration:")
        print(f"   Fast scan mode: {FAST_SCAN}")
        print(f"   Port scan timeout: {SCAN_TIMEOUT} seconds")
        print(f"   Max concurrent workers: {MAX_WORKERS}")
        print("=" * 60)
        
        # Ensure output directory exists
        output_dir = "project/test"
        os.makedirs(output_dir, exist_ok=True)
        
        # Get online devices
        online_devices = self.scan_and_get_online_devices()
        if not online_devices:
            pytest.skip("No online devices found for port scanning")
        
        print(f"📱 Performing port scan on {len(online_devices)} devices")
        
        start_time = time.time()
        port_results = []
        
        # Concurrent port scanning
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            print(f"📤 Submitting {len(online_devices)} port scan tasks...")
            
            future_to_device = {
                executor.submit(self.port_scan_device, device): device 
                for device in online_devices
            }
            
            for i, future in enumerate(concurrent.futures.as_completed(future_to_device), 1):
                device = future_to_device[future]
                try:
                    result = future.result()
                    port_results.append(result)
                    print(f"✅ Port scan completed {i}/{len(online_devices)}: {device.get('hostname', 'Unknown')}")
                except Exception as e:
                    error_result = {
                        "device_ip": device.get('ip_address'),
                        "device_name": device.get('hostname', 'Unknown'),
                        "status": "error",
                        "error": str(e),
                        "scan_duration": 0,
                        "open_ports": [],
                        "total_ports_found": 0
                    }
                    port_results.append(error_result)
                    print(f"❌ Port scan failed {i}/{len(online_devices)}: {device.get('hostname', 'Unknown')}")
        
        scan_duration = time.time() - start_time
        
        # Calculate statistics
        success_count = len([r for r in port_results if r["status"] == "success"])
        failed_count = len([r for r in port_results if r["status"] != "success"])
        total_open_ports = sum(r.get("open_ports_count", 0) for r in port_results)
        devices_with_open_ports = len([r for r in port_results if r.get("open_ports_count", 0) > 0])
        total_ports_scanned = sum(r.get("total_ports_found", 0) for r in port_results)
        
        print(f"\n📊 Port Scan Results:")
        print(f"   ✅ Successful scans: {success_count}/{len(online_devices)}")
        print(f"   ❌ Failed scans: {failed_count}")
        print(f"   🔓 Total open ports: {total_open_ports}")
        print(f"   📊 Devices with open ports: {devices_with_open_ports}")
        print(f"   🔍 Total ports scanned: {total_ports_scanned}")
        print(f"   ⏱️  Total scan time: {scan_duration:.2f} seconds")
        
        # Save port scan results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        port_scan_file = os.path.join(output_dir, f"concurrent_port_scan_{timestamp}.json")
        
        port_scan_data = {
            "test_metadata": {
                "test_name": "Concurrent Port Scan",
                "execution_timestamp": datetime.now().isoformat(),
                "scan_duration_sec": round(scan_duration, 2),
                "fast_scan_mode": FAST_SCAN
            },
            "scan_configuration": {
                "port_scan_timeout": SCAN_TIMEOUT,
                "max_concurrent_workers": MAX_WORKERS
            },
            "scan_statistics": {
                "total_devices": len(online_devices),
                "successful_scans": success_count,
                "failed_scans": failed_count,
                "success_rate": round((success_count / len(online_devices)) * 100, 2),
                "total_open_ports": total_open_ports,
                "devices_with_open_ports": devices_with_open_ports,
                "total_ports_scanned": total_ports_scanned
            },
            "port_scan_results": port_results
        }
        
        with open(port_scan_file, "w", encoding="utf-8") as f:
            json.dump(port_scan_data, f, indent=2, ensure_ascii=False)
        
        print(f"   📄 Results saved to: {os.path.basename(port_scan_file)}")
        
        # Display security findings
        if devices_with_open_ports > 0:
            print(f"\n🔓 Security Findings:")
            security_risks = sorted(
                [r for r in port_results if r.get("open_ports_count", 0) > 0],
                key=lambda x: x.get("open_ports_count", 0),
                reverse=True
            )[:5]  # Top 5 devices with most open ports
            
            for i, result in enumerate(security_risks, 1):
                device_name = result["device_name"]
                device_ip = result["device_ip"]
                open_ports_count = result.get("open_ports_count", 0)
                print(f"   {i}. {device_name} ({device_ip}): {open_ports_count} open ports")
        
        # Test assertions
        assert success_count > 0, "Should successfully complete at least some port scans"
        success_rate = success_count / len(online_devices)
        assert success_rate >= 0.5, f"Port scan success rate too low: {success_rate*100:.1f}%"
        print(f"   ✅ Test passed: {success_count} successful port scans")

# If running this file directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
