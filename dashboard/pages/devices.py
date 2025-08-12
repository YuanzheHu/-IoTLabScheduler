"""
Devices Management Page
Manages and displays IoT devices discovered through network scanning
"""

import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional


def fetch_devices_from_db() -> List[Dict]:
    """
    Fetch devices from the database
    
    Returns:
        List[Dict]: List of device data
    """
    try:
        from config import API_URL
    except ImportError:
        API_URL = "http://localhost:8000/devices"
    
    try:
        # Add trailing slash to avoid 307 redirect
        api_url = API_URL if API_URL.endswith('/') else f"{API_URL}/"
        resp = requests.get(api_url, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        st.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
        return []
    except Exception as e:
        st.error(f"Failed to fetch devices from database: {e}")
        return []


def fetch_devices_scan(subnet: str) -> List[Dict]:
    """
    Scan for devices in the specified subnet
    
    Args:
        subnet (str): Subnet to scan (e.g., "192.168.1.0/24")
        
    Returns:
        List[Dict]: List of discovered devices
    """
    try:
        from config import API_URL
    except ImportError:
        API_URL = "http://localhost:8000/devices"
    
    try:
        # Add trailing slash to avoid 307 redirect
        api_url = API_URL if API_URL.endswith('/') else f"{API_URL}/"
        scan_url = f"{api_url}scan"
        payload = {"subnet": subnet}
        # Increase timeout to 5 minutes for network scanning
        resp = requests.post(scan_url, json=payload, timeout=300)
        
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 500:
            error_detail = resp.json().get('detail', 'Unknown error')
            st.error(f"Backend scan error: {error_detail}")
            return []
        else:
            st.error(f"HTTP error: {resp.status_code} - {resp.text}")
            return []
            
    except requests.exceptions.HTTPError as e:
        st.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
        return []
    except Exception as e:
        st.error(f"Failed to scan devices: {e}")
        return []


def sort_devices_by_status(devices: List[Dict]) -> List[Dict]:
    """
    Sort devices by status (online first, then offline)
    
    Args:
        devices (List[Dict]): List of devices to sort
        
    Returns:
        List[Dict]: Sorted list of devices
    """
    online_devices = [d for d in devices if d.get('status') == 'online']
    offline_devices = [d for d in devices if d.get('status') != 'online']
    return online_devices + offline_devices


def display_devices_compact(devices: List[Dict]) -> None:
    """
    Display devices in a compact card layout
    
    Args:
        devices (List[Dict]): List of devices to display
    """
    st.markdown("""
    <style>
    .device-card {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 12px;
        margin: 8px 0;
        background-color: #fafafa;
        min-height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .device-name {
        font-weight: bold;
        margin-bottom: 8px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .device-info {
        font-size: 0.8em;
        color: #666;
        margin: 4px 0;
    }
    .device-button {
        margin-top: 8px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    cols = st.columns(4)
    for i, device in enumerate(devices):
        col_idx = i % 4
        with cols[col_idx]:
            show_device_card_compact(device)


def show_device_card_compact(device: Dict) -> None:
    """
    Display a single device card in compact format
    
    Args:
        device (Dict): Device data to display
    """
    with st.container():
        hostname = device.get('hostname', 'Unknown Device')
        status = device.get('status', 'unknown')
        mac = device.get('mac_address', 'Unknown')
        ip = device.get('ip_address', '--')
        display_name = hostname[:20] + "..." if len(hostname) > 20 else hostname
        device_info_page = "pages/_device_info.py"
        
        if status == 'online':
            if st.button(f"🟢 **{display_name}**", key=f"device_{mac}", use_container_width=True):
                st.session_state["selected_mac"] = mac
                st.switch_page(device_info_page)
        else:
            if st.button(f"🔴 **{display_name}**", key=f"device_{mac}", use_container_width=True):
                st.session_state["selected_mac"] = mac
                st.switch_page(device_info_page)
        
        st.caption(f"📱 `{mac}`")
        st.caption(f"🌐 {ip}")
        st.markdown("<br>", unsafe_allow_html=True)


def filter_devices(devices: List[Dict], search_term: str) -> List[Dict]:
    """
    Filter devices by search term
    
    Args:
        devices (List[Dict]): List of devices to filter
        search_term (str): Search term to filter by
        
    Returns:
        List[Dict]: Filtered list of devices
    """
    if not search_term:
        return devices
    
    filtered = []
    search_lower = search_term.lower()
    
    for device in devices:
        hostname = device.get('hostname', '').lower()
        mac = device.get('mac_address', '').lower()
        ip = device.get('ip_address', '').lower()
        
        if (search_lower in hostname or 
            search_lower in mac or 
            search_lower in ip):
            filtered.append(device)
    
    return filtered


# Main page content
st.set_page_config(page_title="Devices", layout="wide")
st.title("📱 IoT Devices")

# Device management controls
col1, col2 = st.columns([3, 1])

with col1:
    st.markdown("### 🔍 Device Discovery")
    subnet_input = st.text_input(
        "Enter subnet to scan (e.g., 10.12.0.0/24):",
        value="10.12.0.0/24",
        help="Specify the network subnet to scan for IoT devices"
    )

with col2:
    st.markdown("### ⚡ Actions")
    if st.button("🔍 Scan Network", use_container_width=True):
        try:
            discovered_devices = fetch_devices_scan(subnet_input)
            if discovered_devices and len(discovered_devices) > 0:
                st.success(f"Found {len(discovered_devices)} devices!")
                st.session_state["devices"] = discovered_devices
            else:
                st.warning("No devices found or scan failed")
        except Exception as e:
            st.error(f"Scan failed: {str(e)}")
            st.info("Please check the backend logs for more details")

# Search and filter
search_term = st.text_input(
    "🔍 Search devices:",
    placeholder="Search by hostname, MAC, or IP...",
    help="Filter devices by hostname, MAC address, or IP address"
)

# Fetch and display devices
if "devices" not in st.session_state:
    with st.spinner("Loading devices from database..."):
        devices = fetch_devices_from_db()
        st.session_state["devices"] = devices
else:
    devices = st.session_state["devices"]

# Filter devices by search term
filtered_devices = filter_devices(devices, search_term)

# Sort devices by status (online first)
sorted_devices = sort_devices_by_status(filtered_devices)

# Display device count
if filtered_devices:
    online_count = len([d for d in filtered_devices if d.get('status') == 'online'])
    total_count = len(filtered_devices)
    
    st.markdown(f"### 📋 Device List ({total_count} total, {online_count} online)")
    
    # Pagination
    DEVICES_PER_PAGE = 12
    total_pages = (len(sorted_devices) + DEVICES_PER_PAGE - 1) // DEVICES_PER_PAGE
    page = st.session_state.get('devices_page', 1)
    page = st.number_input('Page', min_value=1, max_value=max(1, total_pages), value=page, step=1, key='devices_page', format='%d')
    
    start_idx = (page - 1) * DEVICES_PER_PAGE
    end_idx = start_idx + DEVICES_PER_PAGE
    page_devices = sorted_devices[start_idx:end_idx]
    
    # Display devices in compact format with pagination
    display_devices_compact(page_devices)
    st.caption(f"Page {page} of {total_pages}")
    
else:
    st.info("🔍 No devices found. Use the scan button to discover devices on your network.") 