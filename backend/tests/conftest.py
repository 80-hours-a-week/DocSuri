from __future__ import annotations

import pytest

from docsuri.u0.adapters import build_u0
from docsuri.u0.config import load_settings


class FakeClock:
    """시간 주입용 — U0 §6 'set → 25h 후 miss' 시뮬레이션."""

    def __init__(self, now: float = 1_000_000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture()
def fake_clock() -> FakeClock:
    return FakeClock()


@pytest.fixture(scope="session")
def u0():
    """mock 모드 U0 포트 묶음 — 자격 증명 불필요."""
    settings = load_settings()
    assert settings.adapter_mode == "mock", "테스트는 mock 모드 전제"
    return build_u0(settings)
