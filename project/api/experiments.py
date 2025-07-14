from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from db.base import SessionLocal
from db.models import Experiment
from .schemas import ExperimentCreate, ExperimentRead
from worker import run_attack_experiment, stop_attack_experiment

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
    # 1. Write experiment record with status 'pending'
    db_exp = Experiment(
        name=exp.name,
        attack_type=exp.attack_type,
        target_ip=exp.target_ip,
        port=exp.port or 55443,
        status="pending",
        start_time=exp.start_time,
        end_time=exp.end_time,
        result=exp.result,
        capture_id=exp.capture_id,
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
        interface="eth0"
    )

    return db_exp

@router.get("/", response_model=List[ExperimentRead])
def list_experiments(db: Session = Depends(get_db)):
    """
    Retrieve a list of all experiments.

    Args:
        db (Session): Database session.

    Returns:
        List[ExperimentRead]: List of all experiment objects.
    """
    return db.query(Experiment).all()

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
    return exp

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
    
    return exp

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

