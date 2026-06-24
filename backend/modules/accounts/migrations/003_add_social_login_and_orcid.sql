-- 003_add_social_login_and_orcid.sql
-- U10 마이페이지 + 소셜로그인 확장: Google/ORCID 로그인 연동 + ORCID 프로필 캐시 + 회원탈퇴 시각.
-- 기존 이메일+비밀번호 로그인은 그대로 유지하고, Google/ORCID를 추가 로그인 수단으로 허용한다
-- (한 계정에 세 수단이 공존 가능 — 소셜 연동 해제해도 로그인 수단이 사라지지 않게 함).
-- Google/ORCID 전용 가입(비밀번호 미설정)을 허용하므로 password_hash를 NULL 허용으로 완화한다.
-- ORCID record(이름/소속)는 별도 캐시 테이블 대신 이 컬럼에 직접 캐싱한다 — works(논문 목록)는
-- 1:N 데이터라 컬럼으로 두지 않고 마이페이지 조회 시마다 ORCID API에서 다시 가져온다.
-- 탈퇴(soft-delete) 여부는 status 값으로 추론하지 않고 별도 bool 컬럼(is_withdrawn)으로 명시
-- 판단한다 — status는 PENDING/ACTIVE/LOCKED 전환과 독립적으로 유지(별도 백업 테이블은 후속 작업).

ALTER TABLE accounts ALTER COLUMN password_hash DROP NOT NULL;

ALTER TABLE accounts ADD COLUMN IF NOT EXISTS google_sub VARCHAR(255);
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS google_linked_at TIMESTAMP;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS orcid_id VARCHAR(19);
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS orcid_linked_at TIMESTAMP;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS orcid_name VARCHAR(255);
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS orcid_affiliation VARCHAR(255);
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS orcid_synced_at TIMESTAMP;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS is_withdrawn BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS withdrawn_at TIMESTAMP;

-- 같은 Google/ORCID 계정이 서로 다른 accounts row 두 곳에 연결되는 것을 막는다.
-- UNIQUE 인덱스는 NULL을 여러 개 허용하므로(연동 안 한 계정 다수) 별도 WHERE절은 불필요하다.
CREATE UNIQUE INDEX IF NOT EXISTS ux_accounts_google_sub ON accounts(google_sub);
CREATE UNIQUE INDEX IF NOT EXISTS ux_accounts_orcid_id ON accounts(orcid_id);
