# ================== Configuration ==================
import time
import threading
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

BASE_URL = "http://localhost:8004"
DEFAULT_PORT = 80
DURATION = 10  # 10 seconds, ensure completion within 30 seconds

# attack_type and target_ip pairs
ATTACK_TYPE_TARGET_IPS = [
    ("syn_flood",    "10.12.0.182"),
    ("udp_flood",    "10.12.0.184"),
    ("icmp_flood",   "10.12.0.185"),
    ("tcp_flood",    "10.12.0.188"),
    ("ip_frag_flood","10.12.0.189"),
]

# ================== Helper Functions ==================
def create_experiment(attack_type, target_ip, port=DEFAULT_PORT, duration=DURATION, status="pending"):
    payload = {
        "name": f"pytest {attack_type}",
        "attack_type": attack_type,
        "target_ip": target_ip,
        "port": port,
        "duration_sec": duration,
        "status": status
    }
    resp = client.post("/experiments/", json=payload)
    assert resp.status_code == 200
    return resp.json()

def wait_for_status(exp_id, expected_statuses, timeout=40, poll_interval=2):
    start = time.time()
    while time.time() - start < timeout:
        resp = client.get(f"/experiments/{exp_id}")
        assert resp.status_code == 200
        status = resp.json()["status"]
        if status in expected_statuses:
            return resp.json()
        time.sleep(poll_interval)
    raise TimeoutError(f"Experiment {exp_id} did not reach status {expected_statuses} in {timeout} seconds")

# ================== Test Cases ==================

# Use only the first pair
@pytest.mark.parametrize("attack_type,target_ip", [ATTACK_TYPE_TARGET_IPS[0]])
def test_create_and_complete_experiment(attack_type, target_ip):
    exp = create_experiment(attack_type, target_ip, duration=DURATION)
    exp_id = exp["id"]
    # Check initial status
    status = client.get(f"/experiments/{exp_id}").json()["status"]
    assert status in ("pending", "running")
    # Wait for completion
    result = wait_for_status(exp_id, ("finished", "failed"))
    assert result["status"] in ("finished", "failed")
    assert result.get("capture_id") is not None

# Run the remaining 4 pairs concurrently
@pytest.mark.parametrize("attack_type_ip_pairs", [ATTACK_TYPE_TARGET_IPS[1:]])
def test_multiple_experiments_concurrent(attack_type_ip_pairs):
    experiment_ids = []
    def submit(idx, attack_type, target_ip):
        exp = create_experiment(attack_type, target_ip, port=DEFAULT_PORT+idx, duration=DURATION)
        experiment_ids.append(exp["id"])
    threads = [threading.Thread(target=submit, args=(i, at, ip)) for i, (at, ip) in enumerate(attack_type_ip_pairs)]
    for t in threads: t.start()
    for t in threads: t.join()
    for exp_id in experiment_ids:
        result = wait_for_status(exp_id, ("finished", "failed"))
        assert result["status"] in ("finished", "failed")
        assert result.get("capture_id") is not None

def test_stop_experiment():
    # Use the first pair
    attack_type, target_ip = ATTACK_TYPE_TARGET_IPS[0]
    exp = create_experiment(attack_type, target_ip, duration=DURATION)
    exp_id = exp["id"]
    time.sleep(2)
    # Stop experiment
    stop_resp = client.post(f"/experiments/{exp_id}/stop")
    assert stop_resp.status_code == 200
    stopped_exp = stop_resp.json()
    assert stopped_exp["status"] == "stopped"
    assert stopped_exp["result"] == "Experiment stopped by user"
    # Verify stopped
    status = client.get(f"/experiments/{exp_id}").json()["status"]
    assert status == "stopped"

def test_experiment_status_endpoint():
    # Use the first pair
    attack_type, target_ip = ATTACK_TYPE_TARGET_IPS[0]
    exp = create_experiment(attack_type, target_ip, duration=DURATION)
    exp_id = exp["id"]
    status_resp = client.get(f"/experiments/{exp_id}/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["id"] == exp_id
    assert "status" in status_data
    wait_for_status(exp_id, ("finished", "failed"))

def test_list_experiments():
    # Use the first two pairs
    attack_type1, target_ip1 = ATTACK_TYPE_TARGET_IPS[0]
    attack_type2, target_ip2 = ATTACK_TYPE_TARGET_IPS[1]
    create_experiment(attack_type1, target_ip1, duration=DURATION)
    create_experiment(attack_type2, target_ip2, duration=DURATION)
    resp = client.get("/experiments/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 2