"""
配置文件：管理PCAP文件输出路径
"""

import os

# PCAP文件输出路径 - 可以通过环境变量快速修改
PCAP_BASE_DIR = os.getenv("PCAP_BASE_DIR", "data/pcaps")

def get_pcap_dir(target_ip, mac_address=None):
    """生成PCAP文件目录路径"""
    if mac_address:
        safe_mac = mac_address.replace(':', '_')
        pcap_dir = os.path.join(PCAP_BASE_DIR, safe_mac)
    else:
        safe_ip = target_ip.replace(':', '_').replace('.', '_')
        pcap_dir = os.path.join(PCAP_BASE_DIR, safe_ip)
    
    # 确保目录存在
    os.makedirs(pcap_dir, exist_ok=True)
    return pcap_dir

def print_config():
    """打印当前配置信息"""
    print(f"PCAP输出路径: {PCAP_BASE_DIR}")
    print(f"绝对路径: {os.path.abspath(PCAP_BASE_DIR)}")
    print(f"目录存在: {os.path.exists(PCAP_BASE_DIR)}")

if __name__ == "__main__":
    print_config()
