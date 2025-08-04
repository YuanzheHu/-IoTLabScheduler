import streamlit as st
import requests
import time
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="Experiments", layout="wide")
st.title("🧪 Experiment Dashboard")

# API 配置
EXPERIMENTS_URL = "http://193.60.241.102:8000/experiments"
CAPTURES_URL = "http://193.60.241.102:8000/captures"

# 添加样式
st.markdown("""
<style>
.status-running { 
    background: linear-gradient(90deg, #4CAF50, #81C784); 
    color: white; 
    padding: 4px 12px; 
    border-radius: 12px; 
    font-weight: 600; 
}
.status-pending { 
    background: linear-gradient(90deg, #FF9800, #FFB74D); 
    color: white; 
    padding: 4px 12px; 
    border-radius: 12px; 
    font-weight: 600; 
}
.status-success { 
    background: linear-gradient(90deg, #2196F3, #64B5F6); 
    color: white; 
    padding: 4px 12px; 
    border-radius: 12px; 
    font-weight: 600; 
}
.status-failed { 
    background: linear-gradient(90deg, #F44336, #E57373); 
    color: white; 
    padding: 4px 12px; 
    border-radius: 12px; 
    font-weight: 600; 
}
.experiment-card {
    background: #f8f9fa;
    border-radius: 12px;
    padding: 16px;
    margin: 8px 0;
    border-left: 4px solid #007acc;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
.metrics-container {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 20px;
    border-radius: 12px;
    margin: 16px 0;
}
/* 统一按钮样式 */
.stButton > button {
    height: 38px !important;
    min-height: 38px !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    transition: all 0.2s ease !important;
}
.stDownloadButton > button {
    height: 38px !important;
    min-height: 38px !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    transition: all 0.2s ease !important;
}

</style>
""", unsafe_allow_html=True)

def fetch_experiments():
    """获取所有实验任务"""
    try:
        resp = requests.get(EXPERIMENTS_URL, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"Failed to fetch experiments: {e}")
        return []

def stop_experiment(experiment_id):
    """停止指定实验"""
    try:
        resp = requests.post(f"{EXPERIMENTS_URL}/{experiment_id}/stop", timeout=10)
        resp.raise_for_status()
        return True, resp.json()
    except Exception as e:
        return False, str(e)

def fetch_experiment_pcaps(experiment_id):
    """获取实验相关的PCAP文件"""
    try:
        # 使用正确的API端点，通过experiment_id参数获取PCAP文件
        url = f"{CAPTURES_URL}/?experiment_id={experiment_id}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        else:
            return []
    except Exception as e:
        # 如果API不存在，返回空列表
        return []

def get_pcap_file(capture_id):
    """下载PCAP文件"""
    url = f"{CAPTURES_URL}/{capture_id}/download"
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            return resp.content
        else:
            return None
    except Exception as e:
        return None

def get_status_badge(status):
    """根据状态返回样式化的徽章"""
    status_map = {
        'PENDING': ('⏳', 'status-pending'),
        'STARTED': ('🚀', 'status-running'),
        'RUNNING': ('▶️', 'status-running'),
        'SUCCESS': ('✅', 'status-success'),
        'FAILURE': ('❌', 'status-failed'),
        'REVOKED': ('🚫', 'status-failed'),
        'RETRY': ('🔄', 'status-pending')
    }
    icon, css_class = status_map.get(status.upper(), ('❓', 'status-pending'))
    return f'<span class="{css_class}">{icon} {status.upper()}</span>'

# 控制区域
col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
with col1:
    st.markdown("### 📊 Real-time Monitoring")
with col2:
    auto_refresh = st.checkbox("Auto Refresh", value=True)
with col3:
    refresh_interval = st.selectbox("Interval", [2, 5, 10, 30], index=1)
with col4:
    if st.button("🔄 Refresh Now", use_container_width=True):
        st.rerun()

# 获取实验数据
experiments = fetch_experiments()

