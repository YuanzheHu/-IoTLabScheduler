"""
Configuration file: Manage PCAP file output paths
"""

import os

# PCAP file output base directory - can be overridden by environment variable
PCAP_BASE_DIR = os.getenv("PCAP_BASE_DIR", "data/pcaps")

def get_pcap_dir(target_ip, mac_address=None):
    """Generate the directory path for PCAP files"""
    if mac_address:
        safe_mac = mac_address.replace(':', '_')
        pcap_dir = os.path.join(PCAP_BASE_DIR, safe_mac)
    else:
        safe_ip = target_ip.replace(':', '_').replace('.', '_')
        pcap_dir = os.path.join(PCAP_BASE_DIR, safe_ip)
    
    # Ensure the directory exists
    os.makedirs(pcap_dir, exist_ok=True)
    return pcap_dir

def print_config():
    """Print current configuration information"""
    print(f"PCAP output directory: {PCAP_BASE_DIR}")
    print(f"Absolute path: {os.path.abspath(PCAP_BASE_DIR)}")
    print(f"Directory exists: {os.path.exists(PCAP_BASE_DIR)}")

if __name__ == "__main__":
    print_config()
