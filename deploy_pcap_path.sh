#!/bin/bash

# Quick PCAP Path Deployment Script
# Usage: ./deploy_pcap_path.sh [path]

echo "=== Quick PCAP Path Deployment Script ==="

# Default path
DEFAULT_PATH="/var/log/iotlab/pcaps"

# Get user input for the path
if [ -n "$1" ]; then
    PCAP_PATH="$1"
else
    read -p "Please enter the PCAP output directory [$DEFAULT_PATH]: " PCAP_PATH
    PCAP_PATH=${PCAP_PATH:-$DEFAULT_PATH}
fi

echo "Setting PCAP output directory to: $PCAP_PATH"

# Create directory
echo "Creating directory: $PCAP_PATH"
sudo mkdir -p "$PCAP_PATH"

# Set permissions
echo "Setting permissions..."
sudo chown $USER:$USER "$PCAP_PATH"
sudo chmod 755 "$PCAP_PATH"

# Set environment variable
echo "Configuring environment variable..."
echo "export PCAP_BASE_DIR=\"$PCAP_PATH\"" >> ~/.bashrc
echo "export PCAP_BASE_DIR=\"$PCAP_PATH\"" >> ~/.profile

# Apply immediately
export PCAP_BASE_DIR="$PCAP_PATH"

echo ""
echo "✅ PCAP path configuration complete!"
echo "📁 New path: $PCAP_PATH"
echo "🔧 Please restart the Celery worker for the changes to take effect"
echo ""
echo "Restart commands:"
echo "  Docker: docker-compose restart worker"
echo "  Direct: pkill -f 'celery.*worker' && celery -A worker.celery worker"
echo ""
echo "Verify configuration:"
echo "  cd project && PCAP_BASE_DIR='$PCAP_PATH' python3 config.py"
