from __future__ import annotations

import json
from io import BytesIO
from urllib.parse import urlparse
from uuid import uuid4

from fastapi.testclient import TestClient
from hypothesis import given
from hypothesis import strategies as st

from backend.app import create_app
from backend.config import Settings
from backend.modules.accounts.models import Principal, UserRole
from backend.modules.novelty import controller
from backend.modules.novelty.adapters import (
    SIMILAR_WORK_DETAIL_FIELDS,
    BedrockNoveltyLlmClient,
    ExternalApiSearchClient,
    NoveltyAdapters,
    NoveltyLlmDraft,
    RetrievalBundle,
    S3ManuscriptSimilarityClient,
    U2FullSearchCorpusRetrievalClient,
    build_llm_adapter,
)
from backend.modules.novelty.models import (
    ArtifactKind,
    ArtifactValidationError,
    EvidenceStatus,
    ExportApprovalError,
    JobState,
    NoveltyJobRequest,
)
from backend.modules.novelty.repository import InMemoryNoveltyRepository
from backend.modules.novelty.security import is_safe_external_url, sanitize_external_query
from backend.modules.novelty.service import NoveltyService
from backend.modules.novelty.streaming import encode_sse
from backend.modules.novelty.validators import normalize_source_key, validate_artifact_payload
from backend.modules.novelty.worker import process_job, run_worker


def _principal(user_id: str | None = None) -> Principal:
    return Principal(user_id=user_id or str(uuid4()), role=UserRole.USER)


def _service_job(repo: InMemoryNoveltyRepository, owner_id: str | None = None):
    owner_id = owner_id or str(uuid4())
    service = NoveltyService(repo)
    created = service.create_job(
        owner_id,
        NoveltyJobRequest(inputType="natural_language", topic="privacy preserving RAG"),
    )
    return service, owner_id, created.jobId


def _client(monkeypatch, principal: Principal | None = None, repo=None) -> TestClient:
    monkeypatch.setenv("NOVELTY_AGENT_ENABLED", "true")
    app = create_app(Settings(env="test", database_url="sqlite://"))
    app.dependency_overrides[controller.get_principal] = lambda: principal or _principal()
    if repo is not None:
        app.dependency_overrides[controller.get_repo] = lambda: repo
    return TestClient(app)


@given(st.text(alphabet=st.characters(min_codepoint=32, max_codepoint=126), min_size=1))
def test_source_key_normalization_is_stable(raw: str) -> None:
    normalized_once = normalize_source_key(" DOI ", raw)
    normalized_twice = normalize_source_key("doi", " ".join(raw.split()))

    assert normalized_once == normalized_twice


def test_supported_artifact_requires_source_refs() -> None:
    try:
        validate_artifact_payload(
            ArtifactKind.NOVELTY_CANDIDATES,
            {"items": [{"evidenceStatus": "supported", "title": "claim"}]},
        )
    except ArtifactValidationError:
        pass
    else:  # pragma: no cover - failure path clarity
        raise AssertionError("supported novelty output must carry sourceRefs")


def test_owner_isolation_blocks_cross_owner_reads() -> None:
    repo = InMemoryNoveltyRepository()
    _, owner_a, job_id = _service_job(repo)
    owner_b = str(uuid4())

    assert repo.get_job(owner_a, job_id).jobId == job_id
    try:
        repo.get_job(owner_b, job_id)
    except KeyError:
        pass
    else:  # pragma: no cover - failure path clarity
        raise AssertionError("cross-owner job read should fail closed")


def test_service_rejects_unbound_manuscript_object_key() -> None:
    repo = InMemoryNoveltyRepository()
    service = NoveltyService(repo)

    try:
        service.create_job(
            "u1",
            NoveltyJobRequest(
                inputType="manuscript",
                topic="owner scoped manuscript",
                manuscript={
                    "fileName": "draft.md",
                    "contentType": "text/markdown",
                    "objectKey": "novelty/u2/other-job/draft.md",
                },
            ),
        )
    except ValueError as exc:
        assert "owner and job" in str(exc)
    else:  # pragma: no cover - failure path clarity
        raise AssertionError("cross-owner manuscript objectKey should be rejected")

    assert repo.list_jobs("u1") == []


def test_state_transition_guard_rejects_backtracking() -> None:
    repo = InMemoryNoveltyRepository()
    service, owner_id, job_id = _service_job(repo)

    service.advance_state(owner_id, job_id, JobState.RETRIEVING_CORPUS, "retrieving")
    try:
        service.advance_state(owner_id, job_id, JobState.QUEUED, "backtrack")
    except Exception as exc:
        assert "invalid transition" in str(exc)
    else:  # pragma: no cover - failure path clarity
        raise AssertionError("backtracking should be rejected")


