"""AE Math EDGE admission contract, derived from the AMOS practical workflow."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class MathEdgeHypothesis:
    """Research-only hypothesis; it contains no trade or broker instruction."""

    hypothesis_id: str
    source_refs: tuple[str, ...]
    mathematical_claim: str
    economic_rationale: str
    falsifiers: tuple[str, ...]
    code_ref: str
    unit_test_refs: tuple[str, ...]
    train_end: str
    oos_start: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "MathEdgeHypothesis":
        def nonempty_text(key: str) -> str:
            value = str(data.get(key, "")).strip()
            if not value:
                raise ValueError(f"{key} is required")
            return value

        def refs(key: str) -> tuple[str, ...]:
            value = data.get(key)
            if not isinstance(value, list) or not value or not all(str(x).strip() for x in value):
                raise ValueError(f"{key} must be a non-empty list")
            return tuple(str(x).strip() for x in value)

        hypothesis = cls(
            hypothesis_id=nonempty_text("hypothesis_id"),
            source_refs=refs("source_refs"),
            mathematical_claim=nonempty_text("mathematical_claim"),
            economic_rationale=nonempty_text("economic_rationale"),
            falsifiers=refs("falsifiers"),
            code_ref=nonempty_text("code_ref"),
            unit_test_refs=refs("unit_test_refs"),
            train_end=nonempty_text("train_end"),
            oos_start=nonempty_text("oos_start"),
        )
        if hypothesis.oos_start <= hypothesis.train_end:
            raise ValueError("oos_start must be after train_end")
        return hypothesis

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_math_evidence(payload: Mapping[str, object]) -> tuple[bool, str]:
    """Require separately reproducible OOS, WFO, and Monte Carlo evidence."""
    validation = payload.get("math_validation")
    if not isinstance(validation, Mapping):
        return False, "MATH_VALIDATION_EVIDENCE_REQUIRED"
    for gate in ("oos", "wfo", "monte_carlo"):
        record = validation.get(gate)
        if not isinstance(record, Mapping):
            return False, f"MATH_{gate.upper()}_EVIDENCE_REQUIRED"
        if record.get("status") != "PASS" or not record.get("artifact") or not record.get("run_id"):
            return False, f"MATH_{gate.upper()}_NOT_VERIFIED"
    return True, "MATH_EDGE_VALIDATION_COMPLETE"
