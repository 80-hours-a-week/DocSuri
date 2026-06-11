"""AWS 어댑터 — ADR §12 확정 매핑 (리전: ap-northeast-1 도쿄, ADR-D3·D9).

자격 증명이 없으면 import는 되지만 호출은 실패한다 — 통합 테스트는
자격 증명 존재 시에만 실행(skip)된다. 콘솔 검증 항목은 ADR §14 참조.
"""

from __future__ import annotations

import json
import time

import boto3
import httpx

from ..config import Settings
from ..cost_guard import CostStore
from ..http_policy import NetworkRetryExceeded, request_with_retry
from ..ports import (
    CachePort,
    Completion,
    KoTranslation,
    Lang,
    OneHopResult,
    PaperHit,
    Persona,
    SearchFilters,
    TelemetryEvent,
    Vector,
)

_PERSONA_SYSTEM = {
    # 상세 톤 설계는 U2의 책임 (U0 §8 — 도메인 로직 금지). 여기서는 포트 계약의
    # persona 파라미터를 모델에 전달하는 최소 힌트만 둔다.
    "pro": "한국어로 답하되 학술 전문 어휘는 원형을 보존하고 한국어 표현을 병기한다.",
    "undergrad": "학부 1~2학년이 이해할 쉬운 한국어로 답한다.",
}


class BedrockEmbedding:
    """EmbeddingPort — embed: Bedrock InvokeModel(Cohere v3) / search: S3 Vectors 직접 조회.

    KB Retrieve는 텍스트 질의 전용이라 search(vec, k, filters) 시그니처와 맞지 않아
    S3 Vectors QueryVectors를 직접 사용한다 (ADR-D2 결과 3에 문서화된 경로).
    인덱스 적재(청킹·동기화)는 KB가 관리한다.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._bedrock = boto3.client("bedrock-runtime", region_name=settings.aws_region)
        self._s3v = boto3.client("s3vectors", region_name=settings.aws_region)

    def embed(self, text: str, lang: Lang) -> Vector:
        body = json.dumps(
            {"texts": [text], "input_type": "search_query", "truncate": "END"}
        )
        response = self._bedrock.invoke_model(
            modelId=self._settings.bedrock_embed_model_id, body=body
        )
        payload = json.loads(response["body"].read())
        embeddings = payload["embeddings"]
        if isinstance(embeddings, dict):  # 일부 API 버전: {"float": [[...]]}
            embeddings = embeddings["float"]
        return embeddings[0]

    def search(
        self, vec: Vector, k: int, filters: SearchFilters | None = None
    ) -> list[PaperHit]:
        query: dict = {
            "vectorBucketName": self._settings.s3v_bucket,
            "indexName": self._settings.s3v_index,
            "queryVector": {"float32": vec},
            "topK": k,
            "returnMetadata": True,
            "returnDistance": True,
        }
        metadata_filter = _to_s3v_filter(filters)
        if metadata_filter:
            query["filter"] = metadata_filter
        response = self._s3v.query_vectors(**query)
        hits = []
        for item in response.get("vectors", []):
            meta = item.get("metadata", {})
            hits.append(
                PaperHit(
                    id=meta.get("id", item.get("key", "")),
                    title=meta.get("title", ""),
                    authors=meta.get("authors", []),
                    year=int(meta.get("year", 0)),
                    citations=int(meta.get("citations", 0)),
                    similarity=round(1.0 - float(item.get("distance", 0.0)), 4),
                    field_tags=meta.get("field_tags", []),
                    abstract_len=int(meta.get("abstract_len", 0)),
                )
            )
        return hits


def _to_s3v_filter(filters: SearchFilters | None) -> dict | None:
    if filters is None:
        return None
    clauses: list[dict] = []
    if filters.year_min is not None:
        clauses.append({"year": {"$gte": filters.year_min}})
    if filters.year_max is not None:
        clauses.append({"year": {"$lte": filters.year_max}})
    if filters.field_tags:
        clauses.append({"field_tags": {"$in": filters.field_tags}})
    if not clauses:
        return None
    return clauses[0] if len(clauses) == 1 else {"$and": clauses}


class BedrockLlm:
    """LlmPort 내부 어댑터 — Converse API, global CRIS (ADR-D4). 게이트웨이가 감싼다."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = boto3.client("bedrock-runtime", region_name=settings.aws_region)

    def complete(self, prompt: str, persona: Persona, budget_tokens: int) -> Completion:
        response = self._client.converse(
            modelId=self._settings.bedrock_llm_model_id,
            system=[{"text": _PERSONA_SYSTEM[persona]}],
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": budget_tokens},
        )
        usage = response["usage"]
        text = response["output"]["message"]["content"][0]["text"]
        return Completion(
            text=text,
            tokens_in=usage["inputTokens"],
            tokens_out=usage["outputTokens"],
            model_id=self._settings.bedrock_llm_model_id,
        )


