#!/bin/bash

# 创建必要的目录
mkdir -p /usr/src/app/logs
mkdir -p /usr/src/app/data
chmod -R 777 /usr/src/app/data /usr/src/app/logs

# 等待Redis可用
echo "Waiting for Redis..."
until nc -z localhost 6379; do
    sleep 1
done
echo "Redis is available"

# 根据服务类型启动不同的进程
case "$SERVICE_TYPE" in
    "web")
        echo "Starting FastAPI service..."
        if [ "${FASTAPI_RELOAD}" = "true" ]; then
            uvicorn main:app --host ${FASTAPI_HOST:-0.0.0.0} \
                            --port ${FASTAPI_PORT:-8000} \
                            --reload \
                            --workers ${FASTAPI_WORKERS:-1}
        else
            uvicorn main:app --host ${FASTAPI_HOST:-0.0.0.0} \
                            --port ${FASTAPI_PORT:-8000} \
                            --workers ${FASTAPI_WORKERS:-1}
        fi
        ;;
    "worker")
        echo "Starting Celery worker..."
        celery -A worker.celery worker \
            --loglevel=${LOG_LEVEL:-info} \
            --logfile=${LOG_DIR}/celery.log \
            --concurrency=${CELERY_CONCURRENCY:-4} \
            --hostname=worker@%h
        ;;
    "flower")
        echo "Starting Flower dashboard..."
        celery --broker=${CELERY_BROKER_URL} flower \
            --port=${FLOWER_PORT:-5555} \
            --log-file=${LOG_DIR}/flower.log
        ;;
    *)
        echo "Unknown service type: $SERVICE_TYPE"
        exit 1
        ;;
esac