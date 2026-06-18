# U7 Summarization — Security Test Instructions

**단계**: CONSTRUCTION → Build & Test · **유닛**: U7 Summarization · **일자**: 2026-06-19
**대상**: 비용 발생 LLM 기능의 위협(인젝션·남용·비노출·근거화·격리). SEC 체크리스트 + QT-5.

## 보안 체크리스트 (코드 위치)

| 위협 | 방어 | 위치 | 검증 |
|---|---|---|---|
| **프롬프트 인젝션** | 본문 격리 `[지시]┃[데이터]<paper>` + 제어문자 제거 | `prompts/templates.py`·`domain/refiner.py` | 인젝션 텍스트가 지시로 해석 안 됨(통합) |
| **할루시네이션/날조** | U7 결정적 근거화(앵커 실재·수치)·근거 없으면 기권 | `domain/grounding.py` | `test_domain_grounding`(가짜 앵커·수치 불일치 → 기권) |
| **내부 필드 노출(SEC-9)** | 응답 `to_dict` 화이트리스트(토큰·비용·캐시키·모델/프롬프트 식별자 차단) | `domain/models.py` | `test_pbt`(SEC-9 라운드트립) |
| **권한 없는 접근(SEC-8)** | 개인 용어집 owner 스코프(`WHERE user_id`)·게이트웨이 인증 위임 | `adapters/rds_glossary.py`·`api/router.py`(401) | owner 격리(통합 S4) |
| **요청 남용(SEC-11)** | 레이트리밋·비용 게이트 = U6 게이트웨이/CostGuard | `service/orchestrator.py`(`get_budget_state`) | `test_orchestrator`(비용 저하→기권) |
| **PII/저작권 로깅(SEC-3)** | 원문/번역/프롬프트 무분별 로깅 금지(텔레메트리는 메트릭만) | `service/orchestrator.py`(`_emit` 태그=task/verdict) | 로그에 본문 미포함 |
| **fail-closed(SEC-15)** | 예외→일반화 기권(스택 비노출) | `api/gateway_seam.py`·`api/router.py` | 예외 주입→`AbstainDTO` |
| **공급망(SEC-10)** | 락파일·SCA·이미지 핀 = backend 모노레포 공유 툴링 | (공유 CI) | 시스템 레인 |

## Run (정적/단위)
```bash
cd backend/modules/summarization
ruff check src tests                         # S 규칙(보안) 포함 — clean
PYTHONPATH="src:../../../shared/python/src" python -m pytest tests/test_domain_grounding.py tests/test_pbt.py -q
```

## QT-5 근거화 평가셋
- U7은 근거화 출력(앵커·기권 결정)을 **표면**으로 제공. 평가셋 구축·실행 소유 = **U6/OP**(QT-1 평가셋에 요약/번역 케이스 추가). 본 유닛은 결정적 게이트의 통과/기권 결과를 노출한다.
