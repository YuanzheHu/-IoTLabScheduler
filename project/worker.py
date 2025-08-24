import os
import time
import logging
import sys
from datetime import datetime
from celery import Celery
from db.base import SessionLocal
from db.models import Experiment, Device
from core.attack_engine import AttackEngine
from core.attack_engine_v2 import CyclicAttackEngine, AttackConfig, AttackType, AttackMode
import asyncio
from core.traffic_capture import TcpdumpUtil
from db.models import Capture
from typing import Dict, Any
from db.models import ScriptExecution
from config import get_pcap_dir
import tempfile
import subprocess
import os
from datetime import datetime

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
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filename='logs/app.log',
    filemode='a'
)
# Also log to stdout
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

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

@celery.task(name="stop_attack_experiment")
def stop_attack_experiment(experiment_id):
    """
    Celery task to stop a running attack experiment.

    Args:
        experiment_id (int): ID of the experiment to stop.

    Returns:
        bool: True if experiment stopped successfully, False otherwise.
    """
    logger = logging.getLogger(__name__)
    db = SessionLocal()
    try:
        # Fetch the experiment record from the database by ID
        exp = db.query(Experiment).get(experiment_id)
        if not exp:
            logger.error(f"Experiment {experiment_id} not found.")
            return False

        # Initialize the attack engine and stop the attack
        engine = AttackEngine()
        
        # Create a new asyncio event loop for the attack (Celery worker context)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Stop the attack asynchronously
        result = loop.run_until_complete(engine.stop_attack())
        loop.close()

        if result:
            logger.info(f"Experiment {experiment_id} stopped successfully")
        else:
            logger.warning(f"Experiment {experiment_id} was not running or failed to stop")
                
        return result
    except Exception as e:
        logger.error(f"Failed to stop experiment {experiment_id}: {e}")
        return False
    finally:
        db.close()

