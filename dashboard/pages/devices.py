import streamlit as st
import requests
import pandas as pd
from datetime import datetime

def fetch_devices_from_db():
    try:
        from config import API_URL
    except ImportError:
        API_URL = "http://localhost:8000/devices"
    try:
        resp = requests.get(API_URL, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        st.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
        return []
    except Exception as e:
        st.error(f"Failed to fetch devices from database: {e}")
        return []

def fetch_devices_scan(subnet):
    try:
        from config import API_URL
    except ImportError:
        API_URL = "http://localhost:8000/devices"
    try:
        scan_url = f"{API_URL}/scan"
        payload = {"subnet": subnet}
        resp = requests.post(scan_url, json=payload, timeout=300)  # 增加超时时间到5分钟
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        st.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
        return []
    except Exception as e:
        st.error(f"Failed to scan devices: {e}")
        return []

def sort_devices_by_status(devices):
    online_devices = [d for d in devices if d.get('status') == 'online']
    offline_devices = [d for d in devices if d.get('status') != 'online']
    return online_devices + offline_devices

def display_devices_compact(devices):
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

def show_device_card_compact(device):
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

def filter_devices(devices, search_term):
    if not search_term:
        return devices
    filtered = []
    search_lower = search_term.lower()
    for device in devices:
        if (search_lower in device.get('mac_address', '').lower() or
            search_lower in device.get('hostname', '').lower() or
            search_lower in device.get('ip_address', '').lower()):
            filtered.append(device)
    return filtered

# =================== UI 逻辑 ===================

st.set_page_config(page_title="Devices")
st.title("📱 Devices")

# 移除 show_device_details 相关逻辑
if st.session_state.get('show_device_details', False):
    pass  # 详情页已迁移到 device_info.py

# Scan configuration
col1, col2, col3 = st.columns([3, 1, 1])
with col1:
    subnet = st.text_input(
        "Subnet to scan",
        value="193.60.241.96/27",
        help="Enter subnet in CIDR notation (e.g., 193.60.241.96/27 for current network)"
    )
with col2:
    scan_button = st.button("🔍 Scan", type="primary")
with col3:
    auto_scan = st.checkbox("Auto scan", value=False)

# Trigger scan from sidebar
if st.session_state.get('trigger_scan', False):
    scan_button = True
    st.session_state['trigger_scan'] = False

# Always fetch devices on page load or refresh
devices = []
if scan_button or auto_scan:
    with st.spinner("Scanning network..."):
        devices = fetch_devices_scan(subnet)
        st.session_state['devices'] = devices
else:
    with st.spinner("Loading devices..."):
        devices = fetch_devices_from_db()
        st.session_state['devices'] = devices

# Sort devices: online first, then offline
devices = sort_devices_by_status(devices)

# Show device count
if devices:
    online_count = sum(1 for d in devices if d.get('status') == 'online')
    total_count = len(devices)
    st.success(f"Found {total_count} devices ({online_count} online, {total_count - online_count} offline)")

# Search functionality
search = st.text_input("🔍 Search devices", placeholder="Search by MAC, name, or IP")
if search:
    devices = filter_devices(devices, search)

# Display devices in a more compact layout
if devices:
    # 分页参数
    DEVICES_PER_PAGE = 12
    total_pages = (len(devices) + DEVICES_PER_PAGE - 1) // DEVICES_PER_PAGE
    page = st.session_state.get('devices_page', 1)
    page = st.number_input('Page', min_value=1, max_value=total_pages, value=page, step=1, key='devices_page', format='%d')
    start_idx = (page - 1) * DEVICES_PER_PAGE
    end_idx = start_idx + DEVICES_PER_PAGE
    display_devices_compact(devices[start_idx:end_idx])
    st.caption(f"Page {page} of {total_pages}")
else:
    st.info("No devices found. Click 'Scan' to discover devices on your network.") 