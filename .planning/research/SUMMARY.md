# Project Research Summary

**Project:** Power to Choose - EFL Parser
**Domain:** PDF document processing pipeline with LLM-powered data extraction
**Researched:** 2026-03-21
**Confidence:** HIGH (stack/architecture), MEDIUM (features/pitfalls)

## Executive Summary

This project adds automated EFL (Electricity Facts Label) PDF parsing to the existing Power to Choose plan comparison tool. EFL documents are standardized Texas PUCT disclosures containing pricing tiers, contract terms, and charges that enable accurate cost comparison beyond the basic API data. The research indicates this is a classic document processing pipeline: download PDFs → extract text → use LLM for structured parsing → validate and store in SQLite. The recommended approach uses pdfplumber for text extraction (strong table handling), LiteLLM + instructor for structured LLM outputs with validation, and a background task queue architecture to handle long-running extractions without blocking the API.

The primary risk is data quality from LLM extraction — free-tier models can produce inconsistent structures, hit rate limits, or fail on edge cases (scanned PDFs, multi-column layouts, long documents exceeding context windows). Mitigation requires strict Pydantic validation, exponential backoff retry logic, PDF format detection before extraction, and separating provider charges from TDU pass-through charges in the schema to enable accurate comparison. Secondary risks include SQLite query performance degradation without proper indexing and duplicate records without unique constraints.

Testing with real EFL samples is critical — feature complexity assumptions and extraction accuracy targets cannot be validated until processing actual provider PDFs (recommended: collect 10-20 representative samples before finalizing roadmap phases).

## Key Findings

### Recommended Stack

The stack leverages existing FastAPI infrastructure and adds specialized PDF processing + LLM integration libraries. Core approach: async-first for concurrent downloads, Pydantic-validated structured outputs from LLMs, SQLite with careful schema design for analytical queries.

**Core technologies:**
- **pdfplumber 0.11.9**: Primary PDF text extraction — excels at structured table detection needed for pricing tiers and charge breakdowns
- **LiteLLM 1.82.5 + instructor 1.14.5**: Unified LLM interface to OpenRouter with automatic structured output validation via Pydantic schemas — eliminates manual JSON parsing and retry logic
- **httpx 0.28.1**: Async HTTP client for concurrent PDF downloads and LLM API calls — required for non-blocking batch processing
- **aiosqlite**: Async SQLite interface for non-blocking database operations in FastAPI routes — prevents event loop blocking
- **pydantic-settings 2.13.1**: Type-safe configuration management for API keys and pipeline settings

**Critical version dependencies:** All packages require Pydantic v2.x (already in use with FastAPI). No OCR libraries needed initially (EFLs are typically machine-generated PDFs, not scanned documents).

### Expected Features

Feature priority is driven by data completeness for accurate cost comparison (Phase 1 table stakes) followed by advanced analysis capabilities (Phase 2 differentiators).

**Must have (table stakes):**
- **Price per kWh extraction** (500/1000/2000 tier benchmarks) — core comparison metric, legally required in EFLs
- **Base charge and TDU delivery charges** — completes total cost calculation, TDU must be separated from provider charges
- **Contract term and early termination fee** — high-impact consumer decision factors
- **Plan type and renewable percentage** — basic classification and filtering

**Should have (competitive):**
- **Bill simulation engine** — calculate estimated bill for any usage level, major differentiator requiring accurate extraction of all charges and tiers
- **Usage tier boundaries** — enables precise cost modeling beyond standard benchmarks
- **Special terms extraction** (bill credits, promotions, autopay discounts) — high value for discovering "hidden value" but complex unstructured text parsing

**Defer (v2+):**
- **Time-of-use rate extraction** — complex table structures, smaller plan subset, needs TOU detection first
- **Seasonal rate variations** — lower frequency, can calculate from examples
- **Historical pricing comparison** — requires time-series data accumulation over multiple scraping runs

**Anti-features (explicitly avoid):**
- Real-time PDF monitoring (high complexity, plans stable for weeks)
- Multi-state support (Texas-only per project constraints)
- OCR for handwritten content (EFLs are professionally generated)
- Automatic plan recommendation (requires user preference modeling, out of scope)

### Architecture Approach

Standard document processing pipeline with async task queue architecture. API accepts job requests (202 Accepted), returns job ID immediately, processes in background with progress tracking via status endpoint. Key pattern: fail-fast error handling at each stage (download → extract → parse → store) to prevent cascade of corrupt data.

