-- 002_add_role_and_totp.sql
-- U3 Accounts BR-A7: 관리자(ADMIN) 역할 + TOTP MFA 시크릿 컬럼 추가.
-- 역할은 DB가 단일 출처다 (공개 가입은 항상 USER; ADMIN은 시딩 경로로만 주입 — 권한 상승 방어).
-- totp_secret은 관리자 MFA 등록(enroll) 시점에 채워지며, 평문 시크릿은 로그에 남기지 않는다 (SEC-3).

ALTER TABLE accounts ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'USER';
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(64);
