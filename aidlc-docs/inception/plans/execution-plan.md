# 실행 계획 (Execution Plan)

**단계**: INCEPTION → Workflow Planning · **일자**: 2026-06-15 · **프로젝트 유형**: Greenfield

## 상세 분석 요약

### 변경 영향 평가 (Change Impact Assessment)
- **사용자 대면 변경**: 예 — 제품 전체가 신규 사용자 대면(디스커버리 UI, 계정, 라이브러리).
- **구조 변경**: 예 — 신규 풀스택 아키텍처(인제스천 파이프라인 + 검색 서비스 + 모바일 웹 + 계정).
- **데이터 모델 변경**: 예 — 신규 스키마(논문/임베딩, 사용자, 검색 저장/라이브러리/이력).
- **API 변경**: 예 — 신규 엔드포인트(검색, 인증, 저장 데이터).
- **NFR 영향**: 예 — 성능(P50<3s), 보안/인증, 확장성/비용 상한, 신뢰성/우아한 저하, 관측성.

### 리스크 평가 (Risk Assessment)
- **리스크 수준**: 중간~높음(Medium–High) — 공개 프로덕션·신규 시스템이나 단일 앵커(디스커버리) MVP로 잘 한정됨.
- **롤백 복잡도**: 보통 — git-flow + IaC 재배포(RES-2, RES-4는 NFR Design에서 확정).
- **테스트 복잡도**: 보통~복잡 — 엄격 근거화 평가셋(QT-1/2), PBT(QT-4), 우아한 저하(QT-3).

> Greenfield이므로 브라운필드 전용 항목(변환 범위, 컴포넌트 관계도, 모듈 조정)은 N/A.

## 워크플로 시각화

```mermaid
flowchart TD
    Start(["사용자 요청"])

    subgraph INCEPTION["🔵 INCEPTION"]
        WD["워크스페이스 탐지<br/><b>완료</b>"]
        RE["리버스 엔지니어링<br/><b>건너뜀</b>"]
        RA["요구사항 분석<br/><b>완료</b>"]
        US["사용자 스토리<br/><b>완료</b>"]
        WP["워크플로 계획<br/><b>진행</b>"]
        AD["애플리케이션 설계<br/><b>실행</b>"]
        UG["유닛 생성<br/><b>실행</b>"]
    end

    subgraph CONSTRUCTION["🟢 CONSTRUCTION"]
        FD["기능 설계<br/><b>실행</b>"]
        NFRA["NFR 요구사항<br/><b>실행</b>"]
        NFRD["NFR 설계<br/><b>실행</b>"]
        IDS["인프라 설계<br/><b>실행</b>"]
        CG["코드 생성<br/><b>실행</b>"]
        BT["빌드 & 테스트<br/><b>실행</b>"]
    end

    subgraph OPERATIONS["🟡 OPERATIONS"]
        OPS["운영<br/><b>플레이스홀더</b>"]
    end

    Start --> WD --> RE --> RA --> US --> WP
    WP --> AD --> UG
    UG --> FD --> NFRA --> NFRD --> IDS --> CG --> BT
    BT --> OPS --> Done(["완료"])

    style WD fill:#4CAF50,stroke:#1B5E20,stroke-width:3px,color:#fff
    style RA fill:#4CAF50,stroke:#1B5E20,stroke-width:3px,color:#fff
    style US fill:#4CAF50,stroke:#1B5E20,stroke-width:3px,color:#fff
    style WP fill:#FFA726,stroke:#E65100,stroke-width:3px,color:#000
    style AD fill:#FFA726,stroke:#E65100,stroke-width:3px,stroke-dasharray: 5 5,color:#000
    style UG fill:#FFA726,stroke:#E65100,stroke-width:3px,stroke-dasharray: 5 5,color:#000
    style FD fill:#FFA726,stroke:#E65100,stroke-width:3px,stroke-dasharray: 5 5,color:#000
    style NFRA fill:#FFA726,stroke:#E65100,stroke-width:3px,stroke-dasharray: 5 5,color:#000
    style NFRD fill:#FFA726,stroke:#E65100,stroke-width:3px,stroke-dasharray: 5 5,color:#000
    style IDS fill:#FFA726,stroke:#E65100,stroke-width:3px,stroke-dasharray: 5 5,color:#000
    style CG fill:#4CAF50,stroke:#1B5E20,stroke-width:3px,color:#fff
    style BT fill:#4CAF50,stroke:#1B5E20,stroke-width:3px,color:#fff
    style RE fill:#BDBDBD,stroke:#424242,stroke-width:2px,stroke-dasharray: 5 5,color:#000
    style OPS fill:#FFF59D,stroke:#F9A825,stroke-width:2px,color:#000
    style Start fill:#CE93D8,stroke:#6A1B9A,stroke-width:3px,color:#000
    style Done fill:#CE93D8,stroke:#6A1B9A,stroke-width:3px,color:#000

    linkStyle default stroke:#333,stroke-width:2px
```

