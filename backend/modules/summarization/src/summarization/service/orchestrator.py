"""SummarizationOrchestrationService — on-demand pipeline (business-logic-model.md §2).

  cacheLookup → costGate → selectSource → refine → loadGlossary → routeLength →
  generate(buffer) → groundingValidate(1 retry) → assemble → writeThrough → emitTelemetry

Three-tier degradation kept distinct (nfr-design §1.3):
  • cost   → CostDegradedDTO  (U6 get_budget_state, single authority — never re-judged)
  • outage → AbstainDTO       (LlmUnavailable after one retry; Bedrock circuit)
  • source → abstract fallback / SourceUnavailableDTO

Streaming (Q5/BR-S8) is buffer-validate-then-render: the structured draft is validated as
a whole before exposure (no ungrounded token leaks, FR-5). Progressive client render is an
API/presentation concern; the domain returns a complete, validated result.
"""

from __future__ import annotations

from docsuri_shared.ports import CostGuardCircuitBreaker, ObservabilityHub

from ..domain.assembler import ResultAssembler
from ..domain.cache_key import build_cache_key
from ..domain.glossary import GlossaryResolver
from ..domain.grounding import GroundingValidator
from ..domain.length_router import LengthRoute, LengthRouter
from ..domain.models import (
    AbstainDTO,
    CostDegradedDTO,
    GroundingInput,
    RequestContext,
    SourceUnavailableDTO,
    SummaryRequest,
    SummaryResponse,
    Task,
)
from ..domain.refiner import InputRefiner
from ..domain.source_selector import SourceSelector
from ..ports.ports import LlmGatewayPort, LlmUnavailable, SummaryStorePort


def _is_cost_degraded(budget) -> bool:
    """Any non-normal cost degrade or an open circuit gates LLM spend (BR-S13)."""
    mode = str(getattr(budget, "degrade_mode", "normal") or "normal").lower().replace("_", "-")
    circuit = str(getattr(budget, "circuit_state", "closed") or "closed").lower()
    return mode not in ("normal", "none") or circuit == "open"


