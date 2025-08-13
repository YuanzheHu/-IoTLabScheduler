"""
Scan Engine Module

This module provides functionality for:
- TCP and UDP port scanning on devices
- OS fingerprinting on devices
- Single device scanning
- Batch scanning of multiple devices
- Scan result recording and logging
"""

import asyncio
import logging
import subprocess
import csv
import os
import json
import sys
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

# Logging configuration
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


class ScanType(Enum):
    """Enumeration for scan types."""
    PORT_SCAN = "port_scan"      # TCP+UDP port scan
    OS_SCAN = "os_scan"          # OS fingerprinting


class ScanResult:
    """Class representing the result of a scan."""

    def __init__(
        self,
        target_ip: str,
        device_name: str = "Unknown",
        scan_type: ScanType = ScanType.PORT_SCAN
    ):
        """Initializes a ScanResult object.

        Args:
            target_ip: The IP address of the target device.
            device_name: The name of the device.
            scan_type: The type of scan performed.
        """
        self.target_ip = target_ip
        self.device_name = device_name
        self.scan_type = scan_type
        self.scan_time = datetime.now()
        self.scan_duration = 0.0
        self.tcp_ports = []
        self.udp_ports = []
        self.os_info = {}
        self.error = None
        self.raw_output = ""
        self.command = ""

    def to_dict(self) -> Dict[str, Any]:
        """Converts the scan result to a dictionary.

        Returns:
            A dictionary representation of the scan result.
        """
        return {
            "target_ip": self.target_ip,
            "device_name": self.device_name,
            "scan_type": self.scan_type.value,
            "scan_time": self.scan_time.isoformat(),
            "scan_duration": self.scan_duration,
            "tcp_ports": self.tcp_ports,
            "udp_ports": self.udp_ports,
            "total_tcp_ports": len(self.tcp_ports),
            "total_udp_ports": len(self.udp_ports),
            "os_info": self.os_info,
            "error": self.error,
            "raw_output": self.raw_output,
            "command": self.command
        }


