"""
Scan Visualization Page
Comprehensive visualization of all scan results with IP vs Ports, Services, and OS analysis
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import urllib.parse
import numpy as np

# ============================================================================
# ANALYSIS FUNCTIONS - Must be defined before page execution
# ============================================================================

def calculate_device_risk_score(device: Dict) -> Dict:
    """计算设备风险评分 - 更严格的标准，重点关注开放端口"""
    
    risk_factors = {
        'open_ports': 0,
        'open_filtered_ports': 0,  # 新增：open|filtered端口风险
        'high_risk_services': 0,
        'network_exposure': 0,
        'vendor_risk': 0,
        'os_detection': 0,
        'port_scan_status': 0,
        'port_vulnerabilities': 0,  # 新增：端口漏洞风险
        'service_versions': 0,      # 新增：服务版本风险
        'network_services': 0       # 新增：网络服务风险
    }
    
    # 1. 开放端口风险 - 大幅提高基础分数
    ports = device.get('ports', [])
    open_ports = [p for p in ports if p.get('state') == 'open']
    open_filtered_ports = [p for p in ports if p.get('state') == 'open|filtered']
    
    risk_factors['open_ports'] = len(open_ports) * 12  # 每个开放端口12分（从5分提高到12分）
    risk_factors['open_filtered_ports'] = len(open_filtered_ports) * 8  # 每个open|filtered端口8分
    
    # 2. 高风险服务风险 - 提高风险权重
    high_risk_services = {
        'ssh': 15, 'telnet': 20, 'ftp': 15, 'rsh': 25, 'rlogin': 25,
        'vnc': 18, 'rdp': 18, 'smb': 12, 'snmp': 10, 'dns': 6,
        'http': 8, 'https': 5, 'smtp': 12, 'pop3': 12, 'imap': 12,
        'mysql': 15, 'postgresql': 15, 'redis': 18, 'mongodb': 18,
        'telnet': 20, 'rsh': 25, 'rlogin': 25, 'finger': 20
    }
    
    # 检查开放端口和open|filtered端口的高风险服务
    all_risky_ports = open_ports + open_filtered_ports
    for port in all_risky_ports:
        service = port.get('service', '').lower()
        if service in high_risk_services:
            risk_factors['high_risk_services'] += high_risk_services[service]
    
    # 3. 网络暴露风险 - 提高距离风险
    if device.get('network_distance'):
        try:
            distance = int(device['network_distance'].split()[0])
            risk_factors['network_exposure'] = distance * 8  # 距离越远风险越高（从3分提高到8分）
        except:
            risk_factors['network_exposure'] = 0
    
    # 4. 厂商风险 - 更严格的厂商评估
    vendor_risk_levels = {
        'Unknown': 12, 'Generic': 8, 'Cisco': 4, 'HP': 4, 'Dell': 4,
        'Juniper': 4, 'Arista': 4, 'Brocade': 6, 'Extreme': 6
    }
    vendor = device.get('vendor', 'Unknown')
    risk_factors['vendor_risk'] = vendor_risk_levels.get(vendor, 8)  # 默认风险提高
    
    # 5. OS检测状态风险 - 提高未检测风险
    if device.get('os_guesses'):
        risk_factors['os_detection'] = 0  # 已检测到OS
    else:
        risk_factors['os_detection'] = 12  # 未检测到OS（从5分提高到12分）
    
    # 6. 端口扫描状态风险 - 提高未扫描风险
    if device.get('ports'):
        risk_factors['port_scan_status'] = 0  # 已扫描
    else:
        risk_factors['port_scan_status'] = 20  # 未扫描（从10分提高到20分）
    
    # 7. 端口漏洞风险 - 新增：检查常见漏洞端口
    vulnerable_ports = {21, 23, 25, 53, 80, 110, 143, 161, 389, 443, 445, 1433, 1521, 3306, 5432, 6379, 8080, 8443}
    for port in all_risky_ports:
        port_num = port.get('port', 0)
        if port_num in vulnerable_ports:
            risk_factors['port_vulnerabilities'] += 8  # 每个漏洞端口8分
    
    # 8. 服务版本风险 - 新增：检查服务版本信息
    for port in all_risky_ports:
        version = port.get('version', '')
        if version and ('old' in version.lower() or 'deprecated' in version.lower()):
            risk_factors['service_versions'] += 12  # 过时服务版本12分
    
    # 9. 网络服务风险 - 新增：检查网络服务类型
    network_service_ports = {80, 443, 8080, 8443, 3000, 5000, 8000, 9000}
    for port in all_risky_ports:
        port_num = port.get('port', 0)
        if port_num in network_service_ports:
            risk_factors['network_services'] += 5  # 网络服务端口5分
    
    # 计算总分
    total_risk = sum(risk_factors.values())
    
    # 更严格的风险等级划分
    if total_risk < 25:
        risk_level = 'Low'
    elif total_risk < 60:
        risk_level = 'Medium'
    elif total_risk < 100:
        risk_level = 'High'
    else:
        risk_level = 'Critical'  # 新增：极高风险等级
    
    return {
        'total_score': total_risk,
        'risk_level': risk_level,
        'risk_factors': risk_factors,
        'recommendations': generate_risk_recommendations(risk_factors)
    }

def generate_risk_recommendations(risk_factors: Dict) -> List[str]:
    """生成风险建议 - 重点关注开放端口安全"""
    
    recommendations = []
    
    # 开放端口相关建议
    if risk_factors['open_ports'] > 0:
        if risk_factors['open_ports'] > 10:
            recommendations.append("🔴 Critical: High number of open ports - Immediately close unnecessary ports")
        elif risk_factors['open_ports'] > 5:
            recommendations.append("🟠 Warning: Multiple open ports detected - Review and close unnecessary ports")
        else:
            recommendations.append("🟡 Notice: Open ports detected - Verify these ports are necessary")
    
    # open|filtered端口相关建议
    if risk_factors['open_filtered_ports'] > 0:
        if risk_factors['open_filtered_ports'] > 5:
            recommendations.append("🔴 Critical: High number of open|filtered ports - These ports may be accessible")
        else:
            recommendations.append("🟠 Warning: Open|filtered ports detected - Investigate accessibility")
    
    # 高风险服务建议
    if risk_factors['high_risk_services'] > 20:
        recommendations.append("🔴 Critical: Multiple high-risk services detected - Immediate security review required")
    elif risk_factors['high_risk_services'] > 10:
        recommendations.append("🟠 Warning: High-risk services detected - Secure or disable these services")
    
    # 端口漏洞建议
    if risk_factors['port_vulnerabilities'] > 0:
        recommendations.append("🔴 Critical: Vulnerable ports detected - Apply security patches immediately")
    
    # 服务版本建议
    if risk_factors['service_versions'] > 0:
        recommendations.append("🟠 Warning: Outdated service versions detected - Update to latest versions")
    
    # 网络服务建议
    if risk_factors['network_services'] > 10:
        recommendations.append("🟠 Warning: Multiple network services exposed - Review external accessibility")
    
    # 网络暴露建议
    if risk_factors['network_exposure'] > 20:
        recommendations.append("🟠 Warning: Device is far from network core - Consider network segmentation")
    
    # 厂商风险建议
    if risk_factors['vendor_risk'] > 8:
        recommendations.append("🟠 Warning: Unknown vendor detected - Verify device authenticity")
    
    # OS检测建议
    if risk_factors['os_detection'] > 0:
        recommendations.append("🟡 Notice: OS not detected - Run OS detection scan for better assessment")
    
    # 端口扫描建议
    if risk_factors['port_scan_status'] > 0:
        recommendations.append("🟡 Notice: Port scan not performed - Run comprehensive port scan")
    
    # 如果没有具体风险，给出一般性建议
    if not recommendations:
        recommendations.append("✅ Device appears to be secure - Continue monitoring")
    
    return recommendations

def create_risk_summary_chart(data: List[Dict]):
    """创建风险摘要图表"""
    
    # 计算所有设备的风险评分
    risk_data = []
    for device in data:
        risk_score = calculate_device_risk_score(device)
        risk_data.append({
            'Device': device.get('hostname', device.get('ip_address', 'Unknown')),
            'IP': device.get('ip_address', 'Unknown'),
            'Risk_Score': risk_score['total_score'],
            'Risk_Level': risk_score['risk_level'],
            'Vendor': device.get('vendor', 'Unknown'),
            'Open_Ports': len([p for p in device.get('ports', []) if p.get('state') == 'open'])
        })
    
    if not risk_data:
        return None
    
    df_risk = pd.DataFrame(risk_data)
    
    # 创建风险等级分布饼图
    risk_level_counts = df_risk['Risk_Level'].value_counts()
    
    fig1 = px.pie(
            values=risk_level_counts.values,
            names=risk_level_counts.index,
            title="Device Risk Level Distribution",
            color_discrete_map={
                'Low': '#00ff00',
                'Medium': '#ffff00', 
                'High': '#ff0000',
                'Critical': '#8b0000'  # 深红色表示极高风险
            }
        )
    
    fig1.update_layout(height=400, title_x=0.5)
    
    # 创建风险评分分布直方图
    fig2 = px.histogram(
        df_risk,
        x='Risk_Score',
        color='Risk_Level',
        title="Risk Score Distribution",
        labels={'Risk_Score': 'Risk Score', 'count': 'Device Count'},
        color_discrete_map={
            'Low': '#00ff00',
            'Medium': '#ffff00',
            'High': '#ff0000',
            'Critical': '#8b0000'  # 深红色表示极高风险
        }
    )
    
    fig2.update_layout(height=400, title_x=0.5)
    
    return fig1, fig2

def create_risk_details_table(data: List[Dict]):
    """创建风险详情表格"""
    
    risk_details = []
    for device in data:
        risk_score = calculate_device_risk_score(device)
        
        risk_details.append({
            'Device Name': device.get('hostname', 'Unknown'),
            'IP Address': device.get('ip_address', 'Unknown'),
            'Risk Score': risk_score['total_score'],
            'Risk Level': risk_score['risk_level'],
            'Open Ports': len([p for p in device.get('ports', []) if p.get('state') == 'open']),
            'Open|Filtered': len([p for p in device.get('ports', []) if p.get('state') == 'open|filtered']),
            'High Risk Services': risk_score['risk_factors']['high_risk_services'],
            'Port Vulnerabilities': risk_score['risk_factors']['port_vulnerabilities'],
            'Network Distance': device.get('network_distance', 'Unknown'),
            'Vendor': device.get('vendor', 'Unknown'),
            'OS Detected': 'Yes' if device.get('os_guesses') else 'No',
            'Top Recommendation': risk_score['recommendations'][0] if risk_score['recommendations'] else 'None'
        })
    
    if not risk_details:
        return None
    
    df_risk_details = pd.DataFrame(risk_details)
    df_risk_details = df_risk_details.sort_values('Risk Score', ascending=False)
    
    return df_risk_details

# Page configuration
st.set_page_config(
    page_title="Scan Visualization",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Scan Visualization - Comprehensive Analysis")
st.markdown("---")

# Configuration
API_BASE_URL = "http://localhost:8000"
DEVICES_URL = f"{API_BASE_URL}/devices/"
SCAN_RESULTS_URL = f"{API_BASE_URL}/scan-results"

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_all_devices():
    """Fetch all devices from the API"""
    try:
        response = requests.get(DEVICES_URL, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to fetch devices: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Error fetching devices: {e}")
        return []

@st.cache_data(ttl=300)
def fetch_device_scan_results(device_id: int):
    """Fetch scan results for a specific device"""
    try:
        response = requests.get(f"{SCAN_RESULTS_URL}/device/{device_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to fetch scan results for device {device_id}: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error fetching scan results for device {device_id}: {e}")
        return []

@st.cache_data(ttl=300)
def fetch_comprehensive_scan_data():
    """Fetch comprehensive scan data for all devices"""
    devices = fetch_all_devices()
    if not devices:
        return []
    
    comprehensive_data = []
    
    for device in devices:
        device_id = device.get('id')
        if not device_id:
            continue
            
        # Get latest scan results for this device
        scan_results = fetch_device_scan_results(device_id)
        
        # Extract latest OS scan and Port scan
        latest_os_scan = None
        latest_port_scan = None
        
        for scan in scan_results:
            if scan.get('scan_type') == 'os_scan':
                if not latest_os_scan or scan.get('scan_time', '') > latest_os_scan.get('scan_time', ''):
                    latest_os_scan = scan
            elif scan.get('scan_type') == 'port_scan':
                if not latest_port_scan or scan.get('scan_time', '') > latest_port_scan.get('scan_time', ''):
                    latest_port_scan = scan
        
        # Build comprehensive device data
        device_data = {
            'device_id': device_id,
            'hostname': device.get('hostname', 'Unknown'),
            'mac_address': device.get('mac_address', 'Unknown'),
            'ip_address': device.get('ip_address', 'Unknown'),
            'status': device.get('status', 'unknown'),
            'vendor': device.get('vendor', 'Unknown'),
            'network_distance': device.get('network_distance'),
            'latency': device.get('latency'),
            'last_seen': device.get('last_seen'),
            'os_scan_time': latest_os_scan.get('scan_time') if latest_os_scan else None,
            'port_scan_time': latest_port_scan.get('scan_time') if latest_port_scan else None,
            'os_guesses': latest_os_scan.get('os_guesses', []) if latest_os_scan else [],
            'os_details': latest_os_scan.get('os_details', {}) if latest_os_scan else {},
            'ports': latest_port_scan.get('ports', []) if latest_port_scan else [],
            'open_ports': len([p for p in latest_port_scan.get('ports', []) if p.get('state') == 'open']) if latest_port_scan else 0,
            'total_ports_scanned': len(latest_port_scan.get('ports', [])) if latest_port_scan else 0,
            'port_scan_duration': latest_port_scan.get('scan_duration', 0) if latest_port_scan else 0,
            'os_scan_duration': latest_os_scan.get('scan_duration', 0) if latest_os_scan else 0,
        }
        
        comprehensive_data.append(device_data)
    
    return comprehensive_data

def create_ip_vs_ports_chart(data: List[Dict]):
    """Create IP vs Ports chart with port status colors for online devices"""
    if not data:
        return None
    
    # Prepare data for the chart - only include devices with port scan data
    chart_data = []
    devices_with_ports = []
    
    for device in data:
        # Only include online devices with IP addresses that have port scan data
        if (device.get('status') == 'online' and 
            device.get('ip_address') and 
            device.get('ip_address') not in ['', 'Unknown', 'None']):
            
            ip_address = device['ip_address']
            device_name = device.get('hostname', 'Unknown')
            vendor = device.get('vendor', 'Unknown')
            ports = device.get('ports', [])
            
            # Only include devices that have actual port scan data
            if ports and len(ports) > 0:
                devices_with_ports.append({
                    'ip_address': ip_address,
                    'device_name': device_name,
                    'vendor': vendor,
                    'total_ports': len(ports)
                })
                
                # Count ports by status
                port_status_counts = {}
                for port in ports:
                    status = port.get('state', 'unknown')
                    if status not in port_status_counts:
                        port_status_counts[status] = 0
                    port_status_counts[status] += 1
                
                # Create a row for each port status
                for status, count in port_status_counts.items():
                    chart_data.append({
                        'IP Address': ip_address,
                        'Device Name': device_name,
                        'Port Count': count,
                        'Port Status': status.title(),
                        'Vendor': vendor,
                        'Total Ports': len(ports)
                    })
    
    if not chart_data:
        return None
    
    df = pd.DataFrame(chart_data)
    
    # Sort devices by total ports (descending) - only devices with ports
    devices_with_ports.sort(key=lambda x: x['total_ports'], reverse=True)
    
    # Create ordered categories for IP addresses based on total ports
    ip_order = [device['ip_address'] for device in devices_with_ports]
    
    # Sort by total ports (descending), then by port status
    df['IP Address'] = pd.Categorical(df['IP Address'], categories=ip_order, ordered=True)
    df = df.sort_values(['IP Address', 'Port Status'])
    
    # Create stacked bar chart
    fig = px.bar(
        df,
        x='IP Address',
        y='Port Count',
        color='Port Status',
        title="Online Devices IP Address vs Port Status Distribution Analysis",
        labels={'Port Count': 'Port Count', 'IP Address': 'Device IP Address', 'Port Status': 'Port Status'},
        hover_data=['Device Name', 'Total Ports', 'Vendor'],
        color_discrete_map={
            'Open': '#00ff00',      # Green - Open ports
            'Closed': '#ff4444',    # Red - Closed ports  
            'Filtered': '#ffa500',  # Orange - Filtered ports
            'Open|Filtered': '#ffff00',  # Yellow - Open or filtered ports
            'Unknown': '#808080',   # Gray - Unknown status
        }
    )
    
    fig.update_layout(
        height=600,
        xaxis_tickangle=45,
        showlegend=True,
        title_x=0.5,
        barmode='stack',  # Stack mode to display different port statuses
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig

def create_online_devices_scan_status_chart(comprehensive_data: List[Dict]):
    """Create a chart showing scan status for all online devices"""
    # Get all devices (not just from comprehensive_data)
    all_devices = fetch_all_devices()
    
    # Filter for online devices only
    online_devices = [d for d in all_devices if d.get('status') == 'online' and d.get('ip_address')]
    
    if not online_devices:
        return None
    
    chart_data = []
    
    for device in online_devices:
        device_id = device.get('id')
        ip_address = device.get('ip_address')
        hostname = device.get('hostname', 'Unknown')
        vendor = device.get('vendor', 'Unknown')
        
        # Check if device has scan data - check actual scan records, not just results
        has_port_scan = False
        has_os_scan = False
        port_scan_empty = False
        os_scan_empty = False
        
        # Get scan results for this device to check if scans were performed
        if device_id:
            scan_results = fetch_device_scan_results(device_id)
            
            for scan in scan_results:
                if scan.get('scan_type') == 'port_scan':
                    has_port_scan = True
                    # Check if scan was performed but had no results
                    ports = scan.get('ports', [])
                    if not ports or len(ports) == 0:
                        port_scan_empty = True
                elif scan.get('scan_type') == 'os_scan':
                    has_os_scan = True
                    # Check if scan was performed but had no results
                    os_guesses = scan.get('os_guesses', [])
                    if not os_guesses or len(os_guesses) == 0:
                        os_scan_empty = True
        
        # Determine scan status with more granular information
        if has_port_scan and has_os_scan:
            if port_scan_empty and os_scan_empty:
                scan_status = "Both Scans (No Results)"
                color_status = "#ff8c00"  # Dark orange
            elif port_scan_empty or os_scan_empty:
                scan_status = "Both Scans (Partial Results)"
                color_status = "#32cd32"  # Lime green
            else:
                scan_status = "Both Scans (Complete)"
                color_status = "#00ff00"  # Green
        elif has_port_scan:
            if port_scan_empty:
                scan_status = "Port Scan (No Results)"
                color_status = "#ffb347"  # Light orange
            else:
                scan_status = "Port Scan Only"
                color_status = "#ffa500"  # Orange
        elif has_os_scan:
            if os_scan_empty:
                scan_status = "OS Scan (No Results)"
                color_status = "#87ceeb"  # Light blue
            else:
                scan_status = "OS Scan Only"
                color_status = "#00bfff"  # Blue
        else:
            scan_status = "No Scans"
            color_status = "#ff4444"  # Red
        
        chart_data.append({
            'IP Address': ip_address,
            'Device Name': hostname,
            'Scan Status': scan_status,
            'Vendor': vendor,
            'Port Scan': '✅' if has_port_scan and not port_scan_empty else ('⚠️' if has_port_scan else '❌'),
            'OS Scan': '✅' if has_os_scan and not os_scan_empty else ('⚠️' if has_os_scan else '❌')
        })
    
    if not chart_data:
        return None
    
    df = pd.DataFrame(chart_data)
    
    # Create bar chart
    fig = px.bar(
        df,
        x='IP Address',
        y=[1] * len(df),  # All bars same height
        color='Scan Status',
        title="Online Devices Scan Status Overview",
        labels={'y': 'Device Count', 'IP Address': 'Device IP Address'},
        hover_data=['Device Name', 'Vendor', 'Port Scan', 'OS Scan'],
        color_discrete_map={
            'Both Scans (Complete)': '#00ff00',      # Green - Complete with results
            'Both Scans (Partial Results)': '#32cd32',  # Lime green - Some results
            'Both Scans (No Results)': '#ff8c00',    # Dark orange - Scanned but no results
            'Port Scan Only': '#ffa500',             # Orange - Port scan with results
            'Port Scan (No Results)': '#ffb347',     # Light orange - Port scan no results
            'OS Scan Only': '#00bfff',               # Blue - OS scan with results
            'OS Scan (No Results)': '#87ceeb',       # Light blue - OS scan no results
            'No Scans': '#ff4444'                    # Red - Not scanned
        }
    )
    
    fig.update_layout(
        height=400,
        xaxis_tickangle=45,
        showlegend=True,
        title_x=0.5,
        yaxis=dict(showticklabels=False, title=""),  # Hide y-axis as it's not meaningful
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig, df

def create_service_analysis_charts(data: List[Dict]):
    """Create comprehensive service analysis visualizations"""
    if not data:
        return None, None
    
    # Collect all services and their states
    service_counts = {}
    service_by_state = {'open': {}, 'closed': {}, 'filtered': {}, 'open|filtered': {}}
    port_service_mapping = {}
    
    for device in data:
        ports = device.get('ports', [])
        for port in ports:
            service = port.get('service', 'unknown')
            state = port.get('state', 'unknown')
            port_num = port.get('port', '')
            
            # Count services
            if service not in service_counts:
                service_counts[service] = 0
            service_counts[service] += 1
            
            # Count by state
            if state in service_by_state:
                if service not in service_by_state[state]:
                    service_by_state[state][service] = 0
                service_by_state[state][service] += 1
            
            # Map port numbers to services
            if port_num and '/' in str(port_num):
                port_number = str(port_num).split('/')[0]
                if port_number not in port_service_mapping:
                    port_service_mapping[port_number] = set()
                port_service_mapping[port_number].add(service)
    
    # Create service distribution pie chart
    if service_counts:
        # Top 15 services
        top_services = sorted(service_counts.items(), key=lambda x: x[1], reverse=True)[:15]
        
        fig1 = px.pie(
            values=[s[1] for s in top_services],
            names=[s[0] for s in top_services],
            title="Top 15 Services Distribution",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig1.update_layout(height=400, title_x=0.5)
        
        # Create stacked bar chart by state
        service_state_data = []
        for service, count in sorted(service_counts.items(), key=lambda x: x[1], reverse=True)[:20]:
            for state in ['open', 'closed', 'filtered', 'open|filtered']:
                service_state_data.append({
                    'Service': service,
                    'State': state.title(),
                    'Count': service_by_state.get(state, {}).get(service, 0)
                })
        
        df_services = pd.DataFrame(service_state_data)
        
        fig2 = px.bar(
            df_services,
            x='Service',
            y='Count',
            color='State',
            title="Service Distribution by Port State",
            labels={'Count': 'Number of Ports', 'Service': 'Service Name'},
            color_discrete_map={
                'Open': '#00ff00',       # Green - Open ports (same as IP vs Ports)
                'Closed': '#ff4444',     # Red - Closed ports (same as IP vs Ports)
                'Filtered': '#ffa500',   # Orange - Filtered ports (same as IP vs Ports)
                'Open|Filtered': '#ffff00'  # Yellow - Open or filtered ports (same as IP vs Ports)
            }
        )
        
        fig2.update_layout(
            height=400,
            xaxis_tickangle=45,
            barmode='stack',
            title_x=0.5
        )
        
        return fig1, fig2
    
    return None, None

def create_os_analysis_charts(data: List[Dict]):
    """Create comprehensive OS analysis visualizations"""
    if not data:
        return None, None, None, None
    
    # OS Detection Analysis
    os_patterns = {}
    vendor_os_mapping = {}
    vendor_counts = {}
    os_detection_stats = {
        'Detected': 0,
        'Not Detected': 0,
        'Multiple Matches': 0
    }
    
    for device in data:
        os_guesses = device.get('os_guesses', [])
        os_details = device.get('os_details', {})
        vendor = device.get('vendor', 'Unknown')
        
        # Count vendors (for all devices, regardless of OS detection)
        # Skip 'Unknown' vendors
        if vendor and vendor != 'Unknown' and vendor != '':
            if vendor not in vendor_counts:
                vendor_counts[vendor] = 0
            vendor_counts[vendor] += 1
        
        if os_guesses and len(os_guesses) > 0:
            if len(os_guesses) > 1:
                os_detection_stats['Multiple Matches'] += 1
            else:
                os_detection_stats['Detected'] += 1
            
            # Get OS info
            os_info = "Unknown"
            if os_details.get('details'):
                os_info = os_details['details']
            elif os_guesses:
                os_info = os_guesses[0]
            
            # Count OS patterns
            if os_info not in os_patterns:
                os_patterns[os_info] = 0
            os_patterns[os_info] += 1
            
            # Map vendor to OS
            if vendor not in vendor_os_mapping:
                vendor_os_mapping[vendor] = {}
            if os_info not in vendor_os_mapping[vendor]:
                vendor_os_mapping[vendor][os_info] = 0
            vendor_os_mapping[vendor][os_info] += 1
        else:
            os_detection_stats['Not Detected'] += 1
    
    # Create OS detection success rate pie chart
    fig1 = px.pie(
        values=list(os_detection_stats.values()),
        names=list(os_detection_stats.keys()),
        title="OS Detection Success Rate",
        color_discrete_map={
            'Detected': '#00ff00',
            'Not Detected': '#ff0000',
            'Multiple Matches': '#ffff00'
        }
    )
    fig1.update_layout(height=400, title_x=0.5)
    
    # Create top OS patterns bar chart
    if os_patterns:
        top_patterns = sorted(os_patterns.items(), key=lambda x: x[1], reverse=True)[:15]
        
        # Truncate long OS names for display
        pattern_names = []
        for pattern, _ in top_patterns:
            # Handle None or empty OS names
            if pattern is None or pattern == '':
                pattern_names.append("Unknown")
            elif len(str(pattern)) > 40:
                pattern_names.append(str(pattern)[:40] + "...")
            else:
                pattern_names.append(str(pattern))
        
        fig2 = px.bar(
            x=[p[1] for p in top_patterns],
            y=pattern_names,
            orientation='h',
            title="Top 15 Operating System Patterns",
            labels={'x': 'Device Count', 'y': 'Operating System'},
            color_discrete_sequence=['#3498db']
        )
        fig2.update_layout(height=400, title_x=0.5)
    else:
        fig2 = None
    
    # Create top 15 vendors bar chart
    if vendor_counts:
        # Get top 15 vendors by device count
        top_vendors = sorted(vendor_counts.items(), key=lambda x: x[1], reverse=True)[:15]
        
        # Truncate long vendor names for display (similar to OS patterns)
        vendor_names = []
        for vendor, _ in top_vendors:
            # Handle None or empty vendor names
            if vendor is None or vendor == '':
                vendor_names.append("Unknown")
            elif len(str(vendor)) > 40:
                vendor_names.append(str(vendor)[:40] + "...")
            else:
                vendor_names.append(str(vendor))
        
        fig3 = px.bar(
            x=[v[1] for v in top_vendors],
            y=vendor_names,
            orientation='h',
            title="Top 15 Vendors by Device Count",
            labels={'x': 'Device Count', 'y': 'Vendor'},
            color_discrete_sequence=['#3498db']  # Same color as OS patterns
        )
        fig3.update_layout(height=400, title_x=0.5)  # Same height as OS patterns
    else:
        fig3 = None
    
    # Create vendor-OS heatmap
    vendor_os_data = []
    for vendor, os_dict in vendor_os_mapping.items():
        # Skip 'Unknown' vendors in heatmap
        if vendor and vendor != 'Unknown' and vendor != '':
            for os_info, count in os_dict.items():
                # Handle None or empty OS values
                safe_os_info = "Unknown" if os_info is None or os_info == '' else str(os_info)
                
                vendor_os_data.append({
                    'Vendor': str(vendor),
                    'OS': safe_os_info[:30] + "..." if len(safe_os_info) > 30 else safe_os_info,
                    'Count': count
                })
    
    if vendor_os_data:
        df_heatmap = pd.DataFrame(vendor_os_data)
        # Pivot for heatmap
        pivot_df = df_heatmap.pivot_table(
            index='Vendor', 
            columns='OS', 
            values='Count', 
            fill_value=0
        )
        
        # Limit to top vendors and OS
        top_vendors = pivot_df.sum(axis=1).nlargest(10).index
        top_os = pivot_df.sum(axis=0).nlargest(10).index
        pivot_df = pivot_df.loc[top_vendors, top_os]
        
        fig4 = px.imshow(
            pivot_df,
            labels=dict(x="Operating System", y="Vendor", color="Device Count"),
            title="Vendor vs Operating System Heatmap",
            color_continuous_scale="Blues"
        )
        fig4.update_layout(
            height=600, 
            title_x=0.5,
            xaxis=dict(tickangle=45, tickfont=dict(size=12)),
            yaxis=dict(tickfont=dict(size=12)),
            font=dict(size=12)
        )
    else:
        fig4 = None
    
    return fig1, fig2, fig3, fig4
    
    return fig1, None, None, None

def create_port_distribution_analysis(data: List[Dict]):
    """Create port distribution analysis focused on protocol types and port ranges"""
    if not data:
        return None, None, None
    
    # Analyze ports with focus on protocol and range distribution
    analysis_data = []
    protocol_stats = {'TCP': 0, 'UDP': 0}
    range_stats = {'Well-known': 0, 'Registered': 0, 'Dynamic': 0}
    
    for device in data:
        ports = device.get('ports', [])
        for port in ports:
            port_str = str(port.get('port', ''))
            state = port.get('state', 'unknown')
            
            if '/' in port_str:
                try:
                    parts = port_str.split('/')
                    port_num = int(parts[0])
                    protocol = parts[1].upper()
                    
                    # Categorize by port range
                    if 0 <= port_num <= 1023:
                        range_category = 'Well-known'
                        range_description = 'System Services (0-1023)'
                        range_color = '#2E86AB'  # Blue
                    elif 1024 <= port_num <= 49151:
                        range_category = 'Registered'
                        range_description = 'User Applications (1024-49151)'
                        range_color = '#A23B72'  # Purple
                    else:
                        range_category = 'Dynamic'
                        range_description = 'Temporary Connections (49152-65535)'
                        range_color = '#F18F01'  # Orange
                    
                    # Count for statistics
                    protocol_stats[protocol] += 1
                    range_stats[range_category] += 1
                    
                    analysis_data.append({
                        'Port_Number': port_num,
                        'Protocol': protocol,
                        'Range_Category': range_category,
                        'Range_Description': range_description,
                        'Range_Color': range_color,
                        'Full_Port': port_str,
                        'Device': device.get('hostname', 'Unknown'),
                        'Service': port.get('service', 'unknown'),
                        'State': state
                    })
                except:
                    pass
    
    if not analysis_data:
        return None, None, None
    
    df_analysis = pd.DataFrame(analysis_data)
    
    # Figure 1: Protocol Distribution Pie Chart
    protocol_counts = df_analysis['Protocol'].value_counts()
    fig1 = px.pie(
        values=protocol_counts.values,
        names=protocol_counts.index,
        title="Protocol Distribution: TCP vs UDP",
        color_discrete_map={
            'TCP': '#1f77b4',  # Blue
            'UDP': '#ff7f0e'   # Orange
        }
    )
    fig1.update_layout(height=400, title_x=0.5)
    
    # Figure 2: Port Range Distribution
    range_counts = df_analysis['Range_Category'].value_counts()
    fig2 = px.bar(
        x=range_counts.index,
        y=range_counts.values,
        title="Port Range Distribution",
        labels={'x': 'Port Range Category', 'y': 'Number of Ports'},
        color=range_counts.index,
        color_discrete_map={
            'Well-known': '#2E86AB',    # Blue
            'Registered': '#A23B72',    # Purple  
            'Dynamic': '#F18F01'        # Orange
        }
    )
    fig2.update_layout(
        height=400,
        title_x=0.5,
        showlegend=False,
        xaxis=dict(title='Port Range Category'),
        yaxis=dict(title='Number of Ports')
    )
    
    # Figure 3: Comprehensive Port Mapping (Protocol × Range)
    # Create a matrix showing protocol vs range distribution
    protocol_range_matrix = df_analysis.groupby(['Protocol', 'Range_Category']).size().unstack(fill_value=0)
    
    # Create heatmap without automatic text to avoid overlap
    fig3 = px.imshow(
        protocol_range_matrix.values,
        labels=dict(x="Port Range", y="Protocol", color="Port Count"),
        x=protocol_range_matrix.columns,
        y=protocol_range_matrix.index,
        title="Protocol × Port Range Distribution Heatmap",
        color_continuous_scale="Blues",
        text_auto=False  # Disable auto text to prevent overlap
    )
    
    # Increase height and adjust layout for better spacing
    fig3.update_layout(
        height=400,  # Increased height
        title_x=0.5,
        xaxis=dict(
            title='Port Range Category',
            title_standoff=20,
            tickfont=dict(size=12)
        ),
        yaxis=dict(
            title='Protocol Type',
            title_standoff=20,
            tickfont=dict(size=12)
        ),
        font=dict(size=12),
        margin=dict(l=80, r=80, t=80, b=80)  # Add margins for better spacing
    )
    
    # Add text annotations with better positioning and dynamic color
    max_value = protocol_range_matrix.max().max() if not protocol_range_matrix.empty else 1
    for i, protocol in enumerate(protocol_range_matrix.index):
        for j, range_cat in enumerate(protocol_range_matrix.columns):
            count = protocol_range_matrix.loc[protocol, range_cat]
            if count > 0:
                # Use dark text for light backgrounds, light text for dark backgrounds
                intensity = count / max_value
                text_color = "white" if intensity > 0.5 else "#333333"  # Dark gray instead of pure black
                
                fig3.add_annotation(
                    x=j, y=i,
                    text=f"<b>{count}</b>",  # Bold formatting
                    showarrow=False,
                    font=dict(color=text_color, size=14, family="Arial"),
                    xanchor="center",
                    yanchor="middle"
                )
    
    return fig1, fig2, fig3

# Main page content
st.markdown("## 🔍 Data Collection and Analysis")

# Fetch data
with st.spinner("🔄 Fetching comprehensive scan data..."):
    comprehensive_data = fetch_comprehensive_scan_data()

if not comprehensive_data:
    st.warning("📊 No comprehensive scan data available yet.")
    st.info("💡 **Getting Started**: Run OS scan and Port scan on some devices to see detailed analysis here.")
    
    # Show basic guidance even without data
    st.markdown("## 🚀 Getting Started")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🔍 **Step 1: Device Discovery**
        - Navigate to the **Devices** page
        - Click **🔍 Scan Network** to discover devices
        - Wait for subnet scanning to complete
        """)
        
        st.markdown("""
        ### 🖥️ **Step 3: OS Detection**
        - Select online devices from the Devices page
        - Run **🖥️ OS Scan** for operating system detection
        - Review detected OS information
        """)
    
    with col2:
        st.markdown("""
        ### 🔍 **Step 2: Port Scanning**
        - Select online devices from the Devices page
        - Run **🔍 Port Scan** to identify open services
        - Choose between fast or comprehensive scanning
        """)
        
        st.markdown("""
        ### 📊 **Step 4: Analysis**
        - Return to this page to view comprehensive analysis
        - Explore different visualization tabs
        - Export results for reporting
        """)
    
    # Show sample visualization placeholders
    st.markdown("## 📊 Available Analysis Views")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔍 Scan Status", "📊 IP vs Ports", "🔧 Service Analysis", "🖥️ OS Analysis"
    ])
    
    with tab1:
        st.info("**Scan Status Overview** - Shows which devices have been scanned and their current status")
        st.markdown("- ✅ Complete scans with results")
        st.markdown("- ⚠️ Scans performed but no results")
        st.markdown("- ❌ Devices not yet scanned")
    
    with tab2:
        st.info("**IP vs Ports Analysis** - Displays port status distribution across all devices")
        st.markdown("- 🟢 Open ports (services running)")
        st.markdown("- 🔴 Closed ports")
        st.markdown("- 🟠 Filtered ports (firewall blocked)")
    
    with tab3:
        st.info("**Service Analysis** - Analyzes detected services and their distribution")
        st.markdown("- Service type distribution")
        st.markdown("- Service security analysis")
        st.markdown("- Port-to-service mapping")
    
    with tab4:
        st.info("**Operating System Analysis** - Shows OS detection results and patterns")
        st.markdown("- OS detection success rates")
        st.markdown("- Top 15 operating system patterns")
        st.markdown("- Top 15 vendors by device count")
        st.markdown("- Vendor vs OS correlations")
        st.markdown("- Device fingerprinting results")
    
    # Add quick navigation
    st.markdown("## 🚀 Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔍 Go to Devices Page", use_container_width=True):
            st.switch_page("pages/devices.py")
    
    with col2:
        if st.button("🔄 Refresh This Page", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    with col3:
        if st.button("📊 View Dashboard", use_container_width=True):
            st.switch_page("dashboard.py")
    
    st.stop()  # Stop here but show the interface above

# Summary Statistics
st.markdown("## 📈 Summary Statistics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    total_devices = len(comprehensive_data)
    online_devices = sum(1 for d in comprehensive_data if d.get('status') == 'online')
    st.metric("Total Devices", total_devices)
    st.metric("Online Devices", online_devices)

with col2:
    devices_with_os_scan = sum(1 for d in comprehensive_data if d.get('os_guesses') or d.get('os_details', {}).get('details'))
    devices_with_port_scan = sum(1 for d in comprehensive_data if d.get('total_ports_scanned', 0) > 0)
    st.metric("OS Scanned", devices_with_os_scan)
    st.metric("Port Scanned", devices_with_port_scan)

with col3:
    total_open_ports = sum(d.get('open_ports', 0) for d in comprehensive_data)
    avg_open_ports = total_open_ports / devices_with_port_scan if devices_with_port_scan > 0 else 0
    st.metric("Total Open Ports", total_open_ports)
    st.metric("Avg Open Ports", f"{avg_open_ports:.1f}")

with col4:
    unique_vendors = len(set(d.get('vendor', 'Unknown') for d in comprehensive_data if d.get('vendor') and d.get('vendor') != 'Unknown'))
    total_services = len(set(p.get('service', 'unknown') for d in comprehensive_data for p in d.get('ports', [])))
    st.metric("Unique Vendors", unique_vendors)
    st.metric("Total Services", total_services)

# Tab-based layout for different visualizations (removed Risk Assessment and Advanced Charts)
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔍 Scan Status", "📊 IP vs Ports", "🔧 Service Analysis", "🖥️ OS Analysis",
    "📈 Port Distribution"
])