**Major components:**
1. **API Layer (FastAPI routers)** — trigger endpoint (POST /efl/process), status endpoint (GET /efl/status/{job_id}), results endpoint (GET /efl/results/{plan_id})
2. **Processing Layer (background tasks)** — PDF downloader (httpx with retry), LLM extractor (LiteLLM + instructor), parser (Pydantic validation), orchestrator (pipeline coordination)
3. **Storage Layer** — SQLite for structured EFL data + job status tracking, filesystem cache for downloaded PDFs

**Data flow:** Job enqueued → PDF downloaded and cached → text extracted via pdfplumber → LLM called with structured schema → Pydantic validates output → stored in SQLite → job status updated to complete. State transitions: queued → downloading → extracting → parsing → storing → completed (or failed at any stage).

**Scaling strategy:** Start with FastAPI BackgroundTasks (sufficient for 1-100 plans), migrate to arq (async Redis queue) if needing better job management for 100+ plans, switch to PostgreSQL only if concurrent write bottleneck emerges (>10 concurrent writers).

### Critical Pitfalls

Top 5 pitfalls with highest impact on data quality and reliability:

1. **Scanned vs. text-based PDF detection failure** — Pipeline attempts text extraction on scanned image PDFs with no extractable text, wasting LLM credits on empty content. Prevention: detect via text length threshold (<50 chars = scanned), route to vision model or manual review. Address in Phase 1.

2. **Free-tier model rate limits without exponential backoff** — nvidia/nemotron free tier has aggressive rate limits, pipeline fails after 5-10 PDFs without retry logic. Prevention: use tenacity library with exponential backoff + jitter, queue-based sequential processing, checkpoint progress. Address in Phase 2.

3. **SQLite schema without ANALYZE and missing indexes** — Analytical queries perform full table scans, queries that should take milliseconds take seconds as data grows. Prevention: run `PRAGMA optimize` after schema creation and bulk inserts, design indexes with query patterns in mind, use `EXPLAIN QUERY PLAN` to verify. Address in Phase 3.

4. **Pricing tier extraction without structured schema validation** — LLM produces inconsistent JSON structures (arrays vs objects vs flat text), downstream analysis crashes or produces wrong comparisons. Prevention: strict JSON schema in prompt, Pydantic validation enforces types/ranges, log failures for debugging. Address in Phase 2 + Phase 4.

5. **TDU charge confusion (pass-through vs provider charge)** — Schema treats all charges identically, incorrectly attributes regulated TDU fees to provider, making plans appear more expensive than they are. Prevention: separate schema columns with charge_type categorization, LLM prompt explicitly requests distinction, validate TDU consistency across plans. Address in Phase 3 (schema) + Phase 2 (prompt).

**Additional high-risk pitfalls:**
- PDF layout ambiguity (whitespace collapse in multi-column layouts) — use pdfplumber with coordinates instead of pypdf
- No duplicate detection across re-runs — implement UNIQUE constraint on (plan_id, company_id, effective_date)
- Free-tier context window overflow for long PDFs — implement token counting and page-by-page extraction strategy

## Implications for Roadmap

Research suggests 4-phase structure: foundation (PDF processing + infrastructure) → core extraction (LLM integration + validation) → data modeling (schema + storage) → analysis capabilities (bill simulation).

### Phase 1: PDF Processing Infrastructure
**Rationale:** Must establish reliable PDF download, caching, and format detection before any LLM work. Prevents wasted LLM credits on unusable PDFs and establishes async patterns for batch processing.

**Delivers:**
- PDF download service with httpx async client and retry logic
- Filesystem cache with path management
- Scanned vs text-based PDF detection (text length threshold)
- Background task orchestration (FastAPI BackgroundTasks for MVP)
- Job status tracking schema and API endpoints

**Addresses features:**
- Foundation for all downstream features (enables extraction)

**Avoids pitfalls:**
- Pitfall #1: Scanned PDF detection prevents wasted LLM calls
- PDF download timeouts and provider CDN issues

**Research flag:** Standard patterns, no deep research needed (well-documented httpx/asyncio patterns).

---

### Phase 2: LLM Integration + Structured Extraction
**Rationale:** Core value proposition depends on accurate structured data extraction. Must implement retry logic, validation, and prompt engineering before attempting complex features. Validates extraction accuracy early with real EFL samples.

**Delivers:**
- LiteLLM + instructor integration with OpenRouter
- Pydantic models for EFL data schema (pricing tiers, charges, contract terms)
- Exponential backoff retry logic for rate limits
- Token counting and context window overflow handling
- Prompt engineering for charge categorization (provider vs TDU)
- Extraction validation pipeline (sanity checks, confidence scoring)

