"""Fail-closed bridge from Vibe-Trading research proposals to AMOS tick research.

This module intentionally has no broker or live-order capability.
"""

from .contracts import CostModel, RawTick, StrategyProposal, ValidationResult
from .gateway import prepare_research_run
from .math_edge import MathEdgeHypothesis
from .pipeline import execute_research_pipeline

__all__ = [
    "CostModel", "RawTick", "StrategyProposal", "ValidationResult",
    "MathEdgeHypothesis", "prepare_research_run", "execute_research_pipeline",
]
