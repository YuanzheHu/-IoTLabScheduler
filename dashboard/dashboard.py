"""
IoT Lab Scheduler - Main Dashboard Entry Point
Main dashboard application for managing IoT network experiments and device scanning
"""

import streamlit as st
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

# Header section
st.markdown("""
<div style='text-align: center; padding: 2rem 0 3rem 0;'>
    <h1 style='font-size: 3rem; margin: 0; color: #1f77b4;'>IoT Lab Scheduler</h1>
    <p style='font-size: 1.2rem; color: #666; margin: 0.5rem 0 0 0;'>IoT Network Security Testing Platform</p>
</div>
""", unsafe_allow_html=True)

# Platform overview
st.markdown("""
<div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
           color: white; padding: 2rem; border-radius: 10px; margin-bottom: 3rem; text-align: center;'>
    <p style='font-size: 1.1rem; margin: 0; line-height: 1.6;'>
        Discover IoT devices, analyze network security, and conduct controlled DoS attack experiments in laboratory environments for research and education purposes.
    </p>
</div>
""", unsafe_allow_html=True)

# Main features section
st.markdown("<h2 style='text-align: center; margin-bottom: 2rem;'>Core Features</h2>", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div style='padding: 1.5rem; border: 1px solid #e0e0e0; border-radius: 10px; height: 200px; 
                display: flex; flex-direction: column; justify-content: space-between; box-sizing: border-box;'>
        <div style='text-align: center;'>
            <h3 style='color: #1f77b4; margin: 0 0 1rem 0;'>Device Discovery</h3>
        </div>
        <div style='flex: 1; display: flex; align-items: center;'>
            <ul style='text-align: left; padding-left: 1rem; line-height: 1.6; margin: 0; list-style-type: disc;'>
                <li>Network device scanning</li>
                <li>Port & service detection</li>
                <li>Real-time monitoring</li>
            </ul>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div style='padding: 1.5rem; border: 1px solid #e0e0e0; border-radius: 10px; height: 200px; 
                display: flex; flex-direction: column; justify-content: space-between; box-sizing: border-box;'>
        <div style='text-align: center;'>
            <h3 style='color: #1f77b4; margin: 0 0 1rem 0;'>DoS Testing</h3>
        </div>
        <div style='flex: 1; display: flex; align-items: center;'>
            <ul style='text-align: left; padding-left: 1rem; line-height: 1.6; margin: 0; list-style-type: disc;'>
                <li>5 attack types supported</li>
                <li>Single/cyclic modes</li>
                <li>Real-time monitoring</li>
            </ul>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div style='padding: 1.5rem; border: 1px solid #e0e0e0; border-radius: 10px; height: 200px; 
                display: flex; flex-direction: column; justify-content: space-between; box-sizing: border-box;'>
        <div style='text-align: center;'>
            <h3 style='color: #1f77b4; margin: 0 0 1rem 0;'>Analysis</h3>
        </div>
        <div style='flex: 1; display: flex; align-items: center;'>
            <ul style='text-align: left; padding-left: 1rem; line-height: 1.6; margin: 0; list-style-type: disc;'>
                <li>Traffic capture (PCAP)</li>
                <li>Impact analysis</li>
                <li>Data visualization</li>
            </ul>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Spacer
st.markdown("<div style='margin: 3rem 0;'></div>", unsafe_allow_html=True)

# Quick start section
st.markdown("<h2 style='text-align: center; margin-bottom: 2rem;'>Quick Start</h2>", unsafe_allow_html=True)

start_col1, start_col2 = st.columns(2, gap="large")

with start_col1:
    st.markdown("""
    <div style='text-align: center; padding: 2rem; border: 2px solid #1f77b4; border-radius: 10px; 
                height: 140px; display: flex; flex-direction: column; justify-content: center; box-sizing: border-box;'>
        <h3 style='color: #1f77b4; margin: 0 0 1rem 0;'>Step 1: Discover Devices</h3>
        <p style='margin: 0; color: #666; font-size: 0.95rem;'>Scan your network to find and analyze IoT devices</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<div style='margin: 1rem 0;'></div>", unsafe_allow_html=True)
    st.button("Go to Devices", use_container_width=True, type="primary", key="devices_btn")

with start_col2:
    st.markdown("""
    <div style='text-align: center; padding: 2rem; border: 2px solid #1f77b4; border-radius: 10px; 
                height: 140px; display: flex; flex-direction: column; justify-content: center; box-sizing: border-box;'>
        <h3 style='color: #1f77b4; margin: 0 0 1rem 0;'>Step 2: Run Experiments</h3>
        <p style='margin: 0; color: #666; font-size: 0.95rem;'>Create and monitor DoS attack experiments</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<div style='margin: 1rem 0;'></div>", unsafe_allow_html=True)
    st.button("Go to Experiments", use_container_width=True, type="primary", key="experiments_btn")

# Navigation handling
if st.session_state.get("devices_btn"):
    st.switch_page("pages/devices.py")
if st.session_state.get("experiments_btn"):
    st.switch_page("pages/experiments.py")

# Spacer
st.markdown("<div style='margin: 3rem 0;'></div>", unsafe_allow_html=True)

# Additional tools section
st.markdown("<h2 style='text-align: center; margin-bottom: 2rem;'>Additional Tools</h2>", unsafe_allow_html=True)

tool_col1, tool_col2 = st.columns(2, gap="large")

with tool_col1:
    if st.button("Scan Visualization", use_container_width=True):
        st.switch_page("pages/scan_visualisation.py")

with tool_col2:
    if st.button("Settings", use_container_width=True):
        st.switch_page("pages/settings.py")

# Footer
st.markdown("<div style='margin: 4rem 0 2rem 0;'></div>", unsafe_allow_html=True)
st.markdown("""
<div style='text-align: center; padding: 1rem; background-color: #f8f9fa; border-radius: 10px;'>
    <p style='margin: 0; color: #666; font-size: 0.9rem;'>
        For educational and research purposes only. Use responsibly in controlled environments.
    </p>
</div>
""", unsafe_allow_html=True)

# Display auto refresh status if enabled
if auto_refresh_enabled:
    st.info("Auto refresh enabled")