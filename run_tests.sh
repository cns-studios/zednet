#!/bin/bash
# Run security tests with detailed output

set -e

echo "========================================"
echo "ZedNet Security Test Suite"
echo "========================================"
echo ""

# Activate venv if exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "Running Path Sanitization Tests..."
echo "===================================="
pytest tests/test_sanitization.py -v --tb=short --color=yes

echo ""
echo "Running General Security Tests..."
echo "=================================="
pytest tests/test_security.py -v --tb=short --color=yes

echo ""
echo "Running All Tests with Coverage..."
echo "==================================="
pytest tests/ -v --cov=core --cov=server --cov-report=term --cov-report=html

echo ""
echo "========================================"
echo "Security tests complete!"
echo "Coverage report: htmlcov/index.html"
echo "========================================"