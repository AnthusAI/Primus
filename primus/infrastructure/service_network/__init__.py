"""Client-neutral network foundations for long-lived Primus services."""

from .foundation import (
    ServiceNetworkFoundationStack,
    ServiceNetworkSettings,
    resolve_service_network_environment,
)

__all__ = [
    "ServiceNetworkFoundationStack",
    "ServiceNetworkSettings",
    "resolve_service_network_environment",
]
