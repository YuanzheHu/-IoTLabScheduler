# PCAP Path Configuration Guide

## Overview

The output path for PCAP files can now be quickly configured via an environment variable, without modifying any code.

## Quick Start

### 1. View Current Configuration
```bash
cd project
python3 config.py
```

### 2. Temporarily Modify Path (for testing)
```bash
# Set environment variable
export PCAP_BASE_DIR="/custom/path/pcaps"

# Verify configuration
cd project
PCAP_BASE_DIR="/custom/path/pcaps" python3 config.py
```

### 3. Permanently Modify Path (recommended)
```bash
# Use deployment script (recommended)
./deploy_pcap_path.sh /var/log/iotlab/pcaps

# Or manually set
echo 'export PCAP_BASE_DIR="/var/log/iotlab/pcaps"' >> ~/.bashrc
source ~/.bashrc
```

### 4. Restart Worker to Apply Configuration
```bash
# Docker method
docker-compose restart worker

# Direct run method
pkill -f "celery.*worker"
celery -A worker.celery worker --loglevel=INFO
```

## Common Path Examples

### System Log Directory (recommended for production)
```bash
export PCAP_BASE_DIR="/var/log/iotlab/pcaps"
```

### User Home Directory (recommended for development)
```bash
export PCAP_BASE_DIR="$HOME/pcaps"
```

### Mounted Storage Directory (recommended for high data volume scenarios)
```bash
export PCAP_BASE_DIR="/mnt/storage/pcaps"
```

### Application Data Directory (recommended for standard deployment)
```bash
export PCAP_BASE_DIR="/opt/iotlab/data/pcaps"
```

### Temporary Directory (recommended for testing environment)
```bash
export PCAP_BASE_DIR="/tmp/iotlab/pcaps"
```

## Deployment Script Usage

### Basic Usage
```bash
# Interactive path input
./deploy_pcap_path.sh

# Directly specify path
./deploy_pcap_path.sh /var/log/iotlab/pcaps
```

### Script Features
- ✅ Automatically create directories
- ✅ Set correct permissions
- ✅ Configure environment variables
- ✅ Provide restart guidance

## Verify Configuration

### 1. Check Environment Variable
```bash
echo $PCAP_BASE_DIR
```

### 2. Test Configuration File
```bash
cd project
python3 config.py
```

### 3. Run Test Experiment
Start a new experiment and check if PCAP files are saved to the new path.

## Troubleshooting

### Permission Issues
```bash
# Check directory permissions
ls -la /var/log/iotlab/pcaps

# Fix permissions
sudo chown -R $USER:$USER /var/log/iotlab/pcaps
sudo chmod -R 755 /var/log/iotlab/pcaps
```

### Path Does Not Exist
```bash
# Create directory
sudo mkdir -p /var/log/iotlab/pcaps

# Verify path
python3 -c "import os; print(os.path.exists('/var/log/iotlab/pcaps'))"
```

### Environment Variable Not Effective
```bash
# Check environment variable
env | grep PCAP

# Reload configuration
source ~/.bashrc

# Or re-login
```

## Important Notes

1. **Restart Worker**: Must restart Celery worker after modifying path
2. **Permission Settings**: Ensure application has write permission to new path
3. **Disk Space**: Ensure new path has sufficient disk space
4. **Existing Files**: Old PCAP files remain in original location, unaffected

## Advantages

- 🚀 **Quick Deployment**: One command to modify path
- 🔧 **Flexible Configuration**: Support for multiple deployment environments
- 📁 **Organized by MAC**: PCAP files organized by device MAC address
- 🔒 **Permission Security**: Automatically set correct file permissions
- 📋 **Operation Guidance**: Provide complete deployment and verification steps
