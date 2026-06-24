-- 004_create_account_withdrawal_backups.sql
-- U10 회원탈퇴(soft-delete) 시 accounts 행을 스냅샷으로 보관하는 백업 테이블.
-- 탈퇴 시 accounts는 is_withdrawn=true + withdrawn_at만 표시하고 행 자체는 지우지 않지만,
-- 분쟁/법적 대응 등을 위해 탈퇴 시점 스냅샷을 별도로 5년간 보관한다(purge_after 이후 하드
-- 삭제 대상 — 실제 정리 배치는 후속 작업).
-- 범위 주의: 이 테이블은 U3(accounts)가 소유한 데이터만 스냅샷한다. 라이브러리(U4)·행동
-- 이벤트/관심 프로필(U9)은 1:N 데이터라 이 테이블에 담을 수 없고, 각 모듈이 탈퇴 이벤트를
-- 구독해 자기 데이터를 별도로 백업/정리해야 한다(후속 작업, 이 파일의 범위 밖).
-- password_hash/totp_secret은 재로그인 복구 목적이 아니므로 의도적으로 백업하지 않는다.

CREATE TABLE IF NOT EXISTS account_withdrawal_backups (
    id VARCHAR(36) PRIMARY KEY,
    original_account_id VARCHAR(36) NOT NULL,
    email VARCHAR(254) NOT NULL,
    status VARCHAR(20) NOT NULL,
    google_sub VARCHAR(255),
    orcid_id VARCHAR(19),
    orcid_name VARCHAR(255),
    orcid_affiliation VARCHAR(255),
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
