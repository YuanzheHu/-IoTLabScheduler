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

    def __init__(self, output_file='capture.pcap', interface='any', extra_args=None):
        """Initialize TcpdumpUtil.
        
        Args:
            output_file (str): Output file for captured packets
            interface (str): Network interface to capture on ('any' for all interfaces)
            extra_args (list): Additional tcpdump arguments
        """
        self.output_file = output_file
        self.interface = interface
        self.extra_args = extra_args or []
        self.process = None

    def start(self):
        """Start the tcpdump process with bidirectional capture."""
        if self.process is not None:
            raise RuntimeError('tcpdump is already running')
        
        # Build command with options for bidirectional capture
        cmd = [
            'tcpdump',
            '-i', self.interface,
            '-w', self.output_file,
            '-s', '0',  # Capture full packet size
            '-n',  # Don't resolve hostnames
            '-v'   # Verbose output
        ]
        
        # Add extra arguments
        cmd.extend(self.extra_args)
        
        self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid)

    def stop(self):
        """Stop the tcpdump process."""
        if self.process is None:
            raise RuntimeError('tcpdump is not running')
            
        os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
        self.process.wait()
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
            print(f"✅ Test successful! Capture file created: {test_file} ({file_size} bytes)")
        else:
            print("❌ Test failed: Capture file not created")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")