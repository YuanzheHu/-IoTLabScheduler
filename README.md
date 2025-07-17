# IoT Lab Experiment Scheduler

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.95+-green.svg)](https://fastapi.tiangolo.com/)
[![Celery](https://img.shields.io/badge/Celery-5.2+-orange.svg)](https://docs.celeryproject.org/)
[![Docker](https://img.shields.io/badge/Docker-Required-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A prototype system for managing, scheduling, and monitoring network experiments on IoT devices in a laboratory environment. Built with microservices architecture using FastAPI, Celery, and Redis.

## Features

- **Device Discovery**: Subnet scanning with nmap
- **Port & OS Fingerprinting**: On-demand device scanning
- **Network Attack Experiments**: SYN/UDP/ICMP flooding with async execution
- **Traffic Capture**: Automated PCAP capture and archiving
- **Real-time Monitoring**: Live log streaming and experiment status tracking
- **Plugin Interface**: Extensible architecture for new experiment types

## Architecture
![System Architecture & Experiment Flow](docs/images/sequence%20diagram.png)

**Figure:** High-level architecture and experiment scheduling flow.

- **FastAPI** exposes REST endpoints for device management and experiment scheduling.
- **Celery** workers execute experiments asynchronously, coordinating with the **Attack Engine** and **Traffic Capture** modules.
- **Redis** acts as the message broker and result backend for Celery.
- **SQLite** stores device, experiment, and capture metadata.
- **Plugin Interface** allows new experiment types to be added without modifying the core system.

## Docker Build & Run

To build and run the IoT Lab Experiment Scheduler using Docker:

### Prerequisites

- Docker and Docker Compose

### Quick Start

1. Clone the repository:
```bash
git clone <repository-url>
cd IoTLabScheduler
```

2. Build and start all services with Docker Compose:
```bash
docker-compose up --build -d

docker compose up -d --build --scale worker=4
```

4. Access the services:
- **FastAPI API**: http://localhost:8000
- **Flower Dashboard**: http://localhost:5556
- **API Documentation**: http://localhost:8000/docs

### Docker Services

The `docker-compose.yml` includes:
- **FastAPI Web Server** (Port 8000)
- **Celery Workers** (Multiple instances)
- **Redis** (Message broker and result backend)
- **Flower Dashboard** (Port 5556)

### Testing

Run the test suite:
```bash
cd project
pytest
```

## Development

### Local Development Setup

1. Install dependencies:
```bash
pip install -r project/requirements.txt
```

2. Start Redis:
```bash
docker run -d -p 6379:6379 redis:7
```

3. Run the FastAPI server:
```bash
cd project
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

4. Start Celery worker:
```bash
cd project
celery -A worker.celery worker --loglevel=info
```

5. Start Flower dashboard:
```bash
cd project
celery -A worker.celery flower --port=5556
```

### Usage

1. **Device Discovery**:
```bash
curl -X POST "http://localhost:8000/devices/scan" \
     -H "Content-Type: application/json" \
     -d '{"subnet": "10.12.0.0/24"}'
```

2. **Schedule an Experiment**:
```bash
curl -X POST "http://localhost:8000/experiments/" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "SYN Flood Test",
       "attack_type": "SYN",
       "target_ip": "192.168.1.100",
       "duration_sec": 60
     }'
```

3. **Check Experiment Status**:
```bash
curl "http://localhost:8000/experiments/{experiment_id}/status"
```

4. **Download PCAP File**:
```bash
curl "http://localhost:8000/captures/{capture_id}/download" \
     --output experiment.pcap
```

## API Endpoints

### Device Management
- `GET /devices/` - List all devices
- `POST /devices/scan` - Scan subnet for devices
- `GET /devices/{id}` - Get device details
- `GET /devices/{ip}/portscan` - Port scan device
- `GET /devices/{ip}/oscan` - OS fingerprint device

### Experiment Management
- `POST /experiments/` - Schedule new experiment
- `GET /experiments/` - List all experiments
- `GET /experiments/{id}` - Get experiment details
- `POST /experiments/{id}/stop` - Stop running experiment

### Traffic Capture
- `GET /captures/` - List PCAP records
- `GET /captures/{id}` - Get capture metadata
- `GET /captures/{id}/download` - Download PCAP file

## Project Structure

```
IoTLabScheduler/
├── project/
│   ├── api/              # FastAPI endpoints
│   ├── core/             # Core business logic
│   ├── db/               # Database models and setup
│   ├── data/             # PCAP files and data
│   ├── logs/             # Application logs
│   ├── tests/            # Test suite
│   ├── main.py           # FastAPI application
│   └── worker.py         # Celery worker tasks
├── docs/                 # Documentation
├── docker-compose.yml    # Docker services
└── README.md
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

