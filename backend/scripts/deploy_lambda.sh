#!/usr/bin/env bash
# Lambda 컨테이너 배포 — env_setup_plan C-D1 (idempotent).
# 사용: AWS_PROFILE=<프로필> bash scripts/deploy_lambda.sh
set -euo pipefail

REGION=ap-northeast-2
FUNC=docsuri-api
REPO=docsuri-backend
ROLE=docsuri-lambda-role
KB_ID=$(python3 -c "import json;print(json.load(open('data/aws_outputs.json'))['kb_id'])")
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
ECR="$ACCOUNT.dkr.ecr.$REGION.amazonaws.com"
IMAGE="$ECR/$REPO:latest"

echo "[deploy] 계정 $ACCOUNT · 리전 $REGION · KB $KB_ID"

# 1. ECR 리포지토리
aws ecr describe-repositories --repository-names "$REPO" --region "$REGION" >/dev/null 2>&1 ||
  aws ecr create-repository --repository-name "$REPO" --region "$REGION" \
    --tags Key=project,Value=docsuri-demo >/dev/null
echo "[deploy] ECR 준비"

# 2. 이미지 빌드(arm64)·푸시
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ECR" >/dev/null
docker buildx build --platform linux/arm64 --provenance=false -t "$IMAGE" --push .
echo "[deploy] 이미지 푸시 완료"

# 3. 실행 롤
if ! aws iam get-role --role-name "$ROLE" >/dev/null 2>&1; then
  aws iam create-role --role-name "$ROLE" --tags Key=project,Value=docsuri-demo \
    --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}' >/dev/null
  aws iam attach-role-policy --role-name "$ROLE" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
  echo "[deploy] IAM 롤 생성 — 전파 대기 10s"; sleep 10
fi
aws iam put-role-policy --role-name "$ROLE" --policy-name docsuri-api-access \
  --policy-document "{
    \"Version\":\"2012-10-17\",
    \"Statement\":[
      {\"Effect\":\"Allow\",\"Action\":[\"bedrock:InvokeModel\",\"bedrock:InvokeModelWithResponseStream\"],\"Resource\":\"*\"},
      {\"Effect\":\"Allow\",\"Action\":[\"dynamodb:GetItem\",\"dynamodb:PutItem\",\"dynamodb:UpdateItem\",\"dynamodb:Query\"],
       \"Resource\":\"arn:aws:dynamodb:$REGION:$ACCOUNT:table/docsuri-*\"},
      {\"Effect\":\"Allow\",\"Action\":[\"s3vectors:QueryVectors\",\"s3vectors:GetIndex\",\"s3vectors:GetVectors\"],
       \"Resource\":\"arn:aws:s3vectors:$REGION:$ACCOUNT:bucket/docsuri-vectors*\"}
    ]}" >/dev/null
ROLE_ARN=$(aws iam get-role --role-name "$ROLE" --query Role.Arn --output text)

# 4. 함수 생성/갱신 — 검증과 동일 형태(arm64, 1024MB)
ENVVARS="Variables={DOCSURI_ADAPTER_MODE=aws,DOCSURI_KB_ID=$KB_ID}"
if aws lambda get-function --function-name "$FUNC" --region "$REGION" >/dev/null 2>&1; then
  aws lambda update-function-code --function-name "$FUNC" --image-uri "$IMAGE" --region "$REGION" >/dev/null
  aws lambda wait function-updated --function-name "$FUNC" --region "$REGION"
  aws lambda update-function-configuration --function-name "$FUNC" --region "$REGION" \
    --environment "$ENVVARS" --timeout 60 --memory-size 1024 >/dev/null
  echo "[deploy] 함수 코드·설정 갱신"
else
  aws lambda create-function --function-name "$FUNC" --region "$REGION" \
    --package-type Image --code ImageUri="$IMAGE" --role "$ROLE_ARN" \
    --architectures arm64 --memory-size 1024 --timeout 60 \
    --environment "$ENVVARS" --tags project=docsuri-demo >/dev/null
  echo "[deploy] 함수 생성"
fi
aws lambda wait function-active --function-name "$FUNC" --region "$REGION"

# 5. API Gateway HTTP API (퍼블릭 진입점 — 데모 전용, NFR-SEC-01 비로그인)
# ⚠️ Lambda Function URL(NONE)은 이 조직 SCP가 익명 호출을 403으로 차단해 사용 불가
#    (2026-06-12 실측, env-setup-report 참조) — HTTP API 프록시로 우회한다.
LARN=$(aws lambda get-function --function-name "$FUNC" --region "$REGION" \
  --query Configuration.FunctionArn --output text)
API_ID=$(aws apigatewayv2 get-apis --region "$REGION" \
  --query "Items[?Name=='$FUNC'].ApiId | [0]" --output text)
if [ "$API_ID" = "None" ] || [ -z "$API_ID" ]; then
  API_ID=$(aws apigatewayv2 create-api --name "$FUNC" --protocol-type HTTP \
    --target "$LARN" --region "$REGION" --tags project=docsuri-demo \
    --query ApiId --output text)
  echo "[deploy] API Gateway 생성 ($API_ID)"
fi
aws lambda add-permission --function-name "$FUNC" --region "$REGION" \
  --statement-id apigw-invoke --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:$REGION:$ACCOUNT:$API_ID/*" >/dev/null 2>&1 || true
URL="https://$API_ID.execute-api.$REGION.amazonaws.com"
echo "[deploy] API URL: $URL"
python3 - "$URL" "$API_ID" <<'PYEOF'
import json, sys
from pathlib import Path
p = Path("data/aws_outputs.json")
d = json.loads(p.read_text())
d["api_url"] = sys.argv[1]
d["api_gateway_id"] = sys.argv[2]
p.write_text(json.dumps(d, ensure_ascii=False, indent=1))
PYEOF
echo "[deploy] aws_outputs.json 갱신 완료"
