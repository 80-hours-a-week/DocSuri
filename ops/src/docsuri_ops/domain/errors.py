from __future__ import annotations


class OpsError(Exception):
    """Base U6 Reliability/Ops error."""


class ValidationError(OpsError):
    """Raised when an incoming event or payload is invalid."""


class PublisherUnavailableError(OpsError):
    """Raised when alert or incident publication cannot be completed."""


class HealthCheckError(OpsError):
    """Raised when health evaluation cannot complete safely."""
