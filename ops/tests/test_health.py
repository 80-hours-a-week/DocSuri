from __future__ import annotations

from datetime import UTC, datetime, timedelta

from docsuri_ops.health import HealthCheckService


class StatsProvider:
    def __init__(self, timestamp: datetime, index_count: int = 3, expected_count: int = 3) -> None:
        self.timestamp = timestamp
        self.index_count = index_count
        self.expected_count = expected_count

    def get_index_stats(self) -> dict:
        return {
            "last_write_timestamp": self.timestamp,
            "index_count": self.index_count,
            "expected_index_count": self.expected_count,
        }


def test_shallow_health_is_healthy() -> None:
    service = HealthCheckService()

    assert service.shallow_check().status == "healthy"


def test_deep_health_detects_stale_index_stats() -> None:
    stale_timestamp = datetime.now(UTC) - timedelta(days=2)
    service = HealthCheckService(index_stats_provider=StatsProvider(stale_timestamp))

    status = service.deep_check()

    assert status.status == "degraded"
    assert status.stale
    assert status.dependencies["indexStats"] == "degraded"


def test_deep_health_detects_dependency_down() -> None:
    service = HealthCheckService(dependencies={"eventStore": lambda: False})

    status = service.deep_check()

    assert status.status == "unhealthy"
    assert status.dependencies["eventStore"] == "unhealthy"
