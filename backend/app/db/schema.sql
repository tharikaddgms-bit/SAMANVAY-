-- ==============================================================================
-- SAMANVAY DATABASE SCHEMA (SIH 2026 - Problem Statement SIH26263)
-- Standard SQL DDL compatible with SQLite3 and PostgreSQL
-- ==============================================================================

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    role VARCHAR(50) NOT NULL, -- 'INSTITUTION_ADMIN', 'VERIFICATION_OFFICER', 'STUDENT'
    institution_id VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    apaar_id VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    normalized_name VARCHAR(255) NOT NULL,
    dob VARCHAR(20) NOT NULL,
    guardian_name VARCHAR(255),
    institution_id VARCHAR(50) NOT NULL,
    institution_name VARCHAR(255) NOT NULL,
    program VARCHAR(100) DEFAULT 'B.Tech Computer Science & Engineering',
    verification_status VARCHAR(50) NOT NULL DEFAULT 'UNVERIFIED', 
    -- 'UNVERIFIED', 'FORMAT_VALID', 'DEMO_VERIFIED', 'OFFICIALLY_VERIFIED'
    review_status VARCHAR(50) NOT NULL DEFAULT 'PENDING_REVIEW', 
    -- 'PENDING_REVIEW', 'REQUIRES_CORRECTION', 'CORRECTED', 'APPROVED'
    apaar_blind_index VARCHAR(64) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS discrepancies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    field_name VARCHAR(50) NOT NULL,
    existing_value TEXT NOT NULL,
    proposed_value TEXT,
    flag_reason TEXT NOT NULL,
    similarity_score REAL DEFAULT 0.0,
    severity VARCHAR(20) DEFAULT 'MEDIUM', -- 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    review_status VARCHAR(50) DEFAULT 'UNRESOLVED', 
    -- 'UNRESOLVED', 'ACCEPTED_CORRECTION', 'REJECTED_CORRECTION', 'INFO_REQUESTED'
    reviewer_id VARCHAR(100),
    reviewer_notes TEXT,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS duplicate_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_a_id INTEGER NOT NULL,
    student_b_id INTEGER NOT NULL,
    composite_score REAL NOT NULL,
    field_scores_json TEXT NOT NULL,
    flag_reasons_json TEXT NOT NULL,
    is_cross_institution BOOLEAN DEFAULT FALSE,
    review_decision VARCHAR(50) DEFAULT 'NEEDS_FURTHER_REVIEW', 
    -- 'CONFIRMED_MATCH', 'NOT_A_MATCH', 'NEEDS_FURTHER_REVIEW'
    reviewer_id VARCHAR(100),
    reviewer_notes TEXT,
    reviewed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_a_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (student_b_id) REFERENCES students(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS credentials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    credential_id VARCHAR(100) UNIQUE NOT NULL,
    student_id INTEGER NOT NULL,
    canonical_json TEXT NOT NULL,
    signature TEXT NOT NULL,
    qr_payload_json TEXT NOT NULL,
    issued_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    is_revoked BOOLEAN DEFAULT FALSE,
    revocation_reason TEXT,
    revoked_at TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp VARCHAR(50) NOT NULL,
    actor_id VARCHAR(100) NOT NULL,
    actor_role VARCHAR(50) NOT NULL,
    action_type VARCHAR(100) NOT NULL,
    record_id VARCHAR(100),
    details_json TEXT NOT NULL,
    previous_hash VARCHAR(64) NOT NULL,
    entry_hash VARCHAR(64) NOT NULL
);

-- Indices for performance and indexing
CREATE INDEX IF NOT EXISTS idx_students_apaar_blind ON students(apaar_blind_index);
CREATE INDEX IF NOT EXISTS idx_students_status ON students(verification_status);
CREATE INDEX IF NOT EXISTS idx_students_institution ON students(institution_id);
CREATE INDEX IF NOT EXISTS idx_audit_entry_hash ON audit_log(entry_hash);
