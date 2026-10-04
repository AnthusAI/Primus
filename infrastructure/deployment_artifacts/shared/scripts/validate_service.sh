#!/bin/bash

# Wait a bit for the service to fully start
sleep 5

# Check if the primus-command-worker service is running
if ! systemctl is-active --quiet primus-command-worker; then
    echo "Service primus-command-worker is not running"
    systemctl status primus-command-worker --no-pager
    exit 1
fi

echo "Service primus-command-worker is running successfully"
systemctl status primus-command-worker --no-pager
exit 0 
