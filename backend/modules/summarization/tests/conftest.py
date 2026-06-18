"""Pytest fixtures. Shared stubs/helpers live in ``tests.stubs`` (real-first: test-only)."""

from __future__ import annotations

import pytest

from summarization.domain.models import SummaryDraft
from tests.stubs import SAMPLE_PAPER, valid_draft


@pytest.fixture
def sample_paper() -> str:
    return SAMPLE_PAPER


@pytest.fixture(name="valid_draft")
def valid_draft_fixture() -> SummaryDraft:
    return valid_draft()
