-- Job tracking table (Phase 1)
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL,
    efl_url TEXT,
    status TEXT NOT NULL DEFAULT 'queued',
    pdf_type TEXT,
    error TEXT,
    extracted_data TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_jobs_plan_id ON jobs(plan_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);

-- Normalized EFL data tables (Phase 3)

-- Plans table: one row per unique plan extraction
CREATE TABLE IF NOT EXISTS plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id TEXT NOT NULL,
    provider_name TEXT NOT NULL,
    plan_name TEXT NOT NULL,
    plan_type TEXT NOT NULL CHECK(plan_type IN ('fixed', 'variable')),
    contract_term_months INTEGER,
    early_termination_fee REAL,
    etf_conditions TEXT,
    renewable_energy_pct REAL,
    special_terms TEXT,
    efl_url TEXT,
    extracted_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(plan_id, provider_name, plan_name)
);

-- Pricing tiers: price per kWh at standard usage levels
CREATE TABLE IF NOT EXISTS pricing_tiers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_rowid INTEGER NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    usage_kwh INTEGER NOT NULL,
    price_per_kwh REAL NOT NULL,
    UNIQUE(plan_rowid, usage_kwh)
);

-- Charges: categorized charges (base, energy, TDU delivery, etc.)
CREATE TABLE IF NOT EXISTS charges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_rowid INTEGER NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    charge_type TEXT NOT NULL CHECK(charge_type IN ('base', 'energy', 'tdu_delivery', 'tdu_fixed', 'minimum_usage')),
    amount REAL NOT NULL,
    unit TEXT NOT NULL CHECK(unit IN ('monthly', 'per_kwh')),
    threshold_kwh INTEGER,
    UNIQUE(plan_rowid, charge_type, unit)
);

-- Analytical indexes (DB-03)
CREATE INDEX IF NOT EXISTS idx_plans_plan_type ON plans(plan_type);
CREATE INDEX IF NOT EXISTS idx_plans_contract_term ON plans(contract_term_months);
CREATE INDEX IF NOT EXISTS idx_plans_renewable ON plans(renewable_energy_pct);
CREATE INDEX IF NOT EXISTS idx_plans_provider ON plans(provider_name);
CREATE INDEX IF NOT EXISTS idx_pricing_tiers_plan ON pricing_tiers(plan_rowid);
CREATE INDEX IF NOT EXISTS idx_pricing_tiers_usage ON pricing_tiers(usage_kwh, price_per_kwh);
CREATE INDEX IF NOT EXISTS idx_charges_plan ON charges(plan_rowid);
CREATE INDEX IF NOT EXISTS idx_charges_type ON charges(charge_type);
