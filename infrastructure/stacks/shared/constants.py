"""
Shared constants for Primus infrastructure.

This module contains constants that are used across multiple stacks.
"""

# ECR Repository Name Template (without environment suffix)
LAMBDA_SCORE_PROCESSOR_REPOSITORY_BASE = "primus/lambda/score-processor"
CONSOLE_WORKER_REPOSITORY_BASE = "primus-console-worker"

# AWS Region
DEFAULT_REGION = "us-west-2"
