# pull official base image
FROM python:3.11-slim

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV TZ=Europe/London

# install dependencies
RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt

# install network tools for attack and diagnostics
# hping3: for network attacks
# tcpdump: for packet capture  
# nmap: for network scanning
# iproute2: provides 'ip' command for network interface management
# iputils-ping: provides 'ping' command for connectivity testing
RUN apt-get update && apt-get install -y \
    hping3 \
    tcpdump \
    nmap \
    iproute2 \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# copy project
COPY . .

# create logs directory
RUN mkdir -p logs
RUN mkdir -p data