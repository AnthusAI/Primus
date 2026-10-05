"""Primus agent documentation knowledge base.

The :mod:`primus.documentation` package owns the runtime view of the
agent-facing documentation tree. Markdown files under
``documentation/agent/`` carry YAML frontmatter that this package parses
into a structured index used by :mod:`MCP.tools.tactus_runtime.execute`
to back ``primus.docs.list`` and ``primus.docs.get``.
"""

from primus.documentation.repository import (
    Document,
    DocumentationRepository,
    InvalidDocumentationKeyError,
    InvalidDocumentationFile,
    ListResult,
)

__all__ = [
    "Document",
    "DocumentationRepository",
    "InvalidDocumentationKeyError",
    "InvalidDocumentationFile",
    "ListResult",
]
