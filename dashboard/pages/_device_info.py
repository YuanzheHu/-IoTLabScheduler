"""
Device Information Page
Detailed view and management of individual IoT devices
"""

import streamlit as st
import requests
import urllib.parse
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import datetime
from typing import Dict, List, Optional, Any
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.icon_fix import apply_icon_fixes

# Import configuration
try:
    from config import API_URL, EXPERIMENTS_URL, CAPTURES_URL
except ImportError:
    API_URL = "http://localhost:8000/devices"
    EXPERIMENTS_URL = "http://localhost:8000/experiments"
    CAPTURES_URL = "http://localhost:8000/captures"

# Page configuration
st.set_page_config(
    page_title="Device Info",
    page_icon="📋",
    layout="wide"
)

st.title("📋 Device Details")

# Apply icon fixes
apply_icon_fixes()

# Auto refresh configuration
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("### 📊 Device Monitoring Console")
with col2:
    auto_refresh = st.checkbox("🔄 Auto Refresh", value=True, help="Enable automatic page refresh")

# Get selected device MAC from session state
mac = st.session_state.get("selected_mac", None)

if not mac:
    st.error("No device specified. Please select a device from the device list.")
    st.stop()


def fetch_device_by_mac(mac: str) -> Optional[Dict[str, Any]]:
    """
    Fetch device information by MAC address
    
    Args:
        mac (str): MAC address string
        
    Returns:
        Optional[Dict[str, Any]]: Device information as a dictionary, or None if not found
    """
    try:
        url = f"{API_URL}/mac/{urllib.parse.quote(mac)}"
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"Failed to fetch device info: {e}")
        return None


# Fetch device information
device = fetch_device_by_mac(mac)
if not device:
    st.error("Device not found.")
    st.stop()

# Navigation back to devices list
if st.button("← Back to Devices", use_container_width=True):
    st.switch_page("pages/devices.py")

# Device details section
with st.expander("📋 Device Details", expanded=True):
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(f"**Device Name:** {device.get('hostname', 'Unknown')}")
        st.markdown(f"**MAC Address:** `{device.get('mac_address', 'Unknown')}`")
        st.markdown(f"**IP Address:** {device.get('ip_address', '--')}")
        
        status = device.get('status', 'unknown')
        if status == 'online':
            st.success("🟢 **Status: Online**")
        else:
            st.error("🔴 **Status: Offline**")
    
    with col2:
        st.markdown("**Device Type:** IoT Device")
        
        # Process last seen timestamp
        last_seen_raw = device.get('last_seen', None)
        if last_seen_raw:
            try:
                if isinstance(last_seen_raw, (int, float)):
                    last_seen_dt = datetime.datetime.fromtimestamp(last_seen_raw)
                else:
                    last_seen_dt = datetime.datetime.fromisoformat(last_seen_raw.replace('Z', '+00:00'))
                last_seen_str = last_seen_dt.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                last_seen_str = str(last_seen_raw)
        else:
            last_seen_str = 'Unknown'
        
        st.markdown(f"**Last Seen:** {last_seen_str}")
        st.markdown("**Network:** Local subnet")