with tab1:
    st.markdown("### 🔍 Online Devices Scan Status Overview")
    st.markdown("""
    📌 **Status Legend**: 
    - 🟢 **Green (Both Scans Complete)**: Device has both scans with results
    - 🟢 **Lime (Both Scans Partial)**: Device has both scans, some with results
    - 🟠 **Dark Orange (Both Scans No Results)**: Device scanned but no results found
    - 🟠 **Orange (Port Scan Only)**: Device has port scan with results
    - 🟠 **Light Orange (Port Scan No Results)**: Port scanned but no open ports
    - 🔵 **Blue (OS Scan Only)**: Device has OS scan with results  
    - 🔵 **Light Blue (OS Scan No Results)**: OS scanned but no detection
    - 🔴 **Red (No Scans)**: Device has not been scanned yet
    
    **Shows all online devices** with detailed scan status - distinguishes between "not scanned" vs "scanned but no results".
    
    **Symbol Legend**: ✅ = Has results, ⚠️ = Scanned but no results, ❌ = Not scanned
    """)
    
    # Create and display scan status chart
    scan_status_result = create_online_devices_scan_status_chart(comprehensive_data)
    if scan_status_result:
        scan_status_chart, scan_status_df = scan_status_result
        st.plotly_chart(scan_status_chart, use_container_width=True)
        
        # Display detailed table
        st.markdown("#### 📋 Detailed Scan Status Table")
        st.dataframe(scan_status_df, use_container_width=True)
        
        # Show summary statistics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            complete_scans = len(scan_status_df[scan_status_df['Scan Status'] == 'Both Scans (Complete)'])
            st.metric("✅ Complete", complete_scans)
        with col2:
            partial_scans = len(scan_status_df[scan_status_df['Scan Status'].str.contains('Partial|No Results')])
            st.metric("⚠️ Scanned/No Results", partial_scans)
        with col3:
            single_scans = len(scan_status_df[scan_status_df['Scan Status'].str.contains('Only')])
            st.metric("🔄 Single Scan", single_scans)
        with col4:
            no_scans = len(scan_status_df[scan_status_df['Scan Status'] == 'No Scans'])
            st.metric("❌ Not Scanned", no_scans)
    else:
        st.info("📊 No online devices found. Please ensure devices are online first.")

