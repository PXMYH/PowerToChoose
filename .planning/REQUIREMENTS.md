# Requirements: Power to Choose - EFL Parser

**Defined:** 2026-03-22
**Core Value:** Accurately extract and store structured pricing, charges, and contract details from EFL PDFs so users can make informed electricity plan comparisons.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### PDF Processing

- [ ] **PDF-01**: System can download EFL PDFs from provider URLs with retry logic
- [ ] **PDF-02**: System caches downloaded PDFs locally to avoid redundant downloads
- [ ] **PDF-03**: System detects whether a PDF is text-based or scanned image
- [ ] **PDF-04**: System extracts text content from text-based EFL PDFs using pdfplumber

### LLM Integration

- [ ] **LLM-01**: System integrates with OpenRouter via LiteLLM to call nvidia/nemotron model
- [ ] **LLM-02**: System sends extracted PDF text to LLM with structured extraction prompt
- [ ] **LLM-03**: System handles rate limits with exponential backoff and retry logic
- [ ] **LLM-04**: System validates LLM output against Pydantic schema before storage

### Data Extraction

- [ ] **EXT-01**: System extracts price per kWh at 500/1000/2000 kWh usage tiers
- [ ] **EXT-02**: System extracts base/fixed monthly charges
- [ ] **EXT-03**: System extracts contract term length (months)
- [ ] **EXT-04**: System extracts early termination fee amount and conditions
- [ ] **EXT-05**: System extracts TDU delivery charges separately from provider charges
- [ ] **EXT-06**: System extracts renewable energy percentage
- [ ] **EXT-07**: System extracts plan type (fixed vs variable)
- [ ] **EXT-08**: System extracts minimum usage charges/penalties if present
- [ ] **EXT-09**: System extracts provider name and plan identifier

### Storage

- [ ] **DB-01**: SQLite database with normalized schema for plans, charges, and pricing tiers
- [ ] **DB-02**: UNIQUE constraints prevent duplicate plan entries on re-processing
- [ ] **DB-03**: Proper indexes on price, term, renewable_pct for analytical queries
- [ ] **DB-04**: Charge categorization distinguishes base/energy/tdu_delivery charges
- [ ] **DB-05**: Schema supports querying for later analysis, insights, and simulation

### Pipeline

- [ ] **PIPE-01**: Background task processes EFL extraction without blocking API
- [ ] **PIPE-02**: Job status tracking (queued/downloading/extracting/parsing/storing/completed/failed)
- [ ] **PIPE-03**: API endpoint to trigger EFL processing for a plan or batch of plans
- [ ] **PIPE-04**: API endpoint to retrieve parsed EFL data for a plan

### Validation

- [ ] **VAL-01**: Cross-validate extracted prices against Power to Choose API data
- [ ] **VAL-02**: Sanity checks flag negative prices, missing required fields, tier gaps
- [ ] **VAL-03**: Confidence scoring flags low-confidence extractions for review

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Advanced Extraction

- **ADV-01**: Bill simulation engine calculates estimated cost for any usage level
- **ADV-02**: Time-of-use rate extraction (peak/off-peak pricing schedules)
- **ADV-03**: Seasonal rate variation extraction (summer vs winter pricing)
- **ADV-04**: Special terms extraction (bill credits, promotions, autopay discounts)
- **ADV-05**: Rate escalation clause extraction for multi-year plans

### Historical

- **HIST-01**: Track plan price changes over time across multiple EFL versions
- **HIST-02**: Provider pricing pattern analysis

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time EFL monitoring | Plans stable for weeks, batch processing sufficient |
| Multi-state support | Texas only per project constraints |
| OCR for scanned PDFs | EFLs are machine-generated; flag scanned for manual review |
| Terms of Service parsing | Massive legal docs, low signal-to-noise |
| Automatic plan recommendation | Requires user preference modeling |
| UI for EFL data | Backend pipeline first, UI is a separate milestone |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PDF-01 | Phase 1 | Pending |
| PDF-02 | Phase 1 | Pending |
| PDF-03 | Phase 1 | Pending |
| PDF-04 | Phase 1 | Pending |
| LLM-01 | Phase 2 | Pending |
| LLM-02 | Phase 2 | Pending |
| LLM-03 | Phase 2 | Pending |
| LLM-04 | Phase 2 | Pending |
| EXT-01 | Phase 2 | Pending |
| EXT-02 | Phase 2 | Pending |
| EXT-03 | Phase 2 | Pending |
| EXT-04 | Phase 2 | Pending |
| EXT-05 | Phase 2 | Pending |
| EXT-06 | Phase 2 | Pending |
| EXT-07 | Phase 2 | Pending |
| EXT-08 | Phase 2 | Pending |
| EXT-09 | Phase 2 | Pending |
| DB-01 | Phase 3 | Pending |
| DB-02 | Phase 3 | Pending |
| DB-03 | Phase 3 | Pending |
| DB-04 | Phase 3 | Pending |
| DB-05 | Phase 3 | Pending |
| PIPE-01 | Phase 1 | Pending |
| PIPE-02 | Phase 1 | Pending |
| PIPE-03 | Phase 4 | Pending |
| PIPE-04 | Phase 4 | Pending |
| VAL-01 | Phase 4 | Pending |
| VAL-02 | Phase 4 | Pending |
| VAL-03 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 27 total
- Mapped to phases: 27
- Unmapped: 0

---
*Requirements defined: 2026-03-22*
*Last updated: 2026-03-22 after initial definition*
