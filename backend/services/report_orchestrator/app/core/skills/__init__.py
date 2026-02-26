"""
Skills package.

Provides dynamic, per-agent skill card selection for prompt minimization.
"""

from .service import build_skill_instruction_context, get_skill_service

__all__ = [
    "build_skill_instruction_context",
    "get_skill_service",
]

