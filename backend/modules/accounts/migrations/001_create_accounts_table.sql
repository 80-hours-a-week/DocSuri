-- 001_create_accounts_table.sql
-- U3 Accounts 테이블 스키마 DDL 마이그레이션 스크립트 (TD-U3-3)

-- 1. accounts 테이블 생성 (사용자 및 자격증명 해시 저장소)
CREATE TABLE IF NOT EXISTS accounts (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(254) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    failure_count INTEGER NOT NULL DEFAULT 0,
    last_failed_at TIMESTAMP NULL
);

-- 이메일 기반 초고속 검색 인덱스 추가 (SEC-12, BR-A5)
CREATE INDEX IF NOT EXISTS idx_accounts_email ON accounts(email);

-- 2. verification_tokens 테이블 생성 (이메일 인증 링크 활성화 토큰 보관)
CREATE TABLE IF NOT EXISTS verification_tokens (
    token VARCHAR(64) PRIMARY KEY,
    email VARCHAR(254) NOT NULL,
    expires_at TIMESTAMP NOT NULL
);

-- 토큰 및 이메일 기반 룩업/만료 배치 처리 인덱스 추가 (BR-A5)
CREATE INDEX IF NOT EXISTS idx_verification_tokens_email ON verification_tokens(email);
CREATE INDEX IF NOT EXISTS idx_verification_tokens_token ON verification_tokens(token);