class ScanEngine:
    """Scan engine supporting port scanning and OS fingerprinting."""

    def __init__(
        self,
        devices_status_file: str = "../data/identified_devices_status.csv",
        scan_results_dir: str = "../data/scan_results"
    ):
        """Initializes the ScanEngine.

        Args:
            devices_status_file: Path to the CSV file containing device status.
            scan_results_dir: Directory to store scan results.
        """
        self.devices_status_file = devices_status_file
        self.scan_results_dir = scan_results_dir
        self.last_scan_result: Optional[ScanResult] = None
        self.last_scan_time: Optional[str] = None

        # Ensure the scan results directory exists
        os.makedirs(self.scan_results_dir, exist_ok=True)

    def get_online_devices(self) -> List[Dict[str, str]]:
        """Retrieves the list of online devices from the status CSV file.

        Returns:
            A list of dictionaries, each representing an online device.
        """
        online_devices = []
        if not os.path.exists(self.devices_status_file):
            logger.error(f"Device status file not found: {self.devices_status_file}")
            return online_devices

        try:
            with open(self.devices_status_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('Status') == 'online' and row.get('IP'):
                        online_devices.append({
                            'IP': row['IP'],
                            'MAC': row['MAC'],
                            'Name': row['Name']
                        })
        except Exception as e:
            logger.error(f"Error reading device status file: {e}")

        logger.info(f"Found {len(online_devices)} online devices")
        return online_devices

    async def scan_single_device(
        self,
        target_ip: str,
        device_name: str = "Unknown",
        scan_type: ScanType = ScanType.PORT_SCAN,
        fast_scan: bool = True
    ) -> ScanResult:
        """Scans a single device.

        Args:
            target_ip: The target device's IP address.
            device_name: The name of the device.
            scan_type: The type of scan (port scan/OS scan).
            fast_scan: Whether to use fast scan mode.

        Returns:
            ScanResult: The result of the scan.
        """
        logger.info(
            f"Starting scan for device: {target_ip} ({device_name}) - "
            f"Scan type: {scan_type.value} - Fast mode: {fast_scan}"
        )

        result = ScanResult(target_ip, device_name, scan_type)

        try:
            # Build the scan command based on scan type
            command = self._build_scan_command(target_ip, scan_type, fast_scan)
            result.command = " ".join(command)

            # Execute the scan
            start_time = datetime.now()
            output = await self._run_command(command)
            end_time = datetime.now()

            result.scan_duration = (end_time - start_time).total_seconds()
            result.raw_output = output

            # Parse the scan result
            if not output.startswith("Error:"):
                if scan_type == ScanType.PORT_SCAN:
                    self._parse_port_scan_output(result, output)
                elif scan_type == ScanType.OS_SCAN:
                    self._parse_os_scan_output(result, output)
            else:
                result.error = output

        except Exception as e:
            result.error = str(e)
            logger.error(f"Error scanning device {target_ip}: {e}")

        # Save the scan result
        self._save_scan_result(result)

        # Update last scan status
        self.last_scan_result = result
        self.last_scan_time = result.scan_time.isoformat()

        logger.info(
            f"Device {target_ip} scan completed, duration {result.scan_duration:.2f} seconds"
        )
        return result

    async def scan_multiple_devices(
        self,
        devices: List[Dict[str, str]],
        scan_type: ScanType = ScanType.PORT_SCAN,
        delay_between_scans: float = 1.0
    ) -> Dict[str, Any]:
        """Scans multiple devices in batch.

        Args:
            devices: List of devices, each containing IP, MAC, and Name.
            scan_type: The type of scan.
            delay_between_scans: Delay between scans in seconds.

        Returns:
            Dict: A summary containing all scan results.
        """
        if not devices:
            logger.warning("No devices to scan")
            return {"error": "No devices to scan"}

        logger.info(
            f"Starting batch scan of {len(devices)} devices - Scan type: {scan_type.value}"
        )

        all_results = []
        total_start_time = datetime.now()

        for i, device in enumerate(devices):
            try:
                logger.info(
                    f"Scan progress: {i+1}/{len(devices)} - {device.get('IP', 'Unknown')}"
                )

                result = await self.scan_single_device(
                    device['IP'],
                    device.get('Name', 'Unknown'),
                    scan_type
                )
                all_results.append(result)

                # Delay between scans to avoid network congestion
                if i < len(devices) - 1:
                    await asyncio.sleep(delay_between_scans)

            except Exception as e:
                logger.error(
                    f"Error scanning device {device.get('IP', 'Unknown')}: {e}"
                )
                error_result = ScanResult(
                    device.get('IP', 'Unknown'),
                    device.get('Name', 'Unknown'),
                    scan_type
                )
                error_result.error = str(e)
                all_results.append(error_result)

        total_end_time = datetime.now()
        total_duration = (total_end_time - total_start_time).total_seconds()

        # Generate summary
        summary = self._generate_scan_summary(
            all_results, total_start_time, total_end_time, total_duration
        )

        # Save summary
        self._save_scan_summary(summary)

        logger.info(
            f"Batch scan completed, scanned {len(all_results)} devices, "
            f"total duration {total_duration:.2f} seconds"
        )
        return summary

    async def scan_all_online_devices(
        self,
        scan_type: ScanType = ScanType.PORT_SCAN,
        delay_between_scans: float = 1.0
    ) -> Dict[str, Any]:
        """Scans all online devices.

        Args:
            scan_type: The type of scan.
            delay_between_scans: Delay between scans in seconds.

        Returns:
            Dict: Scan summary.
        """
        online_devices = self.get_online_devices()
        return await self.scan_multiple_devices(
            online_devices, scan_type, delay_between_scans
        )

    def _build_scan_command(
        self,
        target_ip: str,
        scan_type: ScanType,
        fast_scan: bool = True
    ) -> List[str]:
        """Builds the nmap command based on scan type.

        Args:
            target_ip: The target IP address.
            scan_type: The type of scan.
            fast_scan: Whether to use fast scan mode.

        Returns:
            List[str]: The nmap command as a list of arguments.
        """
        base_command = ["nmap"]

        if scan_type == ScanType.PORT_SCAN:
            if fast_scan:
                # Fast port scan: scan top TCP and UDP ports
                return base_command + [
                    "-sS", "-sU", "-T4", "--top-ports", "20", "--max-retries", "1", target_ip
                ]
            else:
                # Full port scan
                return base_command + [
                    "-sS", "-sU", "-T4", "-F", "--max-retries", "2", target_ip
                ]
        elif scan_type == ScanType.OS_SCAN:
            if fast_scan:
                # Fast OS scan
                return base_command + [
                    "-O", "-T4", "--osscan-guess", "--max-retries", "1", target_ip
                ]
            else:
                # Full OS scan
                return base_command + [
                    "-O", "-T4", "--osscan-guess", "--max-retries", "2", target_ip
                ]
        else:
            # Default to fast port scan
            return base_command + [
                "-sS", "-T4", "--top-ports", "20", "--max-retries", "1", target_ip
            ]

    async def _run_command(
        self,
        command: List[str],
        timeout: int = 45
    ) -> str:
        """Runs a command asynchronously and returns its output.

        Args:
            command: The command to run as a list of arguments.
            timeout: Timeout in seconds.

        Returns:
            str: The command output or error message.
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Set timeout (45 seconds, leaving 5 seconds for frontend)
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                # Timeout, terminate process
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5)
                except asyncio.TimeoutError:
                    proc.kill()
                return f"Error: Command timed out ({timeout} seconds)"

            if proc.returncode != 0:
                error_msg = (
                    f"Command failed: {' '.join(command)}\n"
                    f"Error output: {stderr.decode()}"
                )
                logger.error(error_msg)
                return f"Error: {stderr.decode()}"

            return stdout.decode()
        except Exception as e:
            error_msg = f"Error running command {' '.join(command)}: {e}"
            logger.error(error_msg)
            return f"Error: {str(e)}"

    def _parse_port_scan_output(self, result: ScanResult, output: str):
        """Parses the output of a port scan.

        Args:
            result: The ScanResult object to populate.
            output: The raw output from nmap.
        """
        in_ports = False

        for line in output.splitlines():
            if line.startswith("PORT"):
                in_ports = True
                continue
            elif line.startswith("Nmap scan report for"):
                in_ports = False
                continue
            elif line.startswith("Not shown:"):
                in_ports = False
                continue
            elif line.startswith("Nmap done:"):
                break

            if in_ports and line.strip():
                parts = line.split()
                if len(parts) >= 2:
                    port_info = parts[0]  # e.g., "22/tcp" or "53/udp"
                    state = parts[1]
                    service = parts[2] if len(parts) > 2 else "unknown"

                    # Extract port number and protocol
                    if "/" in port_info:
                        port_num, protocol = port_info.split("/")
                        port_data = {
                            "port": f"{port_num}/{protocol}",
                            "state": state,
                            "service": service
                        }

                        logger.debug(f"Parsed port: {port_data}")

                        if protocol == "tcp":
                            result.tcp_ports.append(port_data)
                        elif protocol == "udp":
                            result.udp_ports.append(port_data)
                        else:
                            logger.warning(f"Unknown protocol: {protocol}")
                    else:
                        logger.warning(f"Could not parse port info: {port_info}")

    def _parse_os_scan_output(self, result: ScanResult, output: str):
        """Parses the output of an OS scan with enhanced information extraction.

        Args:
            result: The ScanResult object to populate.
            output: The raw output from nmap.
        """
        os_info = {
            "mac_address": None,
            "vendor": None,
            "network_distance": None,
            "os_guesses": [],
            "os_details": {},
            "port_info": [],
            "scan_summary": {},
            "host_status": None,
            "scan_statistics": {}
        }
        
        in_os_details = False
        in_port_section = False
        lines = output.splitlines()
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue
                
            # 解析扫描开始信息
            if "Starting Nmap" in line:
                os_info["scan_summary"]["nmap_version"] = line.split("Nmap")[1].split("(")[0].strip()
                os_info["scan_summary"]["scan_start"] = line.split("at")[1].strip() if "at" in line else None
            
            # 解析扫描目标
            elif "Nmap scan report for" in line:
                target = line.split("Nmap scan report for")[1].strip()
                os_info["scan_summary"]["target"] = target
            
            # 解析主机状态和延迟
            elif "Host is up" in line:
                os_info["host_status"] = "up"
                if "(" in line and ")" in line:
                    latency = line.split("(")[1].split(")")[0]
                    os_info["scan_summary"]["latency"] = latency
            elif "Host is down" in line:
                os_info["host_status"] = "down"
                
            # 解析端口统计信息
            elif "Not shown:" in line:
                port_stats = line.split("Not shown:")[1].strip()
                os_info["scan_statistics"]["hidden_ports"] = port_stats
                
            # 检测端口部分开始
            elif line_stripped.startswith("PORT") and "STATE" in line and "SERVICE" in line:
                in_port_section = True
                continue
                
            # 解析端口信息
            elif in_port_section and "/" in line_stripped:
                parts = line_stripped.split()
                if len(parts) >= 3:
                    port_info = {
                        "port": parts[0],
                        "state": parts[1],
                        "service": parts[2] if len(parts) > 2 else "unknown"
                    }
                    os_info["port_info"].append(port_info)
                    
            # 解析MAC地址和厂商
            elif "MAC Address:" in line:
                mac_part = line.split("MAC Address:")[1].strip()
                if "(" in mac_part and ")" in mac_part:
                    os_info["mac_address"] = mac_part.split("(")[0].strip()
                    os_info["vendor"] = mac_part.split("(")[1].split(")")[0].strip()
                else:
                    os_info["mac_address"] = mac_part
                    
            # 解析网络距离
            elif "Network Distance:" in line:
                distance = line.split("Network Distance:")[1].strip()
                os_info["network_distance"] = distance
                
            # 解析OS详细信息
            elif "OS details:" in line:
                in_os_details = True
                details = line.split("OS details:")[1].strip()
                if details:
                    os_info["os_details"]["details"] = details
                    os_info["os_guesses"].append(details)
                    
            elif "OS CPE:" in line:
                cpe = line.split("OS CPE:")[1].strip()
                os_info["os_details"]["cpe"] = cpe
                
            elif "Aggressive OS guesses:" in line:
                guesses_text = line.split("Aggressive OS guesses:")[1].strip()
                if guesses_text:
                    # 解析多个OS猜测，通常以逗号分隔
                    guesses_list = [g.strip() for g in guesses_text.split(",") if g.strip()]
                    os_info["os_guesses"].extend(guesses_list)
                    os_info["os_details"]["aggressive_guesses"] = guesses_text
                    
            elif "OS guesses:" in line:
                guesses_text = line.split("OS guesses:")[1].strip()
                if guesses_text:
                    guesses_list = [g.strip() for g in guesses_text.split(",") if g.strip()]
                    os_info["os_guesses"].extend(guesses_list)
                    
            elif "Too many fingerprints match this host" in line:
                os_info["os_details"]["too_many_fingerprints"] = True
                # Even with too many fingerprints, we provide useful information
                if os_info["mac_address"] or os_info["port_info"]:
                    os_info["os_guesses"].append("Device detected but too many fingerprints to determine specific OS type")
                    
            elif "No exact OS matches" in line:
                os_info["os_details"]["no_exact_match"] = True
                if os_info["mac_address"] or os_info["port_info"]:
                    os_info["os_guesses"].append("Device detected but no exact OS match found")
                    
            elif "OS detection performed" in line:
                in_os_details = False
                in_port_section = False
                
            # 解析扫描完成信息
            elif "Nmap done:" in line:
                scan_info = line.split("Nmap done:")[1].strip()
                if "scanned in" in scan_info:
                    time_part = scan_info.split("scanned in")[1].strip()
                    os_info["scan_statistics"]["total_time"] = time_part
                os_info["scan_statistics"]["completion_info"] = scan_info

        # If no OS guesses but device info exists, provide default description
        if not os_info["os_guesses"] and (os_info["mac_address"] or os_info["port_info"] or os_info["host_status"]):
            device_info = []
            if os_info["vendor"]:
                device_info.append(f"Vendor: {os_info['vendor']}")
            if os_info["port_info"]:
                open_ports = [p for p in os_info["port_info"] if p["state"] == "open"]
                if open_ports:
                    device_info.append(f"{len(open_ports)} open ports")
            if os_info["network_distance"]:
                device_info.append(f"Network Distance: {os_info['network_distance']}")
                
            if device_info:
                os_info["os_guesses"] = [f"Active device detected ({', '.join(device_info)})"]
            else:
                os_info["os_guesses"] = ["Device detected - view details for more information"]

        result.os_info = os_info

    def _generate_scan_summary(
        self,
        results: List[ScanResult],
        start_time: datetime,
        end_time: datetime,
        total_duration: float
    ) -> Dict[str, Any]:
        """Generates a summary of scan results.

        Args:
            results: List of ScanResult objects.
            start_time: The datetime when the scan started.
            end_time: The datetime when the scan ended.
            total_duration: Total duration of the scan in seconds.

        Returns:
            Dict[str, Any]: The scan summary.
        """
        successful_scans = [r for r in results if r.error is None]
        failed_scans = [r for r in results if r.error is not None]

        total_tcp_ports = sum(len(r.tcp_ports) for r in successful_scans)
        total_udp_ports = sum(len(r.udp_ports) for r in successful_scans)

        # Count OS info
        os_detected = sum(1 for r in successful_scans if r.os_info)
        os_guesses = sum(1 for r in successful_scans if r.os_info.get('aggressive_guesses'))

        return {
            "total_devices": len(results),
            "successful_scans": len(successful_scans),
            "failed_scans": len(failed_scans),
            "total_scan_time": total_duration,
            "scan_start": start_time.isoformat(),
            "scan_end": end_time.isoformat(),
            "total_tcp_ports_found": total_tcp_ports,
            "total_udp_ports_found": total_udp_ports,
            "os_detected": os_detected,
            "os_guesses": os_guesses,
            "results": [r.to_dict() for r in results]
        }

    def _save_scan_result(self, result: ScanResult):
        """Saves a single scan result to a JSON file.

        Args:
            result: The ScanResult object to save.
        """
        timestamp = result.scan_time.strftime("%Y%m%d_%H%M%S")
        scan_type_suffix = result.scan_type.value.replace("_", "")
        filename = f"scan_{result.target_ip.replace('.', '_')}_{scan_type_suffix}_{timestamp}.json"
        filepath = os.path.join(self.scan_results_dir, filename)

        try:
            with open(filepath, 'w') as f:
                json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
            logger.info(f"Scan result saved to: {filepath}")
        except Exception as e:
            logger.error(f"Error saving scan result: {e}")

    def _save_scan_summary(self, summary: Dict[str, Any]):
        """Saves the scan summary to a JSON file.

        Args:
            summary: The scan summary dictionary.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"scan_summary_{timestamp}.json"
        filepath = os.path.join(self.scan_results_dir, filename)

        try:
            with open(filepath, 'w') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            logger.info(f"Scan summary saved to: {filepath}")
        except Exception as e:
            logger.error(f"Error saving scan summary: {e}")

    def get_last_scan_status(self) -> Dict[str, Any]:
        """Gets the status of the last scan.

        Returns:
            A dictionary containing the last scan time and result.
        """
        if self.last_scan_result:
            return {
                "last_scan_time": self.last_scan_time,
                "last_scan_result": self.last_scan_result.to_dict()
            }
        return {"last_scan_time": None, "last_scan_result": None}


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)

    async def main():
        engine = ScanEngine()

        print("=== Scan Engine Test ===")

        # Test port scan
        print("\n1. Test Port Scan:")
        port_result = await engine.scan_single_device("10.12.0.2", "Bose Speaker", ScanType.PORT_SCAN)
        print(f"Port scan result: {port_result.to_dict()}")

        # Test OS scan
        print("\n2. Test OS Scan:")
        os_result = await engine.scan_single_device("10.12.0.2", "Bose Speaker", ScanType.OS_SCAN)
        print(f"OS scan result: {os_result.to_dict()}")

        # Test scan of all online devices
        print("\n3. Test Scan of All Online Devices:")

        # Get online devices
        online_devices = engine.get_online_devices()
        print(f"Found {len(online_devices)} online devices")

        if online_devices:
            print("Online device list:")
            for device in online_devices:
                print(f"  - {device['IP']} ({device['Name']})")

            # Perform port scan on all online devices
            print(f"\nPerforming port scan on all online devices...")
            port_summary = await engine.scan_all_online_devices(ScanType.PORT_SCAN, delay_between_scans=1.0)
            print(f"Port scan summary: {port_summary}")

            # Perform OS scan on all online devices
            print(f"\nPerforming OS scan on all online devices...")
            os_summary = await engine.scan_all_online_devices(ScanType.OS_SCAN, delay_between_scans=1.0)
            print(f"OS scan summary: {os_summary}")
        else:
            print("No online devices found")

    asyncio.run(main())