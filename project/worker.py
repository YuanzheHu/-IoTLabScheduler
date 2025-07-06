import os
import time
import logging
from datetime import datetime
from celery import Celery

# Configure logging with UK timezone
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [UK] %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

celery = Celery(__name__)
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379")
celery.conf.result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379")

# Set timezone for Celery
celery.conf.timezone = 'Europe/London'
celery.conf.enable_utc = False


@celery.task(name="create_task")
def create_task(task_type):
    logger = logging.getLogger(__name__)
    uk_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logger.info(f"[{uk_time}] Starting task with type: {task_type}")
    
    time.sleep(int(task_type) * 10)
    
    uk_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logger.info(f"[{uk_time}] Completed task with type: {task_type}")
    return True 