"""
Primus adapters for Tactus protocols.

These adapters implement Tactus protocols to integrate the standalone
Tactus library with Primus's GraphQL-based infrastructure.
"""

from primus.cli.procedure.tactus_adapters.storage import PrimusStorageAdapter
from primus.cli.procedure.tactus_adapters.hitl import PrimusHITLAdapter
from primus.cli.procedure.tactus_adapters.chat import PrimusChatAdapter
from primus.cli.procedure.tactus_adapters.trace import PrimusTraceSink
from primus.cli.procedure.tactus_adapters.terminal_hitl import TerminalHITLAdapter
from primus.cli.procedure.tactus_adapters.external_children import (
    OptimizerExternalChildResolver,
)

__all__ = [
    'PrimusStorageAdapter',
    'PrimusHITLAdapter',
    'PrimusChatAdapter',
    'PrimusTraceSink',
    'TerminalHITLAdapter',
    'OptimizerExternalChildResolver',
]
