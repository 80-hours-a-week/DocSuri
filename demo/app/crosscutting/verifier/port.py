"""Sentence-level entailment verifier port (AGENTS.md §4.3).

Sprint 1 stub: always returns SUPPORTED. Sprint 2 will plug in the real
Claude-Haiku 4-way classifier. Domain modules import this Protocol only —
they MUST NOT call any verifier implementation directly.

Also owns the SSRF allowlist (infra/CLAUDE.md §SSRF 화이트리스트) — all
outbound HTTP clients must target only domains listed in ALLOWED_DOMAINS.
"""

from __future__ import annotations

import ipaddress
import logging
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse

from app.domain.papers.models import VerifyLabel

logger = logging.getLogger(__name__)

# SSRF allowlist — only these hostnames may be contacted by infra HTTP clients.
ALLOWED_DOMAINS: frozenset[str] = frozenset({
    "export.arxiv.org",
    "api.semanticscholar.org",
    "api.openalex.org",
    "eutils.ncbi.nlm.nih.gov",  # PubMed
    "api.crossref.org",
})


class SSRFViolation(Exception):
    """Raised when an outbound URL fails the SSRF allowlist check."""


def verify_url(url: str) -> None:
    """Validate an outbound URL against the SSRF allowlist.

    Raises SSRFViolation for:
    - No parseable hostname
    - Private/loopback/link-local IP addresses (10.x, 172.16.x, 192.168.x, 127.x, ::1, ...)
    - Hostnames not in ALLOWED_DOMAINS

    Time: O(1)
    Edge: URL with no hostname (e.g. relative paths) → SSRFViolation immediately.
    """
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if not host:
        raise SSRFViolation(f"No hostname parseable from URL: {url!r}")
    try:
        addr = ipaddress.ip_address(host)
        if addr.is_private or addr.is_loopback or addr.is_link_local:
            logger.warning("ssrf.blocked internal_ip=%s url=%s", host, url)
            raise SSRFViolation(f"Internal IP address blocked: {host}")
    except ValueError:
        pass  # not an IP address — proceed to domain check
    if host not in ALLOWED_DOMAINS:
        logger.warning("ssrf.blocked domain=%s url=%s", host, url)
        raise SSRFViolation(f"Domain not in SSRF allowlist: {host!r}")


@dataclass
class VerifyResult:
    label: VerifyLabel
    confidence: float


class VerifierPort(Protocol):
    async def verify(self, sentence: str, evidence_spans: list[str]) -> VerifyResult:
        ...


class AlwaysSupportedVerifier:
    """Sprint 1 walking-skeleton stub. Replaced in Sprint 2."""

    async def verify(self, sentence: str, evidence_spans: list[str]) -> VerifyResult:
        # Trivial heuristic so the badge shows variation in the UI demo:
        # if no evidence given, label as NOT_FOUND so the UI can show all 4 colours.
        if not evidence_spans:
            return VerifyResult(label="NOT_FOUND", confidence=0.5)
        return VerifyResult(label="SUPPORTED", confidence=0.95)
