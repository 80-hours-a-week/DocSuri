from __future__ import annotations

import json
import logging
import time
from typing import Any

from docsuri_shared._generated.dtos.docmodel_schema import DocModel
from docsuri_shared._generated.dtos.evidence_schema import EvidenceItem, SourceRef

from .prompts import build_evidence_extraction_prompt

logger = logging.getLogger(__name__)

_MAX_RETRIES = 1
_MAX_TOKENS = 8192
_CB_FAILURE_THRESHOLD = 5
_CB_RECOVERY_TIMEOUT = 30.0


class LlmUnavailable(Exception):
    """Bedrock 호출 불가 — Orchestrator가 fail-closed로 처리(BR-EV-12)."""


class _LocalCircuitBreaker:
    def __init__(self) -> None:
        self._failures = 0
        self._open_until: float = 0.0

    def allow_request(self) -> bool:
        if self._open_until and time.monotonic() < self._open_until:
            return False
        return True

    def record_success(self) -> None:
        self._failures = 0
        self._open_until = 0.0

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= _CB_FAILURE_THRESHOLD:
            self._open_until = time.monotonic() + _CB_RECOVERY_TIMEOUT


class EvidenceExtractor:
    """LLM 호출 + INV-EV-3 날조 금지 강제 — DocModel 원문에 없는 statement 제거."""

    def __init__(
        self,
        *,
        model_id: str,
        region_name: str | None = None,
        client: Any | None = None,
        max_retries: int = _MAX_RETRIES,
    ) -> None:
        if client is None:
            import boto3
            from botocore.config import Config

            config = Config(
                connect_timeout=5.0,
                read_timeout=60.0,
                retries={'max_attempts': 1},
            )
            client = boto3.client('bedrock-runtime', region_name=region_name, config=config)
        self._client = client
        self._model_id = model_id
        self._max_retries = max_retries
        self._cb = _LocalCircuitBreaker()

    def extract(
        self,
        topic: str,
        doc_models: list[tuple[str, DocModel]],
    ) -> list[EvidenceItem]:
        """DocModel 블록 → EvidenceItem 목록.

        빈 배열이면 Orchestrator가 abstain 처리 (INV-EV-2).
        """
        if not doc_models:
            return []

        system, user = build_evidence_extraction_prompt(topic, doc_models)
        payload = self._invoke_json(system, user)
        raw_items: list[dict] = payload.get('items', [])

        paper_texts = _build_paper_texts(doc_models)
        return _filter_hallucinated(raw_items, paper_texts)

    def _invoke_json(self, system: str, user: str) -> dict:
        if not self._cb.allow_request():
            raise LlmUnavailable('EvidenceExtractor circuit breaker OPEN')

        body = {
            'anthropic_version': 'bedrock-2023-05-31',
            'max_tokens': _MAX_TOKENS,
            'system': system,
            'messages': [{'role': 'user', 'content': [{'type': 'text', 'text': user}]}],
        }
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            if attempt > 0:
                time.sleep(2 ** attempt * 0.5)
            try:
                text = self._stream_text(body)
                payload = _parse_json(text)
                self._cb.record_success()
                return payload
            except Exception as exc:
                last_exc = exc
        self._cb.record_failure()
        raise LlmUnavailable('EvidenceExtractor Bedrock call failed') from last_exc

    def _stream_text(self, body: dict) -> str:
        response = self._client.invoke_model_with_response_stream(
            modelId=self._model_id,
            body=json.dumps(body).encode('utf-8'),
            accept='application/json',
            contentType='application/json',
        )
        chunks: list[str] = []
        for event in response['body']:
            chunk = event.get('chunk', {})
            raw = chunk.get('bytes', b'')
            if raw:
                data = json.loads(raw)
                if data.get('type') == 'content_block_delta':
                    delta = data.get('delta', {})
                    if delta.get('type') == 'text_delta':
                        chunks.append(delta.get('text', ''))
        return ''.join(chunks)


def _parse_json(text: str) -> dict:
    text = text.strip()
    start = text.find('{')
    end = text.rfind('}')
    if start == -1 or end == -1:
        return {}
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {}


def _build_paper_texts(doc_models: list[tuple[str, DocModel]]) -> dict[str, str]:
    """paper_id → 전체 텍스트 맵 (INV-EV-3 quote 검증용)."""
    result: dict[str, str] = {}
    for paper_id, doc_model in doc_models:
        result[paper_id] = doc_model.fullText
    return result


def _filter_hallucinated(
    raw_items: list[dict],
    paper_texts: dict[str, str],
) -> list[EvidenceItem]:
    """INV-EV-3: quote가 원문에 없는 SourceRef 제거 후 유효한 EvidenceItem만 반환."""
    items: list[EvidenceItem] = []
    for raw in raw_items:
        statement = raw.get('statement', '').strip()
        if not statement:
            continue

        supporting = _validate_refs(raw.get('supporting', []), paper_texts)
        conflicting = _validate_refs(raw.get('conflicting', []), paper_texts)

        # supporting이 하나도 없으면 해당 item 제거(날조 위험)
        if not supporting:
            logger.warning('dropping EvidenceItem — no valid supporting refs: %.80s', statement)
            continue

        items.append(
            EvidenceItem(
                statement=statement,
                supporting=supporting,
                conflicting=conflicting,
            )
        )
    return items


def _validate_refs(
    raw_refs: list[dict],
    paper_texts: dict[str, str],
) -> list[SourceRef]:
    valid: list[SourceRef] = []
    for ref in raw_refs:
        paper_id = ref.get('paperId', '')
        record_ref = ref.get('recordRef', '')
        quote = ref.get('quote') or None

        if not paper_id or not record_ref:
            continue

        # INV-EV-3: quote가 있으면 원문 존재 여부 검증
        if quote:
            paper_text = paper_texts.get(paper_id, '')
            if quote not in paper_text:
                logger.warning(
                    'INV-EV-3 violation — quote not found in paper %s, dropping ref',
                    paper_id,
                )
                continue

        valid.append(
            SourceRef(
                paperId=paper_id,
                recordRef=record_ref,
                anchor=ref.get('anchor') or None,
                quote=quote,
            )
        )
    return valid
