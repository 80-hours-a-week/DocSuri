"""BedrockLlmGateway — real LLM adapter (TD-S3/S4), streaming Sonnet/Haiku.

task → model tier (BR-S5): summary=Sonnet, translate=Haiku. Uses Bedrock
``invoke_model_with_response_stream`` and buffers the token stream into a complete JSON
draft so the U7 grounding gate can validate the whole structured output before exposure
(Q5/BR-S8). Explicit timeout + ONE retry; persistent failure raises ``LlmUnavailable`` so
the orchestrator abstains (Q1/RES-9). No Production Mock — this is the single shipped impl.
"""

from __future__ import annotations

import json
from typing import Any

from ..domain.models import (
    Anchor,
    AnchorTarget,
    Glossary,
    RefinedSource,
    SummaryDraft,
    SummaryRequest,
    TranslationDraft,
)
from ..ports.ports import LlmUnavailable
from ..prompts import build_summary_prompt, build_translate_prompt


class BedrockLlmGateway:
    def __init__(
        self,
        *,
        summary_model_id: str,
        translate_model_id: str,
        region_name: str | None = None,
        client: Any | None = None,
        max_retries: int = 1,
    ) -> None:
        if client is None:
            import boto3  # lazy: only the `real` extra needs boto3

            client = boto3.client("bedrock-runtime", region_name=region_name)
        self._client = client
        self._summary_model = summary_model_id
        self._translate_model = translate_model_id
        self._max_retries = max_retries

    # --- public ports --------------------------------------------------------
    def summarize(
        self, refined: RefinedSource, request: SummaryRequest, glossary: Glossary
    ) -> SummaryDraft:
        system, user = build_summary_prompt(refined, request, glossary)
        payload = self._invoke_json(self._summary_model, system, user)
        return _to_summary_draft(payload)

    def translate(
        self, abstract: str, request: SummaryRequest, glossary: Glossary
    ) -> TranslationDraft:
        system, user = build_translate_prompt(abstract, request, glossary)
        payload = self._invoke_json(self._translate_model, system, user)
        return TranslationDraft(
            korean_text=str(payload.get("koreanText", "")),
            kept_terms=tuple(payload.get("keptTerms", [])),
        )

    # --- bedrock plumbing ----------------------------------------------------
    def _invoke_json(self, model_id: str, system: str, user: str) -> dict:
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2000,
            "system": system,
            "messages": [{"role": "user", "content": [{"type": "text", "text": user}]}],
        }
        last_exc: Exception | None = None
        for _ in range(self._max_retries + 1):
            try:
                text = self._stream_text(model_id, body)
                return _parse_json(text)
            except Exception as exc:  # noqa: BLE001 — any Bedrock/transport/parse error → retry/abstain
                last_exc = exc
        raise LlmUnavailable("Bedrock generation failed") from last_exc

    def _stream_text(self, model_id: str, body: dict) -> str:
        """Buffer the response stream into the full text (buffer-validate-stream, Q5)."""
        response = self._client.invoke_model_with_response_stream(
            modelId=model_id,
            body=json.dumps(body).encode("utf-8"),
            accept="application/json",
            contentType="application/json",
        )
        chunks: list[str] = []
        for event in response.get("body", []):
            raw = event.get("chunk", {}).get("bytes")
            if not raw:
                continue
            data = json.loads(raw.decode("utf-8"))
            if data.get("type") == "content_block_delta":
                chunks.append(data.get("delta", {}).get("text", ""))
        return "".join(chunks)


def _parse_json(text: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in model output")
    return json.loads(text[start : end + 1])


def _to_summary_draft(payload: dict) -> SummaryDraft:
    anchors = tuple(
        Anchor(
            field_name=str(a.get("field", "")),
            target=_anchor_target(a.get("target", "section")),
            span=str(a.get("span", "")),
            label=str(a.get("label", "")),
        )
        for a in payload.get("anchors", [])
    )
    repro = payload.get("reproducibility", {}) or {}
    return SummaryDraft(
        tldr=str(payload.get("tldr", "")),
        contributions=tuple(payload.get("contributions", [])),
        method=str(payload.get("method", "")),
        results=str(payload.get("results", "")),
        limitations=str(payload.get("limitations", "")),
        reproducibility={"code": str(repro.get("code", "")), "data": str(repro.get("data", ""))},
        anchors=anchors,
    )


def _anchor_target(value: str) -> AnchorTarget:
    try:
        return AnchorTarget(str(value).lower())
    except ValueError:
        return AnchorTarget.SECTION
