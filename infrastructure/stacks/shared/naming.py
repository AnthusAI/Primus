"""
Centralized naming utilities for Primus infrastructure resources.

Naming convention: primus-{service}-{environment}-{resource}
Examples:
  - primus-scoring-staging-queue
  - primus-scoring-production-dlq
  - primus-monitoring-staging-dashboard
"""

import hashlib


def get_resource_name(service: str, environment: str, resource: str) -> str:
    """
    Generate a standardized resource name.

    Args:
        service: Service name (e.g., 'scoring', 'monitoring')
        environment: Environment name ('staging' or 'production')
        resource: Resource type (e.g., 'queue', 'dlq', 'topic')

    Returns:
        Formatted resource name following Primus naming convention
    """
    return f"primus-{service}-{environment}-{resource}"


def get_sagemaker_endpoint_name(
    scorecard_key: str,
    score_key: str,
    deployment_type: str = 'serverless'
) -> str:
    """
    Generate stable SageMaker endpoint name (doesn't change with model updates).

    Pattern: primus-{scorecard_key}-{score_key}-{deployment_type}
    Example: primus-call-quality-compliance-check-serverless

    Args:
        scorecard_key: Normalized scorecard key (filesystem-safe)
        score_key: Normalized score key (filesystem-safe)
        deployment_type: Deployment type ('serverless' or 'realtime')

    Returns:
        Stable endpoint name for resource discovery
    """
    return f"primus-{scorecard_key}-{score_key}-{deployment_type}"


def get_sagemaker_model_name(
    scorecard_key: str,
    score_key: str,
    model_s3_uri: str
) -> str:
    """
    Generate versioned SageMaker model name (includes hash of model S3 URI).

    Pattern: primus-{scorecard_key}-{score_key}-{hash[:8]}
    Example: primus-call-quality-compliance-check-a1b2c3d4

    Args:
        scorecard_key: Normalized scorecard key (filesystem-safe)
        score_key: Normalized score key (filesystem-safe)
        model_s3_uri: S3 URI to model.tar.gz

    Returns:
        Versioned model name (changes when model S3 URI changes)
    """
    uri_hash = hashlib.sha256(model_s3_uri.encode()).hexdigest()[:8]
    return f"primus-{scorecard_key}-{score_key}-{uri_hash}"


def get_sagemaker_endpoint_config_name(
    scorecard_key: str,
    score_key: str,
    model_s3_uri: str
) -> str:
    """
    Generate versioned SageMaker endpoint config name (includes hash of model S3 URI).

    Pattern: primus-{scorecard_key}-{score_key}-config-{hash[:8]}
    Example: primus-call-quality-compliance-check-config-a1b2c3d4

    Args:
        scorecard_key: Normalized scorecard key (filesystem-safe)
        score_key: Normalized score key (filesystem-safe)
        model_s3_uri: S3 URI to model.tar.gz

    Returns:
        Versioned endpoint config name (changes when model S3 URI changes)
    """
    uri_hash = hashlib.sha256(model_s3_uri.encode()).hexdigest()[:8]
    return f"primus-{scorecard_key}-{score_key}-config-{uri_hash}"
