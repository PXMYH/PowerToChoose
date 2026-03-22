CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL,
    efl_url TEXT,
    status TEXT NOT NULL DEFAULT 'queued',
    pdf_type TEXT,
    error TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_jobs_plan_id ON jobs(plan_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
