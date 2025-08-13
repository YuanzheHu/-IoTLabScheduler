#!/usr/bin/env python3
"""
System Verification Test
Comprehensive test to verify all system components are working correctly
Compatible with pytest framework
"""

import pytest
import requests
import json
import time
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:8000"
STREAMLIT_URL = "http://localhost:8501"
SUBNET = "10.12.0.0/24"

class SystemVerificationTest:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": []
        }
    
    def log_test(self, test_name, status, message="", data=None):
        """Log test result"""
        result = {
            "test": test_name,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        if data:
            result["data"] = data
        
        self.results["tests"].append(result)
        
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_icon} {test_name}: {message}")
        
        return status == "PASS"
    
    def test_api_health(self):
        """Test 1: API Health Check"""
        try:
            response = requests.get(f"{API_BASE_URL}/health", timeout=10)
            if response.status_code == 200:
                return self.log_test("API Health", "PASS", "API is responding")
            else:
                return self.log_test("API Health", "FAIL", f"HTTP {response.status_code}")
        except Exception as e:
            return self.log_test("API Health", "FAIL", str(e))
    
    def test_streamlit_health(self):
        """Test 2: Streamlit Health Check"""
        try:
            response = requests.get(f"{STREAMLIT_URL}/health", timeout=10)
            return self.log_test("Streamlit Health", "PASS", "Streamlit is responding")
        except Exception as e:
            # Streamlit might not have a health endpoint, check main page
            try:
                response = requests.get(STREAMLIT_URL, timeout=10)
                if response.status_code == 200:
                    return self.log_test("Streamlit Health", "PASS", "Streamlit is accessible")
                else:
                    return self.log_test("Streamlit Health", "FAIL", f"HTTP {response.status_code}")
            except Exception as e2:
                return self.log_test("Streamlit Health", "FAIL", str(e2))
    
    def test_database_schema(self):
        """Test 3: Database Schema Verification"""
        try:
            # Test devices endpoint
            response = requests.get(f"{API_BASE_URL}/devices/", timeout=30)
            if response.status_code == 200:
                devices = response.json()
                device_count = len(devices)
                online_count = len([d for d in devices if d.get("status") == "online"])
                return self.log_test("Database Schema", "PASS", 
                                   f"{device_count} devices found ({online_count} online)")
            else:
                return self.log_test("Database Schema", "FAIL", f"HTTP {response.status_code}")
        except Exception as e:
            return self.log_test("Database Schema", "FAIL", str(e))
    
    def test_network_discovery(self):
        """Test 4: Network Discovery Function"""
        try:
            response = requests.post(
                f"{API_BASE_URL}/devices/scan",
                json={"subnet": SUBNET},
                timeout=120
            )
            if response.status_code == 200:
                devices = response.json()
                total = len(devices)
                online = len([d for d in devices if d.get("status") == "online"])
                offline = len([d for d in devices if d.get("status") == "offline"])
                return self.log_test("Network Discovery", "PASS", 
                                   f"Discovered {total} devices ({online} online, {offline} offline)")
            else:
                return self.log_test("Network Discovery", "FAIL", f"HTTP {response.status_code}")
        except Exception as e:
            return self.log_test("Network Discovery", "FAIL", str(e))
    
    def test_port_scan(self):
        """Test 5: Port Scan Function"""
        try:
            # Get first online device
            devices_response = requests.get(f"{API_BASE_URL}/devices/", timeout=30)
            devices = devices_response.json()
            online_devices = [d for d in devices if d.get("status") == "online"]
            
            if not online_devices:
                return self.log_test("Port Scan", "SKIP", "No online devices found")
            
            test_device = online_devices[0]
            ip = test_device.get("ip_address")
            name = test_device.get("hostname", "Unknown")
            
            response = requests.get(
                f"{API_BASE_URL}/devices/{ip}/portscan?save_to_db=true",
                timeout=60
            )
            
            if response.status_code == 200:
                scan_data = response.json()
                port_count = len(scan_data.get("ports", []))
                return self.log_test("Port Scan", "PASS", 
                                   f"Scanned {name} ({ip}), found {port_count} ports")
            else:
                return self.log_test("Port Scan", "FAIL", f"HTTP {response.status_code}")
        except Exception as e:
            return self.log_test("Port Scan", "FAIL", str(e))
    
    def test_os_scan(self):
        """Test 6: OS Scan Function"""
        try:
            # Get first online device
            devices_response = requests.get(f"{API_BASE_URL}/devices/", timeout=30)
            devices = devices_response.json()
            online_devices = [d for d in devices if d.get("status") == "online"]
            
            if not online_devices:
                return self.log_test("OS Scan", "SKIP", "No online devices found")
            
            test_device = online_devices[0]
            ip = test_device.get("ip_address")
            name = test_device.get("hostname", "Unknown")
            
            response = requests.get(
                f"{API_BASE_URL}/devices/{ip}/oscan?save_to_db=true",
                timeout=90
            )
            
            if response.status_code == 200:
                scan_data = response.json()
                vendor = scan_data.get("vendor", "Unknown")
                os_count = len(scan_data.get("os_guesses", []))
                return self.log_test("OS Scan", "PASS", 
                                   f"Scanned {name} ({ip}), vendor: {vendor}, {os_count} OS guesses")
            else:
                return self.log_test("OS Scan", "FAIL", f"HTTP {response.status_code}")
        except Exception as e:
            return self.log_test("OS Scan", "FAIL", str(e))
    
    def test_scan_results_storage(self):
        """Test 7: Scan Results Storage"""
        try:
            # Get first online device to check its scan results
            devices_response = requests.get(f"{API_BASE_URL}/devices/", timeout=30)
            devices = devices_response.json()
            online_devices = [d for d in devices if d.get("status") == "online"]
            
            if not online_devices:
                return self.log_test("Scan Results Storage", "SKIP", "No online devices found")
            
            test_device = online_devices[0]
            mac = test_device.get("mac_address")
            
            # Get device details to check if scan info is populated
            response = requests.get(f"{API_BASE_URL}/devices/mac/{mac}", timeout=30)
            
            if response.status_code == 200:
                device_data = response.json()
                vendor = device_data.get("vendor")
                network_distance = device_data.get("network_distance")
                latency = device_data.get("latency")
                
                if vendor or network_distance or latency:
                    return self.log_test("Scan Results Storage", "PASS", 
                                       f"Device has scan data: vendor={vendor}, distance={network_distance}")
                else:
                    return self.log_test("Scan Results Storage", "WARN", 
                                       "Device found but no scan data populated")
            else:
                return self.log_test("Scan Results Storage", "FAIL", f"HTTP {response.status_code}")
        except Exception as e:
            return self.log_test("Scan Results Storage", "FAIL", str(e))
    
    def test_device_detail_api(self):
        """Test 8: Device Detail API"""
        try:
            # Get first device MAC
            devices_response = requests.get(f"{API_BASE_URL}/devices/", timeout=30)
            devices = devices_response.json()
            
            if not devices:
                return self.log_test("Device Detail API", "SKIP", "No devices found")
            
            test_device = devices[0]
            mac = test_device.get("mac_address")
            
            response = requests.get(f"{API_BASE_URL}/devices/mac/{mac}", timeout=30)
            
            if response.status_code == 200:
                device_data = response.json()
                fields = ["id", "mac_address", "hostname", "status", "vendor", "network_distance", "latency"]
                present_fields = [f for f in fields if f in device_data]
                return self.log_test("Device Detail API", "PASS", 
                                   f"Returns {len(present_fields)}/{len(fields)} expected fields")
            else:
                return self.log_test("Device Detail API", "FAIL", f"HTTP {response.status_code}")
        except Exception as e:
            return self.log_test("Device Detail API", "FAIL", str(e))
    
    def run_all_tests(self):
        """Run all verification tests"""
        print("🚀 Starting System Verification")
        print(f"📋 Testing against:")
        print(f"   API: {API_BASE_URL}")
        print(f"   Streamlit: {STREAMLIT_URL}")
        print(f"   Test subnet: {SUBNET}")
        print()
        
        tests = [
            self.test_api_health,
            self.test_streamlit_health,
            self.test_database_schema,
            self.test_network_discovery,
            self.test_port_scan,
            self.test_os_scan,
            self.test_scan_results_storage,
            self.test_device_detail_api
        ]
        
        passed = 0
        failed = 0
        skipped = 0
        warnings = 0
        
        for test_func in tests:
            try:
                result = test_func()
                if result:
                    passed += 1
                else:
                    # Check if it was a skip or warning
                    last_test = self.results["tests"][-1]
                    if last_test["status"] == "SKIP":
                        skipped += 1
                    elif last_test["status"] == "WARN":
                        warnings += 1
                    else:
                        failed += 1
            except Exception as e:
                self.log_test("Test Execution", "FAIL", f"Test crashed: {e}")
                failed += 1
            
            time.sleep(1)  # Small delay between tests
        
        print(f"\n📊 Verification Results:")
        print(f"   Total tests: {len(tests)}")
        print(f"   ✅ Passed: {passed}")
        print(f"   ❌ Failed: {failed}")
        print(f"   ⚠️ Warnings: {warnings}")
        print(f"   ⏭️ Skipped: {skipped}")
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"system_verification_{timestamp}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"   📄 Detailed results saved to: {filename}")
        
        success_rate = (passed / len(tests)) * 100
        print(f"\n🎯 Overall Success Rate: {success_rate:.1f}%")
        
        if failed == 0:
            print("🎉 System verification completed successfully!")
            return True
        else:
            print(f"⚠️ System verification completed with {failed} failures")
            return False

class TestSystemVerification:
    """Pytest class for system verification tests"""
    
    def test_system_verification(self):
        """Main pytest test method"""
        verifier = SystemVerificationTest()
        success = verifier.run_all_tests()
        
        if success:
            print("\n✅ System is ready for production use!")
        else:
            print("\n❌ System has issues that need to be addressed")
        
        assert success, "System verification failed"

def main():
    """Main function for standalone execution"""
    verifier = SystemVerificationTest()
    success = verifier.run_all_tests()
    
    if success:
        print("\n✅ System is ready for production use!")
    else:
        print("\n❌ System has issues that need to be addressed")
    
    return success

if __name__ == "__main__":
    main()
