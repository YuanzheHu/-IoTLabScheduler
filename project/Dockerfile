# 使用多阶段构建
FROM python:3.11-slim as builder

# 设置工作目录
WORKDIR /build

# 安装构建依赖
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -r requirements.txt

# 最终镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /usr/src/app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Europe/London

# 安装系统工具和网络工具
RUN apt-get update && apt-get install -y \
    netcat-traditional \
    hping3 \
    tcpdump \
    nmap \
    iproute2 \
    iputils-ping \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 从builder阶段复制wheels
COPY --from=builder /build/wheels /wheels

# 安装Python包
RUN pip install --no-cache /wheels/*

# 复制应用代码
COPY . .

# 创建必要的目录并设置权限
RUN mkdir -p /usr/src/app/logs /usr/src/app/data /usr/src/app/scripts && \
    chmod -R 755 /usr/src/app/scripts && \
    chmod -R 777 /usr/src/app/logs /usr/src/app/data

# 复制启动脚本并设置权限
COPY scripts/start.sh /usr/src/app/scripts/
RUN chmod +x /usr/src/app/scripts/start.sh

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${FASTAPI_PORT:-8000}/health || exit 1

# 启动命令
CMD ["/usr/src/app/scripts/start.sh"]