with tab2:
    st.markdown("### 📊 Online Devices IP Address vs Port Status Distribution Analysis")
    st.markdown("""
    📌 **Chart Legend**: 
    - 🟢 **Green (Open)**: Open ports - Services are running
    - 🔴 **Red (Closed)**: Closed ports - Ports are not accessible
    - 🟠 **Orange (Filtered)**: Filtered ports - Blocked by firewall
    - 🟠 **Dark Orange (Open|Filtered)**: Open or filtered ports - Cannot determine exact status
    - ⚪ **Gray (Unknown)**: Unknown status - Port status cannot be determined
    
    **Showing only online devices with port scan data**. Devices are sorted by total ports scanned (highest to lowest). Each device displays port status in stacked format.
    """)
    
    # Create and display IP vs Ports chart
    ip_ports_chart = create_ip_vs_ports_chart(comprehensive_data)
    if ip_ports_chart:
        st.plotly_chart(ip_ports_chart, use_container_width=True)
        
        # Add detailed table
        st.markdown("#### 📋 Device Port Summary Table")
        
        # Create summary table for online devices with port scan data
        table_data = []
        for device in comprehensive_data:
            # Only include online devices with IP addresses that have port scan data
            if (device.get('status') == 'online' and 
                device.get('ip_address') and 
                device.get('ip_address') not in ['', 'Unknown', 'None']):
                
                # Get port details
                ports = device.get('ports', [])
                
                # Only include devices with actual port scan data
                if ports and len(ports) > 0:
                    open_ports = [p for p in ports if p.get('state') == 'open']
                    closed_ports = [p for p in ports if p.get('state') == 'closed']
                    filtered_ports = [p for p in ports if p.get('state') == 'filtered']
                    open_filtered_ports = [p for p in ports if p.get('state') == 'open|filtered']
                    services = list(set([p.get('service', 'unknown') for p in open_ports]))
                    
                    # Format port numbers for display
                    def format_port_numbers(port_list):
                        if not port_list:
                            return 'None'
                        port_nums = []
                        for p in port_list:
                            port_num = p.get('port', '')
                            if '/' in str(port_num):
                                port_num = str(port_num).split('/')[0]
                            port_nums.append(str(port_num))
                        return ', '.join(sorted(port_nums, key=lambda x: int(x) if x.isdigit() else 0))
                    
                    table_data.append({
                        'Device Name': device.get('hostname', 'Unknown'),
                        'IP Address': device['ip_address'],
                        '🟢 Open': len(open_ports),
                        '🔴 Closed': len(closed_ports),
                        '🟠 Filtered': len(filtered_ports),
                        '🟠 Open|Filtered': len(open_filtered_ports),
                        'Open Port Numbers': format_port_numbers(open_ports),
                        'Total Scanned': len(ports),
                        'Services': ', '.join(services[:3]) + ('...' if len(services) > 3 else ''),
                        'Vendor': device.get('vendor', 'Unknown'),
                        'Last Scan': device.get('port_scan_time', 'Never')[:19] if device.get('port_scan_time') else 'Never'
                    })
        
        if table_data:
            df_table = pd.DataFrame(table_data)
            # Sort by total scanned ports (descending) to match chart order
            df_table = df_table.sort_values('Total Scanned', ascending=False)
            st.dataframe(df_table, use_container_width=True)
            
            # Add port status summary statistics
            st.markdown("#### 📊 Port Status Summary")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_open = sum(len([p for p in d.get('ports', []) if p.get('state') == 'open']) for d in comprehensive_data)
                st.metric("Total Open Ports", total_open)
            
            with col2:
                total_filtered = sum(len([p for p in d.get('ports', []) if p.get('state') == 'filtered']) for d in comprehensive_data)
                st.metric("Total Filtered Ports", total_filtered)
            
            with col3:
                total_open_filtered = sum(len([p for p in d.get('ports', []) if p.get('state') == 'open|filtered']) for d in comprehensive_data)
                st.metric("Total Open|Filtered", total_open_filtered)
            
            with col4:
                total_ports = sum(len(d.get('ports', [])) for d in comprehensive_data)
                st.metric("Total Ports Scanned", total_ports)
    else:
        st.info("📊 No port scan data available for online devices. Please run port scans on online devices first to see the IP vs Ports analysis.")

