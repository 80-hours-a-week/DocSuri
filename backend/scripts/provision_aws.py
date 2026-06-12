"""상시 데모 인프라 프로비저닝 — boto3 idempotent (env_setup_plan B1·B2).

생성(존재 시 skip): DynamoDB 3테이블(TTL=expires_at) · S3 소스 버킷 ·
S3 Vectors 버킷+인덱스(Titan V2 1024d, cosine — U0-M3) · KB 서비스 롤 ·
KB + S3 데이터소스(dataDeletionPolicy=RETAIN — teardown 함정 회피).
적재: corpus 100편(본문+.metadata.json 사이드카) → KB ingestion ·
glossary 50개 → DynamoDB.

서울 KB×S3 Vectors×Titan 생성·색인 성공 = ADR-D2 잔여 "서울+Titan 재검증" 닫힘.

실행:
    AWS_PROFILE=AdministratorAccess-028317349537 uv run python scripts/provision_aws.py
    옵션: --skip-seed (리소스만) · --teardown 안내는 teardown_aws.py

출력: data/aws_outputs.json (리소스 ID — 비밀 아님, 커밋 대상) + .env 안내.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

REGION = "ap-northeast-2"  # ADR-D9 (2026-06-11 재검토: 서울)
EMBED_MODEL_ID = "amazon.titan-embed-text-v2:0"  # ADR-D3 재검토
EMBED_DIM = 1024
TAGS = [{"Key": "project", "Value": "docsuri-demo"}]
TAG_MAP = {"project": "docsuri-demo"}

DATA = Path(__file__).resolve().parents[1] / "data"
OUTPUTS = DATA / "aws_outputs.json"

NAMES = {
    "cache_table": "docsuri-cache",
    "glossary_table": "docsuri-glossary",
    "cost_table": "docsuri-cost",
    "vector_bucket": "docsuri-vectors",
    "index": "papers",
    "kb_name": "docsuri-papers",
    "kb_role": "docsuri-kb-role",
}


def log(msg: str) -> None:
    print(f"[provision] {msg}", flush=True)


def ensure_table(ddb, name: str, key: str, ttl: bool) -> None:
    try:
        ddb.create_table(
            TableName=name,
            KeySchema=[{"AttributeName": key, "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": key, "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
            Tags=TAGS,
        )
        log(f"DynamoDB {name} 생성 중…")
        ddb.get_waiter("table_exists").wait(TableName=name)
    except ClientError as e:
        if e.response["Error"]["Code"] != "ResourceInUseException":
            raise
        log(f"DynamoDB {name} 이미 존재 — skip")
    if ttl:
        status = ddb.describe_time_to_live(TableName=name)["TimeToLiveDescription"]
        if status.get("TimeToLiveStatus") not in ("ENABLED", "ENABLING"):
            # U0-L5: TTL 속성명은 어댑터(DynamoCache)의 expires_at과 일치해야 함
            ddb.update_time_to_live(
                TableName=name,
                TimeToLiveSpecification={"Enabled": True, "AttributeName": "expires_at"},
            )
            log(f"DynamoDB {name} TTL(expires_at) 활성화")


def ensure_source_bucket(s3, name: str) -> None:
    try:
        s3.create_bucket(
            Bucket=name,
            CreateBucketConfiguration={"LocationConstraint": REGION},
        )
        log(f"S3 소스 버킷 {name} 생성")
    except ClientError as e:
        if e.response["Error"]["Code"] not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            raise
        log(f"S3 소스 버킷 {name} 이미 존재 — skip")


def ensure_vector_index(s3v) -> str:
    try:
        s3v.create_vector_bucket(vectorBucketName=NAMES["vector_bucket"])
        log(f"S3 Vectors 버킷 {NAMES['vector_bucket']} 생성")
    except ClientError as e:
        if e.response["Error"]["Code"] != "ConflictException":
            raise
        log("S3 Vectors 버킷 이미 존재 — skip")
    try:
        s3v.create_index(
            vectorBucketName=NAMES["vector_bucket"],
            indexName=NAMES["index"],
            dataType="float32",
            dimension=EMBED_DIM,
            distanceMetric="cosine",  # U0-M3: similarity=1-d/2 변환의 전제
            metadataConfiguration={
                # KB가 넣는 대형 메타는 필터 불가로 — 사이드카 year·field_tags는 필터 가능 유지
                "nonFilterableMetadataKeys": ["AMAZON_BEDROCK_METADATA", "AMAZON_BEDROCK_TEXT"]
            },
        )
        log(f"S3 Vectors 인덱스 {NAMES['index']} 생성 (cosine, {EMBED_DIM}d)")
    except ClientError as e:
        if e.response["Error"]["Code"] != "ConflictException":
            raise
        log("S3 Vectors 인덱스 이미 존재 — skip")
    index = s3v.get_index(vectorBucketName=NAMES["vector_bucket"], indexName=NAMES["index"])
    return index["index"]["indexArn"]


def ensure_kb_role(iam, account: str, source_bucket: str, index_arn: str) -> str:
    trust = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "bedrock.amazonaws.com"},
            "Action": "sts:AssumeRole",
            "Condition": {"StringEquals": {"aws:SourceAccount": account}},
        }],
    }
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["bedrock:InvokeModel"],
                "Resource": [f"arn:aws:bedrock:{REGION}::foundation-model/{EMBED_MODEL_ID}"],
            },
            {
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:ListBucket"],
                "Resource": [
                    f"arn:aws:s3:::{source_bucket}",
                    f"arn:aws:s3:::{source_bucket}/*",
                ],
            },
            {
                "Effect": "Allow",
                "Action": ["s3vectors:*"],
                "Resource": [index_arn, index_arn.rsplit("/index/", 1)[0]],
            },
        ],
    }
    try:
        iam.create_role(
            RoleName=NAMES["kb_role"],
            AssumeRolePolicyDocument=json.dumps(trust),
            Tags=TAGS,
        )
        log(f"IAM 롤 {NAMES['kb_role']} 생성")
    except ClientError as e:
        if e.response["Error"]["Code"] != "EntityAlreadyExists":
            raise
        log("IAM 롤 이미 존재 — skip")
    iam.put_role_policy(
        RoleName=NAMES["kb_role"],
        PolicyName="docsuri-kb-access",
        PolicyDocument=json.dumps(policy),
    )
    return iam.get_role(RoleName=NAMES["kb_role"])["Role"]["Arn"]


def ensure_kb(agent, role_arn: str, index_arn: str, source_bucket: str) -> tuple[str, str]:
    kbs = agent.list_knowledge_bases(maxResults=50).get("knowledgeBaseSummaries", [])
    kb_id = next((k["knowledgeBaseId"] for k in kbs if k["name"] == NAMES["kb_name"]), None)
    if kb_id is None:
        for attempt in range(8):  # IAM 전파 대기 재시도
            try:
                kb = agent.create_knowledge_base(
                    name=NAMES["kb_name"],
                    roleArn=role_arn,
                    knowledgeBaseConfiguration={
                        "type": "VECTOR",
                        "vectorKnowledgeBaseConfiguration": {
                            "embeddingModelArn": f"arn:aws:bedrock:{REGION}::foundation-model/{EMBED_MODEL_ID}",
                            "embeddingModelConfiguration": {
                                "bedrockEmbeddingModelConfiguration": {
                                    "dimensions": EMBED_DIM,
                                    "embeddingDataType": "FLOAT32",
                                }
                            },
                        },
                    },
                    storageConfiguration={
                        "type": "S3_VECTORS",
                        "s3VectorsConfiguration": {"indexArn": index_arn},
                    },
                    tags=TAG_MAP,
                )
                kb_id = kb["knowledgeBase"]["knowledgeBaseId"]
                log(f"KB {NAMES['kb_name']} 생성 ({kb_id})")
                break
            except ClientError as e:
                if e.response["Error"]["Code"] in ("ValidationException",) and "role" in str(e).lower() and attempt < 7:
                    log(f"IAM 전파 대기 재시도 {attempt + 1}/8…")
                    time.sleep(5)
                    continue
                raise
    else:
        log(f"KB 이미 존재 — skip ({kb_id})")

    while agent.get_knowledge_base(knowledgeBaseId=kb_id)["knowledgeBase"]["status"] == "CREATING":
        time.sleep(3)

    sources = agent.list_data_sources(knowledgeBaseId=kb_id, maxResults=20).get(
        "dataSourceSummaries", []
    )
    ds_id = next((d["dataSourceId"] for d in sources if d["name"] == "corpus"), None)
    if ds_id is None:
        ds = agent.create_data_source(
            knowledgeBaseId=kb_id,
            name="corpus",
            dataSourceConfiguration={
                "type": "S3",
                "s3Configuration": {"bucketArn": f"arn:aws:s3:::{source_bucket}"},
            },
            dataDeletionPolicy="RETAIN",  # teardown 함정 선제 회피 (검증 세션 기록)
        )
        ds_id = ds["dataSource"]["dataSourceId"]
        log(f"데이터소스 corpus 생성 ({ds_id})")
    else:
        log(f"데이터소스 이미 존재 — skip ({ds_id})")
    return kb_id, ds_id


def seed_corpus(s3, agent, source_bucket: str, kb_id: str, ds_id: str) -> dict:
    papers = json.loads((DATA / "corpus_seed.json").read_text())["papers"]
    docs = json.loads((DATA / "corpus_docs.json").read_text())["docs"]
    uploaded = 0
    for paper in papers:
        pid = paper["id"]
        body = docs.get(pid)
        if not body:
            continue
        s3.put_object(Bucket=source_bucket, Key=f"{pid}.txt", Body=body.encode())
        sidecar = {
            "metadataAttributes": {
                "year": paper["year"],
                "field_tags": paper["field_tags"],
                "citations": paper["citations"],
            }
        }
        s3.put_object(
            Bucket=source_bucket,
            Key=f"{pid}.txt.metadata.json",
            Body=json.dumps(sidecar).encode(),
        )
        uploaded += 1
    log(f"코퍼스 업로드 {uploaded}편 → ingestion 시작")

    job = agent.start_ingestion_job(knowledgeBaseId=kb_id, dataSourceId=ds_id)
    job_id = job["ingestionJob"]["ingestionJobId"]
    started = time.time()
    while True:
        state = agent.get_ingestion_job(
            knowledgeBaseId=kb_id, dataSourceId=ds_id, ingestionJobId=job_id
        )["ingestionJob"]
        if state["status"] in ("COMPLETE", "FAILED"):
            break
        time.sleep(5)
    stats = state.get("statistics", {})
    log(
        f"ingestion {state['status']} {time.time() - started:.1f}s — "
        f"scanned={stats.get('numberOfDocumentsScanned')} "
        f"indexed={stats.get('numberOfNewDocumentsIndexed')} "
        f"failed={stats.get('numberOfDocumentsFailed')}"
    )
    return {"status": state["status"], "elapsed_s": round(time.time() - started, 1), **stats}


def seed_glossary(ddb_res) -> int:
    entries = json.loads((DATA / "glossary_seed.json").read_text())["entries"]
    table = ddb_res.Table(NAMES["glossary_table"])
    with table.batch_writer() as batch:
        for e in entries:
            batch.put_item(
                Item={"term": e["term"].lower(), "ko": e["ko"], "note": e.get("note", "")}
            )
    log(f"용어집 {len(entries)}건 적재")
    return len(entries)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-seed", action="store_true")
    args = parser.parse_args()

    session = boto3.Session(region_name=REGION)
    account = session.client("sts").get_caller_identity()["Account"]
    log(f"계정 {account} · 리전 {REGION}")
    source_bucket = f"docsuri-corpus-{account}"

    ddb = session.client("dynamodb")
    ensure_table(ddb, NAMES["cache_table"], "pk", ttl=True)
    ensure_table(ddb, NAMES["glossary_table"], "term", ttl=False)
    ensure_table(ddb, NAMES["cost_table"], "month", ttl=False)

    s3 = session.client("s3")
    ensure_source_bucket(s3, source_bucket)
    index_arn = ensure_vector_index(session.client("s3vectors"))
    role_arn = ensure_kb_role(session.client("iam"), account, source_bucket, index_arn)
    kb_id, ds_id = ensure_kb(session.client("bedrock-agent"), role_arn, index_arn, source_bucket)

    ingestion: dict = {}
    glossary_count = 0
    if not args.skip_seed:
        ingestion = seed_corpus(s3, session.client("bedrock-agent"), source_bucket, kb_id, ds_id)
        glossary_count = seed_glossary(session.resource("dynamodb"))

    outputs = {
        "region": REGION,
        "account": account,
        "kb_id": kb_id,
        "data_source_id": ds_id,
        "source_bucket": source_bucket,
        "vector_bucket": NAMES["vector_bucket"],
        "index": NAMES["index"],
        "tables": [NAMES["cache_table"], NAMES["glossary_table"], NAMES["cost_table"]],
        "ingestion": ingestion,
        "glossary_seeded": glossary_count,
    }
    OUTPUTS.write_text(json.dumps(outputs, ensure_ascii=False, indent=1))
    log(f"출력 기록 → {OUTPUTS}")
    log("aws 모드 실행 환경 변수:")
    print(f"  export DOCSURI_ADAPTER_MODE=aws AWS_REGION={REGION} DOCSURI_KB_ID={kb_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
