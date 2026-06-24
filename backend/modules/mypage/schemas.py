"""U10 My Page — wire DTOs.

Re-exports the shared SSOT DTOs (``docsuri_shared.dtos``, generated from
``shared/dtos/mypage.schema.json``). U10 MUST NOT redefine them — forking the SSOT is exactly
the defect to avoid (mirrors U4's ``schemas.py`` convention).
"""

from __future__ import annotations

from docsuri_shared.dtos import SubscriptionDTO, SubscriptionPlan, SubscriptionStatusValue

__all__ = [
    "SubscriptionDTO",
    "SubscriptionPlan",
    "SubscriptionStatusValue",
]
