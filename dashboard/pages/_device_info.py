import streamlit as st
import requests
import urllib.parse
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

try:
    from config import API_URL, EXPERIMENTS_URL, CAPTURES_URL
except ImportError:
    API_URL = "http://localhost:8000/devices"
    EXPERIMENTS_URL = "http://localhost:8000/experiments"
    CAPTURES_URL = "http://localhost:8000/captures"

st.set_page_config(page_title="Device Info")
st.title("📋 Device Details")

mac = st.session_state.get("selected_mac", None)

if not mac:
    st.error("No device specified. Please select a device from the device list.")
    st.stop()


def fetch_device_by_mac(mac: str) -> dict:
    """Fetch device information by MAC address.

    Args:
        mac: MAC address string.

    Returns:
        Device information as a dictionary, or None if not found.
    """
    try:
        url = f"{API_URL}/mac/{urllib.parse.quote(mac)}"
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"Failed to fetch device info: {e}")
        return None


device = fetch_device_by_mac(mac)
if not device:
    st.error("Device not found.")
    st.stop()

if st.button("← Back to Devices", use_container_width=True):
    st.switch_page("pages/devices.py")

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
        st.markdown("**Device type:** IoT Device")
        import datetime
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
        st.markdown(f"**Last seen:** {last_seen_str}")
        st.markdown("**Network:** Local subnet")

# --- Port Information Section ---
if device.get('ip_address') and device.get('status') == 'online':
    with st.expander("🔍 Port Information", expanded=True):

        def fetch_latest_port_scan(ip_address: str) -> dict:
            """Fetch the latest port scan result for a device.

            Args:
                ip_address: IP address of the device.

            Returns:
                Latest port scan result as a dictionary, or None if not found.
            """
            try:
                scan_history_url = (
                    f"http://localhost:8000/scan-results/device/{device.get('id')}/latest?scan_type=port_scan"
                )
                resp = requests.get(scan_history_url, timeout=10)
                if resp.status_code == 200:
                    return resp.json()
                return None
            except Exception:
                return None

        latest_scan = fetch_latest_port_scan(device.get('ip_address'))

        if latest_scan and latest_scan.get('ports'):
            ports = latest_scan.get('ports', [])
            open_ports = [p for p in ports if p.get('state') == 'open']
            filtered_ports = [p for p in ports if p.get('state') == 'filtered']
            closed_ports = [p for p in ports if p.get('state') == 'closed']

            col1, col2 = st.columns([1, 1])

            with col1:
                labels = ['Open', 'Closed', 'Filtered']
                values = [len(open_ports), len(closed_ports), len(filtered_ports)]
                colors = ['#00ff00', '#ff0000', '#ffff00']

                fig = go.Figure(
                    data=[
                        go.Pie(
                            labels=labels,
                            values=values,
                            hole=0.3,
                            marker_colors=colors,
                            textinfo='label+percent',
                            textposition='inside',
                        )
                    ]
                )

                fig.update_layout(
                    title="Port Status Distribution",
                    showlegend=True,
                    height=400,
                )

                st.plotly_chart(fig, use_container_width=True)

            with col2:
                if open_ports:
                    port_data = []
                    for port in open_ports:
                        port_num = port.get('port', '').split('/')[0]
                        service = port.get('service', 'unknown')
                        port_data.append(
                            {
                                'Port': f"Port {port_num}",
                                'Service': service,
                                'Status': 'Open',
                            }
                        )

                    df = pd.DataFrame(port_data)

                    fig2 = px.bar(
                        df,
                        x='Port',
                        y='Service',
                        color='Status',
                        color_discrete_map={'Open': '#00ff00'},
                        title="Open Ports and Services",
                    )

                    fig2.update_layout(
                        height=400,
                        xaxis_title="Port Number",
                        yaxis_title="Service",
                    )

                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.info("No open ports found")

            st.markdown("### 🔧 Service Distribution")

            service_counts = {}
            for port in ports:
                service = port.get('service', 'unknown')
                if service in service_counts:
                    service_counts[service] += 1
                else:
                    service_counts[service] = 1

            if service_counts:
                service_data = []
                for service, count in service_counts.items():
                    service_data.append({'Service': service, 'Count': count})

                service_data.sort(key=lambda x: x['Count'], reverse=True)

                df_services = pd.DataFrame(service_data)

                fig3 = px.bar(
                    df_services,
                    x='Service',
                    y='Count',
                    title="Service Distribution",
                    color='Count',
                    color_continuous_scale='viridis',
                )

                fig3.update_layout(
                    height=400,
                    xaxis_title="Service Name",
                    yaxis_title="Number of Ports",
                    xaxis={'categoryorder': 'total descending'},
                )

                fig3.update_xaxes(tickangle=45)

                st.plotly_chart(fig3, use_container_width=True)

            st.markdown("### 📊 Scan Statistics")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Ports", len(ports))
            with col2:
                st.metric("Open Ports", len(open_ports), delta=f"{len(open_ports)} active")
            with col3:
                st.metric("Closed Ports", len(closed_ports))
            with col4:
                st.metric("Scan Time", f"{latest_scan.get('scan_duration', 0):.1f}s")

            if open_ports or filtered_ports:
                st.markdown("### 📋 Port Details")

                table_data = []
                for port in ports:
                    port_num = port.get('port', '').split('/')[0]
                    protocol = port.get('port', '').split('/')[1] if '/' in port.get('port', '') else 'tcp'
                    state = port.get('state', 'unknown')
                    service = port.get('service', 'unknown')

                    status_color = {
                        'open': '🟢',
                        'closed': '🔴',
                        'filtered': '🟡',
                    }.get(state.lower(), '⚪')

                    table_data.append(
                        {
                            'Status': status_color,
                            'Port': port_num,
                            'Protocol': protocol.upper(),
                            'State': state.title(),
                            'Service': service,
                        }
                    )

                df_table = pd.DataFrame(table_data)
                st.dataframe(df_table, use_container_width=True)

            scan_time = latest_scan.get('scan_time', '')
            if scan_time:
                try:
                    scan_dt = datetime.datetime.fromisoformat(scan_time.replace('Z', '+00:00'))
                    scan_time_str = scan_dt.strftime('%Y-%m-%d %H:%M:%S')
                    st.caption(f"📅 Last scanned: {scan_time_str}")
                except Exception:
                    st.caption(f"📅 Last scanned: {scan_time}")
        else:
            st.info("📊 No port scan data available. Click '🔍 Port Scan' to scan this device.")

