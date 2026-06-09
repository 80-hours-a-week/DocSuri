# DocSuri

논문 검색 플랫폼의 요약 및 번역 기능 데모입니다. FastAPI 백엔드가 PostgreSQL의 원본 논문 데이터와 PGVector 청크를 읽어 요약/번역 API를 제공하고, `/`에서 간단한 프론트엔드로 기능을 실행할 수 있습니다.

## 실행

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

브라우저에서 `http://127.0.0.1:8000`을 열면 됩니다. `DATABASE_URL` 또는 `ANTHROPIC_API_KEY`가 비어 있으면 내장 데모 논문과 mock LLM으로 동작합니다.

## 로컬 폴더 저장소

PostgreSQL이 연결되어 있지 않으면 앱은 `LOCAL_PAPER_DIR` 폴더를 먼저 읽습니다. 기본값은 `local_papers`입니다. 여기에 `.json`, `.md`, `.txt`, `.pdf` 파일을 넣으면 `/api/papers` 목록에 표시됩니다. 폴더가 비어 있으면 기존 내장 데모 논문을 사용합니다.

Markdown/TXT/PDF 파일은 파일명 stem을 `paper_id`로 쓰고, 첫 번째 `# 제목` 또는 첫 줄을 제목으로 사용합니다. 본문에 `[§1.1]` 같은 anchor가 있으면 chunk anchor로 사용하고, 없으면 문단 순서대로 `§1.1`, `§2.1` 형식의 임시 anchor를 만듭니다.

JSON 파일은 다음 형식을 사용할 수 있습니다.

```json
{
  "id": "paper-1",
  "title": "Paper title",
  "abstract": "Short abstract",
  "text": "[§1.1] Full paper text...",
  "chunks": [
    {
      "anchor": "§1.1",
      "text": "Chunk text"
    }
  ]
}
```

## PostgreSQL / PGVector

기본 스키마는 [schema.sql](schema.sql)을 참고하세요.

앱은 기본적으로 다음 컬럼 이름을 찾습니다.

- `papers`: `id`, `title`, `abstract`, `structured_markdown` 또는 `full_text`, `pdf_bytes`
- `paper_chunks`: `paper_id`, `chunk_text`, `anchor`, `chunk_index`, `embedding vector`

기존 DB 스키마가 다르면 `.env`에서 테이블명과 id 컬럼명을 바꿀 수 있습니다. 텍스트/청크 컬럼은 앱이 흔한 이름을 자동 탐색합니다.

## API

- `GET /api/papers`: 논문 목록
- `GET /api/papers/{paper_id}`: 논문 미리보기와 청크
- `POST /api/summarize`: `paper_id`, `session_id`, `length_preset`, `angle_preset`
- `POST /api/translate`: `paper_id`, `session_id`, `selected_text` 또는 `char_start`/`char_end`
- `GET /api/glossary/{session_id}`: 세션 용어 사전

요약 문장은 `[§n.m]` 또는 `[p.X ¶Y]` anchor를 포함하고, 응답에는 간단한 `SUPPORTED / PARTIALLY_SUPPORTED / NOT_FOUND` 검증 라벨이 함께 반환됩니다.
