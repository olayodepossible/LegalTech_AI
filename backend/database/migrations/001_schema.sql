-- LegalTech — schema aligned with database/src/models.py
-- Tables: users, activity_history, jobs

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- users (Users.create_user: clerk_user_id, display_name, email)
CREATE TABLE IF NOT EXISTS users (
    clerk_user_id VARCHAR(255) PRIMARY KEY,
    display_name VARCHAR(255),
    email VARCHAR(255),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

-- activity_history (ActivityHistory.create_activity_history)
CREATE TABLE IF NOT EXISTS activity_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clerk_user_id VARCHAR(255) NOT NULL REFERENCES users(clerk_user_id) ON DELETE CASCADE,
    account_name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    details TEXT,
    label VARCHAR(255),
    activity_type VARCHAR(100),
    activity_date VARCHAR(64),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

-- jobs (Jobs.create_job, update_status, update_report, update_charts, update_retirement, update_summary)
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clerk_user_id VARCHAR(255) NOT NULL REFERENCES users(clerk_user_id) ON DELETE CASCADE,
    job_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    request_payload JSONB,
    report_payload JSONB,
    charts_payload JSONB,
    retirement_payload JSONB,
    summary_payload JSONB,
    error_message TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITHOUT TIME ZONE,
    completed_at TIMESTAMP WITHOUT TIME ZONE,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_activity_history_user ON activity_history(clerk_user_id);
CREATE INDEX IF NOT EXISTS idx_jobs_user ON jobs(clerk_user_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_jobs_updated_at
    BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