# --- Actions Section ---
with st.expander("⚡ Actions", expanded=True):
    if device.get('ip_address') and device.get('status') == 'online':
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🔍 Port Scan", use_container_width=True):
                st.session_state["show_port_scan"] = not st.session_state.get("show_port_scan", False)

        with col2:
            if st.button("🖥️ OS Scan", use_container_width=True):
                st.session_state["show_os_scan"] = not st.session_state.get("show_os_scan", False)

        with col3:
            if st.button(" DoS Attack Experiment", use_container_width=True):
                st.session_state["show_dos_form"] = not st.session_state.get("show_dos_form", False)

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

                                st.success(
                                    f"✅ Port scan completed in {scan_result.get('scan_duration', 0):.2f} seconds!"
                                )

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

                            else:
                                st.error(f"OS scan failed: {resp.text}")
                        except Exception as e:
                            st.error(f"Error during OS scan: {e}")

        # DoS Attack Experiment Form
        if st.session_state.get("show_dos_form", False):
            st.markdown(
                """
                <style>
                .dos-form .stTextInput>div>div>input,
                .dos-form .stNumberInput>div>div>input {
                    background-color: #f7f7fa;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )

            with st.form(key="dos_attack_form"):
                st.markdown(
                    f"<div class='dos-form'><b>Start a DoS Attack Experiment on this device</b></div>",
                    unsafe_allow_html=True,
                )
                dos_name = st.text_input(
                    "Experiment Name", value=f"DoS on {device.get('hostname', 'Device')}"
                )
                attack_type = st.selectbox(
                    "Attack Type",
                    ["syn_flood", "udp_flood", "icmp_flood", "tcp_flood", "ip_frag_flood"],
                    index=0,
                )
                dos_port = st.number_input(
                    "Port (optional)", value=55443, min_value=1, max_value=65535
                )
                dos_duration = st.number_input("Duration (seconds)", value=60, min_value=1)
                col1, col2 = st.columns(2)
                with col1:
                    submitted = st.form_submit_button("Start DoS Attack", use_container_width=True)
                with col2:
                    cancel = st.form_submit_button("Cancel", use_container_width=True)

                if cancel:
                    st.session_state["show_dos_form"] = False
                    st.rerun()

                if submitted:
                    payload = {
                        "name": dos_name,
                        "attack_type": attack_type,
                        "target_ip": device.get('ip_address'),
                        "duration_sec": dos_duration,
                    }
                    if dos_port:
                        payload["port"] = dos_port
                    try:
                        resp = requests.post(f"{EXPERIMENTS_URL}/", json=payload, timeout=20)
                        if resp.status_code == 200:
                            exp_id = resp.json().get('id', None)
                            st.success(f"DoS Attack started! Experiment ID: {exp_id}")
                            st.session_state["show_dos_form"] = False
                        else:
                            st.error(f"Failed to start DoS Attack: {resp.text}")
                    except Exception as e:
                        st.error(f"Error: {e}")
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