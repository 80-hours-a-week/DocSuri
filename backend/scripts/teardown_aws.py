"""상시 데모 인프라 해체 — provision_aws.py 의 역순 (env_setup_plan B3).

검증 세션의 함정 대응: KB 삭제 전 데이터소스를 RETAIN으로 강제(이미 RETAIN으로
생성하지만 방어적 재설정) — 벡터스토어를 먼저 지우면 KB가 DELETE_UNSUCCESSFUL로 묶인다.

실행: AWS_PROFILE=<프로필> uv run python scripts/teardown_aws.py --yes
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

REGION = "ap-northeast-2"
OUTPUTS = Path(__file__).resolve().parents[1] / "data" / "aws_outputs.json"
NAMES = {
    "tables": ["docsuri-cache", "docsuri-glossary", "docsuri-cost"],
    "vector_bucket": "docsuri-vectors",
    "index": "papers",
    "kb_name": "docsuri-papers",
    "kb_role": "docsuri-kb-role",
}


def log(msg: str) -> None:
    print(f"[teardown] {msg}", flush=True)


def ignore(code: str):
    def decorator(fn):
        def wrapper(*a, **kw):
            try:
                return fn(*a, **kw)
            except ClientError as e:
                if e.response["Error"]["Code"] != code:
                    raise
                log(f"skip ({code})")
        return wrapper
    return decorator


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--yes", action="store_true", help="확인 없이 진행")
    args = parser.parse_args()
    if not args.yes:
        print("상시 데모 인프라를 전부 삭제합니다. --yes 로 확인해 주세요.")
        return 1

    session = boto3.Session(region_name=REGION)
    account = session.client("sts").get_caller_identity()["Account"]
    source_bucket = f"docsuri-corpus-{account}"
    agent = session.client("bedrock-agent")

    # 1. KB — DS를 RETAIN으로 재설정 후 삭제 (함정 대응)
    for kb in agent.list_knowledge_bases(maxResults=50).get("knowledgeBaseSummaries", []):
        if kb["name"] != NAMES["kb_name"]:
            continue
        kb_id = kb["knowledgeBaseId"]
        for ds in agent.list_data_sources(knowledgeBaseId=kb_id, maxResults=20).get(
            "dataSourceSummaries", []
        ):
            full = agent.get_data_source(knowledgeBaseId=kb_id, dataSourceId=ds["dataSourceId"])[
                "dataSource"
            ]
            agent.update_data_source(
                knowledgeBaseId=kb_id,
                dataSourceId=ds["dataSourceId"],
                name=full["name"],
                dataSourceConfiguration=full["dataSourceConfiguration"],
                dataDeletionPolicy="RETAIN",
            )
        agent.delete_knowledge_base(knowledgeBaseId=kb_id)
        log(f"KB {kb_id} 삭제 요청")
        while True:
            try:
                agent.get_knowledge_base(knowledgeBaseId=kb_id)
                time.sleep(3)
            except ClientError:
                break
        log("KB GONE")

    # 2. S3 Vectors 인덱스·버킷
    s3v = session.client("s3vectors")
    try:
        s3v.delete_index(vectorBucketName=NAMES["vector_bucket"], indexName=NAMES["index"])
        log("S3 Vectors 인덱스 삭제")
        s3v.delete_vector_bucket(vectorBucketName=NAMES["vector_bucket"])
        log("S3 Vectors 버킷 삭제")
    except ClientError as e:
        log(f"S3 Vectors skip: {e.response['Error']['Code']}")

    # 3. 소스 버킷 비우고 삭제
    s3 = session.resource("s3")
    try:
        bucket = s3.Bucket(source_bucket)
        bucket.objects.all().delete()
        bucket.delete()
        log(f"소스 버킷 {source_bucket} 삭제")
    except ClientError as e:
        log(f"소스 버킷 skip: {e.response['Error']['Code']}")

    # 4. DynamoDB
    ddb = session.client("dynamodb")
    for name in NAMES["tables"]:
        try:
            ddb.delete_table(TableName=name)
            log(f"테이블 {name} 삭제")
        except ClientError as e:
            log(f"테이블 {name} skip: {e.response['Error']['Code']}")

    # 5. IAM 롤
    iam = session.client("iam")
    try:
        iam.delete_role_policy(RoleName=NAMES["kb_role"], PolicyName="docsuri-kb-access")
        iam.delete_role(RoleName=NAMES["kb_role"])
        log("IAM 롤 삭제")
    except ClientError as e:
        log(f"IAM skip: {e.response['Error']['Code']}")

    if OUTPUTS.exists():
        OUTPUTS.unlink()
    log("완료 — 잔존 리소스 0 목표. 콘솔에서 최종 확인 권장.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
