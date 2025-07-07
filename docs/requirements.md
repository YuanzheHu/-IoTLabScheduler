# IoT Lab Experiment Scheduler – Requirements Specification

## 1. Overview

The **IoT Lab Experiment Scheduler** is a prototype system for managing, scheduling, and monitoring network experiments on IoT devices in a laboratory environment. The system is designed to be modular and extensible, allowing for the addition of new experiment types in the future.

---

## 2. Objectives

- **Automate device discovery** within a lab network.
- **Schedule and execute network experiments** (e.g., flooding attacks) on selected devices.
- **Capture and manage network traffic data** (PCAP files) during experiments.
- **Monitor and control experiment tasks** in real time.
- **Provide a foundation for adding new experiment types** with minimal changes.

---

## 3. System Architecture

- **Backend:** FastAPI (Python)
- **Task Queue:** Celery with Redis as the broker
- **Database:** SQLite (for prototype; can be replaced with other RDBMS)
- **Containerization:** Docker & docker-compose
- **Storage:**
  - Relational tables: `devices`, `experiments`, `captures`
  - File storage: `./data/pcaps`, `./data/logs`

---

## 4. Core Modules & Features

### 4.1 Device Discovery

- **Network Scanning:** Automatically scan the lab network to discover active IoT devices.
- **Device Fingerprinting:** Collect device metadata (IP, MAC, type, etc.).
- **Status Monitoring:** Track device online/offline status.

### 4.2 Experiment Management

- **Experiment Types:** Support for multiple experiment types (initially SYN/UDP/ICMP flooding attacks).
- **Parameterization:** Allow configuration of experiment parameters (target, duration, intensity, etc.).
- **Extensibility:** New experiment types can be added by implementing a defined interface/class.
- **Experiment Scheduling:** Schedule experiments for immediate or future execution.
- **Integration with tcpdump:** Capture network traffic during experiments.

### 4.3 Capture Management

- **PCAP Storage:** Store captured network traffic files in a structured directory.
- **Metadata Management:** Associate PCAP files with experiments and devices.
- **Download API:** Allow users to download PCAP files via the API.

### 4.4 Task Management & Monitoring

- **Real-Time Status:** Display the status of running, pending, and completed tasks.
- **Task Control:** Allow users to stop running experiments. Only experiments that are currently running can be stopped; pending or completed experiments cannot be stopped or revoked.
- **Logging:** Store logs for each experiment and system event.

---

## 5. Database Schema

### 5.1 Devices Table

| Field         | Type      | Description                |
|---------------|-----------|----------------------------|
| id            | Integer   | Primary key                |
| ip_address    | String    | Device IP address          |
| mac_address   | String    | Device MAC address         |
| device_type   | String    | Device type/fingerprint    |
| status        | String    | Online/Offline             |
| last_seen     | DateTime  | Last seen timestamp        |

### 5.2 Experiments Table

| Field           | Type      | Description                        |
|-----------------|-----------|------------------------------------|
| id              | Integer   | Primary key                        |
| experiment_type | String    | Type of experiment                 |
| parameters      | JSON      | Experiment parameters              |
| status          | String    | Pending/Running/Completed/Failed   |
| scheduled_at    | DateTime  | Scheduled start time               |
| started_at      | DateTime  | Actual start time                  |
| finished_at     | DateTime  | Actual finish time                 |
| device_id       | Integer   | Foreign key to devices             |

### 5.3 Captures Table

| Field         | Type      | Description                |
|---------------|-----------|----------------------------|
| id            | Integer   | Primary key                |
| experiment_id | Integer   | Foreign key to experiments |
| file_path     | String    | Path to PCAP file          |
| created_at    | DateTime  | Capture timestamp          |

---

## 6. API Endpoints (Initial)

- `GET /devices/` – List all discovered devices
- `POST /experiments/` – Schedule a new experiment
- `GET /experiments/{id}` – Get experiment status/details
- `GET /captures/` – List all PCAP captures
- `GET /captures/{id}/download` – Download a PCAP file
- `POST /experiments/{id}/stop` – Stop a running experiment (only allowed if the experiment is currently running)

---

## 7. Extensibility Guidelines

- **Experiment Interface:** All experiment types must implement a common interface (e.g., `BaseExperiment`) with methods for execution, parameter validation, and result reporting.
- **Registration Mechanism:** New experiment types can be registered via a plugin system or configuration file.
- **API Expansion:** New endpoints can be added for experiment-specific parameters or results as needed.
- **Frontend:** Dashboard pages should be designed to accommodate new experiment types and their unique parameters.

---

## 8. Non-Functional Requirements

- **Security:** Only authorized users can schedule or stop experiments.
- **Reliability:** System should handle device/network failures gracefully.
- **Performance:** Must support concurrent experiments and real-time status updates.
- **Portability:** All components must run in Docker containers.

---

## 9. Deliverables

- Source code (with clear structure and comments)
- Dockerfile and docker-compose.yml
- API documentation (Markdown)
- Example frontend pages (HTML/JS or Vue/React)
- Unit tests (pytest)
- CI workflow (GitHub Actions)

---

## 10. Future Extensions

- Support for additional experiment types (e.g., ARP spoofing, MITM, custom scripts)
- User authentication and role management
- Integration with external device inventory systems
- Advanced scheduling (recurring experiments, dependencies)
- Visualization of experiment results and network traffic

---

**End of Document** 