def test_notion_export_requires_preview_then_approval() -> None:
    repo = InMemoryNoveltyRepository()
    service, owner_id, job_id = _service_job(repo)

    try:
        service.complete_export(owner_id, job_id, "page-1")
    except ExportApprovalError:
        pass
    else:  # pragma: no cover - failure path clarity
        raise AssertionError("export should not complete before approval")

    service.preview_export(owner_id, job_id)
    service.approve_export(owner_id, job_id, approved=True)
    export = service.complete_export(owner_id, job_id, "page-1")

    assert export.notionPageId == "page-1"
    assert export.status == "exported"


def test_external_query_and_url_guards() -> None:
    assert sanitize_external_query("  hello\nworld  ") == "hello world"
    assert is_safe_external_url("https://github.com/openai/codex") is True
    assert is_safe_external_url("http://github.com/openai/codex") is False
    assert is_safe_external_url("https://127.0.0.1/admin") is False
    assert is_safe_external_url("https://8.8.8.8/dns-query") is False
    assert is_safe_external_url("https://github.com.evil.example/x") is False
    assert is_safe_external_url("https://news.google.com/search?q=rag") is False
    assert is_safe_external_url("https://zenodo.org/records/123") is True


def test_worker_processes_minimal_job_to_completion() -> None:
    repo = InMemoryNoveltyRepository()
    _, owner_id, job_id = _service_job(repo)

    process_job(repo, owner_id, job_id)

    result = NoveltyService(repo).result(owner_id, job_id)
    assert result.job.state is JobState.DEGRADED
    assert {artifact.kind for artifact in result.artifacts} >= {
        ArtifactKind.EVIDENCE,
        ArtifactKind.EXPERIMENT_PLAN,
    }


def test_u2_corpus_adapter_maps_full_search_cards_to_source_refs() -> None:
    from discovery.mocks import build_mock_orchestrator

    bundle = build_mock_orchestrator()
    result = U2FullSearchCorpusRetrievalClient(
        bundle.orchestrator,
        bundle.grounding_hook,
    ).full_search("u1", "diffusion protein structure")

    assert result.evidenceStatus is EvidenceStatus.SUPPORTED
    assert result.items
    assert result.items[0]["sourceRefs"][0]["url"].startswith("https://")


def test_similarity_adapter_reads_text_manuscript_and_queries_corpus() -> None:
    class FakeS3:
        def get_object(self, **kwargs):
            assert kwargs["Bucket"] == "papers"
            assert kwargs["Key"] == "novelty/u1/job/draft.txt"
            return {
                "Body": BytesIO(
                    b"This manuscript presents a robust framework for privacy preserving "
                    b"retrieval augmented generation evaluation across domain specific "
                    b"scientific workflows with repeated evidence checking. "
                )
            }

    class FakeCorpus:
        def full_search(self, owner_id: str, query: str) -> RetrievalBundle:
            assert owner_id == "u1"
            assert "privacy preserving" in query
            return RetrievalBundle(
                items=[
                    {
                        "title": "Privacy Preserving RAG",
                        "sourceRefs": [
                            {
                                "type": "url",
                                "identifier": "2401.00001",
                                "url": "https://arxiv.org/abs/2401.00001",
                            }
                        ],
                    }
                ],
                evidenceStatus=EvidenceStatus.SUPPORTED,
            )

    result = S3ManuscriptSimilarityClient(
        bucket="papers",
        prefix="novelty/",
        client=FakeS3(),
        corpus=FakeCorpus(),
    ).check(
        "u1",
        {
            "objectKey": "novelty/u1/job/draft.txt",
            "contentType": "text/plain",
            "jobId": "job",
        },
    )

    assert result.evidenceStatus is EvidenceStatus.SUPPORTED
    assert any(item["riskType"] == "sentence_similarity" for item in result.items)
    parsed_url = urlparse(result.items[-1]["sourceRefs"][0]["url"])
    assert parsed_url.scheme == "https"
    assert parsed_url.hostname == "arxiv.org"


def test_similarity_adapter_rejects_cross_owner_object_key() -> None:
    result = S3ManuscriptSimilarityClient(
        bucket="papers",
        prefix="novelty/",
        client=object(),
        corpus=object(),
    ).check(
        "u1",
        {
            "objectKey": "novelty/u2/job/draft.txt",
            "contentType": "text/plain",
        },
    )

    assert result.degradedReason == "manuscript objectKey is outside owner prefix"


def test_similarity_adapter_rejects_cross_job_object_key() -> None:
    result = S3ManuscriptSimilarityClient(
        bucket="papers",
        prefix="novelty/",
        client=object(),
        corpus=object(),
    ).check(
        "u1",
        {
            "objectKey": "novelty/u1/other-job/draft.txt",
            "contentType": "text/plain",
            "jobId": "job",
        },
    )

    assert result.degradedReason == "manuscript objectKey is outside job prefix"


