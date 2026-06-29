"""Grounding fidelity harness — run labeled cases through the U7 ``GroundingValidator`` and
classify each outcome against its expected label (QT-1).

Labels (a reviewer's verdict on the *summary*, independent of the gate):
  - ``faithful``   → the summary is grounded in the source; the gate SHOULD pass.
  - ``fabricated`` → the summary asserts content the source does not support; the gate MUST
                     abstain (a HARD violation: empty/truncated/schema-incomplete, or result
                     numbers mostly absent from the source).

The two error cells matter asymmetrically:
  - ``false_pass``    = fabricated but passed  → a fabrication LEAKED past the gate (worst).
  - ``false_abstain`` = faithful but abstained → over-abstention (a grounded summary withheld).
A recalibration target is born when a held-out set shows either cell is non-zero.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from ..domain.grounding import GroundingValidator
from ..domain.models import GroundingInput

ExpectedLabel = Literal["faithful", "fabricated"]
Classification = Literal["true_pass", "true_abstain", "false_pass", "false_abstain"]


class _Validator(Protocol):
    """Structural type so the harness can run against the real validator or a test fake."""

    def validate(self, gi: GroundingInput) -> object: ...  # returns an object with ``.outcome``


@dataclass(frozen=True, slots=True)
class GroundingEvalCase:
    """One labeled fidelity case. ``confident`` marks a label stable enough to assert on;
    ``confident=False`` cases are review/threshold probes whose label is still OP/team's call."""

    name: str
    gi: GroundingInput
    expected: ExpectedLabel
    rationale: str  # why this label — the human-review anchor
    confident: bool = False


@dataclass(frozen=True, slots=True)
class CaseResult:
    name: str
    expected: ExpectedLabel
    outcome: str  # "pass" | "abstain" (GroundingValidator.AnchorVerdict.outcome)
    classification: Classification

    @property
    def correct(self) -> bool:
        return self.classification in ("true_pass", "true_abstain")


@dataclass(frozen=True, slots=True)
class GroundingEvalReport:
    results: tuple[CaseResult, ...]

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def false_pass(self) -> int:
        """Fabricated cases that passed — fabrications that leaked past the gate (target: 0)."""
        return sum(1 for r in self.results if r.classification == "false_pass")

    @property
    def false_abstain(self) -> int:
        """Faithful cases that abstained — over-abstention (target: 0)."""
        return sum(1 for r in self.results if r.classification == "false_abstain")

    @property
    def correct(self) -> int:
        return sum(1 for r in self.results if r.correct)


def _classify(expected: ExpectedLabel, outcome: str) -> Classification:
    passed = outcome == "pass"
    if expected == "faithful":
        return "true_pass" if passed else "false_abstain"
    return "false_pass" if passed else "true_abstain"


def run_grounding_eval(
    cases: Sequence[GroundingEvalCase], *, validator: _Validator | None = None
) -> GroundingEvalReport:
    """Run each case through the validator and classify pass/abstain vs the expected label.

    The summary-domain analogue of ``run_eval_set`` (ports.md §2.1, summary slot). Pure and
    deterministic — no LLM, no I/O — so it is safe to run in CI as a regression on the gate.
    """
    gate = validator if validator is not None else GroundingValidator()
    results = tuple(
        CaseResult(
            name=case.name,
            expected=case.expected,
            outcome=(outcome := str(getattr(gate.validate(case.gi), "outcome", "abstain"))),
            classification=_classify(case.expected, outcome),
        )
        for case in cases
    )
    return GroundingEvalReport(results=results)
