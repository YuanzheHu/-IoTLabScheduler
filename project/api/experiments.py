from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from db.base import SessionLocal
from db.models import Experiment
from .schemas import ExperimentCreate, ExperimentRead
from worker import run_attack_experiment

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
        status="pending",
        start_time=exp.start_time,
        end_time=exp.end_time,
        result=exp.result,
        capture_id=exp.capture_id
    )
    db.add(db_exp)
    db.commit()
    db.refresh(db_exp)

    # 2. Asynchronously call Celery task, passing experiment ID and parameters
    run_attack_experiment.delay(
        experiment_id=db_exp.id,
        attack_type=exp.attack_type,
        target_ip=exp.target_ip,
        duration=60,  # Can be customized from exp
        interface="eth0"  # Can be customized from exp
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

@router.put("/{experiment_id}", response_model=ExperimentRead)
def update_experiment(experiment_id: int, exp: ExperimentCreate, db: Session = Depends(get_db)):
    """
    Update an existing experiment entry.

    Args:
        experiment_id (int): The ID of the experiment to update.
        exp (ExperimentCreate): Updated experiment data.
        db (Session): Database session.

    Returns:
        ExperimentRead: The updated experiment object.

    Raises:
        HTTPException: If the experiment is not found.
    """
    db_exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if not db_exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    for key, value in exp.dict().items():
        setattr(db_exp, key, value)
    db.commit()
    db.refresh(db_exp)
    return db_exp

@router.delete("/{experiment_id}", response_model=dict)
def delete_experiment(experiment_id: int, db: Session = Depends(get_db)):
    """
    Delete an experiment entry by its ID.

    Args:
        experiment_id (int): The ID of the experiment to delete.
        db (Session): Database session.

    Returns:
        dict: Confirmation of deletion.

    Raises:
        HTTPException: If the experiment is not found.
    """
    db_exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if not db_exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    db.delete(db_exp)
    db.commit()
    return {"ok": True} 