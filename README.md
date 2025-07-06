# FastAPI + Celery + Docker Template

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.95+-green.svg)](https://fastapi.tiangolo.com/)
[![Celery](https://img.shields.io/badge/Celery-5.2+-orange.svg)](https://docs.celeryproject.org/)
[![Docker](https://img.shields.io/badge/Docker-Required-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A production-ready template for building asynchronous task processing systems with FastAPI, Celery, Redis, and Docker. This project demonstrates best practices for handling background tasks, real-time status updates, and scalable microservices architecture.

> **Note**: This project is based on concepts from [TestDriven.io's comprehensive FastAPI and Celery tutorial](https://testdriven.io/blog/fastapi-and-celery/#celery-setup), enhanced with additional features like UK timezone support, comprehensive testing, and production-ready configurations.

## 🚀 Features

- **Asynchronous Task Processing** - Handle long-running tasks without blocking the web API
- **Real-time Status Updates** - Live task status monitoring with automatic polling
- **Scalable Architecture** - Multiple workers, load balancing, and horizontal scaling
- **Production Ready** - Docker containerization, logging, monitoring, and health checks
- **Developer Friendly** - Hot reload, comprehensive testing, and detailed documentation
- **UK Timezone Support** - All timestamps and logs use UK time (Europe/London)
- **Task Monitoring** - Flower dashboard for real-time task queue monitoring

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   FastAPI       │    │   Celery        │
│   (Web UI)      │◄──►│   (Web API)     │◄──►│   (Worker)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Static Files  │    │   Templates     │    │   Logs          │
│   (CSS/JS)      │    │   (HTML)        │    │   (celery.log)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Redis         │
                       │   (Broker)      │
                       └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Flower        │
                       │   (Dashboard)   │
                       └─────────────────┘
```

## 📁 Project Structure

```
fastapi-celery/
├── docker-compose.yml          # Service orchestration
├── .vscode/
│   └── settings.json          # VSCode Redis connection config
├── project/
│   ├── main.py               # FastAPI application
│   ├── worker.py             # Celery task definitions
│   ├── requirements.txt      # Python dependencies
│   ├── Dockerfile           # Container configuration
│   ├── static/
│   │   ├── main.css         # Frontend styles
│   │   └── main.js          # Frontend JavaScript
│   ├── templates/
│   │   ├── _base.html       # Base template
│   │   ├── footer.html      # Footer template
│   │   └── home.html        # Main page template
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py      # Test configuration
│   │   └── test_tasks.py    # Test cases
│   └── logs/                # Celery log directory
└── README.md               # This file
```

## 🛠️ Technology Stack

- **Backend**: FastAPI (Python web framework)
- **Task Queue**: Celery (Distributed task queue)
- **Message Broker**: Redis (In-memory data store)
- **Frontend**: HTML/CSS/JavaScript with Bootstrap
- **Containerization**: Docker & Docker Compose
- **Monitoring**: Flower (Celery monitoring tool)
- **Testing**: pytest
- **Timezone**: UK (Europe/London)

## 🚀 Quick Start

### Prerequisites

- Docker
- Docker Compose
- Git

### 1. Clone and Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd fastapi-celery

# Start all services
docker-compose up -d --build
```

### 2. Access the Application

- **Web Interface**: http://localhost:8004
- **API Documentation**: http://localhost:8004/docs
- **Flower Dashboard**: http://localhost:5556
- **Redis**: localhost:6379

### 3. Test the System

1. Open http://localhost:8004
2. Click "Short", "Medium", or "Long" buttons
3. Watch tasks execute in real-time
4. Monitor task queue in Flower dashboard

## 📚 API Reference

### Endpoints

#### GET /
Returns the main web interface.

#### POST /tasks
Creates a new asynchronous task.

**Request Body:**
```json
{
  "type": 1  // 1=Short(10s), 2=Medium(20s), 3=Long(30s)
}
```

**Response:**
```json
{
  "task_id": "uuid-string"
}
```

#### GET /tasks/{task_id}
Gets the status of a specific task.

**Response:**
```json
{
  "task_id": "uuid-string",
  "task_status": "PENDING|SUCCESS|FAILURE",
  "task_result": null|true|false
}
```

## 🔧 Using as a Template

### 1. Basic Customization

#### Modify Task Types
Edit `project/worker.py` to add your own tasks:

```python
@celery.task(name="process_file")
def process_file(file_path):
    # Your file processing logic
    result = analyze_file(file_path)
    return result

@celery.task(name="send_email")
def send_email(email_data):
    # Your email sending logic
    send_mail(email_data)
    return {"status": "sent"}
```

#### Update API Endpoints
Modify `project/main.py` to handle your tasks:

```python
@app.post("/process-file")
def create_file_task(file_data: dict):
    task = process_file.delay(file_data["path"])
    return {"task_id": task.id}

@app.post("/send-email")
def create_email_task(email_data: dict):
    task = send_email.delay(email_data)
    return {"task_id": task.id}
```

#### Customize Frontend
Update `project/templates/home.html` and `project/static/main.js` for your UI needs.

### 2. Advanced Customization

#### Add Database Support
Add PostgreSQL to `docker-compose.yml`:

```yaml
services:
  database:
    image: postgres:13
    environment:
      POSTGRES_DB: your_db
      POSTGRES_USER: your_user
      POSTGRES_PASSWORD: your_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

#### Add Authentication
Implement JWT authentication in `main.py`:

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.post("/protected-endpoint")
def protected_endpoint(token: str = Depends(security)):
    # Verify token
    pass
```

#### Scale Workers
Increase worker instances:

```bash
docker-compose up -d --scale worker=5
```

### 3. Production Deployment

#### Environment Variables
Create `.env` file:

```env
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
TZ=Europe/London
ENVIRONMENT=production
```

#### Production Docker Compose
Create `docker-compose.prod.yml`:

```yaml
version: '3.8'
services:
  web:
    restart: always
    environment:
      - ENVIRONMENT=production
  worker:
    restart: always
    deploy:
      replicas: 3
  redis:
    restart: always
    volumes:
      - redis_data:/data
```

## 🧪 Testing

### Run All Tests
```bash
docker-compose exec web python -m pytest -v
```

### Run Specific Tests
```bash
# Unit tests (fast)
docker-compose exec web python -m pytest -k "test_mock_task" -v

# Integration tests
docker-compose exec web python -m pytest -k "test_task_status" -v

# API tests
docker-compose exec web python -m pytest -k "test_home" -v
```

### Test Coverage
```bash
docker-compose exec web python -m pytest --cov=. -v
```

## 📊 Monitoring

### Flower Dashboard
Access http://localhost:5556 to monitor:
- Active workers
- Task queue status
- Task execution history
- Worker performance metrics

### Logs
```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs worker
docker-compose logs web

# Follow logs in real-time
docker-compose logs -f worker
```

### Redis Monitoring
```bash
# Connect to Redis CLI
docker exec -it fastapi-celery-redis-1 redis-cli

# View all keys
KEYS *

# Monitor Redis operations
MONITOR
```

## 🔄 Development Workflow

### 1. Local Development
```bash
# Start services
docker-compose up -d

# Make code changes (hot reload enabled)
# View changes at http://localhost:8004

# Run tests
docker-compose exec web python -m pytest -v
```

### 2. Adding New Features
1. Add task definition in `worker.py`
2. Add API endpoint in `main.py`
3. Update frontend in `templates/` and `static/`
4. Add tests in `tests/`
5. Test and deploy

### 3. Debugging
```bash
# View real-time logs
docker-compose logs -f

# Access container shell
docker-compose exec web bash
docker-compose exec worker bash

# Check Redis data
docker exec fastapi-celery-redis-1 redis-cli KEYS "*"
```

## 🚀 Deployment

### Docker Deployment
```bash
# Build and deploy
docker-compose -f docker-compose.prod.yml up -d --build

# Scale workers
docker-compose -f docker-compose.prod.yml up -d --scale worker=5
```

### Kubernetes Deployment
Create Kubernetes manifests for each service and deploy to your cluster.

### Cloud Deployment
Deploy to AWS, GCP, or Azure using their container services.

## 🔧 Configuration

### Environment Variables
- `CELERY_BROKER_URL`: Redis connection URL
- `CELERY_RESULT_BACKEND`: Redis result backend URL
- `TZ`: Timezone (default: Europe/London)

### Docker Configuration
- `ports`: Service port mappings
- `volumes`: File system mounts
- `environment`: Environment variables
- `depends_on`: Service dependencies

### Celery Configuration
- `broker_url`: Message broker URL
- `result_backend`: Result storage URL
- `timezone`: Task execution timezone
- `enable_utc`: UTC timezone setting

## 🐛 Troubleshooting

### Common Issues

#### Redis Connection Issues
```bash
# Check Redis status
docker-compose ps redis

# Test Redis connection
docker exec fastapi-celery-redis-1 redis-cli ping
```

#### Worker Not Processing Tasks
```bash
# Check worker logs
docker-compose logs worker

# Restart worker
docker-compose restart worker
```

#### Frontend Not Updating
```bash
# Check web service
docker-compose logs web

# Clear browser cache
# Check browser console for errors
```

### Reset Everything
```bash
# Complete reset
docker-compose down -v
docker-compose up -d --build
```

## 📈 Performance Optimization

### Scaling Workers
```bash
# Scale to 5 workers
docker-compose up -d --scale worker=5
```

### Redis Optimization
- Configure Redis persistence
- Set appropriate memory limits
- Enable Redis clustering for high availability

### Monitoring Performance
- Use Flower dashboard for metrics
- Monitor Redis memory usage
- Track task execution times

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- FastAPI for the excellent web framework
- Celery for the robust task queue system
- Redis for the reliable message broker
- Docker for the containerization platform
- [TestDriven.io's FastAPI and Celery Tutorial](https://testdriven.io/blog/fastapi-and-celery/#celery-setup) for the foundational concepts and implementation patterns

## 📞 Support

For questions and support:
- Create an issue in the repository
- Check the documentation
- Review the troubleshooting section

---

**Happy coding! 🚀**
