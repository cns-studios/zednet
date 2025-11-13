#!/bin/bash
# Run all security tests

echo "Running ZedNet Security Test Suite"
echo "===================================="

# Activate venv
source venv/bin/activate

# Run tests with coverage
pytest tests/ \
    -v \
    --tb=short \
    --cov=core \
    --cov=server \
    --cov-report=html \
    --cov-report=term

echo ""
echo "Coverage report: htmlcov/index.html"