"""PBT-02 — QueryValidator.normalize idempotent/roundtrip + FR-1/SEC-5 validation (BR-1/2)."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from discovery.domain.validator import MAX_QUERY_LEN, QueryValidator

_validator = QueryValidator()


@given(st.text())
def test_normalize_is_idempotent(raw: str) -> None:
    # PBT-02: normalize(normalize(x)) == normalize(x) — deterministic NFC + whitespace collapse.
    once = _validator.normalize(raw).text
    twice = _validator.normalize(once).text
    assert once == twice


@given(st.text())
def test_normalize_has_no_double_spaces_and_is_trimmed(raw: str) -> None:
    text = _validator.normalize(raw).text
    assert "  " not in text
    assert text == text.strip()


def test_empty_and_whitespace_rejected() -> None:
    assert _validator.validate("").ok is False
    assert _validator.validate("   ").ok is False


def test_control_chars_rejected() -> None:
    assert _validator.validate("hello\x00world").ok is False


def test_too_long_rejected() -> None:
    assert _validator.validate("a" * (MAX_QUERY_LEN + 1)).ok is False
    assert _validator.validate("a" * MAX_QUERY_LEN).ok is True


def test_korean_query_accepted() -> None:
    # cross-lingual (TD-3): Korean must NOT be rejected (no script allowlist, BR-2).
    result = _validator.validate("확산 모델 단백질 구조 예측")
    assert result.ok is True