def test_external_adapter_queries_public_api_sources() -> None:
    class Response:
        status_code = 200

        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

        def raise_for_status(self) -> None:
            return None

    class FakeHttp:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict]] = []

        def get(self, url: str, *, params: dict, headers: dict):
            self.calls.append((url, params))
            host = urlparse(url).hostname
            if host == "api.github.com":
                return Response(
                    {
                        "items": [
                            {
                                "full_name": "docsuri/novelty-baseline",
                                "html_url": "https://github.com/docsuri/novelty-baseline",
                                "description": "Novelty baseline",
                                "updated_at": "2026-07-01T00:00:00Z",
                                "stargazers_count": 7,
                                "language": "Python",
                                "license": {"spdx_id": "MIT"},
                            }
                        ]
                    }
                )
            if host == "huggingface.co":
                return Response(
                    [
                        {
                            "id": "docsuri/rag-eval",
                            "tags": ["rag", "evaluation"],
                            "downloads": 3,
                            "likes": 2,
                        }
                    ]
                )
            if host == "zenodo.org":
                return Response(
                    {
                        "hits": {
                            "hits": [
                                {
                                    "id": "123",
                                    "doi": "10.5281/zenodo.123",
                                    "links": {"html": "https://zenodo.org/records/123"},
                                    "metadata": {
                                        "title": "RAG Evaluation Dataset",
                                        "description": "<p>Dataset for RAG evaluation.</p>",
                                        "publication_date": "2026-06-30",
                                        "keywords": ["rag"],
                                    },
                                }
                            ]
                        }
                    }
                )
            raise AssertionError(f"unexpected external API call: {url}")

    http = FakeHttp()
    result = ExternalApiSearchClient(http).search("privacy preserving RAG")

    assert result.evidenceStatus is EvidenceStatus.SUPPORTED
    assert {url for url, _ in http.calls} == {
        "https://api.github.com/search/repositories",
        "https://huggingface.co/api/datasets",
        "https://zenodo.org/api/records",
    }
    assert {item["sourceType"] for item in result.items} == {"github_repo", "dataset"}
    assert all(item["sourceRefs"] for item in result.items)


