from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from db.base import SessionLocal
from db.models import Experiment, Capture
from .schemas import ExperimentCreate, ExperimentRead
from worker import run_attack_experiment, stop_attack_experiment, run_traffic_capture, celery
from core.traffic_capture import TcpdumpUtil
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/experiments", tags=["experiments"])

def get_db():
    """
    Dependency that provides a SQLAlchemy database session.
    Closes the session after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=ExperimentRead)
def create_experiment(exp: ExperimentCreate, db: Session = Depends(get_db)):
    """
    Create a new experiment entry and trigger the attack experiment asynchronously.

    Args:
        exp (ExperimentCreate): Experiment data to create.
        db (Session): Database session.

    Returns:
        ExperimentRead: The created experiment object.
    """
    from core.network_utils import NetworkUtils
    
    # 动态检测可用的网络接口
    default_interface = NetworkUtils.get_default_interface()
    if not default_interface:
        logger.warning("未找到可用的网络接口，使用 'any' 作为备选")
        default_interface = "any"
    
    logger.info(f"使用网络接口: {default_interface}")
    
    # 1. Write experiment record with status 'pending'
    db_exp = Experiment(
        name=exp.name,
        attack_type=exp.attack_type,
        target_ip=exp.target_ip,
        port=exp.port or 55443,
        status="pending",
        start_time=datetime.now(),
        end_time=None,
        result=None,
        capture_id=None,
        duration_sec=exp.duration_sec
    )
    db.add(db_exp)
    db.commit()
    db.refresh(db_exp)

    # 2. Asynchronously call Celery task, passing experiment ID and parameters
    run_attack_experiment.delay(
        experiment_id=db_exp.id,
        attack_type=exp.attack_type,
        target_ip=exp.target_ip,
        port=exp.port or 55443,
        duration=exp.duration_sec or 60,
        interface=default_interface  # 使用动态检测的接口
    )

    # 手动构建返回字典，确保Pydantic可以正确序列化
    return {
        "id": db_exp.id,
        "name": db_exp.name,
        "attack_type": db_exp.attack_type,
        "target_ip": db_exp.target_ip,
        "port": db_exp.port,
        "duration_sec": db_exp.duration_sec,
        "status": db_exp.status,
        "start_time": db_exp.start_time,
        "end_time": db_exp.end_time,
        "result": db_exp.result,
        "capture_id": db_exp.capture_id
    }

@router.get("/", response_model=List[ExperimentRead])
def list_experiments(db: Session = Depends(get_db)):
    """
    Retrieve a list of all experiments.

    Args:
        db (Session): Database session.

    Returns:
        List[ExperimentRead]: List of all experiment objects.
    """
    experiments = db.query(Experiment).all()
    result = []
    for exp in experiments:
        result.append({
            "id": exp.id,
            "name": exp.name,
            "attack_type": exp.attack_type,
            "target_ip": exp.target_ip,
            "port": exp.port,
            "duration_sec": exp.duration_sec,
            "status": exp.status,
            "start_time": exp.start_time,
            "end_time": exp.end_time,
            "result": exp.result,
            "capture_id": exp.capture_id
        })
    return result

@router.get("/{experiment_id}", response_model=ExperimentRead)
def get_experiment(experiment_id: int, db: Session = Depends(get_db)):
    """
    Retrieve an experiment by its ID.

    Args:
        experiment_id (int): The ID of the experiment to retrieve.
        db (Session): Database session.

    Returns:
        ExperimentRead: The experiment object if found.

    Raises:
        HTTPException: If the experiment is not found.
    """
    exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    # 手动构建返回字典，确保Pydantic可以正确序列化
    return {
        "id": exp.id,
        "name": exp.name,
        "attack_type": exp.attack_type,
        "target_ip": exp.target_ip,
        "port": exp.port,
        "duration_sec": exp.duration_sec,
        "status": exp.status,
        "start_time": exp.start_time,
        "end_time": exp.end_time,
        "result": exp.result,
        "capture_id": exp.capture_id
    }

@router.post("/{experiment_id}/stop", response_model=ExperimentRead)
def stop_experiment(experiment_id: int, db: Session = Depends(get_db)):
    """
    Stop a running experiment.

    Args:
        experiment_id (int): The ID of the experiment to stop.
        db (Session): Database session.

    Returns:
        ExperimentRead: The updated experiment object.

    Raises:
        HTTPException: If the experiment is not found or not running.
    """
    exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    if exp.status != "running":
        raise HTTPException(status_code=400, detail="Experiment is not running")
    
    # Update experiment status to stopped
    exp.status = "stopped"
    exp.end_time = datetime.utcnow()
    exp.result = "Experiment stopped by user"
    db.commit()
    db.refresh(exp)
    
    # Trigger Celery task to stop the attack
    stop_attack_experiment.delay(experiment_id)
    
    # 手动构建返回字典，确保Pydantic可以正确序列化
    return {
        "id": exp.id,
        "name": exp.name,
        "attack_type": exp.attack_type,
        "target_ip": exp.target_ip,
        "port": exp.port,
        "duration_sec": exp.duration_sec,
        "status": exp.status,
        "start_time": exp.start_time,
        "end_time": exp.end_time,
        "result": exp.result,
        "capture_id": exp.capture_id
    }

@router.get("/{experiment_id}/status")
def get_experiment_status(experiment_id: int, db: Session = Depends(get_db)):
    """
    Get the current status of an experiment.

    Args:
        experiment_id (int): The ID of the experiment.
        db (Session): Database session.

    Returns:
        dict: Status information about the experiment.
    """
    exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    return {
        "id": exp.id,
        "name": exp.name,
        "status": exp.status,
        "start_time": exp.start_time,
        "end_time": exp.end_time,
        "result": exp.result
    }

@router.post("/traffic_capture", response_model=ExperimentRead)
def traffic_capture(
    target_ip: str,
    duration_sec: int = 60,
    interface: str = "eth0",
    db: Session = Depends(get_db)
):
    """
    Submit a traffic capture experiment as an async Celery task
    """
    exp = Experiment(
        name=f"Traffic Capture {target_ip}",
        attack_type="traffic_capture",
        target_ip=target_ip,
        port=None,
        status="pending",
        start_time=datetime.utcnow(),
        duration_sec=duration_sec
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)

    # Call the dedicated traffic capture worker task
    run_traffic_capture.delay(
        experiment_id=exp.id,
        target_ip=target_ip,
        duration=duration_sec,
        interface=interface
    )

    # 手动构建返回字典，确保Pydantic可以正确序列化
    return {
        "id": exp.id,
        "name": exp.name,
        "attack_type": exp.attack_type,
        "target_ip": exp.target_ip,
        "port": exp.port,
        "duration_sec": exp.duration_sec,
        "status": exp.status,
        "start_time": exp.start_time,
        "end_time": exp.end_time,
        "result": exp.result,
        "capture_id": exp.capture_id
    }

