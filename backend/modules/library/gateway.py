"""U4 Library — rerun search-gateway seam (INV-L2).

Re-running a saved search or a history entry MUST NOT call U2 directly: it re-enters the
gateway-fronted search contract (U6 ApiGatewayMiddleware → U2) so the cost guard and the
grounding-enforcement hook re-apply on every rerun (no backdoor — application-design "rerun
reconciliation"). U4 ships a deterministic ``StubSearchGateway`` placeholder; the real binding
to the U6 gateway swaps in behind the same ``SearchGatewayPort`` without touching U4 callers.
"""

from __future__ import annotations

from docsuri_shared.dtos import ResultMeta, SearchResultPageDTO, SearchResultSetDTO

from backend.modules.accounts.models import Principal


class StubSearchGateway:
    """Placeholder satisfying ``SearchGatewayPort``. Returns an empty, non-degraded result page —
    an honest stand-in until the U6 gateway is wired. Real implementations forward the query +
    principal through the gateway to U2."""

    async def search(self, query: str, principal: Principal) -> SearchResultSetDTO:
        page = SearchResultPageDTO(
            cards=[],
            meta=ResultMeta(resultCount=0, degraded=False, degradationMode=None),
        )
        return SearchResultSetDTO(page)