with tab3:
    st.markdown("### 🔧 Service Distribution Analysis")
    
    # Create service analysis charts
    service_pie, service_bar = create_service_analysis_charts(comprehensive_data)
    
    if service_pie and service_bar:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(service_pie, use_container_width=True)
        with col2:
            st.plotly_chart(service_bar, use_container_width=True)
        
        # Add service details table
        st.markdown("#### 📋 Service Details")
        
        # Collect service statistics
        service_stats = {}
        for device in comprehensive_data:
            for port in device.get('ports', []):
                service = port.get('service', 'unknown')
                state = port.get('state', 'unknown')
                
                if service not in service_stats:
                    service_stats[service] = {
                        'total': 0,
                        'open': 0,
                        'open_filtered': 0,
                        'devices': set()
                    }
                
                service_stats[service]['total'] += 1
                if state == 'open':
                    service_stats[service]['open'] += 1
                    service_stats[service]['devices'].add(device.get('hostname', 'Unknown'))
                elif state == 'open|filtered':
                    service_stats[service]['open_filtered'] += 1
                    service_stats[service]['devices'].add(device.get('hostname', 'Unknown'))
        
        # Create service table
        service_table = []
        for service, stats in sorted(service_stats.items(), key=lambda x: x[1]['total'], reverse=True)[:20]:
            service_table.append({
                'Service': service,
                'Total Ports': stats['total'],
                'Open Ports': stats['open'],
                'Open|Filtered': stats['open_filtered'],
                'Device Count': len(stats['devices']),
                'Sample Devices': ', '.join(list(stats['devices'])[:3]) + ('...' if len(stats['devices']) > 3 else '')
            })
        
        if service_table:
            df_services = pd.DataFrame(service_table)
            st.dataframe(df_services, use_container_width=True)
    else:
        st.info("No service data available for visualization")

