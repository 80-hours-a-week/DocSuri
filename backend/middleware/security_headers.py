from __future__ import annotations

SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'; frame-ancestors 'self'",
    "Referrer-Policy": "no-referrer",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
}


def build_security_headers() -> dict[str, str]:
    return dict(SECURITY_HEADERS)


def apply_security_headers(response) -> None:
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