def test_bedrock_llm_adapter_maps_source_ref_indexes_only() -> None:
    class FakeBedrock:
        def invoke_model_with_response_stream(self, **kwargs):
            body = json.loads(kwargs["body"].decode("utf-8"))
            assert body["anthropic_version"] == "bedrock-2023-05-31"
            payload = {
                "similarWorks": [
                    {
                        "title": "Prior RAG benchmark",
                        "summary": "Grounded baseline.",
                        "sourceRefIndexes": [0],
                        "url": "https://invented.example/not-used",
                    }
                ],
                "noveltyCandidates": [
                    {
                        "title": "Freshness-aware evaluation",
                        "rationale": "Compare recent dataset evidence against corpus baselines.",
                        "sourceRefIndexes": [1],
                    }
                ],
                "experimentPlan": {
                    "researchQuestion": "How can RAG novelty be evaluated?",
                    "noveltyAngle": "Evaluate freshness against grounded baselines.",
                    "hypotheses": ["Freshness signals improve differentiation."],
                    "baselines": ["Prior RAG benchmark"],
                    "procedure": ["Compare against corpus and dataset baselines."],
                    "datasets": ["RAG Evaluation Dataset"],
                    "metrics": ["baseline delta"],
                    "resources": ["Public dataset and evaluation script"],
                    "risks": ["dataset mismatch"],
                    "sourceRefIndexes": [1],
                },
            }
            text = json.dumps(payload)
            return {
                "body": [
                    {
                        "chunk": {
                            "bytes": json.dumps(
                                {
                                    "type": "content_block_delta",
                                    "delta": {
                                        "type": "text_delta",
                                        "text": text[: len(text) // 2],
                                    },
                                }
                            ).encode("utf-8")
                        }
                    },
                    {
                        "chunk": {
                            "bytes": json.dumps(
                                {
                                    "type": "content_block_delta",
                                    "delta": {
                                        "type": "text_delta",
                                        "text": text[len(text) // 2 :],
                                    },
                                }
                            ).encode("utf-8")
                        }
                    },
                    {
                        "chunk": {
                            "bytes": json.dumps(
                                {"type": "message_delta", "delta": {"stop_reason": "end_turn"}}
                            ).encode("utf-8")
                        }
                    },
                ]
            }

    corpus_ref = {
        "type": "url",
        "identifier": "2401.00001",
        "title": "Prior RAG benchmark",
        "url": "https://arxiv.org/abs/2401.00001",
    }
    dataset_ref = {
        "type": "url",
        "identifier": "10.5281/zenodo.123",
        "title": "RAG Evaluation Dataset",
        "url": "https://zenodo.org/records/123",
    }

    draft = BedrockNoveltyLlmClient(
        model_id="global.anthropic.claude-sonnet-4-6",
        client=FakeBedrock(),
    ).draft(
        topic="RAG novelty evaluation",
        corpus=RetrievalBundle(items=[{"title": "Prior", "sourceRefs": [corpus_ref]}]),
        external=RetrievalBundle(items=[{"title": "Dataset", "sourceRefs": [dataset_ref]}]),
    )

    assert draft.degradedReason is None
    assert draft.similarWorks["items"][0]["sourceRefs"] == [corpus_ref]
    assert draft.noveltyCandidates["items"][0]["sourceRefs"] == [dataset_ref]
    assert draft.experimentPlan["metrics"] == ["baseline delta"]
    assert draft.experimentPlan["sourceRefs"] == [dataset_ref]
    assert "Novelty score" not in draft.experimentPlan["metrics"]


def test_build_llm_adapter_uses_long_stream_read_timeout(monkeypatch) -> None:
    import boto3

    captured = {}

    def fake_client(service_name, *, region_name, config):
        captured["service_name"] = service_name
        captured["region_name"] = region_name
        captured["config"] = config
        return object()

    monkeypatch.setattr(boto3, "client", fake_client)
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-northeast-2")

    build_llm_adapter()

    assert captured["service_name"] == "bedrock-runtime"
    assert captured["region_name"] == "ap-northeast-2"
    assert captured["config"].read_timeout == 300.0


def test_bedrock_llm_adapter_maps_similar_work_detail_columns() -> None:
    captured_bodies: list[dict] = []

    class FakeBedrock:
        def invoke_model_with_response_stream(self, **kwargs):
            captured_bodies.append(json.loads(kwargs["body"].decode("utf-8")))
            payload = {
                "similarWorks": [
                    {
                        "title": "Prior RAG benchmark",
                        "summary": "Grounded baseline.",
                        "problem": {
                            "value": "  benchmark leakage  ",
                            "sourceRefIndexes": [0],
                        },
                        "method": {
                            "value": "contrastive evaluation",
                            "sourceRefIndexes": [0],
                        },
                        # B-001 회귀 — row 출처는 유효해도 칸 자체 근거가 비면 기권
                        "dataset": {"value": "RAG-Bench", "sourceRefIndexes": []},
                        "results": None,
                        # 구형 bare string — 필드별 근거 검증 불가 → 기권
                        "limitations": "small cohort",
                        # overlap 키 자체가 없음 → null(기권)로 정규화되어야 한다
                        "sourceRefIndexes": [0],
                    },
                    {
                        # 유효한 sourceRef가 없는 row — 상세 칸이 전부 기권되어야 한다
                        "title": "Ungrounded speculation",
                        "summary": "No valid refs.",
                        "problem": "invented problem",
                        # 칸 형식은 맞지만 refs가 무효(범위 밖) → 기권
                        "method": {"value": "invented method", "sourceRefIndexes": [99]},
                        "dataset": "invented dataset",
                        "results": "invented results",
                        "limitations": "invented limitations",
                        "overlap": "invented overlap",
                        "sourceRefIndexes": [99],
                    },
                ],
                "noveltyCandidates": [
                    {"title": "Freshness-aware evaluation", "sourceRefIndexes": [0]}
                ],
                "experimentPlan": {
                    "researchQuestion": "How can RAG novelty be evaluated?",
                    "noveltyAngle": "Evaluate freshness against grounded baselines.",
                    "hypotheses": ["Freshness signals improve differentiation."],
                    "baselines": ["Prior RAG benchmark"],
                    "procedure": ["Compare against corpus baselines."],
                    "datasets": ["RAG Evaluation Dataset"],
                    "metrics": ["baseline delta"],
                    "resources": ["Public dataset"],
                    "risks": ["dataset mismatch"],
                    "sourceRefIndexes": [0],
                },
            }
            return {
                "body": [
                    _stream_chunk(
                        {
                            "type": "content_block_delta",
                            "delta": {"type": "text_delta", "text": json.dumps(payload)},
                        }
                    )
                ]
            }

    corpus_ref = {
        "type": "url",
        "identifier": "2401.00001",
        "title": "Prior RAG benchmark",
        "url": "https://arxiv.org/abs/2401.00001",
    }

    draft = BedrockNoveltyLlmClient(
        model_id="global.anthropic.claude-sonnet-4-6",
        client=FakeBedrock(),
    ).draft(
        topic="RAG novelty evaluation",
        corpus=RetrievalBundle(items=[{"title": "Prior", "sourceRefs": [corpus_ref]}]),
        external=RetrievalBundle(items=[]),
    )

    item = draft.similarWorks["items"][0]
    assert item["problem"] == "benchmark leakage"
    assert item["method"] == "contrastive evaluation"
    # B-001 — row 출처가 있어도 칸 자신의 근거가 없으면 기권(null)
    assert item["dataset"] is None
    assert item["results"] is None
    assert item["limitations"] is None
    assert item["overlap"] is None
    # 리뷰 반영 — sourceRef 없는 row는 상세 칸 전부 기권(null): 근거 없는 값 노출 금지
    ungrounded = draft.similarWorks["items"][1]
    assert ungrounded["evidenceStatus"] == EvidenceStatus.ABSTAINED.value
    assert all(ungrounded[column] is None for column in SIMILAR_WORK_DETAIL_FIELDS)
    # 상세 칼럼은 유사 연구 표 전용 — novelty candidates에는 붙지 않는다
    assert "method" not in draft.noveltyCandidates["items"][0]
    # 프롬프트 계약과 추측 금지 지시가 실제 호출 본문에 실려 나간다
    user_text = captured_bodies[0]["messages"][0]["content"][0]["text"]
    assert '"limitations"' in user_text
    assert "never guess" in captured_bodies[0]["system"].lower()


def test_worker_completes_when_adapters_are_not_degraded() -> None:
    source_ref = {
        "type": "url",
        "identifier": "2401.00001",
        "url": "https://arxiv.org/abs/2401.00001",
    }

    class CleanCorpus:
        def full_search(self, owner_id: str, query: str) -> RetrievalBundle:
            return RetrievalBundle(items=[{"title": query, "sourceRefs": [source_ref]}])

    class CleanExternal:
        def search(self, query: str) -> RetrievalBundle:
            return RetrievalBundle(items=[{"title": query, "sourceRefs": [source_ref]}])

    class CleanLlm:
        def draft(self, *, topic, corpus, external) -> NoveltyLlmDraft:
            return NoveltyLlmDraft(
                similarWorks={
                    "items": [
                        {
                            "title": "Prior work",
                            "evidenceStatus": EvidenceStatus.SUPPORTED.value,
                            "sourceRefs": [source_ref],
                        }
                    ],
                    "evidenceStatus": EvidenceStatus.SUPPORTED.value,
                    "sourceRefs": [source_ref],
                },
                noveltyCandidates={
                    "items": [
                        {
                            "title": "Novel candidate",
                            "evidenceStatus": EvidenceStatus.SUPPORTED.value,
                            "sourceRefs": [source_ref],
                        }
                    ],
                    "evidenceStatus": EvidenceStatus.SUPPORTED.value,
                    "sourceRefs": [source_ref],
                },
                experimentPlan={
                    "researchQuestion": topic,
                    "noveltyAngle": "Evaluate against grounded prior work.",
                    "hypotheses": ["Grounded difference improves novelty."],
                    "baselines": ["Prior work"],
                    "procedure": ["Run baseline comparison."],
                    "datasets": ["RAG Evaluation Dataset"],
                    "metrics": ["baseline delta"],
                    "resources": ["Evaluation script"],
                    "risks": ["dataset mismatch"],
                    "evidenceStatus": EvidenceStatus.SUPPORTED.value,
                    "sourceRefs": [source_ref],
                },
            )

    repo = InMemoryNoveltyRepository()
    _, owner_id, job_id = _service_job(repo)

    process_job(
        repo,
        owner_id,
        job_id,
        adapters=NoveltyAdapters(
            corpus=CleanCorpus(),
            external=CleanExternal(),
            llm=CleanLlm(),
        ),
    )

    assert NoveltyService(repo).result(owner_id, job_id).job.state is JobState.COMPLETED


def test_worker_emits_step_detail_payloads() -> None:
    source_ref = {
        "type": "url",
        "identifier": "2401.00002",
        "url": "https://arxiv.org/abs/2401.00002",
    }

    class TwoItemCorpus:
        def full_search(self, owner_id: str, query: str) -> RetrievalBundle:
            return RetrievalBundle(
                items=[
                    {"title": "A", "sourceRefs": [source_ref]},
                    {"title": "B", "sourceRefs": [source_ref]},
                ],
                evidenceStatus=EvidenceStatus.SUPPORTED,
            )

    repo = InMemoryNoveltyRepository()
    _, owner_id, job_id = _service_job(repo)

    process_job(repo, owner_id, job_id, adapters=NoveltyAdapters(corpus=TwoItemCorpus()))

    payloads: dict[JobState, list[dict]] = {}
    for event in repo.list_events(owner_id, job_id):
        payloads.setdefault(event.state, []).append(event.payload)

    # US-NV7(#257) — 검색 단계는 시작(도구+쿼리)·완료(count) 이벤트, LLM 단계는 결과 수 동봉
    corpus_events = payloads[JobState.RETRIEVING_CORPUS]
    assert corpus_events[0] == {"source": "U2 full search", "query": "privacy preserving RAG"}
    assert corpus_events[-1]["count"] == 2
    external_events = payloads[JobState.SEARCHING_EXTERNAL]
    assert external_events[0]["query"] == "privacy preserving RAG"
    assert external_events[-1]["count"] == 0
    assert "reason" in external_events[-1]  # Noop external은 저하 사유를 실어 보낸다
    assert payloads[JobState.SUMMARIZING_PRIOR_WORK][0]["count"] == 0
    assert payloads[JobState.PLANNING_EXPERIMENT][0]["outputSummary"] == "privacy preserving RAG"


def test_worker_manuscript_path_records_similarity_risk_degradation() -> None:
    repo = InMemoryNoveltyRepository()
    service = NoveltyService(repo)
    owner_id = str(uuid4())
    created = service.create_job(
        owner_id,
        NoveltyJobRequest(
            inputType="manuscript",
            topic="novelty agent draft",
            manuscript={"fileName": "draft.md", "contentType": "text/markdown"},
        ),
    )

    process_job(repo, owner_id, created.jobId)

    result = service.result(owner_id, created.jobId)
    assert result.job.state is JobState.DEGRADED
    assert ArtifactKind.RISK_SIGNALS in {artifact.kind for artifact in result.artifacts}


def test_supported_adapter_without_source_refs_degrades_not_fails() -> None:
    class UnsupportedCorpus:
        def full_search(self, owner_id: str, query: str) -> RetrievalBundle:
            return RetrievalBundle(
                items=[{"title": query}],
                evidenceStatus=EvidenceStatus.SUPPORTED,
            )

    repo = InMemoryNoveltyRepository()
    _, owner_id, job_id = _service_job(repo)

    process_job(repo, owner_id, job_id, adapters=NoveltyAdapters(corpus=UnsupportedCorpus()))

    result = NoveltyService(repo).result(owner_id, job_id)
    assert result.job.state is JobState.DEGRADED
    assert "missing sourceRefs" in repo.list_events(owner_id, job_id)[-1].model_dump_json()


def test_worker_loop_acks_successful_message() -> None:
    class Message:
        def __init__(self, body):
            self.body = body

    repo = InMemoryNoveltyRepository()
    _, owner_id, job_id = _service_job(repo)
    message = Message({"ownerId": owner_id, "jobId": job_id})
    acked: list[Message] = []
    calls = 0

    def receive():
        nonlocal calls
        calls += 1
        return [message] if calls == 1 else []

    run_worker(
        repo_factory=lambda: repo,
        receive=receive,
        ack=acked.append,
        should_stop=lambda: calls > 1,
    )

    assert acked == [message]
    assert NoveltyService(repo).result(owner_id, job_id).job.state is JobState.DEGRADED


def test_worker_loop_acks_missing_job_message_as_stale() -> None:
    class CountingRepo(InMemoryNoveltyRepository):
        def __init__(self) -> None:
            super().__init__()
            self.commits = 0
            self.rollbacks = 0

        def commit(self) -> None:
            self.commits += 1

        def rollback(self) -> None:
            self.rollbacks += 1

    class Message:
        def __init__(self, body):
            self.body = body

    repo = CountingRepo()
    message = Message({"ownerId": "u1", "jobId": "missing"})
    acked: list[Message] = []
    calls = 0

    def receive():
        nonlocal calls
        calls += 1
        return [message] if calls == 1 else []

    run_worker(
        repo_factory=lambda: repo,
        receive=receive,
        ack=acked.append,
        should_stop=lambda: calls > 1,
    )

    assert acked == [message]
    assert repo.commits == 1
    assert repo.rollbacks == 0


def test_worker_loop_commits_and_acks_recorded_failure() -> None:
    class BrokenCorpus:
        def full_search(self, owner_id: str, query: str) -> RetrievalBundle:
            raise RuntimeError("corpus unavailable")

    class CountingRepo(InMemoryNoveltyRepository):
        def __init__(self) -> None:
            super().__init__()
            self.commits = 0
            self.rollbacks = 0

        def commit(self) -> None:
            self.commits += 1

        def rollback(self) -> None:
            self.rollbacks += 1

    class Message:
        def __init__(self, body):
            self.body = body

    repo = CountingRepo()
    _, owner_id, job_id = _service_job(repo)
    message = Message({"ownerId": owner_id, "jobId": job_id})
    acked: list[Message] = []
    calls = 0

    def receive():
        nonlocal calls
        calls += 1
        return [message] if calls == 1 else []

    run_worker(
        repo_factory=lambda: repo,
        receive=receive,
        ack=acked.append,
        should_stop=lambda: calls > 1,
        adapters=NoveltyAdapters(corpus=BrokenCorpus()),
    )

    result = NoveltyService(repo).result(owner_id, job_id)
    assert result.job.state is JobState.FAILED
    assert acked == [message]
    assert repo.commits == 1
    assert repo.rollbacks == 0


def test_sse_snapshot_encodes_progress_event() -> None:
    repo = InMemoryNoveltyRepository()
    _, owner_id, job_id = _service_job(repo)
    event = repo.list_events(owner_id, job_id)[0]

    encoded = encode_sse(event)

    assert encoded.startswith("event: progress\n")
    assert f'"jobId":"{job_id}"' in encoded


def test_api_create_status_and_cancel(monkeypatch) -> None:
    principal = _principal()
    repo = InMemoryNoveltyRepository()
    client = _client(monkeypatch, principal, repo)

    created = client.post(
        "/api/novelty/jobs",
        json={"inputType": "natural_language", "topic": "adaptive literature review agent"},
    )
    job_id = created.json()["jobId"]
    status = client.get(f"/api/novelty/jobs/{job_id}")
    cancelled = client.post(f"/api/novelty/jobs/{job_id}/cancel")

    assert created.status_code == 200
    assert status.json()["job"]["state"] == "degraded"
    assert cancelled.json()["state"] == "degraded"


def test_api_lists_jobs_and_persists_chat_messages(monkeypatch) -> None:
    principal = _principal()
    repo = InMemoryNoveltyRepository()
    client = _client(monkeypatch, principal, repo)

    created = client.post(
        "/api/novelty/jobs",
        json={"inputType": "natural_language", "topic": "adaptive literature review agent"},
    )
    job_id = created.json()["jobId"]
    added = client.post(
        f"/api/novelty/jobs/{job_id}/messages",
        json={"content": "compare against recent RAG evaluation papers"},
    )
    listed = client.get("/api/novelty/jobs")
    messages = client.get(f"/api/novelty/jobs/{job_id}/messages")

    assert created.status_code == 200
    assert added.status_code == 200
    assert listed.json()["jobs"][0]["jobId"] == job_id
    assert [item["content"] for item in messages.json()["messages"]] == [
        "adaptive literature review agent",
        "compare against recent RAG evaluation papers",
    ]


def test_api_rejects_unsupported_manuscript(monkeypatch) -> None:
    client = _client(monkeypatch, _principal(), InMemoryNoveltyRepository())

    resp = client.post(
        "/api/novelty/jobs",
        json={
            "inputType": "manuscript",
            "topic": "novelty agent",
            "manuscript": {
                "fileName": "draft.pdf",
                "contentType": "application/pdf",
            },
        },
    )

    assert resp.status_code == 422


def test_api_marks_job_failed_when_sqs_dispatch_fails(monkeypatch) -> None:
    class BrokenSqs:
        def send_message(self, **kwargs):
            del kwargs
            raise RuntimeError("sqs down")

    import boto3

    principal = _principal()
    repo = InMemoryNoveltyRepository()
    monkeypatch.setenv(
        "DOCSURI_NOVELTY_JOB_QUEUE_URL",
        "https://sqs.ap-northeast-2.amazonaws.com/123/docsuri-novelty-agent-job-queue",
    )
    monkeypatch.setattr(boto3, "client", lambda *_args, **_kwargs: BrokenSqs())
    client = _client(monkeypatch, principal, repo)

    resp = client.post(
        "/api/novelty/jobs",
        json={"inputType": "natural_language", "topic": "adaptive literature review agent"},
    )

    jobs = repo.list_jobs(principal.user_id)
    assert resp.status_code == 503
    assert jobs[0].state is JobState.FAILED


def test_api_rejects_blank_topic_before_job_is_created(monkeypatch) -> None:
    principal = _principal()
    repo = InMemoryNoveltyRepository()
    client = _client(monkeypatch, principal, repo)

    resp = client.post(
        "/api/novelty/jobs",
        json={"inputType": "natural_language", "topic": "   "},
    )

    assert resp.status_code == 422
    assert repo.list_jobs(principal.user_id) == []


def _stream_chunk(payload: dict) -> dict:
    return {"chunk": {"bytes": json.dumps(payload).encode("utf-8")}}


def test_bedrock_llm_client_invokes_at_cost_guard_warning() -> None:
    """NFR-C1 — agent hard gate는 warning(80%)에서는 Bedrock을 막지 않는다."""
    from docsuri_ops.cost_guard import CostGuardCircuitBreaker
    from docsuri_ops.domain.models import UsageEvent

    class _Invoke:
        called = False

        def invoke_model_with_response_stream(self, **kwargs):
            self.called = True
            return {
                "body": [
                    _stream_chunk(
                        {
                            "type": "content_block_delta",
                            "delta": {"type": "text_delta", "text": "{}"},
                        }
                    )
                ]
            }

    guard = CostGuardCircuitBreaker()
    guard.record_spend(UsageEvent(event_id="seed", amount_usd=1280.0, source="test"))
    ref = {"type": "url", "identifier": "2401.00001", "url": "https://arxiv.org/abs/2401.00001"}
    client = _Invoke()

    draft = BedrockNoveltyLlmClient(model_id="m", client=client, cost_guard=guard).draft(
        topic="t",
        corpus=RetrievalBundle(items=[{"title": "Prior", "sourceRefs": [ref]}]),
        external=RetrievalBundle(items=[]),
    )

    assert client.called is True
    assert draft.degradedReason is None


def test_bedrock_llm_client_degrades_without_invoke_when_cost_guard_critical() -> None:
    """NFR-C1 — critical cost guard 상태면 Bedrock 호출 없이 cost_degraded로 저하한다."""
    from docsuri_ops.cost_guard import CostGuardCircuitBreaker
    from docsuri_ops.domain.models import UsageEvent

    class _NoInvoke:
        def invoke_model_with_response_stream(self, **kwargs):
            raise AssertionError("LLM must not be invoked while the cost guard is gated")

    guard = CostGuardCircuitBreaker()
    guard.record_spend(UsageEvent(event_id="seed", amount_usd=1520.0, source="test"))
    ref = {"type": "url", "identifier": "2401.00001", "url": "https://arxiv.org/abs/2401.00001"}

    draft = BedrockNoveltyLlmClient(model_id="m", client=_NoInvoke(), cost_guard=guard).draft(
        topic="t",
        corpus=RetrievalBundle(items=[{"title": "Prior", "sourceRefs": [ref]}]),
        external=RetrievalBundle(items=[]),
    )

    assert draft.degradedReason == "cost_degraded"


def test_bedrock_llm_client_records_spend_from_usage() -> None:
    """NFR-C1 — 스트림 usage 이벤트의 토큰이 cost guard 지출로 기록된다."""
    from docsuri_ops.cost_guard import CostGuardCircuitBreaker

    class _FakeBedrock:
        def invoke_model_with_response_stream(self, **kwargs):
            return {
                "body": [
                    _stream_chunk(
                        {
                            "type": "message_start",
                            "message": {"usage": {"input_tokens": 1_000_000, "output_tokens": 1}},
                        }
                    ),
                    _stream_chunk(
                        {
                            "type": "content_block_delta",
                            "delta": {"type": "text_delta", "text": json.dumps({})},
                        }
                    ),
                    _stream_chunk(
                        {
                            "type": "message_delta",
                            "delta": {"stop_reason": "end_turn"},
                            "usage": {"output_tokens": 200_000},
                        }
                    ),
                ]
            }

    guard = CostGuardCircuitBreaker()
    ref = {"type": "url", "identifier": "2401.00001", "url": "https://arxiv.org/abs/2401.00001"}

    BedrockNoveltyLlmClient(model_id="m", client=_FakeBedrock(), cost_guard=guard).draft(
        topic="t",
        corpus=RetrievalBundle(items=[{"title": "Prior", "sourceRefs": [ref]}]),
        external=RetrievalBundle(items=[]),
    )

    # 기본 단가 $3/1M input + $15/1M output → 1M in + 0.2M out = $6
    assert abs(guard.get_budget_state().spend_usd - 6.0) < 1e-9


def test_api_reset_deletes_only_own_jobs(monkeypatch) -> None:
    """US-EV8(#272) 전체 초기화 — 소유 잡 전부 삭제(멱등), 타 사용자 잡 보존."""
    owner_a = _principal()
    owner_b = _principal()
    repo = InMemoryNoveltyRepository()
    client_a = _client(monkeypatch, owner_a, repo)
    client_b = _client(monkeypatch, owner_b, repo)

    client_a.post(
        "/api/novelty/jobs",
        json={"inputType": "natural_language", "topic": "reset target job one"},
    )
    client_a.post(
        "/api/novelty/jobs",
        json={"inputType": "natural_language", "topic": "reset target job two"},
    )
    kept = client_b.post(
        "/api/novelty/jobs",
        json={"inputType": "natural_language", "topic": "surviving job"},
    ).json()["jobId"]

    assert client_a.delete("/api/novelty/jobs").status_code == 204
    assert client_a.get("/api/novelty/jobs").json()["jobs"] == []
    assert client_b.get(f"/api/novelty/jobs/{kept}").status_code == 200
    # 멱등 — 이미 비어 있어도 204.
    assert client_a.delete("/api/novelty/jobs").status_code == 204


def test_sql_delete_job_and_reset_purge_child_rows() -> None:
    """US-EV8(#272)/SEC-14 — SQL 삭제는 이벤트·메시지 등 자식 행까지 제거(고아 금지 회귀)."""
    from backend.db import make_engine, make_session_factory
    from backend.modules.novelty.models import ChatMessageCreateRequest
    from backend.modules.novelty.repository import (
        ArtifactTable,
        Base,
        NotionExportTable,
        NoveltyJobTable,
        NoveltyMessageTable,
        ProgressEventTable,
        SqlNoveltyRepository,
    )

    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = make_session_factory(engine)()
    repo = SqlNoveltyRepository(session)
    service = NoveltyService(repo)
    owner = str(uuid4())

    first = service.create_job(
        owner, NoveltyJobRequest(inputType="natural_language", topic="cascade delete first")
    )
    service.create_job(
        owner, NoveltyJobRequest(inputType="natural_language", topic="cascade delete second")
    )
    service.record_event(repo.get_job(owner, first.jobId), "cascade seed event")
    service.add_message(owner, first.jobId, ChatMessageCreateRequest(content="history row"))
    assert session.query(ProgressEventTable).count() > 0
    assert session.query(NoveltyMessageTable).count() > 0

    service.delete_job(owner, first.jobId)

    assert session.query(ProgressEventTable).filter_by(job_id=first.jobId).count() == 0
    assert session.query(NoveltyMessageTable).filter_by(job_id=first.jobId).count() == 0

    service.delete_all_jobs(owner)

    for table in (
        NoveltyJobTable,
        ProgressEventTable,
        NoveltyMessageTable,
        ArtifactTable,
        NotionExportTable,
    ):
        assert session.query(table).count() == 0