with tab4:
    st.markdown("### 🖥️ Operating System Analysis")
    
    # Create OS analysis charts
    os_pie, os_bar, os_vendors, os_heatmap = create_os_analysis_charts(comprehensive_data)
    
    if os_pie:
        # First row: OS Detection Success Rate and Top OS Patterns
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(os_pie, use_container_width=True)
        with col2:
            if os_bar:
                st.plotly_chart(os_bar, use_container_width=True)
        
        # Second row: Top 15 Vendors and Vendor-OS Heatmap (side by side)
        if os_vendors and os_heatmap:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### 🏭 Top 15 Vendors by Device Count")
                st.plotly_chart(os_vendors, use_container_width=True)
                st.markdown("*Shows the distribution of devices across identified vendors (Unknown vendors excluded)*")
            with col2:
                st.markdown("#### 🔥 Vendor vs Operating System Heatmap")
                st.plotly_chart(os_heatmap, use_container_width=True)
                st.markdown("*Correlation between device vendors and detected operating systems*")
        elif os_vendors:
            # Only vendors chart available
            st.markdown("#### 🏭 Top 15 Vendors by Device Count")
            st.plotly_chart(os_vendors, use_container_width=True)
            st.markdown("*Shows the distribution of devices across identified vendors (Unknown vendors excluded)*")
        elif os_heatmap:
            # Only heatmap available
            st.markdown("#### 🔥 Vendor vs Operating System Heatmap")
            st.plotly_chart(os_heatmap, use_container_width=True)
            st.markdown("*Correlation between device vendors and detected operating systems*")
        
        # Add OS details table
        st.markdown("#### 📋 OS Detection Details")
        
        # Create OS table
        os_table = []
        for device in comprehensive_data:
            os_info = "Not Detected"
            if device.get('os_details', {}).get('details'):
                os_info = device['os_details']['details']
            elif device.get('os_guesses'):
                os_info = device['os_guesses'][0] if device['os_guesses'] else "Not Detected"
            
            if os_info != "Not Detected":
                os_table.append({
                    'Device Name': device.get('hostname', 'Unknown'),
                    'IP Address': device.get('ip_address', 'Unknown'),
                    'OS Information': os_info[:60] + '...' if len(os_info) > 60 else os_info,
                    'Vendor': device.get('vendor', 'Unknown'),
                    'Detection Time': device.get('os_scan_time', 'Never')[:19] if device.get('os_scan_time') else 'Never'
                })
        
        if os_table:
            df_os = pd.DataFrame(os_table)
            st.dataframe(df_os, use_container_width=True)
    else:
        st.info("No OS detection data available for visualization. Run OS scans on devices to see vendor distribution and OS patterns.")

