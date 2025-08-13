#!/usr/bin/env python3
"""
Batch Port Scan Test - Using pytest framework
Get all online devices and perform batch port scanning
"""

import pytest
import requests
import json
import time
import concurrent.futures
from typing import List, Dict
from datetime import datetime

# ==================== Configuration Parameters ====================
API_BASE_URL = "http://localhost:8000"  # API base URL
SUBNET_TO_SCAN = "10.12.0.0/24"        # Subnet to scan
FAST_SCAN = True                         # Whether to use fast scan mode
MAX_WORKERS = 5                          # Maximum concurrent scan threads
SCAN_TIMEOUT = 120                       # Timeout for each port scan (seconds)
OS_SCAN_TIMEOUT = 180                    # Timeout for each OS scan (seconds)
OS_SCAN_PORTS = "22,80,443"             # Ports for OS fingerprinting
# ================================================

class TestBatchPortScan:
    """Batch port scan test class"""
    
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
            print(f"🔍 Starting scan for device: {device_name} ({device_ip})")
            
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
                        "protocol": port.get('protocol'),
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
                
                print(f"✅ {device_name} scan completed: {len(open_ports)} open ports, took {scan_duration}s")
                
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                scan_result.update({
                    "status": "failed",
                    "error": error_msg
                })
                print(f"❌ {device_name} scan failed: {error_msg}")
                
        except requests.exceptions.Timeout:
            scan_result.update({
                "status": "timeout",
                "error": f"Scan timeout ({SCAN_TIMEOUT} seconds)"
            })
            print(f"⏰ {device_name} scan timeout")
            
        except Exception as e:
            scan_result.update({
                "status": "error",
                "error": str(e)
            })
            print(f"❌ {device_name} scan error: {e}")
        
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
    
    def test_batch_port_scan_sequential(self):
        """Test: Sequential port scan on all online devices"""
        print(f"\n🚀 Starting sequential batch port scan test - {datetime.now()}")
        print(f"📋 Test configuration:")
        print(f"   Subnet: {SUBNET_TO_SCAN}")
        print(f"   Fast scan: {FAST_SCAN}")
        print(f"   Scan timeout: {SCAN_TIMEOUT} seconds")
        print(f"   Execution mode: Sequential scan")
        
        # 1. Get all online devices
        online_devices = self.scan_and_get_online_devices()
        
        if not online_devices:
            pytest.skip("No online devices found, skipping test")
        
        # 2. Scan each device sequentially
        scan_results = []
        total_start_time = time.time()
        
        for i, device in enumerate(online_devices, 1):
            print(f"\n📱 Scanning device {i}/{len(online_devices)}")
            result = self.port_scan_device(device)
            scan_results.append(result)
            
            # Brief pause between devices to avoid network congestion
            if i < len(online_devices):
                time.sleep(1)
        
        total_duration = round(time.time() - total_start_time, 2)
        
        # 3. Count results
        success_count = len([r for r in scan_results if r["status"] == "success"])
        failed_count = len([r for r in scan_results if r["status"] == "failed"])
        timeout_count = len([r for r in scan_results if r["status"] == "timeout"])
        error_count = len([r for r in scan_results if r["status"] == "error"])
        
        total_open_ports = sum(r.get("open_ports_count", 0) for r in scan_results)
        
        print(f"\n📊 Sequential batch port scan completed!")
        print(f"   Devices scanned: {len(online_devices)}")
        print(f"   Total duration: {total_duration} seconds")
        print(f"   Successful scans: {success_count}")
        print(f"   Failed scans: {failed_count}")
        print(f"   Timeout scans: {timeout_count}")
        print(f"   Error scans: {error_count}")
        print(f"   Total open ports found: {total_open_ports}")
        
        # 4. Save detailed results
        results_file = f"sequential_port_scan_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump({
                "test_config": {
                    "subnet": SUBNET_TO_SCAN,
                    "fast_scan": FAST_SCAN,
                    "scan_timeout": SCAN_TIMEOUT,
                    "execution_mode": "sequential",
                    "description": "Sequential port scan execution to avoid network congestion"
                },
                "test_summary": {
                    "test_timestamp": datetime.now().isoformat(),
                    "total_devices": len(online_devices),
                    "total_duration_sec": total_duration,
                    "success_count": success_count,
                    "failed_count": failed_count,
                    "timeout_count": timeout_count,
                    "error_count": error_count,
                    "total_open_ports": total_open_ports
                },
                "scan_results": scan_results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"   Detailed results saved to: {results_file}")
        
        # 5. Output open ports summary
        if total_open_ports > 0:
            print(f"\n🔓 Open ports summary:")
            for result in scan_results:
                if result.get("open_ports_count", 0) > 0:
                    device_name = result["device_name"]
                    device_ip = result["device_ip"]
                    open_ports = result["open_ports"]
                    print(f"   📱 {device_name} ({device_ip}):")
                    for port in open_ports[:5]:  # Only show first 5 ports
                        print(f"      - {port['port']}/{port['protocol']} ({port['service']})")
                    if len(open_ports) > 5:
                        print(f"      - ... and {len(open_ports) - 5} more ports")
        
        # 6. Assert test results
        assert success_count > 0, "Should successfully scan at least some devices"
        assert failed_count + timeout_count + error_count < len(online_devices) * 0.5, "Failure rate should not exceed 50%"
        
        print("✅ Sequential batch port scan test passed!")
    
    def test_batch_port_scan_parallel(self):
        """Test: Parallel port scan on all online devices"""
        print(f"\n🚀 Starting parallel batch port scan test - {datetime.now()}")
        print(f"📋 Test configuration:")
        print(f"   Subnet: {SUBNET_TO_SCAN}")
        print(f"   Fast scan: {FAST_SCAN}")
        print(f"   Scan timeout: {SCAN_TIMEOUT} seconds")
        print(f"   Max concurrent workers: {MAX_WORKERS}")
        print(f"   Execution mode: Parallel scan")
        
        # 1. Get all online devices
        online_devices = self.scan_and_get_online_devices()
        
        if not online_devices:
            pytest.skip("No online devices found, skipping test")
        
        # 2. Scan all devices in parallel
        scan_results = []
        total_start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Submit all scan tasks
            future_to_device = {
                executor.submit(self.port_scan_device, device): device 
                for device in online_devices
            }
            
            # Collect results
            for future in concurrent.futures.as_completed(future_to_device):
                device = future_to_device[future]
                try:
                    result = future.result()
                    scan_results.append(result)
                except Exception as e:
                    # If thread execution fails, create error result
                    error_result = {
                        "device_ip": device.get('ip_address'),
                        "device_name": device.get('hostname', 'Unknown Device'),
                        "device_mac": device.get('mac_address'),
                        "status": "thread_error",
                        "error": str(e),
                        "scan_duration": 0,
                        "open_ports": []
                    }
                    scan_results.append(error_result)
                    print(f"❌ Thread execution error: {e}")
        
        total_duration = round(time.time() - total_start_time, 2)
        
        # 3. Count results
        success_count = len([r for r in scan_results if r["status"] == "success"])
        failed_count = len([r for r in scan_results if r["status"] == "failed"])
        timeout_count = len([r for r in scan_results if r["status"] == "timeout"])
        error_count = len([r for r in scan_results if r["status"] in ["error", "thread_error"]])
        
        total_open_ports = sum(r.get("open_ports_count", 0) for r in scan_results)
        avg_scan_time = sum(r.get("scan_duration", 0) for r in scan_results) / len(scan_results) if scan_results else 0
        
        print(f"\n📊 Parallel batch port scan completed!")
        print(f"   Devices scanned: {len(online_devices)}")
        print(f"   Total duration: {total_duration} seconds")
        print(f"   Average single device scan time: {avg_scan_time:.2f} seconds")
        print(f"   Successful scans: {success_count}")
        print(f"   Failed scans: {failed_count}")
        print(f"   Timeout scans: {timeout_count}")
        print(f"   Error scans: {error_count}")
        print(f"   Total open ports found: {total_open_ports}")
        
        # 4. Save detailed results
        results_file = f"parallel_port_scan_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump({
                "test_config": {
                    "subnet": SUBNET_TO_SCAN,
                    "fast_scan": FAST_SCAN,
                    "scan_timeout": SCAN_TIMEOUT,
                    "max_workers": MAX_WORKERS,
                    "execution_mode": "parallel",
                    "description": "Parallel port scan execution for improved efficiency"
                },
                "test_summary": {
                    "test_timestamp": datetime.now().isoformat(),
                    "total_devices": len(online_devices),
                    "total_duration_sec": total_duration,
                    "avg_scan_duration_sec": round(avg_scan_time, 2),
                    "success_count": success_count,
                    "failed_count": failed_count,
                    "timeout_count": timeout_count,
                    "error_count": error_count,
                    "total_open_ports": total_open_ports
                },
                "scan_results": scan_results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"   Detailed results saved to: {results_file}")
        
        # 5. Output open ports summary
        if total_open_ports > 0:
            print(f"\n🔓 Open ports summary:")
            # Sort by number of open ports
            sorted_results = sorted(
                [r for r in scan_results if r.get("open_ports_count", 0) > 0],
                key=lambda x: x.get("open_ports_count", 0),
                reverse=True
            )
            
            for result in sorted_results[:10]:  # Only show top 10 devices
                device_name = result["device_name"]
                device_ip = result["device_ip"]
                open_ports = result["open_ports"]
                print(f"   📱 {device_name} ({device_ip}) - {len(open_ports)} open ports:")
                for port in open_ports[:3]:  # Only show first 3 ports
                    print(f"      - {port['port']}/{port['protocol']} ({port['service']})")
                if len(open_ports) > 3:
                    print(f"      - ... and {len(open_ports) - 3} more ports")
        
        # 6. Assert test results
        assert success_count > 0, "Should successfully scan at least some devices"
        assert failed_count + timeout_count + error_count < len(online_devices) * 0.5, "Failure rate should not exceed 50%"
        
        print("✅ Parallel batch port scan test passed!")
        print(f"⚡ Efficiency improvement: Parallel scan saves approximately {max(0, round((avg_scan_time * len(online_devices) - total_duration) / 60, 1))} minutes compared to sequential scan")

    def test_port_scan_specific_devices(self):
        """Test: Detailed port scan on specified devices"""
        print(f"\n🚀 Starting specified device port scan test - {datetime.now()}")
        
        # Get online devices
        online_devices = self.scan_and_get_online_devices()
        
        if not online_devices:
            pytest.skip("No online devices found, skipping test")
        
        # Select first 3 devices for detailed scan
        selected_devices = online_devices[:3]
        print(f"📱 Selected {len(selected_devices)} devices for detailed scan")
        
        detailed_results = []
        
        for device in selected_devices:
            device_ip = device.get('ip_address')
            device_name = device.get('hostname', 'Unknown Device')
            
            print(f"\n🔍 Detailed scan for device: {device_name} ({device_ip})")
            
            # Perform detailed scan (non-fast mode)
            try:
                scan_url = f"{API_BASE_URL}/devices/{device_ip}/portscan"
                params = {
                    "fast_scan": False,  # Detailed scan
                    "save_to_db": True
                }
                
                response = requests.get(scan_url, params=params, timeout=300)  # 5 minute timeout
                
                if response.status_code == 200:
                    scan_data = response.json()
                    ports = scan_data.get('ports', [])
                    
                    detailed_result = {
                        "device": device,
                        "scan_data": scan_data,
                        "total_ports": len(ports),
                        "open_ports": len([p for p in ports if p.get('state') == 'open']),
                        "closed_ports": len([p for p in ports if p.get('state') == 'closed']),
                        "filtered_ports": len([p for p in ports if p.get('state') == 'filtered'])
                    }
                    
                    detailed_results.append(detailed_result)
                    
                    print(f"✅ Detailed scan completed:")
                    print(f"   Total ports: {detailed_result['total_ports']}")
                    print(f"   Open ports: {detailed_result['open_ports']}")
                    print(f"   Closed ports: {detailed_result['closed_ports']}")
                    print(f"   Filtered ports: {detailed_result['filtered_ports']}")
                    
                else:
                    print(f"❌ Detailed scan failed: HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Detailed scan error: {e}")
        
        # Save detailed scan results
        if detailed_results:
            results_file = f"detailed_port_scan_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(results_file, "w", encoding="utf-8") as f:
                json.dump({
                    "test_timestamp": datetime.now().isoformat(),
                    "scan_type": "detailed",
                    "scanned_devices": len(detailed_results),
                    "results": detailed_results
                }, f, indent=2, ensure_ascii=False)
            
            print(f"\n📄 Detailed scan results saved to: {results_file}")
        
        assert len(detailed_results) > 0, "Should successfully complete at least one detailed scan"
        print("✅ Specified device detailed port scan test passed!")

    def test_batch_os_scan_sequential(self):
        """Test: Sequential OS scan on all online devices"""
        print(f"\n🚀 Starting sequential batch OS scan test - {datetime.now()}")
        print(f"📋 Test configuration:")
        print(f"   Subnet: {SUBNET_TO_SCAN}")
        print(f"   Fast scan: {FAST_SCAN}")
        print(f"   OS scan ports: {OS_SCAN_PORTS}")
        print(f"   OS scan timeout: {OS_SCAN_TIMEOUT} seconds")
        print(f"   Execution mode: Sequential scan")
        
        # 1. Get all online devices
        online_devices = self.scan_and_get_online_devices()
        
        if not online_devices:
            pytest.skip("No online devices found, skipping test")
        
        # Limit to first 5 devices for demo purposes
        selected_devices = online_devices[:5]
        print(f"📱 Selected {len(selected_devices)} devices for OS scanning")
        
        # 2. Scan each device sequentially
        scan_results = []
        total_start_time = time.time()
        
        for i, device in enumerate(selected_devices, 1):
            print(f"\n🖥️ OS scanning device {i}/{len(selected_devices)}")
            result = self.os_scan_device(device)
            scan_results.append(result)
            
            # Brief pause between devices to avoid network congestion
            if i < len(selected_devices):
                time.sleep(2)
        
        total_duration = round(time.time() - total_start_time, 2)
        
        # 3. Count results
        success_count = len([r for r in scan_results if r["status"] == "success"])
        failed_count = len([r for r in scan_results if r["status"] == "failed"])
        timeout_count = len([r for r in scan_results if r["status"] == "timeout"])
        error_count = len([r for r in scan_results if r["status"] == "error"])
        
        total_os_guesses = sum(len(r.get("os_guesses", [])) for r in scan_results)
        devices_with_vendor = len([r for r in scan_results if r.get("vendor")])
        
        print(f"\n📊 Sequential batch OS scan completed!")
        print(f"   Devices scanned: {len(selected_devices)}")
        print(f"   Total duration: {total_duration} seconds")
        print(f"   Successful scans: {success_count}")
        print(f"   Failed scans: {failed_count}")
        print(f"   Timeout scans: {timeout_count}")
        print(f"   Error scans: {error_count}")
        print(f"   Total OS guesses: {total_os_guesses}")
        print(f"   Devices with vendor info: {devices_with_vendor}")
        
        # 4. Save detailed results
        results_file = f"sequential_os_scan_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump({
                "test_config": {
                    "subnet": SUBNET_TO_SCAN,
                    "fast_scan": FAST_SCAN,
                    "os_scan_ports": OS_SCAN_PORTS,
                    "os_scan_timeout": OS_SCAN_TIMEOUT,
                    "execution_mode": "sequential",
                    "description": "Sequential OS scan execution to avoid network congestion"
                },
                "test_summary": {
                    "test_timestamp": datetime.now().isoformat(),
                    "total_devices": len(selected_devices),
                    "total_duration_sec": total_duration,
                    "success_count": success_count,
                    "failed_count": failed_count,
                    "timeout_count": timeout_count,
                    "error_count": error_count,
                    "total_os_guesses": total_os_guesses,
                    "devices_with_vendor": devices_with_vendor
                },
                "scan_results": scan_results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"   Detailed results saved to: {results_file}")
        
        # 5. Output OS scan summary
        if total_os_guesses > 0:
            print(f"\n🖥️ OS scan summary:")
            for result in scan_results:
                if result.get("os_guesses"):
                    device_name = result["device_name"]
                    device_ip = result["device_ip"]
                    os_guesses = result["os_guesses"]
                    vendor = result.get("vendor", "Unknown")
                    print(f"   📱 {device_name} ({device_ip}):")
                    print(f"      Vendor: {vendor}")
                    print(f"      OS Guesses: {', '.join(os_guesses[:3])}")
                    if len(os_guesses) > 3:
                        print(f"      ... and {len(os_guesses) - 3} more guesses")
        
        # 6. Assert test results
        print("✅ Sequential batch OS scan test completed!")

    def test_quick_system_check(self):
        """Quick system verification with minimal scanning (3 devices max)"""
        print("🚀 Quick System Check - Testing core functionality with minimal devices")
        
        # Get online devices
        online_devices = self.scan_and_get_online_devices()
        
        if not online_devices:
            pytest.skip("No online devices found for quick check")
        
        # Select maximum 3 devices for quick testing
        test_devices = online_devices[:3]
        print(f"📱 Selected {len(test_devices)} devices for quick check")
        
        success_count = 0
        for i, device in enumerate(test_devices, 1):
            device_name = device.get('hostname', 'Unknown')
            device_ip = device.get('ip_address')
            
            print(f"\n[{i}/{len(test_devices)}] Testing: {device_name} ({device_ip})")
            
            try:
                # Quick port scan
                port_result = self.port_scan_device(device)
                if port_result.get('status') == 'success':
                    print(f"   ✅ Port scan: {port_result.get('total_ports', 0)} ports")
                else:
                    print(f"   ❌ Port scan failed")
                    continue
                
                # Quick OS scan
                os_result = self.os_scan_device(device)
                if os_result.get('status') == 'success':
                    vendor = os_result.get('vendor', 'Unknown')
                    os_count = len(os_result.get('os_guesses', []))
                    print(f"   ✅ OS scan: vendor={vendor}, {os_count} OS guesses")
                    success_count += 1
                else:
                    print(f"   ❌ OS scan failed")
                    
            except Exception as e:
                print(f"   ❌ Error testing {device_name}: {e}")
        
        # Assert reasonable success
        success_rate = success_count / len(test_devices)
        print(f"\n📊 Quick check completed: {success_count}/{len(test_devices)} devices successful ({success_rate*100:.1f}%)")
        
        assert success_count > 0, "No devices passed the quick check"
        assert success_rate >= 0.5, f"Success rate too low: {success_rate*100:.1f}%"
        print("✅ Quick system check passed!")

    def test_combined_port_and_os_scan(self):
        """Test: Combined port scan and OS scan on selected online devices"""
        print(f"\n🚀 Starting combined port and OS scan test - {datetime.now()}")
        print(f"📋 Test configuration:")
        print(f"   Subnet: {SUBNET_TO_SCAN}")
        print(f"   Fast scan: {FAST_SCAN}")
        print(f"   Port scan timeout: {SCAN_TIMEOUT} seconds")
        print(f"   OS scan timeout: {OS_SCAN_TIMEOUT} seconds")
        print(f"   OS scan ports: {OS_SCAN_PORTS}")
        
        # 1. Get all online devices
        online_devices = self.scan_and_get_online_devices()
        
        if not online_devices:
            pytest.skip("No online devices found, skipping test")
        
        # Limit to first 3 devices for comprehensive testing
        selected_devices = online_devices[:3]
        print(f"📱 Selected {len(selected_devices)} devices for combined scanning")
        
        # 2. Perform both scans on each device
        combined_results = []
        total_start_time = time.time()
        
        for i, device in enumerate(selected_devices, 1):
            print(f"\n📱 Combined scanning device {i}/{len(selected_devices)}: {device.get('hostname', 'Unknown')}")
            
            # Port scan
            print(f"   🔍 Performing port scan...")
            port_result = self.port_scan_device(device)
            
            # OS scan
            print(f"   🖥️ Performing OS scan...")
            os_result = self.os_scan_device(device)
            
            # Combine results
            combined_result = {
                "device": device,
                "port_scan": port_result,
                "os_scan": os_result,
                "combined_duration": port_result.get("scan_duration", 0) + os_result.get("scan_duration", 0),
                "total_open_ports": port_result.get("open_ports_count", 0),
                "total_os_guesses": len(os_result.get("os_guesses", [])),
                "vendor": os_result.get("vendor"),
                "network_distance": os_result.get("network_distance"),
                "latency": os_result.get("latency")
            }
            
            combined_results.append(combined_result)
            
            # Brief pause between devices
            if i < len(selected_devices):
                time.sleep(3)
        
        total_duration = round(time.time() - total_start_time, 2)
        
        # 3. Calculate combined statistics
        port_success = len([r for r in combined_results if r["port_scan"]["status"] == "success"])
        os_success = len([r for r in combined_results if r["os_scan"]["status"] == "success"])
        
        total_open_ports = sum(r["total_open_ports"] for r in combined_results)
        total_os_guesses = sum(r["total_os_guesses"] for r in combined_results)
        devices_with_vendor = len([r for r in combined_results if r["vendor"]])
        
        print(f"\n📊 Combined scan completed!")
        print(f"   Devices scanned: {len(selected_devices)}")
        print(f"   Total duration: {total_duration} seconds")
        print(f"   Port scan success: {port_success}/{len(selected_devices)}")
        print(f"   OS scan success: {os_success}/{len(selected_devices)}")
        print(f"   Total open ports found: {total_open_ports}")
        print(f"   Total OS guesses: {total_os_guesses}")
        print(f"   Devices with vendor info: {devices_with_vendor}")
        
        # 4. Save combined results
        results_file = f"combined_port_os_scan_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump({
                "test_config": {
                    "subnet": SUBNET_TO_SCAN,
                    "fast_scan": FAST_SCAN,
                    "port_scan_timeout": SCAN_TIMEOUT,
                    "os_scan_timeout": OS_SCAN_TIMEOUT,
                    "os_scan_ports": OS_SCAN_PORTS,
                    "description": "Combined port scan and OS scan for comprehensive device analysis"
                },
                "test_summary": {
                    "test_timestamp": datetime.now().isoformat(),
                    "total_devices": len(selected_devices),
                    "total_duration_sec": total_duration,
                    "port_scan_success": port_success,
                    "os_scan_success": os_success,
                    "total_open_ports": total_open_ports,
                    "total_os_guesses": total_os_guesses,
                    "devices_with_vendor": devices_with_vendor
                },
                "combined_results": combined_results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"   Combined results saved to: {results_file}")
        
        # 5. Output comprehensive summary
        print(f"\n🔍 Comprehensive device analysis:")
        for result in combined_results:
            device_name = result["device"].get('hostname', 'Unknown')
            device_ip = result["device"].get('ip_address')
            open_ports = result["total_open_ports"]
            os_guesses = result["total_os_guesses"]
            vendor = result["vendor"] or "Unknown"
            
            print(f"   📱 {device_name} ({device_ip}):")
            print(f"      Open ports: {open_ports}")
            print(f"      OS guesses: {os_guesses}")
            print(f"      Vendor: {vendor}")
        
        print("✅ Combined port and OS scan test completed!")

# If running this file directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
