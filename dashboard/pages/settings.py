"""
Settings Management Page
System configuration and external service links
"""

import streamlit as st
import subprocess
import sys
import os
import requests
from utils.icon_fix import apply_icon_fixes

# Page configuration
st.set_page_config(
    page_title="Settings",
    page_icon="⚙️",
    layout="wide"
)

apply_icon_fixes()

st.title("⚙️ Settings")
st.markdown("**System Configuration & Management**")
st.divider()

# External Services
st.markdown("## 🔗 External Services")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📚 **FastAPI Documentation**")
    st.markdown("Access the complete API documentation and interactive testing interface")
    if st.button("🚀 **Open API Docs**", use_container_width=True):
        st.markdown("""
        <script>window.open('http://localhost:8000/docs#', '_blank')</script>
        """, unsafe_allow_html=True)
    st.caption("URL: http://localhost:8000/docs#")

with col2:
    st.markdown("### 🌸 **Celery Flower Dashboard**")
    st.markdown("Monitor background tasks and queue management")
    if st.button("🌺 **Open Flower**", use_container_width=True):
        st.markdown("""
        <script>window.open('http://localhost:5555/', '_blank')</script>
        """, unsafe_allow_html=True)
    st.caption("URL: http://localhost:5555/")

st.divider()

# Database Management
st.markdown("## 🗄️ Database Management")

