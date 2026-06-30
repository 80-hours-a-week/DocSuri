from __future__ import annotations

import json
import os
from typing import Any

from .adapters import NoveltyAdapters
from .models import TERMINAL_STATES, ArtifactKind, EvidenceStatus, InputType, JobState
from .repository import NoveltyRepository
from .service import NoveltyService


class InvalidWorkerPayload(ValueError):
    pass


def parse_sqs_payload(body: str | bytes | dict[str, Any]) -> tuple[str, str]:
    if isinstance(body, bytes):
        body = body.decode("utf-8")
    payload = json.loads(body) if isinstance(body, str) else body
    owner_id = payload.get("ownerId") or payload.get("owner_id")
    job_id = payload.get("jobId") or payload.get("job_id")
    if not owner_id or not job_id:
        raise InvalidWorkerPayload("ownerId and jobId are required")
    return str(owner_id), str(job_id)


def process_sqs_payload(
    repo: NoveltyRepository,
    body: str | bytes | dict[str, Any],
    *,
    adapters: NoveltyAdapters | None = None,
    observability=None,
) -> None:
    owner_id, job_id = parse_sqs_payload(body)
    process_job(repo, owner_id, job_id, adapters=adapters, observability=observability)


def process_job(
    repo: NoveltyRepository,
    owner_id: str,
    job_id: str,
    *,
    adapters: NoveltyAdapters | None = None,
    observability=None,
) -> None:
    adapters = adapters or NoveltyAdapters()
    service = NoveltyService(repo, observability)
    job = repo.get_job(owner_id, job_id)
    if job.cancelled or job.state in TERMINAL_STATES:
        return
    try:
        service.advance_state(owner_id, job_id, JobState.RETRIEVING_CORPUS, "Searching U2 corpus")
        corpus = adapters.corpus.full_search(owner_id, job.topic)
        service.save_artifact(
            owner_id,
            job_id,
            ArtifactKind.EVIDENCE,
            "Corpus evidence",
            {
                "items": corpus.items,
                "evidenceStatus": corpus.evidenceStatus.value,
                "degradedReason": corpus.degradedReason,
                "sourceRefs": [],
            },
        )

        service.advance_state(
            owner_id,
            job_id,
            JobState.SEARCHING_EXTERNAL,
            "Searching external sources",
        )
        external = adapters.external.search(job.topic)
        service.save_artifact(
            owner_id,
            job_id,
            ArtifactKind.EXTERNAL_FINDINGS,
            "External findings",
            {
                "items": external.items,
                "evidenceStatus": external.evidenceStatus.value,
                "degradedReason": external.degradedReason,
                "sourceRefs": [],
            },
        )

        service.advance_state(
            owner_id,
            job_id,
            JobState.SUMMARIZING_PRIOR_WORK,
            "Summarizing similar completed work",
        )
        service.save_artifact(
            owner_id,
            job_id,
            ArtifactKind.SIMILAR_WORKS,
            "Similar completed work",
            {
                "items": [],
                "evidenceStatus": EvidenceStatus.ABSTAINED.value,
                "sourceRefs": [],
            },
        )

        if job.inputType is InputType.MANUSCRIPT and job.manuscript is not None:
            service.advance_state(
                owner_id,
                job_id,
                JobState.CHECKING_SIMILARITY,
                "Checking sentence similarity and AI-style risks",
            )
            similarity = adapters.similarity.check(owner_id, job.manuscript.model_dump())
            service.save_artifact(
                owner_id,
                job_id,
                ArtifactKind.RISK_SIGNALS,
                "Similarity and style risk signals",
                {
                    "items": similarity.items,
                    "evidenceStatus": similarity.evidenceStatus.value,
                    "degradedReason": similarity.degradedReason,
                    "sourceRefs": [],
                },
            )

        service.advance_state(
            owner_id,
            job_id,
            JobState.FORMING_IDEAS,
            "Forming novelty candidates",
        )
        service.save_artifact(
            owner_id,
            job_id,
            ArtifactKind.NOVELTY_CANDIDATES,
            "Novelty candidates",
            {
                "items": [
                    {
                        "title": "Add an evidence-backed differentiator after corpus retrieval",
                        "evidenceStatus": EvidenceStatus.ABSTAINED.value,
                        "sourceRefs": [],
                    }
                ]
            },
        )

        service.advance_state(
            owner_id,
            job_id,
            JobState.PLANNING_EXPERIMENT,
            "Drafting experiment plan",
        )
        service.save_artifact(
            owner_id,
            job_id,
            ArtifactKind.EXPERIMENT_PLAN,
            "Experiment plan",
            {
                "researchQuestion": job.topic,
                "hypotheses": ["A differentiator grounded in retrieved evidence improves novelty."],
                "datasets": ["To be selected from dataset search results."],
                "metrics": [
                    "Novelty score",
                    "baseline delta",
                    "reproducibility checklist pass rate",
                ],
                "risks": ["Weak evidence", "dataset mismatch", "unapproved Notion export"],
            },
        )
        service.advance_state(owner_id, job_id, JobState.COMPLETED, "Novelty analysis complete")
    except Exception as exc:
        service.advance_state(
            owner_id,
            job_id,
            JobState.FAILED,
            "Novelty analysis failed",
            {"error": str(exc)},
        )
        raise


def main() -> None:
    # The ECS worker entrypoint is intentionally small; queue consumption will be wired when the
    # SQS adapter lands. This keeps image activation safe: the service can scale to zero and start.
    payload = os.getenv("DOCSURI_NOVELTY_INLINE_JOB")
    if payload:
        print(json.dumps({"status": "inline_job_not_supported", "payload": json.loads(payload)}))
    else:
        print(json.dumps({"status": "idle", "worker": "novelty"}))


if __name__ == "__main__":
    main()
