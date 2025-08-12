"""
Auto Refresh Utility for Streamlit Dashboard
Provides auto refresh functionality for real-time data updates
"""

import streamlit as st


def setup_auto_refresh():
    """
    Setup auto refresh functionality for the dashboard
    
    Returns:
        bool: True if auto refresh is enabled, False otherwise
    """
    # Check if auto refresh setting already exists in session state
    if 'auto_refresh_enabled' not in st.session_state:
        st.session_state.auto_refresh_enabled = True
    
    # Return auto refresh status
    return st.session_state.auto_refresh_enabled


def toggle_auto_refresh():
    """
    Toggle auto refresh on/off
    
    Returns:
        bool: New auto refresh state
    """
    if 'auto_refresh_enabled' in st.session_state:
        st.session_state.auto_refresh_enabled = not st.session_state.auto_refresh_enabled
    else:
        st.session_state.auto_refresh_enabled = True
    
    return st.session_state.auto_refresh_enabled
