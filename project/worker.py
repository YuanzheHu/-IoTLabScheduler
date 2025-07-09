import os
import time
import logging
from datetime import datetime
from celery import Celery
from db.base import SessionLocal
from db.models import Experiment
from core.attack_engine import AttackEngine
import asyncio
from core.traffic_capture import TcpdumpUtil
from db.models import Capture

"""
Celery worker module for IoT Lab Experiment Scheduler.

This module defines Celery tasks for:
- General background task simulation (create_task)
- Running attack experiments asynchronously (run_attack_experiment)

Celery is configured to use Redis as broker and result backend, with UK timezone.
"""

# Configure logging with UK timezone
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [UK] %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

celery = Celery(__name__)
celery.conf.update(
    broker_url=os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379"),
    result_backend=os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379"),
    timezone='Europe/London',
    enable_utc=False
)

@celery.task(name="create_task")
def create_task(task_type):
    """
    Simulate a background task of variable duration.

    Args:
        task_type (int or str): Determines the duration of the task (in 10s increments).

    Returns:
        bool: True if the task completes successfully.
    """
    logger = logging.getLogger(__name__)
    uk_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logger.info(f"[{uk_time}] Starting task with type: {task_type}")
    time.sleep(int(task_type) * 10)
    uk_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logger.info(f"[{uk_time}] Completed task with type: {task_type}")
    return True

@celery.task(name="run_attack_experiment")
def run_attack_experiment(experiment_id, attack_type, target_ip, duration, interface):
    """
    Celery task to execute a network attack experiment asynchronously.

    Steps:
    1. Update experiment status to 'running' in the database.
    2. Invoke the core AttackEngine to perform the attack.
    3. Update experiment status and result upon completion or failure.

    Args:
        experiment_id (int): ID of the experiment in the database.
        attack_type (str): Type of attack to perform (e.g., 'SYN', 'UDP', 'ICMP').
        target_ip (str): Target IP address for the attack.
        duration (int): Duration of the attack in seconds.
        interface (str): Network interface to use.

    Returns:
        bool: True if experiment completed successfully, False otherwise.
    """
    logger = logging.getLogger(__name__)
    db = SessionLocal()
    try:
        # Step 1: Fetch the experiment record from the database by ID
        exp = db.query(Experiment).get(experiment_id)
        if not exp:
            # If experiment not found, log error and return False
            logger.error(f"Experiment {experiment_id} not found.")
            return False

        # Step 2: Update experiment status to 'running'
        exp.status = "running"
        db.commit()

        # Step 2.5: 启动抓包
        pcap_dir = "data/pcaps"
        os.makedirs(pcap_dir, exist_ok=True)
        pcap_path = os.path.join(pcap_dir, f"exp_{experiment_id}_{int(time.time())}.pcap")
        tcpdump = TcpdumpUtil(output_file=pcap_path, interface=interface)
        tcpdump.start()

        # Step 3: Initialize the attack engine
        engine = AttackEngine()

        # Step 4: Create a new asyncio event loop for the attack (Celery worker context)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Step 5: Run the attack asynchronously and wait for result
        result = loop.run_until_complete(
            engine.start_attack(attack_type, target_ip, interface, duration)
        )
        loop.close()

        # Step 5.5: 停止抓包
        tcpdump.stop()

        # Step 5.6: 保存 PCAP 文件信息到 captures 表
        file_size = os.path.getsize(pcap_path) if os.path.exists(pcap_path) else 0
        capture = Capture(
            file_name=os.path.basename(pcap_path),
            file_path=pcap_path,
            experiment_id=experiment_id,
            file_size=file_size,
            description=f"PCAP for experiment {experiment_id}"
        )
        db.add(capture)
        db.commit()
        db.refresh(capture)
        exp.capture_id = capture.id

        # Step 6: Update experiment status and result based on attack outcome
        exp.status = "finished" if result else "failed"
        exp.end_time = datetime.utcnow()
        exp.result = str(result)
        db.commit()

        # Step 7: Log completion
        logger.info(f"Experiment {experiment_id} completed with status: {exp.status}")
        return True
    except Exception as e:
        # Step 8: On error, log and update experiment status to 'failed'
        logger.error(f"Experiment {experiment_id} failed: {e}")
        if exp:
            exp.status = "failed"
            exp.end_time = datetime.utcnow()
            exp.result = str(e)
            db.commit()
        return False
    finally:
        # Step 9: Always close the DB session
        db.close() 