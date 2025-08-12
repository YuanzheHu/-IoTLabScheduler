"""
Settings Management Page
System configuration and maintenance for IoT Lab Scheduler
"""

import streamlit as st
import subprocess
import sys
import os
from typing import Optional
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.icon_fix import apply_icon_fixes


def reset_database() -> tuple[bool, str, Optional[str]]:
    """
    Reset the database by running the init_db command
    
    Returns:
        tuple[bool, str, Optional[str]]: (success, message, output/error)
    """
    try:
        result = subprocess.run(
            ["python3", "-m", "project.db.init_db"],
            capture_output=True,
            text=True,
            cwd=os.getcwd(),
            timeout=30
        )
        
        if result.returncode == 0:
            return True, "Database reset successful!", result.stdout
        else:
            return False, f"Database reset failed with code {result.returncode}", result.stderr
            
    except subprocess.TimeoutExpired:
        return False, "Database reset timed out!", None
    except FileNotFoundError:
        return False, "python3 command or project.db.init_db module not found!", None
    except Exception as e:
        return False, f"Error during reset: {str(e)}", None


# Page configuration
st.set_page_config(
    page_title="Settings",
    page_icon="⚙️",
    layout="wide"
)

st.title("⚙️ Settings")

# Apply icon fixes
apply_icon_fixes()

# Import configuration
try:
    from config import API_URL, EXPERIMENTS_URL, CAPTURES_URL
except ImportError:
    API_URL = "http://localhost:8000/devices"
    EXPERIMENTS_URL = "http://localhost:8000/experiments"
    CAPTURES_URL = "http://localhost:8000/captures"

# System information
st.markdown("## 📊 System Information")
col1, col2 = st.columns(2)

with col1:
    st.markdown("**API Endpoints:**")
    st.code(f"Devices: {API_URL}")
    st.code(f"Experiments: {EXPERIMENTS_URL}")
    st.code(f"Captures: {CAPTURES_URL}")

with col2:
    st.markdown("**Python Environment:**")
    st.code(f"Python: {sys.version}")
    st.code(f"Working Dir: {os.getcwd()}")

# Database management
st.markdown("## 🗄️ Database Management")

with st.expander("⚠️ Database Reset", expanded=False):
    st.warning("""
    **⚠️ Warning: This operation will reset the entire database!**
    
    - All device information will be cleared
    - All scan results will be deleted
    - All experiment records will be cleared
    - All PCAP file records will be deleted
    
    This operation is irreversible, please use with caution!
    """)
    
    # Confirm reset
    if st.button("🗑️ Reset Database", type="primary", use_container_width=True):
        st.info("Resetting database...")
        
        success, message, output = reset_database()
        
        if success:
            st.success(f"✅ {message}")
            if output:
                st.code(output)
            
            # Show reset completion info
            st.info("""
            **Reset Complete:**
            - Database tables have been recreated
            - All data has been cleared
            - System is ready
            
            Recommended to refresh the page to see the latest status.
            """)
        else:
            st.error(f"❌ {message}")
            if output:
                st.code(output)

# System maintenance
st.markdown("## 🔧 System Maintenance")

with st.expander("🧹 System Cleanup", expanded=False):
    st.info("""
    **System cleanup features:**
    - Clean temporary files
    - Clean log files
    - Optimize database
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🧹 Clean Temp Files", use_container_width=True):
            st.info("Clean temporary files feature is under development...")
    
    with col2:
        if st.button("📊 Optimize Database", use_container_width=True):
            st.info("Database optimization feature is under development...")

# Configuration management
st.markdown("## ⚙️ Configuration")

with st.expander("🔧 API Configuration", expanded=False):
    st.info("Current API configuration:")
    
    api_url = st.text_input("API Base URL", value=API_URL, help="API server address")
    experiments_url = st.text_input("Experiments API URL", value=EXPERIMENTS_URL, help="Experiments API address")
    captures_url = st.text_input("Captures API URL", value=CAPTURES_URL, help="Captures API address")
    
    if st.button("💾 Save Configuration", use_container_width=True):
        st.success("Configuration save feature is under development...")

# Log viewing
st.markdown("## 📋 System Logs")

with st.expander("📄 View Logs", expanded=False):
    st.info("System log viewing feature is under development...")
    
    log_type = st.selectbox("Log Type", ["Application", "Database", "API", "All"])
    
    if st.button("📋 Load Logs", use_container_width=True):
        st.info("Log loading feature is under development...")

# Help information
st.markdown("## ❓ Help & Support")

with st.expander("📚 Documentation", expanded=False):
    st.markdown("""
    **System Documentation:**
    
    ### Database Reset
    - Execute `python3 -m project.db.init_db` command
    - Clear all existing data
    - Recreate database table structure
    
    ### API Endpoints
    - Device Management: `/devices`
    - Experiment Management: `/experiments`
    - Capture Management: `/captures`
    - Scan Results: `/scan-results`
    
    ### Troubleshooting
    - Check Docker container status
    - View API service logs
    - Verify network connectivity
    """)

# Footer
st.markdown("---")
st.caption("IoTLabScheduler - System Settings") 
    
    log_type = st.selectbox("Log Type", ["Application", "Database", "API", "All"])
    
    if st.button("📋 Load Logs", use_container_width=True):
        st.info("Log loading feature is under development...")

# Help information
st.markdown("## ❓ Help & Support")

with st.expander("📚 Documentation", expanded=False):
    st.markdown("""
    **System Documentation:**
    
    ### Database Reset
    - Execute `python3 -m project.db.init_db` command
    - Clear all existing data
    - Recreate database table structure
    
    ### API Endpoints
    - Device Management: `/devices`
    - Experiment Management: `/experiments`
    - Capture Management: `/captures`
    - Scan Results: `/scan-results`
    
    ### Troubleshooting
    - Check Docker container status
    - View API service logs
    - Verify network connectivity
    """)

# Footer
st.markdown("---")