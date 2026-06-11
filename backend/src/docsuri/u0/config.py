"""환경 변수 설정 — NFR-SEC-03: 키는 환경 변수 단일 진입, 평문 금지."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[3] / "data"


@dataclass(frozen=True)
class Settings:
    adapter_mode: str = "mock"
    aws_region: str = "ap-northeast-2"  # DynamoDB / KB / LLM — 서울
    aws_region_embed: str = "ap-northeast-1"  # Cohere Embed — 도쿄 (서울 미지원)
    bedrock_llm_model_id: str = "global.anthropic.claude-haiku-4-5-20251001-v1:0"  # ADR-D4
    bedrock_embed_model_id: str = "cohere.embed-multilingual-v3"  # ADR-D3
    kb_id: str = ""  # ADR-D2: Bedrock KB + S3 Vectors
    s3v_bucket: str = "docsuri-vectors"  # S3 Vectors 직접 조회용 (ADR-D2 결과 3)
    s3v_index: str = "papers"
    ddb_cache_table: str = "docsuri-cache"
    ddb_glossary_table: str = "docsuri-glossary"
    ddb_cost_table: str = "docsuri-cost"
    cost_monthly_cap_usd: float = 50.0  # NFR-COST-01
    # Cohere Embed 최대 입력 2048자 제약에 맞춘 청킹 상수
    chunk_size: int = 2000  # 문자 단위
    chunk_overlap: int = 200  # 청크 간 오버랩
    # ADR-D4 단가 (USD per 1M tokens) — 모델 교체 시 갱신
    llm_price_in_per_mtok: float = 1.0
    llm_price_out_per_mtok: float = 5.0
    default_persona: str = "pro"
    corpus_path: Path = field(default_factory=lambda: DATA_DIR / "corpus_seed.json")
    glossary_path: Path = field(default_factory=lambda: DATA_DIR / "glossary_seed.json")


def load_settings() -> Settings:
    env = os.environ
    mode = env.get("DOCSURI_ADAPTER_MODE", "mock").lower()
    if mode not in ("mock", "aws"):
        raise ValueError(f"DOCSURI_ADAPTER_MODE must be 'mock' or 'aws', got: {mode!r}")
    return Settings(
        adapter_mode=mode,
        aws_region=env.get("AWS_REGION", "ap-northeast-2"),
        aws_region_embed=env.get("AWS_REGION_EMBED", "ap-northeast-1"),
        bedrock_llm_model_id=env.get(
            "DOCSURI_BEDROCK_LLM_MODEL_ID", Settings.bedrock_llm_model_id
        ),
        bedrock_embed_model_id=env.get(
            "DOCSURI_BEDROCK_EMBED_MODEL_ID", Settings.bedrock_embed_model_id
        ),
        kb_id=env.get("DOCSURI_KB_ID", ""),
        s3v_bucket=env.get("DOCSURI_S3V_BUCKET", Settings.s3v_bucket),
        s3v_index=env.get("DOCSURI_S3V_INDEX", Settings.s3v_index),
        ddb_cache_table=env.get("DOCSURI_DDB_CACHE_TABLE", Settings.ddb_cache_table),
        ddb_glossary_table=env.get("DOCSURI_DDB_GLOSSARY_TABLE", Settings.ddb_glossary_table),
        ddb_cost_table=env.get("DOCSURI_DDB_COST_TABLE", Settings.ddb_cost_table),
        cost_monthly_cap_usd=float(env.get("DOCSURI_COST_MONTHLY_CAP_USD", "50")),
    )
