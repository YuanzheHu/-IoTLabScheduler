"""
tcpdump_util.py

Utility for managing tcpdump processes for packet capture.

This module provides the TcpdumpUtil class, which allows starting and stopping
a tcpdump process to capture network packets to a file. It is useful for
automating packet capture in scripts or tests.

Example usage:
    tcpdump = TcpdumpUtil(output_file='capture.pcap', interface='eth0')
    tcpdump.start()
    # ... generate or observe network traffic ...
    tcpdump.stop()
"""

import subprocess
import os
import signal
import time


class TcpdumpUtil:
    """Utility class to manage tcpdump process for packet capture."""

    def __init__(self, output_file='capture.pcap', interface='any', extra_args=None, target_ip=None):
        """Initialize TcpdumpUtil.
        
        Args:
            output_file (str): Output file for captured packets
            interface (str): Network interface to capture on ('any' for all interfaces)
            extra_args (list): Additional tcpdump arguments
            target_ip (str): Target IP address to filter for (optional)
        """
        self.output_file = output_file
        self.interface = interface
        self.extra_args = extra_args or []
        self.target_ip = target_ip
        self.process = None

    def start(self):
        """Start the tcpdump process with bidirectional capture."""
        if self.process is not None:
            raise RuntimeError('tcpdump is already running')
        
        # Build command with options for bidirectional capture
        cmd = [
            'tcpdump',  # In Docker we don't need sudo
            '-i', self.interface,
            '-w', self.output_file,
            '-s', '0',  # Capture full packet size
            '-n',  # Don't resolve hostnames
            '-v',  # Verbose output
            '-e',  # Print link-level header
            '-tttt'  # Print human readable timestamps
        ]
        
        # Add target IP filter if specified
        if self.target_ip:
            # Capture both directions: packets to/from the target IP
            cmd.extend(['host', self.target_ip])
        else:
            # If no target IP, capture all traffic on the interface
            cmd.extend(['-v'])  # Verbose output
        
        # Add extra arguments
        cmd.extend(self.extra_args)
        
        # Add detailed error handling and logging
        print(f"Starting tcpdump command: {' '.join(cmd)}")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
        
        # Check if tcpdump command is available
        try:
            result = subprocess.run(['which', 'tcpdump'], check=True, capture_output=True, text=True)
            print(f"tcpdump path: {result.stdout.strip()}")
        except subprocess.CalledProcessError:
            raise RuntimeError("tcpdump command is not available")
        
        # Check network interface
        try:
            # List all network interfaces
            result = subprocess.run(['ip', 'link', 'show'], check=True, capture_output=True, text=True)
            print(f"Available network interfaces:\n{result.stdout}")
            
            # Get IP address info for the specified interface
            result = subprocess.run(['ip', 'addr', 'show', self.interface], check=True, capture_output=True, text=True)
            print(f"Interface {self.interface} info:\n{result.stdout}")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Network interface check failed: {e}")
        
        # Test if tcpdump can work on the specified interface
        try:
            test_cmd = ['tcpdump', '-i', self.interface, '-c', '1', '-n']
            print(f"Testing tcpdump command: {' '.join(test_cmd)}")
            result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=3)
            print(f"tcpdump test result:\n{result.stdout}\n{result.stderr}")
        except subprocess.TimeoutExpired:
            print("tcpdump test timed out, but this is normal")
        except Exception as e:
            raise RuntimeError(f"tcpdump test failed: {e}")
        
        # Start tcpdump process
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid,
                text=True  # Use text mode
            )
            print(f"tcpdump process started (PID: {self.process.pid})")
        except Exception as e:
            raise RuntimeError(f"Failed to start tcpdump process: {e}")
        
        # Wait a bit to ensure the process starts
        time.sleep(1)
        
        # Check if the process started successfully
        if self.process.poll() is not None:
            stderr_output = self.process.stderr.read() if self.process.stderr else "No error output"
            raise RuntimeError(f"tcpdump process failed to start: {stderr_output}")
        
        # Check if output file was created
        if not os.path.exists(self.output_file):
            raise RuntimeError(f"tcpdump output file was not created: {self.output_file}")
        
        print(f"tcpdump started successfully, output file: {self.output_file}")

    def stop(self):
        """Stop the tcpdump process."""
        if self.process is None:
            raise RuntimeError('tcpdump is not running')
        
        print(f"Stopping tcpdump process (PID: {self.process.pid})")
        
        try:
            # Check if the process is still running
            if self.process.poll() is not None:
                print(f"tcpdump process has already stopped, return code: {self.process.returncode}")
                stdout = self.process.stdout.read() if self.process.stdout else ""
                stderr = self.process.stderr.read() if self.process.stderr else ""
                if stdout:
                    print(f"Process output:\n{stdout}")
                if stderr:
                    print(f"Process error:\n{stderr}")
                return
            
            # Try to gracefully terminate first
            print("Sending SIGTERM signal")
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            
            # Wait up to 5 seconds
            for i in range(10):
                if self.process.poll() is not None:
                    print(f"Process stopped, return code: {self.process.returncode}")
                    break
                print(f"Waiting for process to stop... ({i+1}/10)")
                time.sleep(0.5)
            
            # If still not stopped, force kill
            if self.process.poll() is None:
                print("Sending SIGKILL signal")
                os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                self.process.wait()
                print(f"Process was forcefully killed, return code: {self.process.returncode}")
            
            # Read process output
            stdout = self.process.stdout.read() if self.process.stdout else ""
            stderr = self.process.stderr.read() if self.process.stderr else ""
            if stdout:
                print(f"Process output:\n{stdout}")
            if stderr:
                print(f"Process error:\n{stderr}")
            
            # Check output file
            if os.path.exists(self.output_file):
                file_size = os.path.getsize(self.output_file)
                print(f"PCAP file size: {file_size} bytes")
                if file_size == 0:
                    print("Warning: PCAP file is empty")
            else:
                print(f"Warning: PCAP file does not exist: {self.output_file}")
            
            print("tcpdump process has stopped")
        except Exception as e:
            print(f"Error while stopping tcpdump process: {e}")
        finally:
            self.process = None


if __name__ == '__main__':
    # Test the TcpdumpUtil module
    print("Testing TcpdumpUtil module...")
    
    # Create test capture file
    test_file = 'test_capture.pcap'
    interface = 'lo'  # Use loopback for safe testing
    
    tcpdump = TcpdumpUtil(output_file=test_file, interface=interface)
    
    try:
        print(f"Starting tcpdump capture on {interface}...")
        tcpdump.start()
        
        # Generate some test traffic
        print("Generating test traffic...")
        for i in range(3):
            subprocess.run(['ping', '-c', '1', '127.0.0.1'], 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1)
        
        print("Stopping tcpdump...")
        tcpdump.stop()
        
        # Check if file was created
        if os.path.exists(test_file):
            file_size = os.path.getsize(test_file)
            print(f"Test successful! Capture file created: {test_file} ({file_size} bytes)")
        else:
            print("Test failed: Capture file not created")
            
    except Exception as e:
        print(f"Test failed with error: {e}")