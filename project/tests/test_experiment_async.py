import time
import requests
from fastapi.testclient import TestClient
from main import app
import threading
import pytest

client = TestClient(app)

BASE_URL = "http://localhost:8004"

def test_create_experiment_and_check_async():
    # 1. Create an experiment
    payload = {
        "name": "pytest SYN Flood",
        "attack_type": "syn_flood",
        "target_ip": "10.12.0.177",
        "port": 80,
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
        "port": 443,
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
    ports = [80, 443, 22, 8080]
    num_experiments = len(ips)
    experiment_ids = []
    responses = [None] * num_experiments

    def submit_experiment(idx):
        payload = {
            "name": f"pytest SYN Flood {idx}",
            "attack_type": "syn_flood",
            "target_ip": ips[idx],
            "port": ports[idx],
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

def test_stop_experiment():
    """
    Test stopping a running experiment.
    """
    # 1. Create a long-running experiment
    payload = {
        "name": "pytest Stop Test",
        "attack_type": "syn_flood",
        "target_ip": "10.12.0.177",
        "port": 80,
        "duration_sec": 300,  # 5 minutes
        "status": "pending"
    }
    resp = client.post("/experiments/", json=payload)
    assert resp.status_code == 200
    exp = resp.json()
    exp_id = exp["id"]

    # 2. Wait a moment for experiment to start running
    time.sleep(3)
    
    # 3. Check that experiment is running
    resp = client.get(f"/experiments/{exp_id}")
    assert resp.status_code == 200
    status = resp.json()["status"]
    assert status in ("pending", "running")

    # 4. Stop the experiment
    stop_resp = client.post(f"/experiments/{exp_id}/stop")
    assert stop_resp.status_code == 200
    stopped_exp = stop_resp.json()
    assert stopped_exp["status"] == "stopped"
    assert stopped_exp["result"] == "Experiment stopped by user"

    # 5. Verify experiment is stopped
    resp = client.get(f"/experiments/{exp_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "stopped"

    print("Experiment stop test passed.")

def test_experiment_status_endpoint():
    """
    Test the experiment status endpoint.
    """
    # 1. Create an experiment
    payload = {
        "name": "pytest Status Test",
        "attack_type": "syn_flood",
        "target_ip": "10.12.0.177",
        "port": 80,
        "duration_sec": 10,
        "status": "pending"
    }
    resp = client.post("/experiments/", json=payload)
    assert resp.status_code == 200
    exp = resp.json()
    exp_id = exp["id"]

    # 2. Check status endpoint
    status_resp = client.get(f"/experiments/{exp_id}/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert "id" in status_data
    assert "name" in status_data
    assert "status" in status_data
    assert status_data["id"] == exp_id

    # 3. Wait for completion and check again
    time.sleep(12)
    status_resp = client.get(f"/experiments/{exp_id}/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["status"] in ("finished", "failed")

def test_list_experiments():
    # Create two experiments
    payload1 = {
        "name": "List Test 1",
        "attack_type": "syn_flood",
        "target_ip": "127.0.0.1",
        "duration_sec": 5,
        "status": "pending"
    }
    payload2 = {
        "name": "List Test 2",
        "attack_type": "syn_flood",
        "target_ip": "127.0.0.2",
        "duration_sec": 5,
        "status": "pending"
    }
    client.post("/experiments/", json=payload1)
    client.post("/experiments/", json=payload2)
    resp = client.get("/experiments/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 2