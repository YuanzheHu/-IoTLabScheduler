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
# install hping3, tcpdump, nmap
RUN apt-get update && apt-get install -y hping3 tcpdump nmap

# copy project
COPY . .

# create logs directory
RUN mkdir -p logs
RUN mkdir -p data