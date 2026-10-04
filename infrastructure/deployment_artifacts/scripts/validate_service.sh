#!/bin/bash
set -e

echo "Validating services are running..."

# Check if primus-command-worker service exists and validate it
if sudo systemctl list-unit-files | grep -q primus-command-worker; then
    if sudo systemctl is-active --quiet primus-command-worker; then
        echo "✓ primus-command-worker service is running"
    else
        echo "✗ primus-command-worker service is not running"
        exit 1
    fi
else
    echo "○ primus-command-worker service not found (staging environment)"
fi

# Check if fastapi service exists and validate it
if sudo systemctl list-unit-files | grep -q fastapi.service; then
    if sudo systemctl is-active --quiet fastapi; then
        echo "✓ fastapi service is running"
    else
        echo "✗ fastapi service is not running"
        exit 1
    fi
else
    echo "○ fastapi service not found (staging environment)"
fi

echo "Service validation completed successfully!"
