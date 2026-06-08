# 09. 재현 가능성 자동 평가 (Reproducibility Evaluation)

> 논문 PDF를 입력으로 받아 표준 reproducibility checklist에 따라 자동 점수화 및 미흡 항목 리포트.

---

## 1. 핵심 요소

- **평가 기준**: NeurIPS Reproducibility Checklist + ML Reproducibility Checklist (Pineau 2019) + PRISMA(시스템 리뷰용)를 통합 rubric으로 정리.
- **체크리스트 항목**:
  - 코드 공개 (URL 명시 + 접근 가능)
  - 데이터셋 명시 + 접근 가능 + 라이선스
  - 하이퍼파라미터 전체 표
  - 학습 환경 (HW/SW/seed) 명시
  - 평가 프로토콜 (split, metric, baseline) 명시
  - 결과 재현 가능성 (시드/표준편차 보고)
  - 사전 학습 가중치 출처 명시
  - Compute budget 보고
- **자동 검증**:
  - 코드 URL: HTTP HEAD + GitHub API로 repo 존재·README 존재 확인
  - 데이터셋 URL: HEAD + 공식 라이선스 명시 확인
  - 표·표 셀: GROBID로 추출된 표에 하이퍼파라미터 패턴 매칭
- **rubric 점수**: 0-100 점 (가중치 평균). 카테고리별 sub-score 함께.
- **anchor 첨부**: 각 항목 평가는 논문의 어느 위치에서 추출됐는지 anchor 명시.

---

## 2. 주요 문제

- **명시 vs 실제**: 코드 URL이 있어도 실제로 코드가 비어있거나 paper와 다른 버전일 수 있음. clone 후 검증은 너무 무거움.
- **체크리스트 항목 추출 정확도**: LLM이 "하이퍼파라미터 명시"를 보지만 실제로는 일부만 있는 경우.
- **분야별 표준 차이**: ML 외 분야(생물·물리·사회과학)는 다른 reproducibility 기준. 분야별 rubric 분리 필요.
- **데이터 접근권**: 비공개 데이터셋(병원·기업)을 "비공개"로 명시한 게 reproducibility 실패인지 아닌지 — 분야 관행에 따름.
- **체크리스트 과적합 위험**: 저자가 채점 시스템을 의식해 형식만 갖춰 점수만 높게 받는 행태 발생 가능 ("점수 게이밍").
- **부분 점수의 모호함**: "하이퍼파라미터 70% 명시"가 어느 점수에 해당하는지 일관성.

---

## 3. 파이프라인 설계 & 기술 스택

```
paper_id (이미 GROBID 파싱 완료 가정)
    │
    ▼
┌─────────────────────────┐
│ Checklist Extractor (LLM)│  rubric 항목별 evidence 추출
│  - 코드 URL              │
│  - 데이터셋 URL          │
│  - 하이퍼파라미터 표      │
│  - 평가 프로토콜          │
│  - HW/SW/seed            │
└─────────┬───────────────┘
          ▼
┌─────────────────────────┐
│ URL Verifier            │
│  - HTTP HEAD             │
│  - GitHub API (스타·커밋)│
│  - HuggingFace API       │
└─────────┬───────────────┘
          ▼
┌─────────────────────────┐
│ Table Auditor           │  GROBID 표 → 하이퍼파라미터/결과 검출
└─────────┬───────────────┘
          ▼
┌─────────────────────────┐
│ Per-item Scorer         │  rubric 정의대로 0/1/2 점수
└─────────┬───────────────┘
          ▼
┌─────────────────────────┐
│ Aggregator              │  가중 평균 → 카테고리/총점
└─────────┬───────────────┘
          ▼
┌─────────────────────────┐
│ Report Composer (LLM)   │  미흡 항목 자연어 설명 + 권장
└─────────┬───────────────┘
          ▼
┌─────────────────────────┐
│ Verifier                │  rubric 판정 ↔ 원문 evidence
└─────────┬───────────────┘
          ▼
┌─────────────────────────┐
│ UI: 점수표 + anchor     │
└─────────────────────────┘
```

