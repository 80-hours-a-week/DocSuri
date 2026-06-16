"""BR-9 — ResultAssembler never emits an empty success page.

A grounded result with zero items (e.g. grounding passes but filters every candidate) must
become an AbstainDTO, in BOTH normal and degraded modes — enforced inside assemble itself,
not only by the upstream no-match check.
"""

from __future__ import annotations

from docsuri_shared.dtos import AbstainDTO

from discovery.domain.assembler import ResultAssembler
from discovery.domain.models import DegradeMode, GroundedResults

_assembler = ResultAssembler()


def test_empty_grounded_normal_is_abstain_not_empty_page() -> None:
    response = _assembler.assemble(GroundedResults(items=()), DegradeMode.NORMAL)
    assert isinstance(response.root, AbstainDTO)


def test_empty_grounded_degraded_is_abstain() -> None:
    response = _assembler.assemble(GroundedResults(items=()), DegradeMode.LEXICAL_ONLY)
    assert isinstance(response.root, AbstainDTO)