with tab5:
    st.markdown("### 📈 Port Distribution Analysis")
    st.markdown("""
    📊 **Port Analysis Focus Areas**:
    - **Protocol Distribution**: TCP vs UDP port usage analysis
    - **Port Range Categories**: Distribution across Well-known, Registered, and Dynamic ranges
    - **Protocol × Range Matrix**: Interactive heatmap showing the intersection of protocols and ranges
    
    🔍 **Port Range Categories**:
    - **🔧 Well-known (0-1023)**: System services like HTTP(80), HTTPS(443), SSH(22)
    - **📋 Registered (1024-49151)**: User applications, databases, custom services  
    - **⚡ Dynamic (49152-65535)**: Private/ephemeral ports for temporary connections
    """)
    
    # Create port distribution analysis
    port_analysis_result = create_port_distribution_analysis(comprehensive_data)
    
    if port_analysis_result and port_analysis_result[0] is not None:
        protocol_pie_chart, range_bar_chart, protocol_range_heatmap = port_analysis_result
        
        # Display charts in a responsive layout
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🔌 Protocol Distribution")
            st.plotly_chart(protocol_pie_chart, use_container_width=True)
            st.markdown("*Shows the proportion of TCP vs UDP ports across all scanned devices*")
        
        with col2:
            st.markdown("#### 📊 Port Range Distribution") 
            st.plotly_chart(range_bar_chart, use_container_width=True)
            st.markdown("*Distribution of ports across Well-known, Registered, and Dynamic ranges*")
        
        # Display Protocol × Range Heatmap in full width
        st.markdown("#### 🔥 Protocol × Range Analysis")
        st.plotly_chart(protocol_range_heatmap, use_container_width=True)
        st.markdown("*Interactive heatmap showing how TCP and UDP ports are distributed across different port ranges*")
        
        # Add detailed statistics
        st.markdown("#### 📊 Detailed Distribution Statistics")
        
        # Calculate protocol and range statistics directly from analysis data
        df_analysis = pd.DataFrame([
            {
                'Port_Number': port.get('port', '').split('/')[0] if '/' in str(port.get('port', '')) else 0,
                'Protocol': port.get('port', '').split('/')[1].upper() if '/' in str(port.get('port', '')) else 'Unknown',
                'Range_Category': (
                    'Well-known' if 0 <= int(port.get('port', '').split('/')[0]) <= 1023 else
                    'Registered' if 1024 <= int(port.get('port', '').split('/')[0]) <= 49151 else
                    'Dynamic'
                ) if '/' in str(port.get('port', '')) and port.get('port', '').split('/')[0].isdigit() else 'Unknown'
            }
            for device in comprehensive_data 
            for port in device.get('ports', [])
            if '/' in str(port.get('port', ''))
        ])
        
        if not df_analysis.empty:
            # Display statistics in columns
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("##### 🔌 Protocol Analysis")
                protocol_counts = df_analysis['Protocol'].value_counts()
                total_ports = len(df_analysis)
                
                if 'TCP' in protocol_counts:
                    tcp_count = protocol_counts['TCP']
                    tcp_pct = (tcp_count / total_ports * 100)
                    st.metric("TCP Ports", tcp_count, f"{tcp_pct:.1f}% of total")
                
                if 'UDP' in protocol_counts:
                    udp_count = protocol_counts['UDP']
                    udp_pct = (udp_count / total_ports * 100)
                    st.metric("UDP Ports", udp_count, f"{udp_pct:.1f}% of total")
                
                # Unique port numbers
                unique_tcp = len(df_analysis[df_analysis['Protocol'] == 'TCP']['Port_Number'].unique()) if 'TCP' in protocol_counts else 0
                unique_udp = len(df_analysis[df_analysis['Protocol'] == 'UDP']['Port_Number'].unique()) if 'UDP' in protocol_counts else 0
                st.metric("Unique TCP Port Numbers", unique_tcp)
                st.metric("Unique UDP Port Numbers", unique_udp)
            
            with col2:
                st.markdown("##### 📊 Range Analysis")
                range_counts = df_analysis['Range_Category'].value_counts()
                
                for range_name in ['Well-known', 'Registered', 'Dynamic']:
                    if range_name in range_counts:
                        count = range_counts[range_name]
                        pct = (count / total_ports * 100)
                        
                        # Get TCP/UDP breakdown for this range
                        range_data = df_analysis[df_analysis['Range_Category'] == range_name]
                        tcp_in_range = len(range_data[range_data['Protocol'] == 'TCP'])
                        udp_in_range = len(range_data[range_data['Protocol'] == 'UDP'])
                        
                        st.metric(f"{range_name} Ports", count, f"{pct:.1f}% of total")
                        st.caption(f"🔌 TCP: {tcp_in_range} | 📡 UDP: {udp_in_range}")
            
            with col3:
                st.markdown("##### 🔍 Summary Insights")
                
                # Calculate insights
                most_used_protocol = protocol_counts.index[0] if not protocol_counts.empty else "N/A"
                most_used_range = range_counts.index[0] if not range_counts.empty else "N/A"
                
                st.metric("Most Used Protocol", most_used_protocol)
                st.metric("Most Used Range", most_used_range)
                st.metric("Total Unique Ports", len(df_analysis['Port_Number'].unique()))
                st.metric("Total Devices Scanned", len([d for d in comprehensive_data if d.get('ports')]))
                
                # Protocol diversity index (simple calculation)
                if len(protocol_counts) > 1:
                    diversity = min(protocol_counts.values) / max(protocol_counts.values)
                    st.metric("Protocol Diversity", f"{diversity:.2f}", "Balance between TCP/UDP")
        else:
            st.info("No port data available for detailed statistics.")
        
        # Add port range explanation
        st.markdown("#### 📚 Port Range Reference")
        
        port_info_col1, port_info_col2, port_info_col3 = st.columns(3)
        
        with port_info_col1:
            st.markdown("""
            **🔧 Well-known Ports (0-1023)**
            - System and standard services
            - Requires admin privileges
            - Examples: HTTP(80), HTTPS(443), SSH(22), FTP(21), DNS(53)
            """)
        
        with port_info_col2:
            st.markdown("""
            **📋 Registered Ports (1024-49151)**
            - User and application services
            - Registered with IANA
            - Examples: MySQL(3306), PostgreSQL(5432), MongoDB(27017)
            """)
        
        with port_info_col3:
            st.markdown("""
            **⚡ Dynamic Ports (49152-65535)**
            - Private/ephemeral ports
            - Temporary client connections
            - Examples: Browser sessions, temporary connections
            """)
    else:
        st.info("📊 No port distribution data available. Please run port scans on devices first to see protocol and range analysis.")

