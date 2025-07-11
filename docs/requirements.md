## IoT Lab Experiment Scheduler – Requirements Specification

---

### 1. Overview

The **IoT Lab Experiment Scheduler** is a prototype system for managing, scheduling, and monitoring network experiments on IoT devices in a laboratory environment. It automates device discovery, per-device port/OS scans, experiment execution, PCAP capture and archiving, and real-time log streaming. Built with a microservices architecture, it is modular, scalable, and extensible.

---

### 2. Objectives

* **Automate device discovery** within lab subnets
* **Per-device port & OS fingerprinting** on demand
* **Schedule and execute network flooding experiments** (SYN/UDP/ICMP)
* **Capture traffic as PCAPs**, organize by device, and enable secure download
* **Stream real-time logs** for experiments and system events
* **Provide a plugin interface** for adding new experiment types
* **Ensure reliability** via containerization, retry logic, and monitoring

---

### 3. System Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI Web   │    │  Celery Worker  │    │   Flower        │
│   (Port 8004)   │◄──►│   (Multiple)    │    │   Dashboard     │
└─────────────────┘    └─────────────────┘    │   (Port 5556)   │
         │                       │            └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│   SQLite DB     │    │   Redis         │
│   (Data)        │    │   (Broker)      │
└─────────────────┘    └─────────────────┘
```

* **Backend:** FastAPI (Python 3.11+)
* **Task Queue:** Celery + Redis
* **Database:** SQLite (prototype) via SQLAlchemy
* **Containerization:** Docker & Docker Compose
* **Monitoring:** Flower for task status; real-time logs via SSE/WebSocket
* **Testing:** pytest

---

### 4. Core Modules & Features

#### 4.1 Device Management

* **CRUD Operations** on `devices` table
* **Metadata:** IP, MAC, device type, status, last seen
* **Auto-Discovery:** Scan subnets to populate/update device records
* **On-Demand Scans:** Port and/or OS fingerprint per device

#### 4.2 Experiment Management

* **Experiment Types:** SYN, UDP, ICMP flooding
* **Parameters:** target IP, duration (sec), name
* **Async Execution:** Celery tasks (Pending → Running → Completed/Failed)
* **Stop Control:** API to abort running experiments

#### 4.3 Traffic Capture & Archiving

* **Automated PCAP Capture:** tcpdump during experiments
* **Metadata Linkage:** captures table → experiments table
* **Device-Based Archiving:**

  ```
  data/pcaps/
  └─ <device_name>/
     ├─ <timestamp>_<exp_name>.pcap
     └─ …
  ```
* **Download & Cleanup:** Secure download endpoint; delete stale PCAPs

#### 4.4 Real-Time Logging

* **Log Stream Endpoint:** SSE or WebSocket (`/logs/stream`)
* **Filtering:** by experiment\_id or device\_id
* **JSON-formatted entries** for easy parsing

#### 4.5 Extensibility & Testing

* **Plugin Interface:** `BaseExperiment` for new experiment types
* **Automated Tests:** unit, integration (TestClient), concurrent
* **CI/CD Ready:** Docker Compose for build/test/deploy

---

### 5. Database Schema

#### 5.1 `devices` Table

| Field        | Type     | Description                  |
| ------------ | -------- | ---------------------------- |
| id           | Integer  | Primary key                  |
| ip\_address  | String   | Device IP address            |
| mac\_address | String   | Device MAC address           |
| device\_type | String   | Fingerprinted OS/device type |
| status       | String   | Online / Offline             |
| last\_seen   | DateTime | Last heartbeat timestamp     |
| created\_at  | DateTime | Record creation              |
| updated\_at  | DateTime | Record update                |

#### 5.2 `experiments` Table

| Field         | Type     | Description                            |
| ------------- | -------- | -------------------------------------- |
| id            | Integer  | Primary key                            |
| name          | String   | Experiment name                        |
| attack\_type  | String   | SYN / UDP / ICMP                       |
| target\_ip    | String   | Target device IP                       |
| duration\_sec | Integer  | Duration in seconds                    |
| status        | String   | Pending / Running / Completed / Failed |
| scheduled\_at | DateTime | Scheduled start time                   |
| started\_at   | DateTime | Actual start time                      |
| finished\_at  | DateTime | Actual end time                        |
| created\_at   | DateTime | Record creation                        |
| updated\_at   | DateTime | Record update                          |

#### 5.3 `captures` Table

| Field          | Type     | Description                      |
| -------------- | -------- | -------------------------------- |
| id             | Integer  | Primary key                      |
| experiment\_id | Integer  | FK → experiments.id              |
| file\_path     | String   | Relative path under `data/pcaps` |
| file\_size     | Integer  | Bytes                            |
| created\_at    | DateTime | Capture timestamp                |

---

### 6. API Endpoints

#### 6.1 Device Management

| Method | Endpoint        | Description        |
| ------ | --------------- | ------------------ |
| GET    | `/devices/`     | List devices       |
| POST   | `/devices/`     | Create device      |
| GET    | `/devices/{id}` | Get device details |
| PUT    | `/devices/{id}` | Update device      |
| DELETE | `/devices/{id}` | Delete device      |

#### 6.2 Device Discovery & Fingerprinting

| Method | Endpoint             | Description                                        |
| ------ | -------------------- | -------------------------------------------------- |
| POST   | `/devices/scan`      | Scan subnet: `{ "subnet": "192.168.1.0/24" }`      |
| POST   | `/devices/{id}/scan` | Per-device scan: `{ "scan_types": ["port","os"] }` |

#### 6.3 Experiment Management

| Method | Endpoint                 | Description              |
| ------ | ------------------------ | ------------------------ |
| POST   | `/experiments/`          | Schedule new experiment  |
| GET    | `/experiments/`          | List all experiments     |
| GET    | `/experiments/{id}`      | Get experiment details   |
| PUT    | `/experiments/{id}`      | Update (if not started)  |
| DELETE | `/experiments/{id}`      | Remove experiment record |
| POST   | `/experiments/{id}/stop` | Abort running experiment |

#### 6.4 Traffic Capture & Archiving

| Method | Endpoint                  | Description               |
| ------ | ------------------------- | ------------------------- |
| GET    | `/captures/`              | List PCAP records         |
| GET    | `/captures/{id}`          | Get PCAP metadata         |
| GET    | `/captures/{id}/download` | Download PCAP file        |
| DELETE | `/captures/{id}`          | Delete PCAP file & record |

#### 6.5 Real-Time Log Streaming

| Method | Endpoint       | Description                                |
| ------ | -------------- | ------------------------------------------ |
| GET    | `/logs/stream` | SSE/WebSocket stream of JSON log entries   |
|        |                | Query params: `?experiment_id=&device_id=` |

---

### 7. User Workflow

1. **Subnet Scan**

   * Call `POST /devices/scan` → enter the subnet CIDR → system returns the list of newly added or updated devices

2. **Per-Device Scan**

   * On the devices list or details page, select a device → call `POST /devices/{id}/scan` with `scan_types` of `["port"]`, `["os"]`, or both → system returns the device’s open ports and/or OS fingerprint information

3. **View Devices**

   * Use `GET /devices/` or `GET /devices/{id}` to browse device metadata

4. **Schedule Experiment**

   * Click “New Experiment” → fill in target IP, attack type, duration, and name → call `POST /experiments/` → system returns an experiment ID in Pending status

5. **Monitor Logs**

   * Open the real-time logs view → subscribe to `/logs/stream?experiment_id={id}` → view live logs for scheduling, tcpdump start, traffic statistics, etc.

6. **Stop Experiment**

   * If needed, click “Stop” → call `POST /experiments/{id}/stop` → system aborts the flood and capture, and records the finish time

7. **Retrieve PCAP**

   * After completion, call `GET /captures/?experiment_id={id}` → select a record → call `GET /captures/{id}/download` → download the PCAP from `data/pcaps/<device_name>/…`

8. **Cleanup**

   * Periodically or on demand, call `DELETE /captures/{id}` to remove stale PCAP files and their database records

---

### 8. Non-Functional Requirements

* **Containerized Deployment** via Docker Compose
* **Scalability:** Horizontal Celery worker scaling
* **Reliability:** Task retries and structured logging
* **Test Coverage:** ≥ 80% with pytest
* **Extensibility:** Plugin-based experiment interface

---
