# Streamlit dashboard configuration
# Set the API_BASE_URL to your FastAPI backend
import os
from pathlib import Path

# 尝试加载 .env 文件
try:
    from dotenv import load_dotenv
    # 加载当前目录下的 .env 文件
    env_path = Path(__file__).parent / '.env'
    load_dotenv(env_path)
except ImportError:
    # 如果没有安装 python-dotenv，继续使用系统环境变量
    pass

# 使用环境变量配置API基础URL，默认为localhost:8000
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# 各个服务的完整URL（基础路径，用于后续拼接）
API_URL = f"{API_BASE_URL}/devices"
EXPERIMENTS_URL = f"{API_BASE_URL}/experiments"
CAPTURES_URL = f"{API_BASE_URL}/captures" 