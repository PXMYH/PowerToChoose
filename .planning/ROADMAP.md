# Roadmap: Power to Choose - EFL Parser

**Project:** Power to Choose - EFL Parser
**Core Value:** Accurately extract and store structured pricing, charges, and contract details from EFL PDFs so users can make informed electricity plan comparisons.
**Created:** 2026-03-22
**Granularity:** Standard (5-8 phases)

## Phases

- [ ] **Phase 1: PDF Processing Infrastructure** - Establish reliable PDF download, caching, format detection, and background task orchestration
- [ ] **Phase 2: LLM Integration + Data Extraction** - Integrate OpenRouter LLM and extract structured data from EFL PDFs
- [ ] **Phase 3: Database Schema + Storage** - Design and implement SQLite schema with proper indexes and constraints
- [ ] **Phase 4: API Integration + Validation** - Add API endpoints and validate extracted data against external sources

## Phase Details

### Phase 1: PDF Processing Infrastructure

**Goal**: System can reliably download, cache, and classify EFL PDFs with background task orchestration

**Depends on**: Nothing (first phase)

**Requirements**: PDF-01, PDF-02, PDF-03, PDF-04, PIPE-01, PIPE-02

**Success Criteria** (what must be TRUE):
1. System successfully downloads PDFs from provider URLs with automatic retry on failure
2. Downloaded PDFs are cached locally and reused across re-runs without re-downloading
3. System correctly identifies whether a PDF contains extractable text or is a scanned image
4. Background tasks process EFL extraction without blocking API responses
5. Job status can be queried at any time showing current processing state (queued/downloading/extracting/parsing/storing/completed/failed)

**Plans:** 4 plans

Plans:
- [ ] 01-01-PLAN.md — Project structure, config, routers, and Pydantic models
- [ ] 01-02-PLAN.md — PDF downloader with retry logic and local caching
- [ ] 01-03-PLAN.md — PDF classification (text vs scanned) and text extraction
- [ ] 01-04-PLAN.md — SQLite job tracking, background tasks, and EFL API endpoints

---

### Phase 2: LLM Integration + Data Extraction

**Goal**: System extracts structured pricing, charges, and contract details from EFL PDFs using LLM-powered parsing

**Depends on**: Phase 1 (requires downloaded PDFs and task orchestration)

**Requirements**: LLM-01, LLM-02, LLM-03, LLM-04, EXT-01, EXT-02, EXT-03, EXT-04, EXT-05, EXT-06, EXT-07, EXT-08, EXT-09

**Success Criteria** (what must be TRUE):
1. System extracts all required fields from EFL: prices at 500/1000/2000 kWh, base charges, contract term, early termination fee, plan type, renewable percentage, provider name
2. TDU delivery charges are separated from provider charges in extraction output
3. LLM API rate limits do not cause pipeline failures (exponential backoff handles retries automatically)
4. Extracted data passes Pydantic schema validation before any downstream processing
5. Minimum usage charges and penalties are captured when present in EFL

**Plans**: TBD

---

### Phase 3: Database Schema + Storage

**Goal**: Parsed EFL data is stored in a normalized SQLite schema optimized for analytical queries

**Depends on**: Phase 2 (requires validated extraction output)

**Requirements**: DB-01, DB-02, DB-03, DB-04, DB-05

**Success Criteria** (what must be TRUE):
1. Database has normalized schema with separate tables for plans, charges, and pricing tiers
2. Re-processing the same plan does not create duplicate records (UNIQUE constraints prevent duplicates)
3. Analytical queries filtering by price, term, or renewable percentage complete in under 500ms for 1000+ plans
4. Charge types (base/energy/tdu_delivery) are clearly distinguished in schema
5. Database supports queries needed for later bill simulation and comparison analysis

**Plans**: TBD

---

### Phase 4: API Integration + Validation

**Goal**: API provides access to parsed EFL data with validated accuracy and quality controls

**Depends on**: Phase 3 (requires stored data)

**Requirements**: PIPE-03, PIPE-04, VAL-01, VAL-02, VAL-03

**Success Criteria** (what must be TRUE):
1. API endpoint accepts requests to trigger EFL processing for single plans or batches
2. API endpoint retrieves parsed EFL data for a specific plan by plan ID
3. Extracted prices are cross-validated against Power to Choose API data with discrepancies flagged
4. Sanity checks automatically flag impossible data (negative prices, missing required fields, pricing tier gaps)
5. Low-confidence extractions are marked with confidence scores for manual review

**Plans**: TBD

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. PDF Processing Infrastructure | 0/4 | Planned | - |
| 2. LLM Integration + Data Extraction | 0/0 | Not started | - |
| 3. Database Schema + Storage | 0/0 | Not started | - |
| 4. API Integration + Validation | 0/0 | Not started | - |

## Coverage

**Total v1 requirements:** 27
**Mapped to phases:** 27
**Coverage:** 100%

All requirements mapped to exactly one phase. No orphaned requirements.

---

*Roadmap created: 2026-03-22*
*Next step: `/gsd:execute-phase 1`*
