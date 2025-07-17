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
"""

import sys
import logging
from fastapi import Body, FastAPI, Form, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from worker import create_task, celery
from celery.result import AsyncResult
from api.devices import router as devices_router
from api.experiments import router as experiments_router
from api.captures import router as captures_router
from db.base import Base, engine

# Automatically create all database tables if the database file does not exist
Base.metadata.create_all(bind=engine)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Register API routers for devices, experiments, and captures
app.include_router(devices_router)
app.include_router(experiments_router)
app.include_router(captures_router)

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