## 실행할 단계 (Phases to Execute)

### 🔵 INCEPTION 단계
- [x] 워크스페이스 탐지 (완료)
- [x] 리버스 엔지니어링 (건너뜀 — Greenfield)
- [x] 요구사항 분석 (완료)
- [x] 사용자 스토리 (완료·승인)
- [x] 워크플로 계획 (진행 중 — 본 문서)
- [ ] **애플리케이션 설계 — 실행(EXECUTE)**
  - **근거**: 신규 컴포넌트/서비스(검색·랭킹·근거화, 인제스천, 계정, 사용자 데이터, 모바일 웹)와 컴포넌트 메서드·비즈니스 규칙·의존성 정의 필요.
- [ ] **유닛 생성 — 실행(EXECUTE)**
  - **근거**: 시스템을 다수 유닛으로 분해 필요. 예비 분해(유닛 생성에서 확정): U1 인제스천·인덱싱, U2 디스커버리/검색 API, U3 계정·인증, U4 검색 저장·라이브러리, U5 모바일 웹 프런트엔드, U6 신뢰성·운영(관측성·비용 가드·AI 인시던트 탐지; 횡단 가능).

### 🟢 CONSTRUCTION 단계 (유닛별 루프)
- [ ] **기능 설계 — 실행(EXECUTE)**
  - **근거**: 신규 데이터 모델/스키마, 복잡 비즈니스 로직(검색 랭킹, 근거화/기권, 비용 서킷 브레이커). PBT-01 속성 식별도 여기서 시작.
- [ ] **NFR 요구사항 — 실행(EXECUTE)**
  - **근거**: 성능·보안·확장성·비용 요구 존재, 기술 스택 선정 필요(PBT 프레임워크 선정 포함).
- [ ] **NFR 설계 — 실행(EXECUTE)**
  - **근거**: NFR 요구사항 실행됨 → NFR 패턴 반영. 보류된 Resiliency 결정(CI/CD·롤백·배포 방식 RES-4, 복원력 테스트 RES-14)이 여기서 확정.
- [ ] **인프라 설계 — 실행(EXECUTE)**
  - **근거**: AWS 자원 명세(벡터 스토어, 컴퓨트, DB, 호스팅), 배포 아키텍처, 리전 토폴로지(RES-8) 확정.
- [ ] **코드 생성 — 실행(EXECUTE, 항상)**
  - **근거**: 구현 계획 + 코드/테스트 생성.
- [ ] **빌드 & 테스트 — 실행(EXECUTE, 항상)**
  - **근거**: 빌드·단위/통합 테스트·검증.

### 🟡 OPERATIONS 단계
- [ ] 운영 — 플레이스홀더 (향후 배포·모니터링 워크플로)

## 추정 일정 (Estimated Timeline)
- 캘린더가 아닌 **AI-DLC 단계 기준**: INCEPTION 잔여 2단계(애플리케이션 설계, 유닛 생성) + CONSTRUCTION 유닛별 루프 ×6 유닛(각 기능설계·NFR·인프라·코드 생성) + 빌드 & 테스트.
- 각 단계는 승인 게이트로 구분되며, 데모 우선(히어로 US-H1) 순서로 진행 권장.

## 성공 기준 (Success Criteria)
- **주 목표**: 매직 모먼트(자연어 의도 → 폰에서 수초 내 근거화된 arXiv 결과)를 충족하는 프로덕션급 디스커버리 MVP.
- **핵심 산출물**: 인제스천 파이프라인, 디스커버리/검색 API(엄격 근거화), 계정, 검색 저장/라이브러리, 모바일 웹 UI(폰 목업 프레임), 관측성·비용 가드·AI 인시던트 탐지.
- **품질 게이트**: 날조 인용 0건(QT-1), 관련도 평가셋(QT-2), 우아한 저하(QT-3), PBT(QT-4), 활성 확장(Security/Resiliency/PBT) 각 단계 준수.