**Addresses features:**
- Price per kWh extraction (tiered pricing)
- Base charge extraction
- Contract term and ETF extraction
- Plan type and renewable % classification
- TDU charge extraction with categorization

**Avoids pitfalls:**
- Pitfall #2: Rate limit handling with tenacity retry
- Pitfall #4: Pydantic validation prevents inconsistent structures
- Pitfall #5: Prompt explicitly requests charge type distinction
- Pitfall #7: Token counting prevents context overflow

**Research flag:** NEEDS RESEARCH — Limited documentation on nvidia/nemotron behavior, OpenRouter free-tier rate limits not published, prompt engineering for EFL structure requires experimentation with real samples. Recommend `/gsd:research-phase` for LLM extraction patterns after collecting sample EFLs.

---

### Phase 3: Data Schema + Storage Layer
**Rationale:** Schema design affects all future analytical capabilities. Must separate provider charges from TDU charges, prevent duplicates, and design indexes for query patterns before bulk data insertion.

**Delivers:**
- SQLite schema with proper normalization (plans, charges, pricing_tiers tables)
- UNIQUE constraints on (plan_id, company_id, effective_date) to prevent duplicates
- Indexes designed for analytical queries (WHERE clauses on price/term/renewable_pct)
- Charge categorization (base/energy/tdu_delivery/tdu_other)
- Upsert pattern for re-processing plans
- `PRAGMA optimize` execution after bulk inserts

**Addresses features:**
- Foundation for bill simulation (structured charges table)
- Enables filtering/comparison queries in UI

**Avoids pitfalls:**
- Pitfall #3: Indexes + ANALYZE prevent query performance degradation
- Pitfall #5: Charge categorization schema separates TDU from provider
- Pitfall #6: UNIQUE constraints prevent duplicate records

**Research flag:** Standard SQL patterns, no deep research needed. Schema design can be informed by FEATURES.md requirements.

---

### Phase 4: Data Validation + Quality Assurance
**Rationale:** Cannot trust LLM extractions without validation against known sources. Validation enables confidence scoring and flags plans needing manual review, preventing bad data from reaching users.

**Delivers:**
- Cross-validation against Power to Choose API data (compare extracted prices to API pricing_details)
- Sanity checks (negative prices, missing required fields, tier gaps)
- Confidence scoring (flag low-confidence extractions for review)
- Extraction accuracy metrics (track success rate by provider)
- Manual review queue for failed/low-confidence extractions

**Addresses features:**
- Data quality requirements (99% pricing accuracy target)
- Enables trust in bill simulation results

**Avoids pitfalls:**
- Pitfall #4: Validation catches pricing tier inconsistencies
- TDU charge validation (should be similar across plans for same zip code)

**Research flag:** Standard validation patterns, no deep research needed.

---

### Phase 5: Advanced Analysis + Bill Simulation
**Rationale:** Depends on accurate Phase 2 extractions and Phase 3 schema. Bill simulation is major differentiator but requires complete charge data including special terms.

**Delivers:**
- Bill simulation API endpoint (input: usage kWh, output: estimated cost breakdown)
- Usage tier boundary interpolation for non-standard usage levels
- Special terms extraction (bill credits, promotions, autopay discounts)
- Provider-only cost vs total cost comparison
- Cost comparison API for multiple plans

**Addresses features:**
- Bill simulation engine (key differentiator)
- Usage tier boundaries
- Special terms extraction

**Avoids pitfalls:**
- TDU charge separation enables accurate provider comparison

**Research flag:** NEEDS RESEARCH — Special terms extraction is unstructured text parsing, high variability expected. May need separate research on pattern matching or rule-based extraction vs LLM approach.

---

### Phase Ordering Rationale

**Dependency flow:** Cannot extract (Phase 2) without reliable downloads (Phase 1). Cannot store extractions (Phase 3) without validated data structures (Phase 2). Cannot validate (Phase 4) without stored data (Phase 3). Cannot simulate bills (Phase 5) without complete validated charges (Phase 4).

**Risk mitigation order:** Tackle rate limits and validation (Phase 2) early to avoid batch processing failures. Establish schema with proper constraints (Phase 3) before bulk inserts to prevent cleanup later. Defer advanced features (Phase 5) until core extraction proven reliable.

**Complexity grouping:** Phase 1 is infrastructure (standard async patterns). Phase 2 is AI/ML integration (most uncertain, needs experimentation). Phase 3-4 are data engineering (predictable, best practices well-documented). Phase 5 is domain logic (builds on solid foundation).

