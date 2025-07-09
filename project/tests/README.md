# IoT Lab Scheduler Testing Guide

This document explains how to run and interpret the automated tests for the IoT Lab Experiment Scheduler project.

---

## 1. Environment Preparation

- Make sure Docker and Docker Compose are installed.
- Start all services and scale up workers for concurrency:

```sh
docker compose up -d --build --scale worker=4
```
- Confirm all services are running:

```sh
docker compose ps
```

---

## 2. Enter the Web Container

All tests should be run inside the web container for correct environment and dependencies:

```sh
docker exec -it iotlabscheduler-web-1 /bin/sh
cd /usr/src/app
```

---

## 3. Run Tests

### Run All Tests

```sh
pytest tests/
```

### Run a Single Test File

```sh
pytest tests/test_experiment_async.py
pytest tests/test_tasks.py
```

### Run a Specific Test Function

```sh
pytest tests/test_experiment_async.py -k test_create_experiment_and_check_async -s
pytest tests/test_experiment_async.py -k test_multiple_experiments_concurrent -s
```

---

## 4. Test Descriptions

- **test_create_experiment_and_check_async**: Submits a single experiment and checks that it completes and produces a PCAP file.
- **test_multiple_experiments_concurrent**: Submits multiple experiments in parallel (using different target IPs) and checks that all are processed correctly. Requires multiple Celery workers.
- **test_tasks.py**: Tests basic Celery task queue and status logic.

---

## 5. Best Practices & Troubleshooting

- Always run tests inside the web container for correct environment.
- For concurrent experiment tests, ensure you have at least as many workers as experiments (e.g., 4 workers for 4 experiments).
- Monitor the Flower dashboard at [http://localhost:5556](http://localhost:5556) to see real-time task status and failures.
- If a test fails:
  - Check worker logs: `docker compose logs worker | tail -n 200`
  - Look for Python Tracebacks or error messages.
  - Make sure all dependencies (hping3, tcpdump) are installed and have correct permissions in the worker container.
  - Ensure target IPs are reachable from the worker container.
- If you change the number of workers, restart with:

```sh
docker compose up -d --scale worker=4
```

- To reset the environment (delete all data and logs):

```sh
docker compose down -v
rm -rf project/data/* project/logs/*
```

---

## 6. Example Workflow

```sh
# Start services and scale workers
$ docker compose up -d --build --scale worker=4

# Enter the web container
$ docker exec -it iotlabscheduler-web-1 /bin/sh
$ cd /usr/src/app

# Run single experiment test
$ pytest tests/test_experiment_async.py -k test_create_experiment_and_check_async -s

# Run concurrent experiments test
$ pytest tests/test_experiment_async.py -k test_multiple_experiments_concurrent -s
```

---

## 7. Notes

- All test code is in the `tests/` folder.
- Adjust IP addresses and experiment parameters in the test files as needed for your lab environment.
- For further debugging, always check both the test output and the worker logs. 