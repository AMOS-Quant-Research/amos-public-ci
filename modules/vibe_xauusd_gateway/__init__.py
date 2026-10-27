"""Fail-closed bridge from Vibe-Trading research proposals to AMOS tick research.

This module intentionally has no broker or live-order capability.
"""

from .contracts import CostModel, RawTick, StrategyProposal, ValidationResult
from .gateway import prepare_research_run

__all__ = ["CostModel", "RawTick", "StrategyProposal", "ValidationResult", "prepare_research_run"]
