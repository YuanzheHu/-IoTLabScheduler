import streamlit as st
import subprocess
import sys
import os

st.set_page_config(page_title="Settings")
st.title("⚙️ Settings")

# 导入配置
try:
    from config import API_URL, EXPERIMENTS_URL, CAPTURES_URL
except ImportError:
    API_URL = "http://localhost:8000/devices"
    EXPERIMENTS_URL = "http://localhost:8000/experiments"
    CAPTURES_URL = "http://localhost:8000/captures"

# 系统信息
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

# 数据库管理
st.markdown("## 🗄️ Database Management")

with st.expander("⚠️ Database Reset", expanded=False):
    st.warning("""
    **⚠️ 警告：此操作将重置整个数据库！**
    
    - 所有设备信息将被清除
    - 所有扫描结果将被删除
    - 所有实验记录将被清除
    - 所有PCAP文件记录将被删除
    
    此操作不可逆，请谨慎使用！
    """)
    
    # 确认重置
    if st.button("🗑️ Reset Database", type="primary", use_container_width=True):
        st.info("正在重置数据库...")
        
        try:
            # 执行数据库重置命令
            result = subprocess.run(
                ["python3", "-m", "project.db.init_db"],
                capture_output=True,
                text=True,
                cwd=os.getcwd(),
                timeout=30
            )
            
            if result.returncode == 0:
                st.success("✅ 数据库重置成功！")
                st.code(result.stdout)
                
                # 显示重置后的信息
                st.info("""
                **重置完成：**
                - 数据库表已重新创建
                - 所有数据已清除
                - 系统已准备就绪
                
                建议刷新页面以查看最新状态。
                """)
            else:
                st.error("❌ 数据库重置失败！")
                st.error(f"错误代码: {result.returncode}")
                st.code(result.stderr)
                
        except subprocess.TimeoutExpired:
            st.error("❌ 数据库重置超时！")
        except FileNotFoundError:
            st.error("❌ 找不到python3命令或project.db.init_db模块！")
        except Exception as e:
            st.error(f"❌ 重置过程中发生错误: {str(e)}")

# 系统维护
st.markdown("## 🔧 System Maintenance")

with st.expander("🧹 System Cleanup", expanded=False):
    st.info("""
    **系统清理功能：**
    - 清理临时文件
    - 清理日志文件
    - 优化数据库
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🧹 Clean Temp Files", use_container_width=True):
            st.info("清理临时文件功能开发中...")
    
    with col2:
        if st.button("📊 Optimize Database", use_container_width=True):
            st.info("数据库优化功能开发中...")

# 配置管理
st.markdown("## ⚙️ Configuration")

with st.expander("🔧 API Configuration", expanded=False):
    st.info("当前API配置：")
    
    api_url = st.text_input("API Base URL", value=API_URL, help="API服务器地址")
    experiments_url = st.text_input("Experiments API URL", value=EXPERIMENTS_URL, help="实验API地址")
    captures_url = st.text_input("Captures API URL", value=CAPTURES_URL, help="捕获API地址")
    
    if st.button("💾 Save Configuration", use_container_width=True):
        st.success("配置保存功能开发中...")

# 日志查看
st.markdown("## 📋 System Logs")

with st.expander("📄 View Logs", expanded=False):
    st.info("系统日志查看功能开发中...")
    
    log_type = st.selectbox("日志类型", ["Application", "Database", "API", "All"])
    
    if st.button("📋 Load Logs", use_container_width=True):
        st.info("日志加载功能开发中...")

# 帮助信息
st.markdown("## ❓ Help & Support")

with st.expander("📚 Documentation", expanded=False):
    st.markdown("""
    **系统文档：**
    
    ### 数据库重置
    - 执行 `python3 -m project.db.init_db` 命令
    - 清除所有现有数据
    - 重新创建数据库表结构
    
    ### API端点
    - 设备管理: `/devices`
    - 实验管理: `/experiments`
    - 捕获管理: `/captures`
    - 扫描结果: `/scan-results`
    
    ### 故障排除
    - 检查Docker容器状态
    - 查看API服务日志
    - 验证网络连接
    """)

# 页脚
st.markdown("---")
st.caption("IoTLabScheduler - System Settings") 