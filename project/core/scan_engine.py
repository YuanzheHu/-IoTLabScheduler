"""
Scan Engine Module

This module provides functionality for:
- Port scanning (nmap)
- OS fingerprinting (nmap)
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
import os
import json
import sys

logger = logging.getLogger(__name__)

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

class ScanEngine:
    """Scan engine for port scanning and OS fingerprinting"""

    def __init__(self):
        self.last_scan_result: Optional[Dict[str, Any]] = None
        self.last_scan_type: Optional[str] = None
        self.last_target: Optional[str] = None

    async def port_scan(self, target_ip: str, ports: str = "-", fast_scan: bool = True) -> Dict[str, Any]:
        """
        Perform a port scan on the target IP using nmap.
        Args:
            target_ip: Target IP address
            ports: Ports to scan (default: all ports)
            fast_scan: If True, use fast scan options (-F, -T4, --max-retries 1)
        Returns:
            Dict with scan results
        """
        logger.info(f"Starting port scan on {target_ip} (ports: {ports}, fast: {fast_scan})")
        command = ["nmap", "-sS", "-Pn"]  # -Pn to skip ping detection
        
        if fast_scan:
            if ports == "-":
                # Use -F for fast scan of top ports when scanning all ports
                command.extend(["-F", "-T4", "--max-retries", "1"])
            else:
                # Use fast timing but respect custom port selection
                command.extend(["-T4", "--max-retries", "1"])
                command.extend([f"-p{ports}"])
        else:
            command.extend([f"-p{ports}"])
        
        if fast_scan and ports == "-":
            # Don't add -p when using -F
            command.append(target_ip)
        else:
            command.append(target_ip)
        
        output = await self._run_command(command)
        result = self._parse_port_scan(output)
        self.last_scan_result = result
        self.last_scan_type = "port_scan"
        self.last_target = target_ip
        return result

    async def os_fingerprint(self, target_ip: str, fast_scan: bool = True, ports: str = "22,80,443") -> Dict[str, Any]:
        """
        Perform OS fingerprinting on the target IP using nmap.
        Args:
            target_ip: Target IP address
            fast_scan: If True, use fast scan options (-T4, --max-retries 1)
            ports: Ports to scan for OS fingerprinting (default: '22,80,443')
        Returns:
            Dict with OS fingerprint results
        """
        logger.info(f"Starting OS fingerprint on {target_ip} (fast: {fast_scan}, ports: {ports})")
        command = ["nmap", "-O", "--osscan-guess", "-Pn"]  # -Pn to skip ping detection
        
        if fast_scan:
            command.extend(["-T4", "--max-retries", "1"])
        
        command.extend([f"-p{ports}", target_ip])
        
        output = await self._run_command(command)
        result = self._parse_os_fingerprint(output)
        self.last_scan_result = result
        self.last_scan_type = "os_fingerprint"
        self.last_target = target_ip
        return result

    async def _run_command(self, command: List[str]) -> str:
        """Run a subprocess command asynchronously and return stdout as string."""
        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            logger.error(f"Command failed: {' '.join(command)}\nStderr: {stderr.decode()}")
        return stdout.decode()

    def _parse_port_scan(self, output: str) -> Dict[str, Any]:
        """Parse nmap port scan output into a structured dict."""
        ports = []
        in_ports = False
        for line in output.splitlines():
            if line.startswith("PORT"):
                in_ports = True
                continue
            if in_ports:
                if line.strip() == '' or line.startswith("Nmap done"):
                    break
                parts = line.split()
                if len(parts) >= 3:
                    port, state, service = parts[:3]
                    ports.append({
                        "port": port,
                        "state": state,
                        "service": service
                    })
        return {"ports": ports, "raw_output": output}

    def _parse_os_fingerprint(self, output: str) -> Dict[str, Any]:
        """Parse nmap OS fingerprint output into a structured dict."""
        os_matches = []
        for line in output.splitlines():
            if line.strip().startswith("OS details:"):
                os_matches.append(line.strip().replace("OS details:", "").strip())
            elif line.strip().startswith("Aggressive OS guesses:"):
                os_matches.append(line.strip().replace("Aggressive OS guesses:", "").strip())
        return {"os_guesses": os_matches, "raw_output": output}

    def get_last_scan_status(self) -> Dict[str, Any]:
        """Get the status/result of the last scan."""
        return {
            "scan_type": self.last_scan_type,
            "target": self.last_target,
            "result": self.last_scan_result
        }

if __name__ == "__main__":
    import logging
    import time
    import os
    import json
    logging.basicConfig(level=logging.INFO)
    async def main():
        engine = ScanEngine()
        test_ip = "10.12.0.192"  # Localhost for safe testing
        data_dir = os.path.join(os.path.dirname(__file__), "../data")
        os.makedirs(data_dir, exist_ok=True)
        
        print(f"\n--- Testing port scan on {test_ip} ---")
        start_time = time.time()
        port_result = await engine.port_scan(test_ip)
        scan_time = time.time() - start_time
        print(f"Port scan completed in {scan_time:.2f} seconds")
        print("Port scan result:")
        print(port_result)
        # Save port scan result
        port_file = os.path.join(data_dir, f"port_scan_{test_ip.replace('.', '_')}.json")
        with open(port_file, "w") as f:
            json.dump(port_result, f, indent=2)
        print(f"Port scan result saved to {port_file}")

        print(f"\n--- Testing OS fingerprint on {test_ip} (ports: 22,80,443) ---")
        start_time = time.time()
        os_result = await engine.os_fingerprint(test_ip, ports="22,80,443")
        os_time = time.time() - start_time
        print(f"OS fingerprint completed in {os_time:.2f} seconds")
        print("OS fingerprint result:")
        print(os_result)
        # Save OS fingerprint result
        os_file = os.path.join(data_dir, f"os_fingerprint_{test_ip.replace('.', '_')}.json")
        with open(os_file, "w") as f:
            json.dump(os_result, f, indent=2)
        print(f"OS fingerprint result saved to {os_file}")

        print("\n--- Last scan status ---")
        print(engine.get_last_scan_status())

    import asyncio
    asyncio.run(main()) 