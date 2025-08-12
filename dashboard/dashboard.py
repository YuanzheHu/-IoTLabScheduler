"""
IoT Lab Scheduler - Main Dashboard Entry Point
Main dashboard application for managing IoT network experiments and device scanning
"""

import streamlit as st
import requests
import pandas as pd
from utils.auto_refresh import setup_auto_refresh
from utils.icon_fix import apply_icon_fixes

# Page configuration
st.set_page_config(
    page_title="IoT Lab Scheduler",
    page_icon="🔬",
    layout="wide"
)

# Apply global fix for Material Design Icons display issue
apply_icon_fixes()

# Setup auto refresh functionality
auto_refresh_enabled = setup_auto_refresh()

# Main dashboard title and description
st.title("🔬 IoT Lab Scheduler")
st.write("Welcome to the IoT Lab Scheduler! Please use the sidebar to navigate to different feature pages.")

# Display auto refresh status if enabled
if auto_refresh_enabled:
    st.success("✅ Auto refresh enabled - Page will update every 3 seconds automatically")

# Device statistics section
st.markdown("## 📊 Device Overview")

try:
    from config import API_URL
except ImportError:
    API_URL = "http://localhost:8000/devices"

def fetch_devices_overview():
    """Fetch devices for overview statistics"""
    try:
        resp = requests.get(API_URL, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        else:
            return []
    except Exception:
        return []

def fetch_port_scan_summary():
    """Fetch port scan summary statistics"""
    try:
        # Fetch scan results from the API
        scan_url = "http://localhost:8000/scan-results"
        resp = requests.get(scan_url, timeout=10)
        if resp.status_code == 200:
            scan_results = resp.json()
            
            # Calculate port scan statistics
            total_scans = len(scan_results)
            port_scans = [s for s in scan_results if s.get('scan_type') == 'port_scan']
            port_scan_count = len(port_scans)
            
            # Calculate port statistics across all scans
            total_ports_found = 0
            open_ports_total = 0
            filtered_ports_total = 0
            closed_ports_total = 0
            open_filtered_ports_total = 0
            
            for scan in port_scans:
                ports = scan.get('ports', [])
                for port in ports:
                    if isinstance(port, dict):
                        state = port.get('state', '')
                        if state == 'open':
                            open_ports_total += 1
                        elif state == 'filtered':
                            filtered_ports_total += 1
                        elif state == 'closed':
                            closed_ports_total += 1
                        elif state == 'open|filtered':
                            open_filtered_ports_total += 1
                        total_ports_found += 1
            
            return {
                'total_scans': total_scans,
                'port_scans': port_scan_count,
                'total_ports': total_ports_found,
                'open_ports': open_ports_total,
                'filtered_ports': filtered_ports_total,
                'closed_ports': closed_ports_total,
                'open_filtered_ports': open_filtered_ports_total
            }
        else:
            return None
    except Exception:
        return None

# Fetch device data
with st.spinner("Loading device statistics..."):
    devices = fetch_devices_overview()

if devices:
    # Calculate device statistics
    total_devices = len(devices)
    online_devices = len([d for d in devices if d.get('status') == 'online'])
    offline_devices = total_devices - online_devices
    
    # Display statistics in columns
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Devices", total_devices)
    
    with col2:
        st.metric("Online Devices", online_devices, delta=f"+{online_devices}")
    
    with col3:
        st.metric("Offline Devices", offline_devices, delta=f"-{offline_devices}")
    
    # Device status chart
    if total_devices > 0:
        st.markdown("### 📈 Device Status Distribution")
        
        # Create status data for chart
        status_data = pd.DataFrame([
            {'Status': 'Online', 'Count': online_devices, 'Color': '#00ff00'},
            {'Status': 'Offline', 'Count': offline_devices, 'Color': '#ff0000'}
        ])
        
        # Display as bar chart
        st.bar_chart(status_data.set_index('Status')['Count'])
        
        # Device list preview (top 5)
        st.markdown("### 🔍 Recent Devices")
        recent_devices = devices[:5]  # Show first 5 devices
        
        for device in recent_devices:
            status_icon = "🟢" if device.get('status') == 'online' else "🔴"
            st.markdown(f"{status_icon} **{device.get('hostname', 'Unknown')}** - {device.get('ip_address', 'N/A')} ({device.get('status', 'unknown')})")
        
        if total_devices > 5:
            st.caption(f"Showing 5 of {total_devices} devices. Use the Devices page to see all devices.")
else:
    st.info("🔍 No devices found. Use the Devices page to scan for IoT devices on your network.")

# Port Scan Summary Section
st.markdown("## 🔍 Port Scan Overview")

port_scan_summary = fetch_port_scan_summary()

if port_scan_summary:
    # Display port scan statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Scans", port_scan_summary['total_scans'])
    
    with col2:
        st.metric("Port Scans", port_scan_summary['port_scans'])
    
    with col3:
        st.metric("Total Ports Found", port_scan_summary['total_ports'])
    
    with col4:
        st.metric("Open Ports", port_scan_summary['open_ports'])
    
    # Port status distribution chart
    st.markdown("### 📊 Port Status Distribution")
    
    port_status_data = pd.DataFrame([
        {'Status': 'Open', 'Count': port_scan_summary['open_ports'], 'Color': '#00ff00'},
        {'Status': 'Filtered', 'Count': port_scan_summary['filtered_ports'], 'Color': '#ffff00'},
        {'Status': 'Closed', 'Count': port_scan_summary['closed_ports'], 'Color': '#ff0000'},
        {'Status': 'Open|Filtered', 'Count': port_scan_summary['open_filtered_ports'], 'Color': '#ffa500'}
    ])
    
    # Display as bar chart
    st.bar_chart(port_status_data.set_index('Status')['Count'])
    
    # Port scan details
    st.markdown("### 📋 Port Scan Details")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**Open Ports:** {port_scan_summary['open_ports']}")
        st.markdown(f"**Filtered Ports:** {port_scan_summary['filtered_ports']}")
    
    with col2:
        st.markdown(f"**Closed Ports:** {port_scan_summary['closed_ports']}")
        st.markdown(f"**Open|Filtered:** {port_scan_summary['open_filtered_ports']}")
else:
    st.info("🔍 No port scan data available. Run port scans on devices to see statistics here.")

# Quick actions section
st.markdown("## ⚡ Quick Actions")
col1, col2 = st.columns(2)

with col1:
    if st.button("📱 Go to Devices", use_container_width=True):
        st.switch_page("pages/devices.py")

with col2:
    if st.button("🧪 Go to Experiments", use_container_width=True):
        st.switch_page("pages/experiments.py")

# System status section
st.markdown("## 🖥️ System Status")
col1, col2 = st.columns(2)

with col1:
    st.markdown("**Services:**")
    st.markdown("✅ Dashboard - Running")
    st.markdown("✅ API Backend - Running")
    st.markdown("✅ Database - Connected")

with col2:
    st.markdown("**Features:**")
    st.markdown("✅ Device Scanning")
    st.markdown("✅ Port Analysis")
    st.markdown("✅ Attack Experiments")
    st.markdown("✅ V2 Engine Support")