class DynamoCache:
    """CachePort — DynamoDB TTL (ADR §12). TTL 삭제는 지연되므로 읽기 시 만료를 재검사."""

    def __init__(self, settings: Settings) -> None:
        self._table = boto3.resource("dynamodb", region_name=settings.aws_region).Table(
            settings.ddb_cache_table
        )

    def get(self, key: str) -> bytes | None:
        item = self._table.get_item(Key={"pk": key}).get("Item")
        if not item or float(item["expires_at"]) <= time.time():
            return None
        return bytes(item["value"])

    def set(self, key: str, value: bytes, ttl_s: int) -> None:
        self._table.put_item(
            Item={"pk": key, "value": value, "expires_at": int(time.time() + ttl_s)}
        )


class DynamoGlossary:
    """Glossary — DynamoDB 50행 (ADR §12, 시드는 scripts에서 1회 적재)."""

    def __init__(self, settings: Settings) -> None:
        self._table = boto3.resource("dynamodb", region_name=settings.aws_region).Table(
            settings.ddb_glossary_table
        )

    def lookup(self, term: str) -> KoTranslation | None:
        item = self._table.get_item(Key={"term": term.lower()}).get("Item")
        if not item:
            return None
        return KoTranslation(term=item["term"], ko=item["ko"], note=item.get("note", ""))


class DynamoCostStore(CostStore):
    """CostGuard 누적 저장소 — Lambda 무상태 보완 (ADR-D9 결과 4)."""

    def __init__(self, settings: Settings) -> None:
        self._table = boto3.resource("dynamodb", region_name=settings.aws_region).Table(
            settings.ddb_cost_table
        )

    def add(self, month_key: str, usd: float) -> float:
        from decimal import Decimal

        response = self._table.update_item(
            Key={"month": month_key},
            UpdateExpression="ADD usd :v",
            ExpressionAttributeValues={":v": Decimal(str(usd))},
            ReturnValues="UPDATED_NEW",
        )
        return float(response["Attributes"]["usd"])

    def total(self, month_key: str) -> float:
        item = self._table.get_item(Key={"month": month_key}).get("Item")
        return float(item["usd"]) if item else 0.0


class EmfTelemetry:
    """Telemetry — CloudWatch EMF (ADR-D10): stdout 1행 = 로그 + 메트릭 동시 산출.

    Lambda에서는 stdout이 CloudWatch Logs로 흘러가 EMF가 자동 인식된다.
    """

    NAMESPACE = "DocSuri/U0"

    def record(self, event: TelemetryEvent) -> None:
        payload = event.model_dump()
        payload["_aws"] = {
            "Timestamp": int(time.time() * 1000),
            "CloudWatchMetrics": [
                {
                    "Namespace": self.NAMESPACE,
                    "Dimensions": [["op"]],
                    "Metrics": [
                        {"Name": "latency_ms", "Unit": "Milliseconds"},
                        {"Name": "tokens_in", "Unit": "Count"},
                        {"Name": "tokens_out", "Unit": "Count"},
                    ],
                }
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, default=str))


class SemanticScholarCitation:
    """CitationApi — Semantic Scholar 1-hop + 24h 캐시 + 폴백 (R4 흡수, ADR §12).

    실패 시 빈 결과를 반환한다 — 빈 상태 안내는 UI(NFR-NET-03)의 몫.
    """

    BASE = "https://api.semanticscholar.org/graph/v1/paper"
    FIELDS = "title,year,citationCount,authors,externalIds"
    TTL_S = 24 * 3600
    LIMIT = 15  # U4 CitationView max_nodes=30 — 방향당 15

    def __init__(
        self, cache: CachePort, client: httpx.Client | None = None, api_key: str = ""
    ) -> None:
        self._cache = cache
        headers = {"User-Agent": "DocSuri/0.1 (academic paper assistant)"}
        if api_key:  # 코드 리뷰 M2 — 레이트 리밋 완화용 (DOCSURI_SS_API_KEY)
            headers["x-api-key"] = api_key
        self._client = client or httpx.Client(timeout=10.0, headers=headers)

    def one_hop(self, paper_id: str) -> OneHopResult:
        cache_key = f"cite:{paper_id}:v1"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return OneHopResult.model_validate_json(cached)
        try:
            outgoing = self._fetch(paper_id, "references", "citedPaper")
            incoming = self._fetch(paper_id, "citations", "citingPaper")
        except (NetworkRetryExceeded, httpx.HTTPError, KeyError):
            return OneHopResult(outgoing=[], incoming=[])  # R4 폴백 — 빈 상태
        result = OneHopResult(outgoing=outgoing, incoming=incoming)
        self._cache.set(cache_key, result.model_dump_json().encode(), self.TTL_S)
        return result

    def _fetch(self, paper_id: str, edge: str, node_key: str) -> list[PaperHit]:
        url = f"{self.BASE}/arXiv:{paper_id}/{edge}?fields={self.FIELDS}&limit={self.LIMIT}"
        response = request_with_retry(self._client, "GET", url)
        response.raise_for_status()
        hits = []
        for row in response.json().get("data", []):
            node = row.get(node_key) or {}
            arxiv_id = (node.get("externalIds") or {}).get("ArXiv", "")
            hits.append(
                PaperHit(
                    id=arxiv_id or node.get("paperId", ""),
                    title=node.get("title") or "",
                    authors=[a.get("name", "") for a in node.get("authors", [])],
                    year=node.get("year") or 0,
                    citations=node.get("citationCount") or 0,
                )
            )
        return hits