if experiments:
    # 统计信息
    total_count = len(experiments)
    running_count = len([e for e in experiments if e.get('status', '').upper() in ['RUNNING', 'STARTED']])
    pending_count = len([e for e in experiments if e.get('status', '').upper() == 'PENDING'])
    success_count = len([e for e in experiments if e.get('status', '').upper() == 'SUCCESS'])
    failed_count = len([e for e in experiments if e.get('status', '').upper() in ['FAILURE', 'REVOKED']])
    
    # 指标卡片
    st.markdown(f"""
    <div class="metrics-container">
        <div style="display: flex; justify-content: space-around; text-align: center;">
            <div>
                <h2 style="margin: 0; font-size: 2.5em;">{total_count}</h2>
                <p style="margin: 5px 0;">Total Tasks</p>
            </div>
            <div>
                <h2 style="margin: 0; font-size: 2.5em; color: #4CAF50;">{running_count}</h2>
                <p style="margin: 5px 0;">Running</p>
            </div>
            <div>
                <h2 style="margin: 0; font-size: 2.5em; color: #FF9800;">{pending_count}</h2>
                <p style="margin: 5px 0;">Pending</p>
            </div>
            <div>
                <h2 style="margin: 0; font-size: 2.5em; color: #2196F3;">{success_count}</h2>
                <p style="margin: 5px 0;">Success</p>
            </div>
            <div>
                <h2 style="margin: 0; font-size: 2.5em; color: #F44336;">{failed_count}</h2>
                <p style="margin: 5px 0;">Failed</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 过滤器
    col1, col2 = st.columns([1, 1])
    with col1:
        status_filter = st.selectbox(
            "Filter by Status", 
            ["All", "RUNNING", "PENDING", "SUCCESS", "FAILURE"],
            index=0
        )
    with col2:
        search_term = st.text_input("🔍 Search by name or target", placeholder="Enter search term...")
    
    # 过滤实验
    filtered_experiments = experiments
    if status_filter != "All":
        filtered_experiments = [e for e in filtered_experiments if e.get('status', '').upper() == status_filter]
    if search_term:
        filtered_experiments = [
            e for e in filtered_experiments 
            if search_term.lower() in e.get('name', '').lower() or 
               search_term.lower() in e.get('target_ip', '').lower()
        ]
    
    # 实验列表
    st.markdown("### 📋 Experiment Tasks")
    
    if filtered_experiments:
        for exp in filtered_experiments:
            exp_id = exp.get('id', 'N/A')
            name = exp.get('name', 'Unnamed Experiment')
            status = exp.get('status', 'UNKNOWN')
            target_ip = exp.get('target_ip', 'N/A')
            attack_type = exp.get('attack_type', 'N/A')
            created_at = exp.get('created_at', 'N/A')
            duration = exp.get('duration_sec', 'N/A')
            
            with st.container():
                st.markdown(f"""
                <div class="experiment-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h4 style="margin: 0; color: #2c3e50;">🧪 {name}</h4>
                            <p style="margin: 5px 0; color: #7f8c8d;">
                                <strong>Target:</strong> {target_ip} | 
                                <strong>Type:</strong> {attack_type} | 
                                <strong>Duration:</strong> {duration}s
                            </p>
                        </div>
                        <div style="text-align: right;">
                            {get_status_badge(status)}
                            <br><small style="color: #95a5a6;">ID: {exp_id}</small>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # 只保留停止和PCAP下载按钮，去掉Data和Details
                col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 2])
                
                with col1:
                    if status.upper() in ['RUNNING', 'STARTED', 'PENDING']:
                        if st.button("🛑 Stop", key=f"stop_{exp_id}", use_container_width=True):
                            success, result = stop_experiment(exp_id)
                            if success:
                                st.success(f"实验 {exp_id} 已成功停止！")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"停止实验失败: {result}")
                    else:
                        st.button("🛑 Stop", disabled=True, key=f"stop_disabled_{exp_id}", use_container_width=True)
                
                # col2、col3 保留空白以保持布局一致
                with col4:
                    # PCAP 下载按钮
                    pcap_files = fetch_experiment_pcaps(exp_id)
                    def get_pcap_file(capture_id):
                        url = f"{CAPTURES_URL}/{capture_id}/download"
                        try:
                            resp = requests.get(url, timeout=30)
                            if resp.status_code == 200:
                                return resp.content
                        except Exception:
                            pass
                        return None

                    if pcap_files:
                        # 只下载第一个 PCAP 文件
                        pcap = pcap_files[0]
                        file_bytes = get_pcap_file(pcap['id'])
                        if file_bytes:
                            st.download_button(
                                label="⬇️ Download",
                                data=file_bytes,
                                file_name=pcap['file_name'],
                                mime="application/octet-stream",
                                use_container_width=True,
                                key=f"download_pcap_{exp_id}"
                            )
                        else:
                            # 如果文件获取失败，显示禁用状态的按钮
                            st.button("⬇️ Download", disabled=True, use_container_width=True, key=f"download_pcap_disabled_{exp_id}")
                    else:
                        st.button("⬇️ Download", disabled=True, use_container_width=True, key=f"download_pcap_disabled_{exp_id}")
                st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.info("🔍 当前筛选条件下没有匹配的实验。")

else:
    # 空状态
    st.markdown("""
    <div style="text-align: center; padding: 60px; background: #f8f9fa; border-radius: 15px; margin: 20px 0;">
        <h2 style="color: #6c757d; margin-bottom: 20px;">🌟 No Experiments Yet</h2>
        <p style="color: #6c757d; font-size: 18px; margin-bottom: 30px;">
            Start monitoring your IoT experiments by launching your first task!
        </p>
        <div style="background: white; padding: 20px; border-radius: 10px; border: 2px dashed #dee2e6;">
            <p style="margin: 0; color: #6c757d;">
                💡 <strong>Tip:</strong> Go to the Device Details page and start a DoS experiment to see it here.
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

# 自动刷新
if auto_refresh and experiments:
    time.sleep(refresh_interval)
    st.rerun() 