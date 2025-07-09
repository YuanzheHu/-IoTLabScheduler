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

@app.get("/")
def home(request: Request):
    """
    Render the home page using Jinja2 templates.
    """
    return templates.TemplateResponse("home.html", context={"request": request})

@app.post("/tasks", status_code=201)
def run_task(payload = Body(...)):
    """
    Create and run a Celery task asynchronously.

    Args:
        payload (dict): JSON body containing the task type.

    Returns:
        JSONResponse: Contains the Celery task ID.
    """
    task_type = payload["type"]
    task = create_task.delay(int(task_type))
    return JSONResponse({"task_id": task.id})

@app.get("/tasks/{task_id}")
def get_status(task_id):
    """
    Get the status and result of a Celery task by its ID.

    Args:
        task_id (str): The Celery task ID.

    Returns:
        JSONResponse: Contains task ID, status, and result.
    """
    task_result = AsyncResult(task_id, app=celery)
    result = {
        "task_id": task_id,
        "task_status": task_result.status,
        "task_result": task_result.result
    }
    return JSONResponse(result)
