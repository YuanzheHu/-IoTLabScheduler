from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from db.base import SessionLocal
from db.models import Experiment, Capture
from .schemas import ExperimentCreate, ExperimentRead, ExperimentCreateV2, ExperimentReadV2, ExperimentStatusV2
from worker import run_attack_experiment, stop_attack_experiment, run_traffic_capture, run_cyclic_attack_experiment, celery
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
    
    # Dynamically detect available network interface
    default_interface = NetworkUtils.get_default_interface()
    if not default_interface:
        logger.warning("No available network interface found, using 'any' as fallback")
        default_interface = "any"
    
    logger.info(f"Using network interface: {default_interface}")
    
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
        interface=default_interface  # Use dynamically detected interface
    )

    # Manually construct return dict to ensure Pydantic serialization
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

@router.post("/v2", response_model=ExperimentReadV2)
def create_experiment_v2(exp: ExperimentCreateV2, db: Session = Depends(get_db)):
    """
    Create a new V2 experiment with Attack Engine V2 features.
    
    Supports:
    - Single and cyclic attack modes
    - Network interface selection
    - Configurable cycles and settle time
    - Enhanced attack configuration
    
    Args:
        exp (ExperimentCreateV2): V2 experiment data with enhanced configuration
        db (Session): Database session
        
    Returns:
        ExperimentReadV2: The created V2 experiment object
    """
    logger.info(f"Create V2 experiment: {exp.name}, attack mode: {exp.attack_mode}, cycles: {exp.cycles}")
    
    # 1. Write experiment record with V2 fields
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
        duration_sec=exp.duration_sec,
        interface=exp.interface,
        attack_mode=exp.attack_mode,
        cycles=exp.cycles,
        settle_time_sec=exp.settle_time_sec,
        current_cycle=0,
        total_cycles=exp.cycles
    )
    db.add(db_exp)
    db.commit()
    db.refresh(db_exp)

    # 2. Prepare attack configuration for V2 engine
    attack_config = {
        'attack_type': exp.attack_type,
        'target_ip': exp.target_ip,
        'port': exp.port or 55443,
        'duration_sec': exp.duration_sec or 60,
        'interface': exp.interface,
        'attack_mode': exp.attack_mode,
        'cycles': exp.cycles,
        'settle_time_sec': exp.settle_time_sec
    }

    # 3. Choose appropriate worker task based on attack mode
    if exp.attack_mode == "cyclic" and exp.cycles > 1:
        # Use V2 cyclic attack engine
        run_cyclic_attack_experiment.delay(
            experiment_id=db_exp.id,
            attack_config_dict=attack_config
        )
        logger.info(f"Start cyclic attack experiment {db_exp.id} using V2 engine")
    else:
        # Use V1 attack engine for single mode
        run_attack_experiment.delay(
            experiment_id=db_exp.id,
            attack_type=exp.attack_type,
            target_ip=exp.target_ip,
            port=exp.port or 55443,
            duration=exp.duration_sec or 60,
            interface=exp.interface
        )
        logger.info(f"Start single attack experiment {db_exp.id} using V1 engine")

    # 4. Return V2 experiment object
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
        "capture_id": db_exp.capture_id,
        "interface": db_exp.interface,
        "attack_mode": db_exp.attack_mode,
        "cycles": db_exp.cycles,
        "settle_time_sec": db_exp.settle_time_sec,
        "current_cycle": db_exp.current_cycle,
        "total_cycles": db_exp.total_cycles,
        "attack_results": db_exp.attack_results
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
    
    # Manually construct return dict to ensure Pydantic serialization
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

@router.get("/{experiment_id}/status/v2", response_model=ExperimentStatusV2)
def get_experiment_status_v2(experiment_id: int, db: Session = Depends(get_db)):
    """
    Get enhanced V2 status of an experiment with progress information.
    
    Args:
        experiment_id (int): The ID of the experiment
        db (Session): Database session
        
    Returns:
        ExperimentStatusV2: Enhanced status information with progress tracking
    """
    exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    # Calculate progress percentage for cyclic attacks
    progress_percentage = None
    estimated_remaining_time = None
    
    if exp.attack_mode == "cyclic" and exp.total_cycles and exp.total_cycles > 1:
        if exp.current_cycle is not None:
            progress_percentage = (exp.current_cycle / exp.total_cycles) * 100
        
        # Estimate remaining time based on current progress
        if exp.status == "running" and exp.start_time and exp.duration_sec:
            elapsed_time = (datetime.now() - exp.start_time).total_seconds()
            if progress_percentage and progress_percentage > 0:
                total_estimated_time = (elapsed_time / progress_percentage) * 100
                estimated_remaining_time = max(0, int(total_estimated_time - elapsed_time))
    
    return {
        "id": exp.id,
        "name": exp.name,
        "status": exp.status,
        "start_time": exp.start_time,
        "end_time": exp.end_time,
        "result": exp.result,
        "attack_mode": exp.attack_mode,
        "current_cycle": exp.current_cycle,
        "total_cycles": exp.total_cycles,
        "progress_percentage": progress_percentage,
        "estimated_remaining_time": estimated_remaining_time
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
    
    # Manually construct return dict to ensure Pydantic serialization
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

    # Manually construct return dict to ensure Pydantic serialization
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