@celery.task(name="run_attack_experiment")
def run_attack_experiment(experiment_id, attack_type, target_ip, port, duration, interface):
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
        port (int): Target port for the attack.
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

        # Step 2.5: Start packet capture
        # Archive PCAPs by MAC address instead of IP
        # Get MAC address for the target IP
        device = db.query(Device).filter(Device.ip_address == target_ip).first()
        if device and device.mac_address:
            mac_address = device.mac_address
        else:
            # Fallback to IP if MAC not found
            mac_address = target_ip
        
        # Create directory structure using config
        pcap_dir = get_pcap_dir(target_ip, mac_address)
        
        # Format timestamp as DD-MM-YY-HH-MM-SS
        timestamp = datetime.utcnow().strftime("%d-%m-%y-%H-%M-%S")
        pcap_filename = f"{mac_address}_{timestamp}_UTC.pcap"
        pcap_path = os.path.join(pcap_dir, pcap_filename)
        tcpdump = TcpdumpUtil(output_file=pcap_path, interface=interface, target_ip=target_ip)
        tcpdump.start()

        # Step 3: Initialize the attack engine
        engine = AttackEngine()

        # Step 4: Create a new asyncio event loop for the attack (Celery worker context)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Step 5: Run the attack asynchronously and wait for result
        result = loop.run_until_complete(
            engine.start_attack(attack_type, target_ip, interface, duration, port)
        )
        loop.close()

        # Step 5.5: Stop packet capture
        tcpdump.stop()

        # Step 5.6: Save PCAP file information to the captures table
        file_size = os.path.getsize(pcap_path) if os.path.exists(pcap_path) else 0
        capture = Capture(
            file_name=pcap_filename,
            file_path=pcap_path,
            experiment_id=experiment_id,
            file_size=file_size,
            description=f"PCAP for experiment {experiment_id} (target_ip={target_ip})"
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

@celery.task(name="run_traffic_capture")
def run_traffic_capture(experiment_id, target_ip, duration, interface="eth0"):
    """
    Celery task to perform only traffic capture (no attack), save PCAP and update Experiment/Capture.
    """
    logger = logging.getLogger(__name__)
    db = SessionLocal()
    try:
        exp = db.query(Experiment).get(experiment_id)
        if not exp:
            logger.error(f"Experiment {experiment_id} not found.")
            return False
        exp.status = "running"
        db.commit()
        db.refresh(exp)

        # Start packet capture
        # Archive PCAPs by MAC address instead of IP
        # Get MAC address for the target IP
        device = db.query(Device).filter(Device.ip_address == target_ip).first()
        if device and device.mac_address:
            mac_address = device.mac_address
        else:
            # Fallback to IP if MAC not found
            mac_address = target_ip
        
        # Create directory structure using config
        pcap_dir = get_pcap_dir(target_ip, mac_address)
        
        # Format timestamp as DD-MM-YY-HH-MM-SS
        timestamp = datetime.utcnow().strftime("%d-%m-%y-%H-%M-%S")
        pcap_filename = f"{mac_address}_{timestamp}_UTC.pcap"
        pcap_path = os.path.join(pcap_dir, pcap_filename)
        tcpdump = TcpdumpUtil(output_file=pcap_path, interface=interface, target_ip=target_ip)
        tcpdump.start()
        time.sleep(duration)
        tcpdump.stop()

        # Save PCAP info
        file_size = os.path.getsize(pcap_path) if os.path.exists(pcap_path) else 0
        capture = Capture(
            file_name=pcap_filename,
            file_path=pcap_path,
            experiment_id=experiment_id,
            file_size=file_size,
            description=f"Traffic capture for experiment {experiment_id} (target_ip={target_ip})"
        )
        db.add(capture)
        db.commit()
        db.refresh(capture)
        exp.capture_id = capture.id
        exp.status = "finished"
        exp.end_time = datetime.utcnow()
        exp.result = "traffic_capture_done"
        db.commit()
        logger.info(f"Traffic capture experiment {experiment_id} completed.")
        return True
    except Exception as e:
        logger.error(f"Traffic capture experiment {experiment_id} failed: {e}")
        if exp:
            exp.status = "failed"
            exp.end_time = datetime.utcnow()
            exp.result = str(e)
            db.commit()
        return False
    finally:
        db.close() 

@celery.task(name="run_cyclic_attack_experiment")
def run_cyclic_attack_experiment(experiment_id, attack_config_dict):
    """执行循环攻击实验的Celery任务"""
    import json
    import os
    from datetime import datetime
    from core.traffic_capture import TcpdumpUtil
    
    logger = logging.getLogger(__name__)
    db = SessionLocal()
    
    try:
        # 1. 获取实验记录
        exp = db.query(Experiment).get(experiment_id)
        if not exp:
            logger.error(f"Experiment {experiment_id} not found.")
            return False

        # 2. 更新状态为运行中
        exp.status = "running"
        exp.current_cycle = 0
        exp.total_cycles = attack_config_dict.get('cycles', 1)
        db.commit()

        # 3. 创建AttackConfig对象
        config = AttackConfig(
            attack_type=AttackType(attack_config_dict['attack_type']),
            target_ip=attack_config_dict['target_ip'],
            interface=attack_config_dict.get('interface', 'wlan0'),
            port=attack_config_dict.get('port', 55443),
            duration_sec=attack_config_dict.get('duration_sec', 60),
            settle_time_sec=attack_config_dict.get('settle_time_sec', 30),
            cycles=attack_config_dict.get('cycles', 1),
            mode=AttackMode(attack_config_dict.get('attack_mode', 'single'))
        )

        # 4. 设置流量捕获
        # Archive PCAPs by MAC address instead of IP
        # Get MAC address for the target IP
        device = db.query(Device).filter(Device.ip_address == config.target_ip).first()
        if device and device.mac_address:
            mac_address = device.mac_address
        else:
            # Fallback to IP if MAC not found
            mac_address = config.target_ip
        
        # Create directory structure using config
        pcap_dir = get_pcap_dir(config.target_ip, mac_address)
        
        # Format timestamp as DD-MM-YY-HH-MM-SS
        timestamp = datetime.utcnow().strftime("%d-%m-%y-%H-%M-%S")
        pcap_filename = f"{mac_address}_{timestamp}_UTC.pcap"
        pcap_path = os.path.join(pcap_dir, pcap_filename)
        tcpdump = TcpdumpUtil(output_file=pcap_path, interface=config.interface, target_ip=config.target_ip)
        tcpdump.start()

        # 5. 初始化引擎并执行攻击
        engine = CyclicAttackEngine()
        
        # 在Docker环境中需要特殊处理
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            success = loop.run_until_complete(engine.start_cyclic_attack(config))
        finally:
            loop.close()
            # 停止流量捕获
            tcpdump.stop()

            # 保存PCAP文件信息
            if os.path.exists(pcap_path):
                file_size = os.path.getsize(pcap_path)
                capture = Capture(
                    file_name=pcap_filename,
                    file_path=pcap_path,
                    experiment_id=experiment_id,
                    file_size=file_size,
                    description=f"PCAP for cyclic attack experiment {experiment_id} (target_ip={config.target_ip})"
                )
                db.add(capture)
                db.commit()
                db.refresh(capture)
                exp.capture_id = capture.id
                db.commit()
        
        # 6. 保存结果
        if success:
            results = engine.get_attack_results()
            exp.attack_results = json.dumps([{
                'cycle': r.cycle,
                'start_time': r.start_time.isoformat(),
                'end_time': r.end_time.isoformat(),
                'duration_sec': r.duration_sec,
                'success': r.success,
                'return_code': r.return_code,
                'stdout': r.stdout,
                'stderr': r.stderr,
                'error': r.error
            } for r in results])
            exp.status = "finished"
        else:
            exp.status = "failed"
        
        exp.end_time = datetime.utcnow()
        db.commit()
        
        return success
        
    except Exception as e:
        logger.error(f"Experiment {experiment_id} failed: {e}")
        if exp:
            exp.status = "failed"
            exp.end_time = datetime.utcnow()
            exp.result = str(e)
            db.commit()
        return False
    finally:
        db.close()

@celery.task(name="execute_shell_script")
def execute_shell_script(execution_id: int, script_content: str, parameters: Dict[str, Any]):
    """执行shell脚本的Celery任务"""
    logger = logging.getLogger(__name__)
    db = SessionLocal()
    
    try:
        # 更新执行状态为running
        execution = db.query(ScriptExecution).get(execution_id)
        if not execution:
            logger.error(f"Execution {execution_id} not found")
            return {"success": False, "error": "执行记录不存在"}
        
        execution.status = 'running'
        db.commit()
        
        # 创建临时脚本文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            # 替换脚本中的参数
            processed_script = script_content
            for param_name, param_value in parameters.items():
                processed_script = processed_script.replace(f"${{{param_name}}}", str(param_value))
            
            f.write(processed_script)
            f.flush()
            temp_script_path = f.name
        
        # 设置执行权限
        os.chmod(temp_script_path, 0o755)
        
        # 记录开始时间
        start_time = datetime.utcnow()
        
        # 执行脚本 - 使用Popen实时获取输出
        process = subprocess.Popen(
            [temp_script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd="/usr/src/app",
            env=os.environ.copy()
        )
        
        # 实时读取输出
        stdout_lines = []
        stderr_lines = []
        
        # 读取stdout
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                line = output.strip()
                stdout_lines.append(line)
                logger.info(f"Script output: {line}")
        
        # 读取stderr
        while True:
            error = process.stderr.readline()
            if error == '' and process.poll() is not None:
                break
            if error:
                line = error.strip()
                stderr_lines.append(line)
                logger.warning(f"Script error: {line}")
        
        # 等待进程完成
        return_code = process.poll()
        
        # 记录结束时间
        end_time = datetime.utcnow()
        execution_time = (end_time - start_time).total_seconds()
        
        # 清理临时文件
        os.unlink(temp_script_path)
        
        # 更新执行状态
        execution.status = 'completed' if return_code == 0 else 'failed'
        execution.output = '\n'.join(stdout_lines)
        execution.error = '\n'.join(stderr_lines)
        execution.return_code = return_code
        execution.end_time = end_time
        execution.execution_time_sec = execution_time
        db.commit()
        
        logger.info(f"Script execution {execution_id} completed in {execution_time:.2f}s")
        
        return {
            "success": return_code == 0,
            "return_code": return_code,
            "output": '\n'.join(stdout_lines),
            "error": '\n'.join(stderr_lines),
            "execution_time": execution_time
        }
        
    except subprocess.TimeoutExpired:
        logger.error(f"Script execution {execution_id} timed out")
        execution.status = 'failed'
        execution.error = "脚本执行超时"
        execution.end_time = datetime.utcnow()
        db.commit()
        return {"success": False, "error": "脚本执行超时"}
        
    except Exception as e:
        logger.error(f"Script execution {execution_id} failed: {str(e)}")
        execution.status = 'failed'
        execution.error = str(e)
        execution.end_time = datetime.utcnow()
        db.commit()
        return {"success": False, "error": str(e)}
        
    finally:
        db.close()