# --- Port Information Section ---
if device.get('ip_address') and device.get('status') == 'online':
    with st.expander("🔍 Port Information", expanded=True):

        def fetch_latest_port_scan(device_id: str) -> Optional[Dict[str, Any]]:
            """
            Fetch the latest port scan result for a device
            
            Args:
                device_id (str): Device ID of the device
                
            Returns:
                Optional[Dict[str, Any]]: Latest port scan result as a dictionary, or None if not found
            """
            try:
                scan_history_url = (
                    f"http://localhost:8000/scan-results/device/{device_id}/latest?scan_type=port_scan"
                )
                resp = requests.get(scan_history_url, timeout=10)
                if resp.status_code == 200:
                    result = resp.json()
                    # Validate returned data structure
                    if result and isinstance(result, dict) and result.get('ports'):
                        return result
                return None
            except Exception as e:
                st.error(f"Failed to fetch port scan data: {e}")
                return None

        # Create device-specific session state keys
        device_id = device.get('id')
        device_mac = device.get('mac_address')
        scan_completed_key = f"scan_completed_{device_id}"
        scan_result_key = f"latest_scan_result_{device_id}"
        scan_timestamp_key = f"scan_timestamp_{device_id}"
        
        # Check if current device has new scan results
        if st.session_state.get(scan_completed_key, False) and st.session_state.get(scan_result_key):
            # Use the fresh scan result from session state for this specific device
            latest_scan = st.session_state[scan_result_key]
            scan_source = "Fresh scan"
        else:
            # Fetch from database
            latest_scan = fetch_latest_port_scan(device_id)
            scan_source = "Database"
        
        # Add a button to manually refresh the plots if needed
        if st.session_state.get(scan_completed_key, False):
            if st.button("🔄 Refresh Plots", key=f"refresh_plots_{device_id}"):
                st.rerun()

        # Improved data validation: ensure valid port data
        if latest_scan and latest_scan.get('ports') and len(latest_scan.get('ports', [])) > 0:
            ports = latest_scan.get('ports', [])
            
            # Validate port data validity
            valid_ports = []
            for port in ports:
                if isinstance(port, dict) and port.get('port') and port.get('state'):
                    valid_ports.append(port)
            
            if not valid_ports:
                st.warning("⚠️ Port scan data format is invalid. Please run a new scan.")
                st.info("📊 No valid port scan data available. Click '🔍 Port Scan' to scan this device.")
            else:
                ports = valid_ports
                
                # Show scan source and timestamp with device info
                if scan_source == "Fresh scan":
                    scan_time = st.session_state.get(scan_timestamp_key, "")
                    if scan_time:
                        try:
                            scan_dt = datetime.datetime.fromisoformat(scan_time)
                            scan_time_str = scan_dt.strftime('%Y-%m-%d %H:%M:%S')
                            st.success(f"🔄 Showing fresh scan results for {device.get('ip_address')} from {scan_time_str}")
                        except Exception:
                            st.success(f"🔄 Showing fresh scan results for {device.get('ip_address')}")
                
                # Process port data
                open_ports = [p for p in ports if p.get('state') == 'open']
                filtered_ports = [p for p in ports if p.get('state') == 'filtered']
                closed_ports = [p for p in ports if p.get('state') == 'closed']
                open_filtered_ports = [p for p in ports if p.get('state') == 'open|filtered']
                
                # Improved protocol detection function
                def get_protocol(port_str: str) -> str:
                    """
                    Extract protocol from port string like '80/tcp' or '53/udp'
                    
                    Args:
                        port_str (str): Port string with protocol
                        
                    Returns:
                        str: Protocol (tcp/udp)
                    """
                    if isinstance(port_str, str) and '/' in port_str:
                        return port_str.split('/')[1].lower()
                    return 'tcp'  # Default to tcp if no protocol specified
                
                # Separate TCP and UDP ports with improved detection
                tcp_ports = [p for p in ports if get_protocol(p.get('port', '')) == 'tcp']
                udp_ports = [p for p in ports if get_protocol(p.get('port', '')) == 'udp']
                
                # Calculate statistics - only count truly open ports
                total_ports = len(ports)
                open_count = len(open_ports)  # Only count truly open ports
                tcp_count = len(tcp_ports)
                udp_count = len(udp_ports)
                tcp_percentage = (tcp_count / total_ports * 100) if total_ports > 0 else 0
                udp_percentage = (udp_count / total_ports * 100) if total_ports > 0 else 0
                
                # Display device info and statistics cards
                st.markdown(f"### 📊 Port Scan Results for {device.get('ip_address')} ({device.get('hostname', 'Unknown')})")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Ports", total_ports)
                with col2:
                    st.metric("Open Ports", open_count, delta=f"{open_count} active")
                with col3:
                    st.metric("TCP Ports", tcp_count, delta=f"{tcp_percentage:.1f}%")
                with col4:
                    st.metric("UDP Ports", udp_count, delta=f"{udp_percentage:.1f}%")
                
                # Create grouped bar chart for port status distribution
                st.markdown("### 📊 Port Status Distribution")
                
                # Prepare data for grouped bar chart
                port_ranges = {
                    'System Ports (0-1023)': (0, 1023),
                    'User Ports (1024-65535)': (1024, 65535)
                }
                
                chart_data = []
                for range_name, (start, end) in port_ranges.items():
                    # Filter ports in this range with better error handling
                    range_ports = []
                    for p in ports:
                        try:
                            port_num = p.get('port', '0')
                            if isinstance(port_num, str) and '/' in port_num:
                                port_num = port_num.split('/')[0]
                            port_int = int(port_num)
                            if start <= port_int <= end:
                                range_ports.append(p)
                        except (ValueError, TypeError):
                            continue
                    
                    # Count by protocol and state with improved detection
                    tcp_open = len([p for p in range_ports if get_protocol(p.get('port', '')) == 'tcp' and p.get('state') == 'open'])
                    tcp_closed = len([p for p in range_ports if get_protocol(p.get('port', '')) == 'tcp' and p.get('state') == 'closed'])
                    tcp_filtered = len([p for p in range_ports if get_protocol(p.get('port', '')) == 'tcp' and p.get('state') == 'filtered'])
                    tcp_open_filtered = len([p for p in range_ports if get_protocol(p.get('port', '')) == 'tcp' and p.get('state') == 'open|filtered'])
                    
                    udp_open = len([p for p in range_ports if get_protocol(p.get('port', '')) == 'udp' and p.get('state') == 'open'])
                    udp_closed = len([p for p in range_ports if get_protocol(p.get('port', '')) == 'udp' and p.get('state') == 'closed'])
                    udp_filtered = len([p for p in range_ports if get_protocol(p.get('port', '')) == 'udp' and p.get('state') == 'filtered'])
                    udp_open_filtered = len([p for p in range_ports if get_protocol(p.get('port', '')) == 'udp' and p.get('state') == 'open|filtered'])
                    
                    chart_data.extend([
                        {'Port Range': range_name, 'Protocol': 'TCP', 'State': 'Open', 'Count': tcp_open},
                        {'Port Range': range_name, 'Protocol': 'TCP', 'State': 'Closed', 'Count': tcp_closed},
                        {'Port Range': range_name, 'Protocol': 'TCP', 'State': 'Filtered', 'Count': tcp_filtered},
                        {'Port Range': range_name, 'Protocol': 'TCP', 'State': 'Open|Filtered', 'Count': tcp_open_filtered},
                        {'Port Range': range_name, 'Protocol': 'UDP', 'State': 'Open', 'Count': udp_open},
                        {'Port Range': range_name, 'Protocol': 'UDP', 'State': 'Closed', 'Count': udp_closed},
                        {'Port Range': range_name, 'Protocol': 'UDP', 'State': 'Filtered', 'Count': udp_filtered},
                        {'Port Range': range_name, 'Protocol': 'UDP', 'State': 'Open|Filtered', 'Count': udp_open_filtered},
                    ])
                
                # 只有当有数据时才创建图表
                if any(item['Count'] > 0 for item in chart_data):
                    df_chart = pd.DataFrame(chart_data)
                    
                    # Create grouped bar chart with device info in title
                    fig = px.bar(
                        df_chart,
                        x='Port Range',
                        y='Count',
                        color='State',
                        barmode='group',
                        facet_col='Protocol',
                        color_discrete_map={
                            'Open': '#00ff00',
                            'Closed': '#ff0000', 
                            'Filtered': '#ffff00',
                            'Open|Filtered': '#ffa500'  # Orange for Open|Filtered
                        },
                    )
                    
                    fig.update_layout(
                        height=500,
                        showlegend=True,
                        title=f"Port Status Distribution - {device.get('ip_address')} ({device.get('hostname', 'Unknown')})",
                        xaxis_title="Port Range",
                        yaxis_title="Number of Ports"
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("📊 No port data available for charts. All ports may be in the same state.")
                
                # Service distribution chart with status information
                st.markdown("### 🔧 Service Distribution")
                
                # Count services by status
                service_status_counts = {}
                for port in ports:
                    service = port.get('service', 'unknown')
                    state = port.get('state', 'unknown')
                    
                    if service not in service_status_counts:
                        service_status_counts[service] = {'open': 0, 'closed': 0, 'filtered': 0, 'open|filtered': 0}
                    
                    # Handle composite states like 'Open|Filtered'
                    if '|' in state:
                        # Special handling for 'Open|Filtered' state
                        if state.lower() == 'open|filtered':
                            service_status_counts[service]['open|filtered'] += 1
                        else:
                            # Split other composite states and count each part
                            states = state.split('|')
                            for s in states:
                                s = s.strip().lower()
                                if s in service_status_counts[service]:
                                    service_status_counts[service][s] += 1
                    else:
                        # Single state
                        state_lower = state.lower()
                        if state_lower in service_status_counts[service]:
                            service_status_counts[service][state_lower] += 1
                
                if service_status_counts:
                    # Prepare data for stacked bar chart
                    service_data = []
                    for service, status_counts in service_status_counts.items():
                        total_count = sum(status_counts.values())
                        if total_count > 0:  # Only include services with ports
                            service_data.extend([
                                {'Service': service, 'Status': 'Open', 'Count': status_counts['open']},
                                {'Service': service, 'Status': 'Closed', 'Count': status_counts['closed']},
                                {'Service': service, 'Status': 'Filtered', 'Count': status_counts['filtered']},
                                {'Service': service, 'Status': 'Open|Filtered', 'Count': status_counts['open|filtered']}
                            ])
                    
                    # Sort by total count
                    service_totals = {}
                    for service, status_counts in service_status_counts.items():
                        service_totals[service] = sum(status_counts.values())
                    
                    # Sort services by total count
                    sorted_services = sorted(service_totals.items(), key=lambda x: x[1], reverse=True)
                    service_order = [service for service, _ in sorted_services]
                    
                    df_services = pd.DataFrame(service_data)
                    
                    # Create stacked bar chart with device info in title
                    fig2 = px.bar(
                        df_services,
                        x='Service',
                        y='Count',
                        color='Status',
                        color_discrete_map={
                            'Open': '#00ff00',
                            'Closed': '#ff0000',
                            'Filtered': '#ffff00',
                            'Open|Filtered': '#ffa500'  # Orange for Open|Filtered
                        },
                        barmode='stack'
                    )
                    
                    fig2.update_layout(
                        height=400,
                        title=f"Service Distribution - {device.get('ip_address')} ({device.get('hostname', 'Unknown')})",
                        xaxis_title="Service Name",
                        yaxis_title="Number of Ports",
                        xaxis={'categoryorder': 'array', 'categoryarray': service_order}
                    )
                    
                    fig2.update_xaxes(tickangle=45)
                    
                    st.plotly_chart(fig2, use_container_width=True)
                    
                    # Add service statistics
                    st.markdown("#### 📊 Service Statistics")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        open_services = len([s for s, counts in service_status_counts.items() if counts['open'] > 0])
                        st.metric("Services with Open Ports", open_services)
                    
                    with col2:
                        total_services = len(service_status_counts)
                        st.metric("Total Services", total_services)
                    
                    with col3:
                        avg_ports_per_service = sum(service_totals.values()) / len(service_totals) if service_totals else 0
                        st.metric("Avg Ports per Service", f"{avg_ports_per_service:.1f}")
                    
                    # Add statistics for Open|Filtered states (removed info message)
                    total_open_filtered = sum(counts['open|filtered'] for counts in service_status_counts.values())
                
                # Detailed port table
                st.markdown("### 📋 Port Details")
                
                # Add filters
                col1, col2, col3 = st.columns(3)
                with col1:
                    protocol_filter = st.selectbox(
                        "Protocol Filter",
                        ["All", "TCP", "UDP"],
                        key=f"protocol_filter_{device_id}"
                    )
                with col2:
                    state_filter = st.selectbox(
                        "State Filter", 
                        ["All", "Open", "Closed", "Filtered", "Open|Filtered"],
                        key=f"state_filter_{device_id}"
                    )
                with col3:
                    service_filter = st.text_input(
                        "Service Filter",
                        placeholder="Enter service name...",
                        key=f"service_filter_{device_id}"
                    )
                
                # Filter ports based on selections
                filtered_ports_list = ports.copy()
                
                if protocol_filter != "All":
                    filtered_ports_list = [p for p in filtered_ports_list 
                                        if protocol_filter.lower() in p.get('port', '').lower()]
                
                if state_filter != "All":
                    filtered_ports_list = [p for p in filtered_ports_list 
                                        if p.get('state', '').lower() == state_filter.lower()]
                
                if service_filter:
                    filtered_ports_list = [p for p in filtered_ports_list 
                                        if service_filter.lower() in p.get('service', '').lower()]
                
                # Create table data
                table_data = []
                for port in filtered_ports_list:
                    try:
                        port_num = port.get('port', '').split('/')[0]
                        protocol = port.get('port', '').split('/')[1] if '/' in port.get('port', '') else 'tcp'
                        state = port.get('state', 'unknown')
                        service = port.get('service', 'unknown')
                        
                        status_color = {
                            'open': '🟢',
                            'closed': '🔴',
                            'filtered': '🟡',
                            'open|filtered': '🟠',  # Orange circle for Open|Filtered
                        }.get(state.lower(), '⚪')
                        
                        table_data.append({
                            'Status': status_color,
                            'Port': port_num,
                            'Protocol': protocol.upper(),
                            'State': state.title(),
                            'Service': service,
                        })
                    except Exception:
                        continue
                
                if table_data:
                    df_table = pd.DataFrame(table_data)
                    st.dataframe(
                        df_table, 
                        use_container_width=True,
                        column_config={
                            "Status": st.column_config.TextColumn("Status", width="small"),
                            "Port": st.column_config.NumberColumn("Port", width="small"),
                            "Protocol": st.column_config.TextColumn("Protocol", width="small"),
                            "State": st.column_config.TextColumn("State", width="small"),
                            "Service": st.column_config.TextColumn("Service", width="medium"),
                        }
                    )
                    st.caption(f"Showing {len(table_data)} of {len(ports)} ports")
                else:
                    st.info("No ports match the selected filters")
                
                # Show scan timestamp
                if scan_source == "Fresh scan":
                    scan_time = st.session_state.get(scan_timestamp_key, "")
                    if scan_time:
                        try:
                            scan_dt = datetime.datetime.fromisoformat(scan_time)
                            scan_time_str = scan_dt.strftime('%Y-%m-%d %H:%M:%S')
                            st.caption(f"📅 Fresh scan completed: {scan_time_str}")
                        except Exception:
                            st.caption(f"📅 Fresh scan completed")
                else:
                    scan_time = latest_scan.get('scan_time', '')
                    if scan_time:
                        try:
                            scan_dt = datetime.datetime.fromisoformat(scan_time.replace('Z', '+00:00'))
                            scan_time_str = scan_dt.strftime('%Y-%m-%d %H:%M:%S')
                            st.caption(f"📅 Last scanned: {scan_time_str}")
                        except Exception:
                            st.caption(f"📅 Last scanned: {scan_time}")
        else:
            # 改进错误提示
            if latest_scan is None:
                st.info("📊 No port scan data available. Click '🔍 Port Scan' to scan this device.")
            elif not latest_scan.get('ports'):
                st.info("📊 Port scan completed but no ports found. The device may have no open ports or the scan may have failed.")
            else:
                st.info("📊 No port scan data available. Click '🔍 Port Scan' to scan this device.")

# --- Actions Section ---
with st.expander("⚡ Actions", expanded=True):
    if device.get('ip_address') and device.get('status') == 'online':
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🔍 Port Scan", use_container_width=True, key="port_scan_btn"):
                st.session_state["active_action"] = "port_scan"
                # 重置其他action的状态
                st.session_state["show_port_scan"] = True
                st.session_state["show_os_scan"] = False
                st.session_state["show_dos_form"] = False

        with col2:
            if st.button("🖥️ OS Scan", use_container_width=True, key="os_scan_btn"):
                st.session_state["active_action"] = "os_scan"
                # 重置其他action的状态
                st.session_state["show_port_scan"] = False
                st.session_state["show_os_scan"] = True
                st.session_state["show_dos_form"] = False

        with col3:
            if st.button("🚀 DoS Attack", use_container_width=True, key="dos_btn"):
                st.session_state["active_action"] = "dos_attack"
                # 重置其他action的状态
                st.session_state["show_port_scan"] = False
                st.session_state["show_os_scan"] = False
                st.session_state["show_dos_form"] = True

        # Port Scan Form
        if st.session_state.get("show_port_scan", False):
            st.markdown(
                """
                <style>
                .scan-form .stTextInput>div>div>input,
                .scan-form .stNumberInput>div>div>input {
                    background-color: #f7f7fa;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )

            with st.form(key="port_scan_form"):
                st.markdown(
                    f"<div class='scan-form'><b>🔍 Port Scan for {device.get('hostname', 'Device')} ({device.get('ip_address')})</b></div>",
                    unsafe_allow_html=True,
                )

                scan_ports = st.text_input(
                    "Ports to scan (optional)",
                    placeholder="e.g., 80,443,22,8080 or leave empty for default scan",
                    help="Comma-separated port list. Leave empty for default fast scan.",
                )

                fast_scan = st.checkbox(
                    "Fast scan mode",
                    value=True,
                    help="Use faster scan options (recommended)",
                )

                col1, col2 = st.columns(2)
                with col1:
                    start_port_scan = st.form_submit_button("Start Port Scan", use_container_width=True)
                with col2:
                    cancel_port_scan = st.form_submit_button("Cancel", use_container_width=True)

                if cancel_port_scan:
                    st.session_state["show_port_scan"] = False
                    st.session_state["active_action"] = None
                    st.rerun()

                if start_port_scan:
                    with st.spinner("🔍 Scanning ports..."):
                        try:
                            url = f"{API_URL}/{device.get('ip_address')}/portscan"
                            params = {"fast_scan": fast_scan}
                            if scan_ports.strip():
                                params["ports"] = scan_ports

                            resp = requests.get(url, params=params, timeout=60)
                            if resp.status_code == 200:
                                scan_result = resp.json()

                                # Store scan result in session state for immediate display
                                st.session_state["latest_scan_result"] = scan_result
                                st.session_state["scan_completed"] = True
                                st.session_state["scan_timestamp"] = datetime.datetime.now().isoformat()

                                st.success(
                                    f"✅ Port scan completed in {scan_result.get('scan_duration', 0):.2f} seconds!"
                                )

                                # Show scan results in the form area (before hiding form)
                                if scan_result.get('ports'):
                                    st.markdown("### 📊 Scan Results")

                                    total_ports = len(scan_result['ports'])
                                    tcp_ports = [p for p in scan_result['ports'] if '/tcp' in p['port']]
                                    udp_ports = [p for p in scan_result['ports'] if '/udp' in p['port']]

                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.metric("Total Open Ports", total_ports)
                                    with col2:
                                        st.metric("TCP Ports", len(tcp_ports))
                                    with col3:
                                        st.metric("UDP Ports", len(udp_ports))

                                    if tcp_ports:
                                        st.markdown("**🔴 TCP Ports:**")
                                        for port in tcp_ports:
                                            st.code(f"{port['port']} - {port.get('service', 'unknown')}")

                                    if udp_ports:
                                        st.markdown("**🔵 UDP Ports:**")
                                        for port in udp_ports:
                                            st.code(f"{port['port']} - {port.get('service', 'unknown')}")

                                    with st.expander("📋 Raw Scan Output"):
                                        st.code(scan_result.get('raw_output', 'No output available'))
                                else:
                                    st.info("No open ports found.")

                                # Keep the scan form visible to show results
                                # Don't hide the form and don't rerun to preserve raw output display
                                
                                # Add a done button to close the form
                                if st.button("✅ Done", key="port_scan_done"):
                                    st.session_state["show_port_scan"] = False
                                    st.session_state["active_action"] = None
                                    st.rerun()

                            else:
                                st.error(f"Port scan failed: {resp.text}")
                        except Exception as e:
                            st.error(f"Error during port scan: {e}")

        # OS Scan Form
        if st.session_state.get("show_os_scan", False):
            st.markdown(
                """
                <style>
                .scan-form .stTextInput>div>div>input,
                .scan-form .stNumberInput>div>div>input {
                    background-color: #f7f7fa;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )

            with st.form(key="os_scan_form"):
                st.markdown(
                    f"<div class='scan-form'><b>🖥️ OS Fingerprint for {device.get('hostname', 'Device')} ({device.get('ip_address')})</b></div>",
                    unsafe_allow_html=True,
                )

                os_scan_ports = st.text_input(
                    "Ports for OS detection (optional)",
                    value="22,80,443",
                    placeholder="e.g., 22,80,443",
                    help="Ports to use for OS fingerprinting. Default: 22,80,443",
                )

                os_fast_scan = st.checkbox(
                    "Fast OS scan mode",
                    value=True,
                    help="Use faster OS detection options (recommended)",
                )

                col1, col2 = st.columns(2)
                with col1:
                    start_os_scan = st.form_submit_button("Start OS Scan", use_container_width=True)
                with col2:
                    cancel_os_scan = st.form_submit_button("Cancel", use_container_width=True)

                if cancel_os_scan:
                    st.session_state["show_os_scan"] = False
                    st.session_state["active_action"] = None
                    st.rerun()

                if start_os_scan:
                    with st.spinner("🖥️ Detecting operating system..."):
                        try:
                            url = f"{API_URL}/{device.get('ip_address')}/oscan"
                            params = {"fast_scan": os_fast_scan}
                            if os_scan_ports.strip():
                                params["ports"] = os_scan_ports

                            resp = requests.get(url, params=params, timeout=60)
                            if resp.status_code == 200:
                                os_result = resp.json()

                                st.success(
                                    f"✅ OS scan completed in {os_result.get('scan_duration', 0):.2f} seconds!"
                                )

                                st.markdown("### 🖥️ OS Detection Results")

                                os_guesses = os_result.get('os_guesses', [])
                                if os_guesses:
                                    st.markdown("**🎯 OS Guesses:**")
                                    for i, guess in enumerate(os_guesses, 1):
                                        st.info(f"{i}. {guess}")
                                else:
                                    st.warning("No OS information detected.")

                                os_details = os_result.get('os_details', {})
                                if os_details:
                                    st.markdown("**📋 OS Details:**")
                                    for key, value in os_details.items():
                                        st.code(f"{key}: {value}")

                                with st.expander("📋 Raw OS Scan Output"):
                                    st.code(os_result.get('raw_output', 'No output available'))
                                
                                # Add a done button to close the form
                                if st.button("✅ Done", key="os_scan_done"):
                                    st.session_state["show_os_scan"] = False
                                    st.session_state["active_action"] = None
                                    st.rerun()

                            else:
                                st.error(f"OS scan failed: {resp.text}")
                        except Exception as e:
                            st.error(f"Error during OS scan: {e}")

        # Experiment Monitoring Section
        st.markdown("### 🔬 Experiment Monitoring")
        
        # Check for active experiments for this device
        active_experiments = []
        for key, value in st.session_state.items():
            if key.startswith("experiment_") and value.get("target_ip") == device.get('ip_address'):
                active_experiments.append(value)
        
        if active_experiments:
            st.info(f"📊 Found {len(active_experiments)} active experiment(s) for this device")
            
            for exp in active_experiments:
                with st.expander(f"🔬 {exp['name']} (ID: {exp['id']})", expanded=False):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Experiment ID", exp['id'])
                        st.metric("Target IP", exp['target_ip'])
                    with col2:
                        st.metric("Attack Mode", exp['attack_mode'].upper())
                        st.metric("Total Cycles", exp['cycles'])
                    with col3:
                        start_time = datetime.datetime.fromisoformat(exp['start_time'])
                        st.metric("Start Time", start_time.strftime('%H:%M:%S'))
                        
                        # Add refresh button to check current status
                        if st.button(f"🔄 Refresh Status", key=f"refresh_exp_{exp['id']}"):
                            try:
                                status_resp = requests.get(f"{EXPERIMENTS_URL}/{exp['id']}/status/v2", timeout=10)
                                if status_resp.status_code == 200:
                                    status_data = status_resp.json()
                                    st.success(f"✅ Status: {status_data.get('status', 'Unknown')}")
                                    st.info(f"📈 Progress: {status_data.get('progress', 'N/A')}")
                                    
                                    # Update session state with latest info
                                    exp.update({
                                        "status": status_data.get('status'),
                                        "current_cycle": status_data.get('current_cycle'),
                                        "progress": status_data.get('progress')
                                    })
                                else:
                                    st.error(f"❌ Failed to fetch status: {status_resp.text}")
                            except Exception as e:
                                st.error(f"❌ Error fetching status: {e}")
        
        # DoS Attack Experiment Form V2
        if st.session_state.get("show_dos_form", False):
            st.markdown(
                """
                <style>
                .dos-form .stTextInput>div>div>input,
                .dos-form .stNumberInput>div>div>input,
                .dos-form .stSelectbox>div>div>select {
                    background-color: #f7f7fa;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )

            with st.form(key="dos_attack_form_v2"):
                st.markdown(
                    f"<div class='dos-form'><b>🚀 Start a DoS Attack Experiment V2 on this device</b></div>",
                    unsafe_allow_html=True,
                )
                
                # Basic configuration
                dos_name = st.text_input(
                    "Experiment Name", value=f"DoS V2 on {device.get('hostname', 'Device')}"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    attack_type = st.selectbox(
                        "Attack Type",
                        ["syn_flood", "udp_flood", "icmp_flood", "tcp_flood", "ip_frag_flood"],
                        index=0,
                    )
                    attack_mode = st.selectbox(
                        "Attack Mode",
                        ["single", "cyclic"],
                        index=0,
                        help="Single: One-time attack, Cyclic: Repeated attacks with settle time"
                    )
                
                with col2:
                    dos_port = st.number_input(
                        "Port", value=55443, min_value=1, max_value=65535
                    )
                    interface = st.selectbox(
                        "Network Interface",
                        ["wlan0", "eth0", "any"],
                        index=0,
                        help="Select network interface for the attack"
                    )
                
                # Duration and timing configuration
                col1, col2, col3 = st.columns(3)
                with col1:
                    dos_duration = st.number_input(
                        "Attack Duration (sec)", 
                        value=60, 
                        min_value=1, 
                        max_value=3600,
                        help="Duration of each attack cycle"
                    )
                
                with col2:
                    cycles = st.number_input(
                        "Cycles", 
                        value=1, 
                        min_value=1, 
                        max_value=100,
                        help="Number of attack cycles (for cyclic mode)"
                    )
                
                with col3:
                    settle_time = st.number_input(
                        "Settle Time (sec)", 
                        value=30, 
                        min_value=0, 
                        max_value=300,
                        help="Time between attack cycles"
                    )
                
                # Show total estimated time
                if attack_mode == "cyclic" and cycles > 1:
                    total_time = (dos_duration * cycles) + (settle_time * (cycles - 1))
                    st.info(f"⏱️ Total estimated time: {total_time} seconds ({total_time/60:.1f} minutes)")
                
                # Action buttons
                col1, col2 = st.columns(2)
                with col1:
                    submitted = st.form_submit_button("🚀 Start DoS Attack V2", use_container_width=True)
                with col2:
                    cancel = st.form_submit_button("❌ Cancel", use_container_width=True)

                if cancel:
                    st.session_state["show_dos_form"] = False
                    st.session_state["active_action"] = None
                    st.rerun()

                if submitted:
                    # Prepare payload for V2 API
                    payload = {
                        "name": dos_name,
                        "attack_type": attack_type,
                        "target_ip": device.get('ip_address'),
                        "port": dos_port,
                        "duration_sec": dos_duration,
                        "interface": interface,
                        "attack_mode": attack_mode,
                        "cycles": cycles,
                        "settle_time_sec": settle_time
                    }
                    
                    try:
                        # Use V2 API endpoint
                        resp = requests.post(f"{EXPERIMENTS_URL}/v2", json=payload, timeout=30)
                        if resp.status_code == 200:
                            exp_data = resp.json()
                            exp_id = exp_data.get('id', None)
                            
                            # Store experiment info in session state for monitoring
                            st.session_state[f"experiment_{exp_id}"] = {
                                "id": exp_id,
                                "name": dos_name,
                                "target_ip": device.get('ip_address'),
                                "attack_mode": attack_mode,
                                "cycles": cycles,
                                "start_time": datetime.datetime.now().isoformat()
                            }
                            
                            st.success(f"🚀 DoS Attack V2 started successfully!")
                            st.success(f"📊 Experiment ID: {exp_id}")
                            st.success(f"🎯 Target: {device.get('ip_address')} ({device.get('hostname', 'Device')})")
                            st.success(f"🔄 Mode: {attack_mode.upper()}, Cycles: {cycles}")
                            
                            # Show monitoring option
                            if attack_mode == "cyclic":
                                st.info("📈 Use the 'Monitor Experiments' page to track attack progress")
                            
                            st.session_state["show_dos_form"] = False
                            st.session_state["active_action"] = None
                        else:
                            st.error(f"❌ Failed to start DoS Attack V2: {resp.text}")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
    else:
        st.info("Device is offline - actions unavailable")

# --- PCAP Files Section ---
with st.expander("📦 PCAP Files", expanded=True):

    def fetch_device_pcaps(mac: str) -> list:
        """Fetch PCAP files for a device by MAC address.

        Args:
            mac: MAC address string.

        Returns:
            List of PCAP file dictionaries.
        """
        import urllib.parse
        try:
            url = f"{CAPTURES_URL}/device/{urllib.parse.quote(mac)}"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            st.error(f"Failed to fetch PCAP files: {e}")
            return []

    st.markdown(
        """
        <style>
        .pcap-card {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            border-radius: 12px;
            padding: 16px;
            margin: 12px 0;
            border-left: 4px solid #4CAF50;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.2s ease;
        }
        .pcap-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        .pcap-filename {
            font-weight: 600;
            color: #2c3e50;
            font-size: 16px;
            margin-bottom: 8px;
        }
        .pcap-details {
            color: #7f8c8d;
            font-size: 14px;
            display: flex;
            gap: 20px;
            align-items: center;
        }
        .pcap-size {
            background: #e3f2fd;
            padding: 4px 8px;
            border-radius: 6px;
            font-weight: 500;
        }
        .pcap-date {
            background: #f3e5f5;
            padding: 4px 8px;
            border-radius: 6px;
            font-weight: 500;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    pcap_files = fetch_device_pcaps(mac)
    if pcap_files:
        st.info(f"📊 Found {len(pcap_files)} PCAP file(s) for this device")

        for i, pcap in enumerate(pcap_files):
            file_size = pcap['file_size']
            if file_size > 1024 * 1024:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"
            elif file_size > 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{file_size} bytes"

            created_at = pcap['created_at']
            try:
                from datetime import datetime
                if 'T' in created_at:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    time_str = dt.strftime('%Y-%m-%d %H:%M')
                else:
                    time_str = created_at
            except Exception:
                time_str = created_at

            with st.container():
                st.markdown(
                    f"""
                    <div class="pcap-card">
                        <div class="pcap-filename">📄 {pcap['file_name']}</div>
                        <div class="pcap-details">
                            <span class="pcap-size">📊 {size_str}</span>
                            <span class="pcap-date">🕒 {time_str}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                def get_pcap_file(capture_id: str):
                    """Download a PCAP file by its capture ID.

                    Args:
                        capture_id: The ID of the PCAP capture.

                    Returns:
                        The file bytes if successful, None otherwise.
                    """
                    url = f"{CAPTURES_URL}/{capture_id}/download"
                    try:
                        resp = requests.get(url, timeout=30)
                        if resp.status_code == 200:
                            return resp.content
                        else:
                            st.error("Download failed")
                            return None
                    except Exception as e:
                        st.error(f"Download error: {e}")
                        return None

                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    file_bytes = get_pcap_file(pcap['id'])
                    if file_bytes:
                        st.download_button(
                            label="⬇️ Download",
                            data=file_bytes,
                            file_name=pcap['file_name'],
                            mime="application/octet-stream",
                            use_container_width=True,
                            key=f"download_pcap_{i}",
                        )
                with col2:
                    if st.button("📋 Details", use_container_width=True, key=f"details_pcap_{i}"):
                        st.info(f"File: {pcap['file_name']}\nSize: {size_str}\nCreated: {time_str}")

                st.markdown("<br>", unsafe_allow_html=True)
    else:
                    st.markdown(
                """
                <div style="text-align: center; padding: 40px; background: #f8f9fa; border-radius: 10px; border: 2px dashed #dee2e6;">
                    <h4 style="color: #6c757d; margin-bottom: 10px;">📭 No PCAP Files Found</h4>
                    <p style="color: #6c757d; margin: 0;">No traffic captures are available for this device yet.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

# Auto refresh logic
if auto_refresh:
    import time
    time.sleep(3)  # Fixed refresh interval to 3 seconds
    st.rerun()