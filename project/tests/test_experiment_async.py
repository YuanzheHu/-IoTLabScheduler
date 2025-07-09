import time
import requests
from fastapi.testclient import TestClient
from main import app
import threading

client = TestClient(app)

BASE_URL = "http://localhost:8004"

def test_create_experiment_and_check_async():
    # 1. Create an experiment
    payload = {
        "name": "pytest SYN Flood",
        "attack_type": "syn_flood",
        "target_ip": "10.12.0.177",
        "duration_sec": 10,
        "status": "pending"
    }
    resp = client.post("/experiments/", json=payload)
    assert resp.status_code == 200
    exp = resp.json()
    exp_id = exp["id"]

    # 2. Immediately check experiment status, should be 'pending' or 'running'
    resp2 = client.get(f"/experiments/{exp_id}")
    assert resp2.status_code == 200
    status = resp2.json()["status"]
    assert status in ("pending", "running")

    # 3. Wait for a while and check again, should be 'finished' or 'failed'
    time.sleep(12)
    resp3 = client.get(f"/experiments/{exp_id}")
    assert resp3.status_code == 200
    status2 = resp3.json()["status"]
    assert status2 in ("finished", "failed")
    assert resp3.json()["capture_id"] is not None

    print("Experiment async attack and pcap capture test passed.")
    
def test_experiment_attack_async():
    # 1. Create an experiment
    response = client.post("/experiments/", json={
        "name": "pytest attack",
        "attack_type": "syn_flood",
        "target_ip": "127.0.0.1",
        "duration_sec": 10,
        "status": "pending"
    })
    assert response.status_code == 200
    exp = response.json()
    exp_id = exp["id"]

    # 2. Immediately check experiment status, should be 'pending' or 'running'
    response = client.get(f"/experiments/{exp_id}")
    assert response.status_code == 200
    status = response.json()["status"]
    assert status in ("pending", "running")

    # 3. Wait for a while and check again, should be 'finished' or 'failed'
    time.sleep(70)  # Wait for 1 minute + buffer
    response = client.get(f"/experiments/{exp_id}")
    assert response.status_code == 200
    status = response.json()["status"]
    assert status in ("finished", "failed")
    # Check if a PCAP file is associated
    assert response.json()["capture_id"] is not None 

def test_multiple_experiments_concurrent():
    """
    Submit multiple experiments at the same time and check all are processed (requires multiple workers running).
    """
    ips = ["10.12.0.177", "10.12.0.211", "10.12.0.222", "10.12.0.195"]
    num_experiments = len(ips)
    experiment_ids = []
    responses = [None] * num_experiments

    def submit_experiment(idx):
        payload = {
            "name": f"pytest SYN Flood {idx}",
            "attack_type": "syn_flood",
            "target_ip": ips[idx],
            "duration_sec": 60,
            "status": "pending"
        }
        resp = client.post("/experiments/", json=payload)
        assert resp.status_code == 200
        exp = resp.json()
        experiment_ids.append(exp["id"])
        responses[idx] = exp

    threads = [threading.Thread(target=submit_experiment, args=(i,)) for i in range(num_experiments)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Poll each experiment until it is finished or failed, or timeout
    timeout = 120  # seconds (increase for real network)
    poll_interval = 3
    start = time.time()
    finished = set()
    while time.time() - start < timeout and len(finished) < num_experiments:
        for exp_id in experiment_ids:
            if exp_id in finished:
                continue
            resp = client.get(f"/experiments/{exp_id}")
            assert resp.status_code == 200
            status = resp.json()["status"]
            if status in ("finished", "failed"):
                assert resp.json()["capture_id"] is not None
                finished.add(exp_id)
        time.sleep(poll_interval)
    assert len(finished) == num_experiments, f"Not all experiments finished in {timeout} seconds" 