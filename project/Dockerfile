# Multi-stage build
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency file
COPY requirements.txt .

# Build Python wheels
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -r requirements.txt

# Final image
FROM python:3.11-slim

# Set working directory
WORKDIR /usr/src/app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Europe/London

# Install system and network tools
RUN apt-get update && apt-get install -y \
    netcat-traditional \
    hping3 \
    tcpdump \
    nmap \
    iproute2 \
    iputils-ping \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder stage
COPY --from=builder /build/wheels /wheels

# Install Python packages
RUN pip install --no-cache /wheels/*

# Copy application code
COPY . .

# Create necessary directories and set permissions
RUN mkdir -p /usr/src/app/logs /usr/src/app/data /usr/src/app/scripts && \
    chmod -R 755 /usr/src/app/scripts && \
    chmod -R 777 /usr/src/app/logs /usr/src/app/data

# Copy startup script and set permissions
COPY scripts/start.sh /usr/src/app/scripts/
RUN chmod +x /usr/src/app/scripts/start.sh

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${FASTAPI_PORT:-8000}/health || exit 1

# Startup command
CMD ["/usr/src/app/scripts/start.sh"]