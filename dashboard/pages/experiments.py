"""
Experiments Management Page
Manages and monitors IoT network attack experiments
"""

import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.icon_fix import apply_icon_fixes

# Page configuration
st.set_page_config(
    page_title="Experiments",
    page_icon="🧪",
    layout="wide"
)

st.title("🧪 Experiment Dashboard")

# Apply icon fixes
apply_icon_fixes()

# API configuration - use URLs from config file
try:
    from config import EXPERIMENTS_URL, CAPTURES_URL
except ImportError:
    EXPERIMENTS_URL = "http://localhost:8000/experiments"
    CAPTURES_URL = "http://localhost:8000/captures"

# Custom CSS styles
st.markdown("""
<style>
.status-running { 
    background: linear-gradient(90deg, #4CAF50, #81C784); 
    color: white; 
    padding: 6px 12px; 
    border-radius: 16px; 
    font-weight: 600;
    font-size: 12px;
    text-align: center;
    display: inline-block;
    min-width: 80px;
}
.status-pending { 
    background: linear-gradient(90deg, #FF9800, #FFB74D); 
    color: white; 
    padding: 6px 12px; 
    border-radius: 16px; 
    font-weight: 600;
    font-size: 12px;
    text-align: center;
    display: inline-block;
    min-width: 80px;
}
.status-success { 
    background: linear-gradient(90deg, #2196F3, #64B5F6); 
    color: white; 
    padding: 6px 12px; 
    border-radius: 16px; 
    font-weight: 600;
    font-size: 12px;
    text-align: center;
    display: inline-block;
    min-width: 80px;
}
.status-failed { 
    background: linear-gradient(90deg, #F44336, #E57373); 
    color: white; 
    padding: 6px 12px; 
    border-radius: 16px; 
    font-weight: 600;
    font-size: 12px;
    text-align: center;
    display: inline-block;
    min-width: 80px;
}
.metrics-container {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 24px;
    border-radius: 16px;
    margin: 20px 0;
    box-shadow: 0 8px 25px rgba(0,0,0,0.15);
}
.v2-metrics {
    background: linear-gradient(135deg, #9b59b6 0%, #8e44ad 100%);
    color: white;
    padding: 20px;
    border-radius: 12px;
    margin: 16px 0;
    box-shadow: 0 6px 20px rgba(0,0,0,0.1);
}
.experiment-card {
    background: #ffffff;
    border-radius: 12px;
    padding: 20px;
    margin: 16px 0;
    border-left: 4px solid #007acc;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    transition: all 0.3s ease;
}
.experiment-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0,0,0,0.15);
}
.stButton > button {
    height: 38px !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}
.stDownloadButton > button {
    height: 38px !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}
.filter-container {
    background: #f8f9fa;
    padding: 20px;
    border-radius: 12px;
    margin: 20px 0;
    border: 1px solid #e9ecef;
}
.page-header {
    text-align: center;
    margin: 30px 0;
    padding: 20px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 16px;
}
.page-header h1 {
    margin: 0;
    font-size: 2.5em;
    font-weight: 700;
}
.page-header p {
    margin: 10px 0 0 0;
    font-size: 1.2em;
    opacity: 0.9;
}

</style>
""", unsafe_allow_html=True)

# Page header removed as requested

