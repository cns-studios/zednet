#!/bin/bash
# ZedNet Setup Script

set -e

echo "======================================"
echo "             ZedNet Setup"
echo "======================================"

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $PYTHON_VERSION"

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Set secure permissions
echo "Setting secure permissions..."
chmod 700 data/
chmod 700 data/keys/
chmod 600 data/logs/*.log 2>/dev/null || true

# Create legal directory
mkdir -p legal/
cp legal/*.md . 2>/dev/null || echo "⚠️  Add legal documents to legal/"

echo ""
echo "======================================"
echo "Setup complete!"
echo "======================================"
echo ""
echo "To start ZedNet:"
echo "  1. source venv/bin/activate"
echo "  2. python main.py"
echo ""
echo "⚠️  IMPORTANT: Use a VPN or Tor before starting!"
echo ""