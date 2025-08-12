"""
IoT Lab Experiment Scheduler - Main Application Entry Point

This module initializes the FastAPI application, mounts static and template directories,
registers API routers for devices, experiments, and captures, and provides endpoints for
home page rendering and Celery task management.

Key Features:
- Automatic database table creation on startup
- Modular API routing for devices, experiments, and captures
- Celery-based asynchronous task execution and status querying
- Jinja2 template rendering for the home page
- WebSocket support for real-time script execution monitoring
"""

import sys
import logging
from fastapi import Body, FastAPI, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from worker import create_task, celery
from celery.result import AsyncResult
from api.devices import router as devices_router
from api.experiments import router as experiments_router
from api.captures import router as captures_router
from api.scan_results import router as scan_results_router
from db.base import Base, engine

# Automatically create all database tables if the database file does not exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="IoTLab Scheduler", version="1.0.0")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件和模板
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 注册API路由 - 只保留核心功能
app.include_router(devices_router)
app.include_router(experiments_router)
app.include_router(captures_router)
app.include_router(scan_results_router)

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "timestamp": "2025-08-11T18:30:00Z"}

@app.get("/", response_class=HTMLResponse)
async def root():
    """主页 - 提供API信息和导航链接"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>IoT Lab Scheduler</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #2c3e50; text-align: center; }
            .service { background: #ecf0f1; padding: 20px; margin: 15px 0; border-radius: 5px; border-left: 4px solid #3498db; }
            .service h3 { margin-top: 0; color: #2c3e50; }
            .service a { color: #3498db; text-decoration: none; font-weight: bold; }
            .service a:hover { text-decoration: underline; }
            .status { display: inline-block; padding: 4px 8px; border-radius: 3px; font-size: 12px; font-weight: bold; }
            .status.online { background: #27ae60; color: white; }
            .status.offline { background: #e74c3c; color: white; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔬 IoT Lab Experiment Scheduler</h1>
            <p style="text-align: center; color: #7f8c8d;">IoT设备网络实验调度系统</p>
            
            <div class="service">
                <h3>📚 API 文档</h3>
                <p>查看完整的API文档和交互式测试界面</p>
                <a href="/docs" target="_blank">访问 API 文档 →</a>
                <span class="status online">在线</span>
            </div>
            
            <div class="service">
                <h3>📊 Flower Dashboard</h3>
                <p>监控Celery任务执行状态和队列管理</p>
                <a href="http://localhost:5555" target="_blank">访问 Flower Dashboard →</a>
                <span class="status online">在线</span>
            </div>
            
            <div class="service">
                <h3>🎨 Streamlit UI</h3>
                <p>图形化设备管理和实验调度界面</p>
                <a href="http://localhost:8501" target="_blank">访问 Streamlit UI →</a>
                <span class="status online">在线</span>
            </div>
            
            <div class="service">
                <h3>🔧 主要功能</h3>
                <ul>
                    <li><strong>设备发现</strong>: 子网扫描和设备管理</li>
                    <li><strong>端口扫描</strong>: 设备端口和操作系统指纹识别</li>
                    <li><strong>网络攻击实验</strong>: SYN/UDP/ICMP洪水攻击测试</li>
                    <li><strong>流量捕获</strong>: 自动PCAP捕获和归档</li>
                    <li><strong>实时监控</strong>: 实验状态跟踪和日志流</li>
                    <li><strong>Shell脚本管理</strong>: 脚本上传、执行和实时监控</li>
                </ul>
            </div>
            
            <div class="service">
                <h3>📡 API 端点</h3>
                <ul>
                    <li><code>GET /devices/</code> - 列出所有设备</li>
                    <li><code>POST /devices/scan</code> - 扫描子网设备</li>
                    <li><code>POST /experiments/</code> - 调度新实验</li>
                    <li><code>GET /experiments/</code> - 列出所有实验</li>
                    <li><code>GET /captures/</code> - 列出PCAP记录</li>
                    <li><code>POST /shell-scripts/upload</code> - 上传Shell脚本</li>
                    <li><code>POST /shell-scripts/{id}/execute</code> - 执行脚本</li>
                    <li><code>WS /api/ws/execution/{id}</code> - 实时执行监控</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filename='logs/web.log',
    filemode='a'
)
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)
