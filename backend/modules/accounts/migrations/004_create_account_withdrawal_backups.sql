-- 004_create_account_withdrawal_backups.sql
-- U10 회원탈퇴(soft-delete) 여부는 status로 추론하지 않고 accounts에 별도 bool 컬럼(is_withdrawn)
-- 으로 명시 판단한다 — status는 PENDING/ACTIVE/LOCKED 전환과 독립적으로 유지한다. (참고: develop의
-- 003_create_lifecycle_tables.sql은 status='DEACTIVATED'로 탈퇴를 표현하는 별도 설계를 추가했지만,
-- 이 결정에 따라 U10은 이 bool 컬럼 방식을 그대로 유지한다.)
-- 탈퇴 시 accounts 행 자체는 지우지 않고 is_withdrawn=true + withdrawn_at만 표시하지만, 분쟁/법적
-- 대응 등을 위해 탈퇴 시점 스냅샷을 별도로 5년간 보관한다(purge_after 이후 하드 삭제 대상 — 실제
-- 정리 배치는 후속 작업).
-- 범위 주의: 이 테이블은 accounts가 소유한 데이터만 스냅샷한다. 라이브러리(U4)·행동 이벤트/관심
-- 프로필(U9)·social_identities(소셜 로그인 연동, 1:N)는 전부 1:N 데이터라 이 테이블에 담을 수
-- 없고, 각 모듈/테이블이 탈퇴 이벤트를 구독해 자기 데이터를 별도로 백업/정리해야 한다(후속 작업,
-- 이 파일의 범위 밖). password_hash/totp_secret은 재로그인 복구 목적이 아니므로 의도적으로
-- 백업하지 않는다.

ALTER TABLE accounts ADD COLUMN IF NOT EXISTS is_withdrawn BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS withdrawn_at TIMESTAMP;

CREATE TABLE IF NOT EXISTS account_withdrawal_backups (
    id VARCHAR(36) PRIMARY KEY,
    original_account_id VARCHAR(36) NOT NULL,
    email VARCHAR(254) NOT NULL,
    status VARCHAR(20) NOT NULL,
    signed_up_at TIMESTAMP NOT NULL,
    withdrawn_at TIMESTAMP NOT NULL,
    purge_after TIMESTAMP NOT NULL,
    backed_up_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 탈퇴한 원본 계정으로 백업 행을 찾기 위한 조회 인덱스.
CREATE INDEX IF NOT EXISTS idx_account_withdrawal_backups_original_account_id
    ON account_withdrawal_backups(original_account_id);

-- 5년 보관 만료분을 찾아 하드 삭제하는 배치가 쓸 인덱스(배치 자체는 후속 작업).
CREATE INDEX IF NOT EXISTS idx_account_withdrawal_backups_purge_after
    ON account_withdrawal_backups(purge_after);