# Data Export Section
st.markdown("---")
st.markdown("## 💾 Data Export")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📊 Export Device Summary", use_container_width=True):
        # Create comprehensive summary
        summary_data = []
        for device in comprehensive_data:
            summary_data.append({
                'Device Name': device.get('hostname', 'Unknown'),
                'IP Address': device.get('ip_address', 'Unknown'),
                'MAC Address': device.get('mac_address', 'Unknown'),
                'Status': device.get('status', 'unknown'),
                'Vendor': device.get('vendor', 'Unknown'),
                'Open Ports': device.get('open_ports', 0),
                'Total Ports': device.get('total_ports_scanned', 0),
                'OS Detection': 'Yes' if device.get('os_guesses') else 'No',
                'Last Port Scan': device.get('port_scan_time', 'Never'),
                'Last OS Scan': device.get('os_scan_time', 'Never')
            })
        
        df_export = pd.DataFrame(summary_data)
        csv = df_export.to_csv(index=False)
        
        st.download_button(
            label="⬇️ Download CSV",
            data=csv,
            file_name=f"scan_visualization_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

with col2:
    if st.button("📋 Export Raw Data", use_container_width=True):
        json_data = json.dumps(comprehensive_data, indent=2, default=str)
        st.download_button(
            label="⬇️ Download JSON",
            data=json_data,
            file_name=f"scan_raw_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )

with col3:
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Footer
st.markdown("---")
st.markdown("*This visualization page provides comprehensive analysis of all scan results with interactive charts and detailed statistics.*")