class SummarizationOrchestrationService:
    def __init__(
        self,
        *,
        store: SummaryStorePort,
        source_selector: SourceSelector,
        refiner: InputRefiner,
        glossary_resolver: GlossaryResolver,
        length_router: LengthRouter,
        llm: LlmGatewayPort,
        grounding: GroundingValidator,
        assembler: ResultAssembler,
        cost_guard: CostGuardCircuitBreaker,
        observability: ObservabilityHub,
        model_ver: str,
    ) -> None:
        self._store = store
        self._source = source_selector
        self._refiner = refiner
        self._glossary = glossary_resolver
        self._length = length_router
        self._llm = llm
        self._grounding = grounding
        self._assembler = assembler
        self._cost_guard = cost_guard
        self._obs = observability
        self._model_ver = model_ver

    def run(self, request: SummaryRequest, ctx: RequestContext) -> SummaryResponse:
        user_id = ctx.auth_session.user_id

        # 0. cache lookup (read-through) — HIT ends here (LLM 0 calls, §11).
        glossary_ver = self._glossary_version(user_id)
        key = build_cache_key(request, glossary_ver=glossary_ver, model_ver=self._model_ver)
        cached = self._store.get(key)
        if cached is not None:
            self._emit("u7.cache.hit", 1.0, request)
            return _CachedResult(cached)

        # 1. cost gate (U6 single authority) — BEFORE any LLM spend.
        if _is_cost_degraded(self._cost_guard.get_budget_state()):
            self._emit("u7.cost.degraded", 1.0, request)
            return CostDegradedDTO()

        # 2. source select (+ abstract fallback) — none → source unavailable.
        source = self._source.select(request)
        if source is None:
            return SourceUnavailableDTO(reason="no_full_text_or_abstract")

        # 3. refine (structure-aware) → 5. length route (shape; over-cap or map-reduce → abstain).
        refined = self._refiner.refine(source.raw)
        route = self._length.route(refined.token_count)
        if route == LengthRoute.OVER_CAP or route == LengthRoute.MAP_REDUCE:
            return AbstainDTO(reason="input_too_long")

        # 4. glossary
        glossary = self._glossary.resolve(user_id)

        # 6-7. generate (buffer) → grounding validate, with ONE retry (BR-S7).
        if request.task == Task.TRANSLATE:
            response = self._run_translate(request, source, glossary, key)
        else:
            response = self._run_summary(request, source, refined, glossary, key)
        return response

    # --- summary path --------------------------------------------------------
    def _run_summary(self, request, source, refined, glossary, key) -> SummaryResponse:
        for attempt in (1, 2):
            try:
                draft = self._llm.summarize(refined, request, glossary)
            except LlmUnavailable:
                if attempt == 2:
                    self._emit("u7.llm.unavailable", 1.0, request)
                    return AbstainDTO(reason="generation_unavailable")
                continue
            verdict = self._grounding.validate(GroundingInput(draft=draft, refined=refined))
            self._emit("u7.grounding", 1.0, request, verdict=verdict.outcome)
            if verdict.ok:
                result = self._assembler.assemble_summary(draft, source)
                self._store.put(key, result.to_dict())  # write-through
                self._emit("u7.summary.ok", 1.0, request)
                return result
            if attempt == 2:
                return AbstainDTO(reason="insufficient_grounding")
        return AbstainDTO(reason="insufficient_grounding")  # unreachable; satisfies type checker

    # --- translate path ------------------------------------------------------
    def _run_translate(self, request, source, glossary, key) -> SummaryResponse:
        for attempt in (1, 2):
            try:
                draft = self._llm.translate(source.raw, request, glossary)
            except LlmUnavailable:
                if attempt == 2:
                    return AbstainDTO(reason="generation_unavailable")
                continue
            if not draft.korean_text.strip():
                if attempt == 2:
                    return AbstainDTO(reason="empty_translation")
                continue
            result = self._assembler.assemble_translation(draft, glossary, source)
            self._store.put(key, result.to_dict())
            self._emit("u7.translate.ok", 1.0, request)
            return result
        return AbstainDTO(reason="empty_translation")

    # --- personal glossary (Q8 / §9.1) ---------------------------------------
    def list_glossary_terms(self, user_id: str) -> list[dict]:
        """The user's saved personal terms as ``{termFrom, termTo}`` (owner-scoped). Used to
        pre-fill the badge editor; exposes only the two display fields (no internal flags)."""
        return [
            {"termFrom": m.term_from, "termTo": m.term_to}
            for m in self._glossary.list_user_terms(user_id)
        ]

    def upsert_glossary_term(self, user_id: str, term_from: str, term_to: str) -> int:
        """Persist a personal term override; return the bumped ``glossary_ver`` (Phase 1:
        simple-noun, applied to translation via post-substitution). The version bump folds
        into ``build_cache_key``, invalidating the user's cached results so the next request
        reflects the new term."""
        return self._glossary.upsert_term(user_id, term_from, term_to)

    # --- full-text viewer (Q5=C) ---------------------------------------------
    def full_text(self, paper_id: str, version: int) -> str | None:
        """Normalized full text for the in-app viewer. None → unavailable. OA license
        gating is applied at the router (the source port has no license signal)."""
        return self._source.fetch_full_text(paper_id, version)

    # --- helpers -------------------------------------------------------------
    def _glossary_version(self, user_id: str) -> int:
        repo = getattr(self._glossary, "_repo", None)
        if repo is not None:
            try:
                return repo.get_glossary_version(user_id)
            except Exception:  # noqa: BLE001 — versioning failure → shared baseline
                return 0
        return 0

    def _emit(self, name: str, value: float, request, *, verdict: str | None = None) -> None:
        """Non-blocking telemetry → U6 ObservabilityHub. MUST NOT raise (off response path)."""
        try:
            tags = {"task": str(request.task)}
            if verdict is not None:
                tags["verdict"] = verdict
            self._obs.emit_metric(name, value, tags)
        except Exception:  # noqa: BLE001, S110 — telemetry is advisory, off the response path
            pass


class _CachedResult:
    """Thin wrapper so a cache HIT serializes the stored payload (cached=True) directly."""

    __slots__ = ("_payload",)

    def __init__(self, payload: dict) -> None:
        self._payload = dict(payload)
        self._payload["cached"] = True

    def to_dict(self) -> dict:
        return self._payload
