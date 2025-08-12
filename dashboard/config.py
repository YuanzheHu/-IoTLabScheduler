"""
Streamlit Dashboard Configuration
Configuration file for API endpoints and environment variables
"""

import os
from pathlib import Path

# Try to load .env file
try:
    from dotenv import load_dotenv
    # Load .env file from current directory
    env_path = Path(__file__).parent / '.env'
    load_dotenv(env_path)
except ImportError:
    # Continue using system environment variables if python-dotenv is not installed
    pass

# Use environment variable to configure API base URL, default to localhost:8000
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Complete URLs for various services (base paths for subsequent concatenation)
API_URL = f"{API_BASE_URL}/devices"
EXPERIMENTS_URL = f"{API_BASE_URL}/experiments"
CAPTURES_URL = f"{API_BASE_URL}/captures" 