def list_backups():
    """List all available backup files"""
    try:
        response = requests.get("http://localhost:8000/admin/list-backups", timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "success":
                return True, result.get("backups", []), None
            else:
                return False, [], result.get("message", "Unknown error")
        else:
            return False, [], f"HTTP {response.status_code}: {response.text}"
            
    except requests.exceptions.ConnectionError:
        return False, [], "Cannot connect to API server. Make sure the FastAPI backend is running."
    except requests.exceptions.Timeout:
        return False, [], "Request timed out!"
    except Exception as e:
        return False, [], f"Error listing backups: {str(e)}"

def restore_database(backup_filename):
    """Restore database from backup using the FastAPI endpoint"""
    try:
        payload = {"backup_filename": backup_filename}
        response = requests.post("http://localhost:8000/admin/restore-database", json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "success":
                return True, result.get("message", "Database restore successful!"), result.get("pre_restore_backup", "")
            else:
                return False, result.get("message", "Unknown error"), None
        else:
            return False, f"HTTP {response.status_code}: {response.text}", None
            
    except requests.exceptions.ConnectionError:
        return False, "Cannot connect to API server. Make sure the FastAPI backend is running.", None
    except requests.exceptions.Timeout:
        return False, "Database restore timed out!", None
    except Exception as e:
        return False, f"Error during restore: {str(e)}", None

def backup_database():
    """Create a backup of the database using the FastAPI endpoint"""
    try:
        response = requests.post("http://localhost:8000/admin/backup-database", timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "success":
                return True, result.get("message", "Database backup successful!"), result.get("backup_file", "")
            else:
                return False, result.get("message", "Unknown error"), None
        else:
            return False, f"HTTP {response.status_code}: {response.text}", None
            
    except requests.exceptions.ConnectionError:
        return False, "Cannot connect to API server. Make sure the FastAPI backend is running.", None
    except requests.exceptions.Timeout:
        return False, "Database backup timed out!", None
    except Exception as e:
        return False, f"Error during backup: {str(e)}", None

def reset_database():
    """Reset the database using the FastAPI endpoint"""
    try:
        # Call the database reset API endpoint
        response = requests.post("http://localhost:8000/admin/reset-database", timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "success":
                return True, result.get("message", "Database reset successful!"), str(result.get("tables_recreated", []))
            else:
                return False, result.get("message", "Unknown error"), None
        else:
            return False, f"HTTP {response.status_code}: {response.text}", None
            
    except requests.exceptions.ConnectionError:
        return False, "Cannot connect to API server. Make sure the FastAPI backend is running.", None
    except requests.exceptions.Timeout:
        return False, "Database reset timed out!", None
    except Exception as e:
        return False, f"Error during reset: {str(e)}", None

# Database Backup Section
st.markdown("### 💾 **Database Backup**")
st.info("Create a backup of your current database before making any changes.")

if st.button("💾 **Create Database Backup**", use_container_width=True):
    with st.spinner("Creating database backup..."):
        success, message, backup_file = backup_database()
        
        if success:
            st.success(f"✅ {message}")
            if backup_file:
                st.info(f"📁 **Backup saved as:** `{backup_file}`")
        else:
            st.error(f"❌ {message}")

st.divider()

# Database Restore Section
st.markdown("### 🔄 **Database Restore**")
st.info("Restore your database from a previous backup file.")

# Load available backups
with st.spinner("Loading available backups..."):
    success, backups, error_msg = list_backups()

if success and backups:
    st.markdown(f"**Found {len(backups)} backup files:**")
    
    # Display backups in a nice format
    backup_options = []
    for backup in backups:
        size_mb = backup['size'] / (1024 * 1024)
        display_name = f"{backup['filename']} ({size_mb:.1f} MB) - {backup['created']}"
        backup_options.append((display_name, backup['filename']))
    
    # Selectbox for choosing backup
    if backup_options:
        selected_display, selected_filename = st.selectbox(
            "Choose a backup to restore:",
            options=backup_options,
            format_func=lambda x: x[0],
            index=0
        )
        
        # Show details of selected backup
        selected_backup = next((b for b in backups if b['filename'] == selected_filename), None)
        if selected_backup:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("File Size", f"{selected_backup['size'] / (1024 * 1024):.1f} MB")
            with col2:
                st.metric("Created", selected_backup['created'])
            with col3:
                st.metric("Filename", selected_backup['filename'])
        
        # Confirmation and restore button
        st.warning("⚠️ **Warning:** This will replace your current database!")
        confirm_restore = st.checkbox("I understand this will replace my current database")
        
        if confirm_restore:
            if st.button("🔄 **Restore Database**", type="primary", use_container_width=True):
                with st.spinner("Restoring database..."):
                    success, message, pre_restore_backup = restore_database(selected_filename)
                    
                    if success:
                        st.success(f"✅ {message}")
                        if pre_restore_backup:
                            st.info(f"📁 **Previous database backed up as:** `{pre_restore_backup}`")
                        st.balloons()  # 庆祝动画
                        st.info("💡 **Recommendation:** Refresh the page to see restored data")
                    else:
                        st.error(f"❌ {message}")
        else:
            st.button("🔄 **Restore Database**", disabled=True, use_container_width=True)
            
elif success and not backups:
    st.warning("No backup files found. Create a backup first.")
else:
    st.error(f"❌ Failed to load backups: {error_msg}")

st.divider()

# Database Reset Section
with st.expander("⚠️ **Danger Zone - Database Reset**"):
    st.warning("""
    **⚠️ Warning: This will permanently delete all data!**
    
    This operation will clear:
    - All discovered devices
    - All scan results and experiment records
    - All PCAP file records
    
    **This action cannot be undone.**
    """)
    
    # Confirmation checkbox
    confirm_reset = st.checkbox("I understand this will delete all data permanently")
    
    if confirm_reset:
        if st.button("🗑️ **Reset Database**", type="primary", use_container_width=True):
            with st.spinner("Resetting database..."):
                success, message, output = reset_database()
                
                if success:
                    st.success(f"✅ {message}")
                    if output:
                        with st.expander("📋 Reset Output"):
                            st.code(output)
                    st.info("💡 **Recommendation:** Refresh the page to see updated status")
                else:
                    st.error(f"❌ {message}")
                    if output:
                        with st.expander("📋 Error Details"):
                            st.code(output)

st.divider()

# System Information
st.markdown("## 📊 System Information")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Configuration:**")
    try:
        from config import API_URL, EXPERIMENTS_URL, CAPTURES_URL
        st.code(f"API: {API_URL}")
        st.code(f"Experiments: {EXPERIMENTS_URL}")
        st.code(f"Captures: {CAPTURES_URL}")
    except ImportError:
        st.code("API: http://localhost:8000/devices")
        st.code("Experiments: http://localhost:8000/experiments")
        st.code("Captures: http://localhost:8000/captures")

with col2:
    st.markdown("**Environment:**")
    st.code(f"Python: {sys.version.split()[0]}")
    st.code(f"Working Directory: {os.path.basename(os.getcwd())}")
    st.code(f"Platform: {sys.platform}")

# Service Status Check
st.divider()
st.markdown("## 🔍 Service Status Check")

def check_service_status():
    """Check the status of various services"""
    services = {}
    
    # Check FastAPI
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        services["FastAPI"] = "✅ Online" if response.status_code == 200 else "❌ Error"
    except:
        services["FastAPI"] = "❌ Offline"
    
    # Check Streamlit (self)
    services["Streamlit"] = "✅ Online"
    
    # Check Flower
    try:
        response = requests.get("http://localhost:5555", timeout=5)
        services["Flower"] = "✅ Online" if response.status_code in [200, 405] else "❌ Error"
    except:
        services["Flower"] = "❌ Offline"
    
    return services

if st.button("🔍 **Check Service Status**", use_container_width=True):
    with st.spinner("Checking services..."):
        status = check_service_status()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"**FastAPI:** {status['FastAPI']}")
        with col2:
            st.markdown(f"**Streamlit:** {status['Streamlit']}")
        with col3:
            st.markdown(f"**Flower:** {status['Flower']}")

# Back to Dashboard
st.divider()
if st.button("← **Back to Dashboard**", use_container_width=True):
    st.switch_page("dashboard.py")