**MVP cutline:** Phases 1-4 deliver complete extraction pipeline with validation. Phase 5 adds analysis capabilities but MVP could launch with basic filtered plan comparison using extracted data.

### Research Flags

Phases likely needing deeper research during planning:

- **Phase 2 (LLM Integration):** nvidia/nemotron model behavior, OpenRouter rate limits, prompt engineering for EFL structure — requires experimentation with real EFL samples before finalizing approach. Recommend `/gsd:research-phase` after collecting 10-20 sample EFLs.

- **Phase 5 (Special Terms Extraction):** Unstructured text parsing strategies (LLM vs rule-based vs hybrid), high variability in promotional language across providers — may need pattern analysis of sample EFLs.

Phases with standard patterns (skip research-phase):

- **Phase 1 (PDF Processing):** Well-documented httpx/asyncio patterns, FastAPI background tasks documented in official docs
- **Phase 3 (Schema Design):** Standard SQL normalization and indexing patterns
- **Phase 4 (Validation):** Standard data quality patterns (cross-reference, sanity checks, metrics)

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified from PyPI, library capabilities well-documented, version compatibility checked |
| Features | MEDIUM | Table stakes features identified from domain knowledge and existing plan data structure, but complexity assumptions unvalidated without real EFL samples |
| Architecture | HIGH | Standard document processing pipeline patterns, FastAPI async best practices well-established |
| Pitfalls | MEDIUM | SQLite/LiteLLM pitfalls verified from official docs, EFL-specific pitfalls (TDU charge confusion, tier extraction) inferred from domain knowledge but not tested |

**Overall confidence:** MEDIUM-HIGH

Stack and architecture are HIGH confidence (verified sources, established patterns). Features and pitfalls are MEDIUM confidence due to lack of real EFL PDF samples — complexity assumptions and extraction accuracy targets need validation during Phase 2 implementation.

### Gaps to Address

**Critical gap: Real EFL samples not analyzed**
- Cannot validate feature complexity assumptions (table structure variability, TDU charge formatting, special terms prevalence)
- Cannot test extraction accuracy with chosen LLM model
- Cannot confirm provider PDF format consistency
- **Resolution:** Collect 10-20 representative EFL samples (diverse providers, plan types) before finalizing Phase 2 approach. Consider quick prototype of extraction to validate LLM capability before committing to roadmap.

**Moderate gap: nvidia/nemotron model capabilities unknown**
- Free-tier rate limits not documented by OpenRouter
- Context window size unclear (assumed 4K-8K but unverified)
- Structured output reliability unknown (how well does it follow JSON schemas?)
- **Resolution:** Test with sample EFLs in Phase 2, implement fallback model list if primary model underperforms.

**Minor gap: Power to Choose API data coverage for validation**
- Unclear if API provides detailed pricing tiers for cross-validation
- May need to rely on high-level price matches (500/1000/2000 kWh benchmarks only)
- **Resolution:** Check API response structure during Phase 4, adjust validation strategy based on available fields.

**Minor gap: Provider PDF URL stability**
- Unknown if fact_sheet URLs are permanent or temporary CDN links
- May need re-downloading strategy if URLs expire
- **Resolution:** Implement aggressive caching in Phase 1, store local paths as primary reference.

## Sources

### Primary (HIGH confidence)
- **STACK.md:** Python package versions verified from PyPI (pdfplumber 0.11.9, LiteLLM 1.82.5, instructor 1.14.5, httpx 0.28.1, pydantic 2.12.5, pydantic-settings 2.13.1, pytest 9.0.2)
- **ARCHITECTURE.md:** FastAPI official docs (background tasks, async patterns), aiosqlite patterns, arq/RQ task queue architectures
- **PITFALLS.md:** SQLite official docs (query optimization, ANALYZE), LiteLLM exception mapping docs, OpenAI rate limit best practices

### Secondary (MEDIUM confidence)
- **FEATURES.md:** Texas PUCT EFL requirements (training data), existing plan data structure from codebase (types/plan.ts, PlanTable.tsx)
- **PITFALLS.md:** EFL format variability (inferred from domain knowledge, not verified with samples), TDU charge standardization (Texas electricity market structure from training data)

### Tertiary (LOW confidence, needs validation)
- **nvidia/nemotron model specifications:** Rate limits, context window size, structured output reliability — not documented by OpenRouter, assumed similar to other free-tier models
- **EFL parsing complexity:** Table structure variability, special terms prevalence — assumptions not validated without real PDF samples

---
*Research completed: 2026-03-21*
*Ready for roadmap: Yes (with recommendation to collect sample EFLs before Phase 2)*