### 기술 스택

| 레이어 | 선택 | 비고 |
|---|---|---|
| rubric 저장 | YAML 파일 (분야별) | 사람이 편집 가능 |
| Checklist Extractor | Claude Sonnet | structured output |
| URL verifier | `httpx` HEAD + GitHub API | clone하지 않음 |
| Table auditor | GROBID JSON + 정규식 | |
| Per-item scorer | python rule + LLM 보조 | 규칙 우선 |
| Report composer | Claude Sonnet | 사용자 친화적 권장 |
| 분야 분류 (rubric 선택) | Claude Haiku | 단일 호출 |

---

## 4. 차별화 포인트

- **rubric 명시·투명**: 점수가 *왜* 그런지 항목별 anchor + 규칙으로 설명. 블랙박스 LLM 점수와 차별.
- **URL 자동 검증**: 단순 "URL이 텍스트에 있는가" 너머 "URL이 살아있는가" + "repo가 비어있지 않은가" 확인. PDF만 보는 경쟁 도구와 차별.
- **분야별 rubric**: ML 외 분야 사용자에게도 가치 (PRISMA, COBE, CONSORT 등).
- **저자용 prereview 모드**: 출판 전 저자가 자기 논문을 돌려 미흡 항목을 보강할 수 있게 함 → 학계 전반 reproducibility 향상에 기여.

---

## 5. 위험 요소

- **명예훼손 우려**: 특정 논문에 낮은 점수 부여 후 공개 시 저자/출판사 클레임. 점수는 사용자 개인 결과로만, 공개 랭킹 보드 금지.
- **rubric 편향**: NeurIPS 체크리스트는 ML 중심. 다른 분야에 강제하면 부당한 평가. 분야 분류기의 오분류가 직접 점수에 영향.
- **GitHub repo 일시 비공개**: 검증 시점에 비공개였다가 다시 공개되는 패턴 → false negative. 24h 후 재검증 옵션.
- **체크리스트 게이밍**: 저자가 형식만 갖춰 점수 받고 실제 재현 어렵게 함. 단순 자동 점수만으로는 실질 재현성 보장 못함을 UI에 명시.
- **URL 검증의 false positive**: HEAD가 200이어도 실제 코드가 없거나 깨졌을 수 있음. 깊은 검증(clone, 빌드 시도)은 비용·보안 문제.
- **LLM 컨텍스트 누락**: 부록(appendix)에 하이퍼파라미터가 있는 경우, 컨텍스트 일부만 봐서 누락 판정.

---

## 6. 예상 비용

### 단위 비용 (논문 1편 평가)

| 단계 | 비용 |
|---|---|
| Checklist Extractor (Sonnet, 캐시 히트) | ~$0.05 |
| URL verifier (5-10 URLs) | $0 (HTTP만) |
| GitHub API | $0 (무료 5000 req/h) |
| Table auditor | $0 (룰 기반) |
| Per-item scorer | $0 (룰) |
| Report Composer (Sonnet) | ~$0.03 |
| Verifier (Haiku) | ~$0.005 |
| **합계/평가** | **~$0.09** |

### MVP (월 3,000 평가)

- $0.09 × 3,000 = **$270/월**
- 인프라 ~$50/월
- **총 ~$320/월**

### 스케일업 (월 10만 평가)

- $0.09 × 100,000 = **$9,000/월**
- 인프라 ~$300/월
- GitHub API 한도 초과 시 인증 토큰으로 5000→5000/시간 유지 OK

> 가장 저렴한 기능 중 하나. 결정 변수는 rubric 정확도(품질 ↔ 비용 trade-off가 약함). 학계 무료/저렴 SaaS 가격에 맞춤.
