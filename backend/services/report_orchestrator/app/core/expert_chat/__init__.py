"""
Expert chat orchestration helpers.

This package keeps heavy orchestration logic out of main.py while preserving
the existing atomic-agent runtime model.
"""

from .orchestration import (
    build_execution_stages,
    extract_specialist_response,
    format_shared_evidence_context,
)

__all__ = [
    "build_execution_stages",
    "extract_specialist_response",
    "format_shared_evidence_context",
]

