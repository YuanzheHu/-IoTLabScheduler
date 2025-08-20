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

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates (if directories exist)
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except RuntimeError:
    # Skip mounting if static directory doesn't exist
    pass

try:
    templates = Jinja2Templates(directory="templates")
except Exception:
    # Set to None if templates directory doesn't exist
    templates = None

# Register API routers - keep only core functionality
app.include_router(devices_router)
app.include_router(experiments_router)
app.include_router(captures_router)
app.include_router(scan_results_router)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": "2025-08-11T18:30:00Z"}

@app.post("/admin/reset-database")
async def reset_database():
    """
    Database reset endpoint - WARNING: This will delete all data!
    """
    try:
        from db.base import Base, engine
        from db.models import Device, Experiment, Capture, ScanResult, PortInfo
        
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        
        # Recreate all tables
        Base.metadata.create_all(bind=engine)
        
        return {
            "status": "success", 
            "message": "Database reset completed successfully!",
            "tables_recreated": list(Base.metadata.tables.keys())
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Database reset failed: {str(e)}"
        }

@app.post("/admin/backup-database")
async def backup_database():
    """
    Create a backup of the current database
    """
    import shutil
    from datetime import datetime
    
    try:
        db_path = "data/iotlab.db"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"data/iotlab_backup_{timestamp}.db"
        
        # Copy the database file
        shutil.copy2(db_path, backup_path)
        
        return {
            "status": "success",
            "message": f"Database backup created successfully!",
            "backup_file": backup_path
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Database backup failed: {str(e)}"
        }

@app.get("/admin/list-backups")
async def list_backups():
    """
    List all available database backup files
    """
    import os
    import glob
    from datetime import datetime
    
    try:
        backup_pattern = "data/iotlab_backup_*.db"
        backup_files = glob.glob(backup_pattern)
        
        backups = []
        for backup_file in sorted(backup_files, reverse=True):  # Latest first
            file_stats = os.stat(backup_file)
            backups.append({
                "filename": os.path.basename(backup_file),
                "filepath": backup_file,
                "size": file_stats.st_size,
                "created": datetime.fromtimestamp(file_stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })
        
        return {
            "status": "success",
            "backups": backups,
            "count": len(backups)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to list backups: {str(e)}"
        }

@app.post("/admin/restore-database")
async def restore_database(backup_filename: str = Body(..., embed=True)):
    """
    Restore database from a backup file
    """
    import shutil
    import os
    
    try:
        # Validate backup file exists
        backup_path = f"data/{backup_filename}"
        if not os.path.exists(backup_path):
            return {
                "status": "error",
                "message": f"Backup file {backup_filename} not found!"
            }
        
        # Create backup of current database before restore
        current_db = "data/iotlab.db"
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pre_restore_backup = f"data/iotlab_pre_restore_{timestamp}.db"
        
        if os.path.exists(current_db):
            shutil.copy2(current_db, pre_restore_backup)
        
        # Restore from backup
        shutil.copy2(backup_path, current_db)
        
        return {
            "status": "success",
            "message": f"Database restored successfully from {backup_filename}!",
            "restored_from": backup_path,
            "pre_restore_backup": pre_restore_backup
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Database restore failed: {str(e)}"
        }

@app.get("/", response_class=HTMLResponse)
async def root():
    """Home page - provides API information and navigation links"""
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
            <p style="text-align: center; color: #7f8c8d;">IoT Device Network Experiment Scheduling System</p>
            
            <div class="service">
                <h3>📚 API Documentation</h3>
                <p>View complete API documentation and interactive testing interface</p>
                <a href="/docs" target="_blank">Access API Documentation →</a>
                <span class="status online">Online</span>
            </div>
            
            <div class="service">
                <h3>📊 Flower Dashboard</h3>
                <p>Monitor Celery task execution status and queue management</p>
                <a href="http://localhost:5555" target="_blank">Access Flower Dashboard →</a>
                <span class="status online">Online</span>
            </div>
            
            <div class="service">
                <h3>🎨 Streamlit UI</h3>
                <p>Graphical device management and experiment scheduling interface</p>
                <a href="http://localhost:8501" target="_blank">Access Streamlit UI →</a>
                <span class="status online">Online</span>
            </div>
            
            <div class="service">
                <h3>🔧 Main Features</h3>
                <ul>
                    <li><strong>Device Discovery</strong>: Subnet scanning and device management</li>
                    <li><strong>Port Scanning</strong>: Device port and operating system fingerprinting</li>
                    <li><strong>Network Attack Experiments</strong>: SYN/UDP/ICMP flood attack testing</li>
                    <li><strong>Traffic Capture</strong>: Automatic PCAP capture and archiving</li>
                    <li><strong>Real-time Monitoring</strong>: Experiment status tracking and log streaming</li>
                    <li><strong>Shell Script Management</strong>: Script upload, execution and real-time monitoring</li>
                </ul>
            </div>
            
            <div class="service">
                <h3>📡 API Endpoints</h3>
                <ul>
                    <li><code>GET /devices/</code> - List all devices</li>
                    <li><code>POST /devices/scan</code> - Scan subnet devices</li>
                    <li><code>POST /experiments/</code> - Schedule new experiment</li>
                    <li><code>GET /experiments/</code> - List all experiments</li>
                    <li><code>GET /captures/</code> - List PCAP records</li>
                    <li><code>POST /shell-scripts/upload</code> - Upload shell script</li>
                    <li><code>POST /shell-scripts/{id}/execute</code> - Execute script</li>
                    <li><code>WS /api/ws/execution/{id}</code> - Real-time execution monitoring</li>
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