# Function definitions
def fetch_experiments() -> List[Dict]:
    """
    Fetch all experiment tasks from the API
    
    Returns:
        List[Dict]: List of experiment data
    """
    try:
        resp = requests.get(EXPERIMENTS_URL, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        else:
            st.error(f"Failed to fetch experiment data: HTTP {resp.status_code}")
            return []
    except Exception as e:
        st.error(f"Failed to fetch experiment data: {e}")
        return []

def fetch_experiment_status_v2(experiment_id: int) -> Optional[Dict]:
    """
    Fetch V2 experiment status - Function removed
    
    Returns:
        None: This function has been removed
    """
    # This function has been removed
    return None

def stop_experiment(experiment_id: int) -> Tuple[bool, str]:
    """
    Stop a running experiment
    
    Args:
        experiment_id (int): ID of the experiment to stop
        
    Returns:
        Tuple[bool, str]: (success, message)
    """
    try:
        url = f"{EXPERIMENTS_URL}/{experiment_id}/stop"
        resp = requests.post(url, timeout=10)
        if resp.status_code == 200:
            return True, "Experiment stopped successfully"
        else:
            return False, f"HTTP {resp.status_code}: {resp.text}"
    except Exception as e:
        return False, str(e)

def fetch_experiment_pcaps(experiment_id: int) -> List[Dict]:
    """
    Fetch PCAP files related to an experiment
    
    Args:
        experiment_id (int): ID of the experiment
        
    Returns:
        List[Dict]: List of PCAP file data
    """
    try:
        # Use correct API endpoint to get PCAP files by experiment_id parameter
        url = f"{CAPTURES_URL}/?experiment_id={experiment_id}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        else:
            # Return empty list if API doesn't exist
            return []
    except Exception as e:
        # Return empty list if API doesn't exist
        return []

def get_status_badge(status: str) -> str:
    """
    Generate HTML status badge for experiment status
    
    Args:
        status (str): Experiment status
        
    Returns:
        str: HTML string for status badge
    """
    normalized_status = status.upper() if status else 'UNKNOWN'
    status_map = {
        'PENDING': ('⏳', 'status-pending'),
        'STARTED': ('🚀', 'status-running'),
        'RUNNING': ('▶️', 'status-running'),
        'SUCCESS': ('✅', 'status-success'),
        'FINISHED': ('✅', 'status-success'),
        'FAILURE': ('❌', 'status-failed'),
        'FAILED': ('❌', 'status-failed'),
        'REVOKED': ('🚫', 'status-failed'),
        'RETRY': ('🔄', 'status-pending'),
        'UNKNOWN': ('❓', 'status-pending')
    }
    icon, css_class = status_map.get(normalized_status, ('❓', 'status-pending'))
    return f'<span class="{css_class}">{icon} {normalized_status}</span>'

# Auto refresh configuration
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("### 📊 Real-time Monitoring Console")
with col2:
    auto_refresh = st.checkbox("🔄 Auto Refresh", value=False, help="Enable automatic page refresh")

# Fetch experiment data
with st.spinner("Fetching experiment data..."):
    experiments = fetch_experiments()

if experiments:
    # Statistics
    total_count = len(experiments)
    running_count = len([e for e in experiments if e.get('status', '').upper() in ['RUNNING', 'STARTED']])
    pending_count = len([e for e in experiments if e.get('status', '').upper() == 'PENDING'])
    success_count = len([e for e in experiments if e.get('status', '').upper() in ['SUCCESS', 'FINISHED']])
    failed_count = len([e for e in experiments if e.get('status', '').upper() in ['FAILURE', 'REVOKED', 'FAILED']])
    
    # V2 specific statistics
    v2_experiments = [e for e in experiments if e.get('attack_mode') in ['cyclic', 'single']]
    cyclic_count = len([e for e in experiments if e.get('attack_mode') == 'cyclic'])
    
    # Main metrics cards
    st.markdown(f"""
    <div class="metrics-container">
        <div style="display: flex; justify-content: space-around; text-align: center;">
            <div>
                <h2 style="margin: 0; font-size: 2.8em;">{total_count}</h2>
                <p style="margin: 5px 0; font-size: 16px;">Total Experiments</p>
            </div>
            <div>
                <h2 style="margin: 0; font-size: 2.8em; color: #4CAF50;">{running_count}</h2>
                <p style="margin: 5px 0; font-size: 16px;">Running</p>
            </div>
            <div>
                <h2 style="margin: 0; font-size: 2.8em; color: #FF9800;">{pending_count}</h2>
                <p style="margin: 5px 0; font-size: 16px;">Pending</p>
            </div>
            <div>
                <h2 style="margin: 0; font-size: 2.8em; color: #2196F3;">{success_count}</h2>
                <p style="margin: 5px 0; font-size: 16px;">Completed</p>
            </div>
            <div>
                <h2 style="margin: 0; font-size: 2.8em; color: #F44336;">{failed_count}</h2>
                <p style="margin: 5px 0; font-size: 16px;">Failed</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # V2 metrics cards
    if v2_experiments:
        st.markdown(f"""
        <div class="v2-metrics">
            <div style="display: flex; justify-content: space-around; text-align: center;">
                <div>
                    <h3 style="margin: 0; font-size: 1.8em;">{len(v2_experiments)}</h3>
                    <p style="margin: 5px 0;">V2 Experiments</p>
                </div>
                <div>
                    <h3 style="margin: 0; font-size: 1.8em;">{cyclic_count}</h3>
                    <p style="margin: 5px 0;">Cyclic Attacks</p>
                </div>
                <div>
                    <h3 style="margin: 0; font-size: 1.8em;">{len(v2_experiments) - cyclic_count}</h3>
                    <p style="margin: 5px 0;">Single Attacks</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Filter section
    with st.container():
        st.markdown("### 🔍 Experiment Filters")
        
        with st.container():
            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
            
            with col1:
                status_filter = st.selectbox(
                    "📊 Status Filter",
                    ["All", "Running", "Pending", "Completed", "Failed"],
                    index=0,
                    help="Filter by experiment status"
                )
            
            with col2:
                attack_mode_filter = st.selectbox(
                    "🎯 Attack Mode",
                    ["All", "Single", "Cyclic"],
                    index=0,
                    help="Filter by attack mode"
                )
            
            with col3:
                attack_type_filter = st.selectbox(
                    "⚡ Attack Type",
                    ["All", "syn_flood", "udp_flood", "icmp_flood", "tcp_flood", "ip_frag_flood"],
                    index=0,
                    help="Filter by attack type"
                )
            
            with col4:
                search_term = st.text_input(
                    "🔍 Search",
                    placeholder="Name or target IP...",
                    help="Search by experiment name or target IP address"
                )
    
    # Filter experiments
    filtered_experiments = experiments
    
    # Status filtering
    if status_filter != "All":
        status_mapping = {
            "Running": ["RUNNING", "STARTED"],
            "Pending": ["PENDING"],
            "Completed": ["SUCCESS", "FINISHED"],
            "Failed": ["FAILURE", "REVOKED", "FAILED"]
        }
        target_statuses = status_mapping.get(status_filter, [])
        filtered_experiments = [e for e in filtered_experiments if e.get('status', '').upper() in target_statuses]
    
    # Attack mode filtering
    if attack_mode_filter != "All":
        if attack_mode_filter == "Single":
            filtered_experiments = [e for e in filtered_experiments if e.get('attack_mode') == 'single']
        elif attack_mode_filter == "Cyclic":
            filtered_experiments = [e for e in filtered_experiments if e.get('attack_mode') == 'cyclic']
    
    # Attack type filtering
    if attack_type_filter != "All":
        filtered_experiments = [e for e in filtered_experiments if e.get('attack_type') == attack_type_filter]
    
    # Search filtering
    if search_term:
        filtered_experiments = [
            e for e in filtered_experiments 
            if search_term.lower() in e.get('name', '').lower() or 
               search_term.lower() in e.get('target_ip', '').lower()
        ]
    
    # Experiment list
    st.markdown(f"### 📋 Experiment List ({len(filtered_experiments)}/{total_count})")
    
    if filtered_experiments:
        for exp in filtered_experiments:
            exp_id = exp.get('id', 'N/A')
            name = exp.get('name', 'Unnamed Experiment')
            status = exp.get('status', 'UNKNOWN')
            target_ip = exp.get('target_ip', 'N/A')
            attack_type = exp.get('attack_type', 'N/A')
            start_time = exp.get('start_time', 'N/A')
            end_time = exp.get('end_time', 'N/A')
            duration = exp.get('duration_sec', 'N/A')
            
            # V2 specific fields
            attack_mode = exp.get('attack_mode', 'V1')
            cycles = exp.get('cycles', 1)
            current_cycle = exp.get('current_cycle', 0)
            total_cycles = exp.get('total_cycles', 1)
            interface = exp.get('interface', 'N/A')
            
            with st.container():
                # Experiment card - using Streamlit native components
                st.markdown("---")
                
                # Use column layout to create card effect
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    # Experiment title and V2 identifier
                    if attack_mode != 'V1':
                        st.markdown(f"### 🧪 {name} 🆕")
                    else:
                        st.markdown(f"### 🧪 {name}")
                    
                    # Basic information
                    st.markdown(f"**🎯 Target:** {target_ip} | **⚡ Type:** {attack_type.upper()} | **⏱️ Duration:** {duration}s")
                    
                    # V2 specific information
                    if attack_mode != 'V1':
                        st.markdown(f"**🔄 Mode:** {attack_mode.upper()} | **🌐 Interface:** {interface}")
                    
                    if attack_mode == 'cyclic' and total_cycles > 1:
                        progress = (current_cycle/total_cycles*100) if total_cycles > 0 else 0
                        st.markdown(f"**🔄 Cycles:** {current_cycle}/{total_cycles}")
                        st.progress(progress/100, text=f"Progress: {progress:.1f}%")
                    
                    # Time information
                    if start_time != 'N/A':
                        st.markdown(f"**📅 Start Time:** {start_time}")
                    if end_time and end_time != 'N/A':
                        st.markdown(f"**📅 End Time:** {end_time}")
                
                with col2:
                    # Status display
                    status_badge = get_status_badge(status)
                    st.markdown(status_badge, unsafe_allow_html=True)
                    st.markdown(f"**ID:** {exp_id}")
                    
                    if attack_mode != 'V1':
                        st.markdown("**🆕 V2**", help="Attack Engine V2 Experiment")
                
                # Action buttons
                col1, col2, col3 = st.columns([1, 1, 1])
                
                with col1:
                    if status.upper() in ['RUNNING', 'STARTED', 'PENDING']:
                        if st.button("🛑 Stop", key=f"stop_{exp_id}", use_container_width=True, help="Stop running experiment"):
                            success, result = stop_experiment(exp_id)
                            if success:
                                st.success(f"✅ Experiment {exp_id} stopped successfully!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"❌ Failed to stop experiment: {result}")
                    else:
                        st.button("🛑 Stop", disabled=True, key=f"stop_disabled_{exp_id}", use_container_width=True)
                
                with col2:
                    if st.button("📋 Details", key=f"details_{exp_id}", use_container_width=True, help="View experiment details"):
                        # Curated configuration summary
                        mode = exp.get('attack_mode', 'single')
                        atype = exp.get('attack_type', 'N/A')
                        iface = exp.get('interface', 'N/A')
                        duration = exp.get('duration_sec', 'N/A')
                        port = exp.get('port', None)
                        cycles_val = exp.get('cycles', None)
                        settle_val = exp.get('settle_time_sec', None)

                        # Build lines conditionally
                        lines = []
                        lines.append(f"- Attack Type: `{atype}`")
                        lines.append(f"- Attack Mode: `{mode}`")
                        lines.append(f"- Interface: `{iface}`")
                        if atype != 'icmp_flood' and port:
                            lines.append(f"- Port: `{port}`")
                        lines.append(f"- Duration (sec): `{duration}`")
                        if mode == 'cyclic':
                            if cycles_val is not None:
                                lines.append(f"- Cycles: `{cycles_val}`")
                            if settle_val is not None:
                                lines.append(f"- Settle Time (sec): `{settle_val}`")
                        # Optional time fields
                        if start_time and start_time != 'N/A':
                            lines.append(f"- Start Time: `{start_time}`")
                        if end_time and end_time != 'N/A':
                            lines.append(f"- End Time: `{end_time}`")

                        st.markdown("\n".join(lines))
                
                with col3:
                    # PCAP download button
                    pcap_files = fetch_experiment_pcaps(exp_id)
                    
                    if pcap_files:
                        # Download first PCAP file only
                        pcap = pcap_files[0]
                        def get_pcap_file(capture_id):
                            url = f"{CAPTURES_URL}/{capture_id}/download"
                            try:
                                resp = requests.get(url, timeout=30)
                                if resp.status_code == 200:
                                    return resp.content
                            except Exception:
                                pass
                            return None
                        
                        file_bytes = get_pcap_file(pcap['id'])
                        if file_bytes:
                            st.download_button(
                                label="⬇️ Download PCAP",
                                data=file_bytes,
                                file_name=pcap['file_name'],
                                mime="application/octet-stream",
                                use_container_width=True,
                                key=f"download_pcap_{exp_id}",
                                help="Download experiment PCAP file"
                            )
                        else:
                            st.button("⬇️ Download PCAP", disabled=True, use_container_width=True, key=f"download_pcap_disabled_{exp_id}")
                    else:
                        st.button("⬇️ Download PCAP", disabled=True, use_container_width=True, key=f"download_pcap_disabled_{exp_id}")
                
                st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.info("🔍 No experiments match current filter criteria.")

else:
    # Empty state
    st.markdown("""
    <div style="text-align: center; padding: 80px; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border-radius: 20px; margin: 30px 0; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
        <h2 style="color: #6c757d; margin-bottom: 25px;">🌟 No Experiments Yet</h2>
        <p style="color: #7f8c8d; font-size: 18px; margin-bottom: 35px;">
            Start your first IoT network attack experiment!
        </p>
        <div style="background: white; padding: 25px; border-radius: 15px; border: 2px dashed #dee2e6; display: inline-block;">
            <p style="margin: 0; color: #7f8c8d; font-size: 16px;">
                💡 <strong>Tip:</strong> Go to the "Device Details" page and start a DoS experiment to see it here.
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Automatic refresh
if auto_refresh and experiments:
    time.sleep(3)  # Fixed refresh interval to 3 seconds 