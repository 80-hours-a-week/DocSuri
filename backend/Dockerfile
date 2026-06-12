# Lambda 컨테이너 이미지 — ADR-D1(FastAPI + Web Adapter) · ADR-D9(서버리스, arm64 1024MB)
# 콜드스타트 실측 기준과 동일 형태 (u0-aws-env-verification §3: 콜드 P50 887ms).
FROM public.ecr.aws/docker/library/python:3.12-slim

# AWS Lambda Web Adapter — HTTP 앱을 무수정으로 Lambda에 탑재
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.9.1 /lambda-adapter /opt/extensions/lambda-adapter
ENV PORT=8080 AWS_LWA_INVOKE_MODE=buffered

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
# corpus_seed.json — aws 모드 search의 메타데이터 조인에 필요 (config.DATA_DIR=/app/data)
COPY data/corpus_seed.json data/glossary_seed.json ./data/

# editable 설치 — config.py의 상대 DATA_DIR(/app/data) 경로 유지
RUN pip install --no-cache-dir -e .

CMD ["uvicorn", "docsuri.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080"]
