# Pitfalls Research

**Domain:** PDF Parsing + LLM Extraction for Energy Pricing Documents
**Researched:** 2026-03-21
**Confidence:** MEDIUM (verified official docs for SQLite/LiteLLM, training data for domain-specific EFL patterns)

## Critical Pitfalls

### Pitfall 1: Scanned vs. Text-Based PDF Detection Failure

**What goes wrong:**
Pipeline treats all PDFs identically, attempting text extraction on scanned image PDFs (which contain no extractable text) and wasting LLM credits on empty content, or worse, sending multipage text PDFs to vision models when simple text extraction would suffice.

**Why it happens:**
EFL PDFs from Texas providers vary wildly — some are generated programmatically (text-based), others are scanned documents (image-based), and some are hybrid (text with embedded image tables). Developers assume one extraction strategy fits all.

**How to avoid:**
1. **Detection phase first**: Use pypdf to attempt text extraction before LLM call
2. **Threshold check**: If extracted text < 50 characters for a multi-page PDF, treat as scanned
3. **Fallback strategy**: Route text-based PDFs to simple extraction, image-based to vision model
4. **Log classification**: Track which providers consistently use which format for optimization

```python
# Detection pattern
text = pypdf.extract_text(pdf)
if len(text.strip()) < 50 and page_count > 1:
    strategy = "vision_model"  # Scanned document
else:
    strategy = "text_extraction"  # Text-based PDF
```

**Warning signs:**
- LLM responses with "No text found" or empty extractions
- High token usage with minimal structured output
- Vision model costs applied to text-only documents
- Extraction success rate < 70% across all providers

**Phase to address:**
Phase 1 (PDF Download & Classification) — detection logic must exist before any LLM calls

---

### Pitfall 2: Free-Tier Model Rate Limits Without Exponential Backoff

**What goes wrong:**
Free-tier models (nvidia/nemotron) have aggressive rate limits. Without proper retry logic, the pipeline fails silently or crashes after processing 5-10 PDFs, requiring manual restart and losing progress. Continuous resending of failed requests burns through rate limit quota without making progress.

**Why it happens:**
Free-tier LLMs are quota-limited (requests per minute, tokens per day). Developers test with 1-2 PDFs successfully, then run batch processing on 100+ plans and hit walls. OpenRouter doesn't provide detailed rate limit headers, making it hard to detect limits proactively.

**How to avoid:**
1. **Exponential backoff with jitter**: Use tenacity/backoff library, not manual sleep
2. **Queue-based processing**: Process PDFs sequentially with delays, not parallel batch
3. **Checkpoint progress**: Save extraction state after each PDF to resume on failure
4. **Rate limit buffer**: If free tier allows 10 req/min, throttle to 6-7 req/min
5. **Timeout handling**: Set LiteLLM timeout to 60s (free models can be slow)

```python
from tenacity import retry, wait_random_exponential, stop_after_attempt

@retry(
    wait=wait_random_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5)
)
def extract_with_llm(pdf_content):
    return litellm.completion(model="openrouter/nvidia/nemotron...", ...)
```

**Warning signs:**
- Sudden failures after initial success (5-10 PDFs processed, then errors)
- `RateLimitError` or `429` status codes in logs
- LiteLLM timeout errors after 30+ seconds
- Processing queue stalls without error messages

**Phase to address:**
Phase 2 (LLM Integration) — retry logic must be implemented from day one, tested with 20+ PDFs

---

### Pitfall 3: SQLite Schema Without ANALYZE and Missing Indexes

**What goes wrong:**
Analytical queries (e.g., "find all plans with base charge > $10 AND TDU delivery < $0.05 for 1000 kWh usage") perform full table scans. Without running `ANALYZE`, SQLite cannot optimize join orders or use skip-scan indexes. Queries that should take milliseconds take seconds as data grows.

**Why it happens:**
Developers design schema, add indexes, but never run `PRAGMA optimize` or `ANALYZE`. SQLite defaults to guessing data distribution (assumes 10 duplicates per value), leading to suboptimal query plans. Common mistake: adding indexes on non-selective columns (like boolean flags) without statistics.

**How to avoid:**
1. **Run `PRAGMA optimize` after initial schema creation and after bulk inserts**
2. **Design indexes with query patterns in mind**:
   - Equality constraints first, then inequalities
   - Covering indexes for frequently accessed columns (avoid double lookups)
3. **Use `EXPLAIN QUERY PLAN` to verify index usage during development**
4. **Avoid gaps in index column usage** (if index is `(plan_id, company_id, price)`, can't use `price` if `company_id` is unconstrained)
5. **Index left-most columns used in WHERE clauses**

**Warning signs:**
- Queries slow down significantly after 500+ plans inserted
- `EXPLAIN QUERY PLAN` shows "SCAN TABLE" instead of "SEARCH TABLE USING INDEX"
- Identical queries have inconsistent performance (no statistics = bad guesses)
- Joins between plans/charges tables take >100ms

**Phase to address:**
Phase 3 (Schema Design) — schema must be designed with query patterns in mind; Phase 4 (Data Storage) — `ANALYZE` must run after initial bulk insert

---

### Pitfall 4: Pricing Tier Extraction Without Structured Schema Validation

**What goes wrong:**
EFL documents have tiered pricing (e.g., 0-500 kWh @ $0.12, 501-1000 @ $0.10, 1000+ @ $0.08). LLM extraction produces inconsistent JSON structures — sometimes an array, sometimes nested objects, sometimes flat text. Downstream analysis code crashes when encountering unexpected structures, and incorrect tier assignments lead to wrong price comparisons.

**Why it happens:**
LLMs are probabilistic. Even with JSON schema prompts, free-tier models may hallucinate structures, merge tiers incorrectly, or extract partial data. Developers trust LLM output without validation because initial tests pass with well-formatted PDFs.

**How to avoid:**
1. **Strict JSON schema in LLM prompt** with required fields and types:
```json
{
  "pricing_tiers": [
    {"min_kwh": 0, "max_kwh": 500, "rate_per_kwh": 0.12},
    {"min_kwh": 501, "max_kwh": 1000, "rate_per_kwh": 0.10},
    {"min_kwh": 1001, "max_kwh": null, "rate_per_kwh": 0.08}
  ]
}
```
2. **Pydantic validation** after LLM extraction to enforce types, ranges, and required fields
3. **Sanity checks**: Tiers must be contiguous (no gaps), non-overlapping, and rates must be numeric > 0
4. **Fallback to null + manual review flag** if validation fails (don't crash, don't store garbage)
5. **Log validation failures with PDF URL** for debugging/reprocessing

**Warning signs:**
- Extraction success rate < 90% for a single provider's PDFs
- Price comparison results seem incorrect (lower usage showing higher cost)
- Database contains `null` values for pricing tiers
- JSON parsing errors in logs

**Phase to address:**
Phase 2 (LLM Integration) — schema design and validation logic; Phase 4 (Data Storage) — validation enforcement before DB insert

---

### Pitfall 5: Ignoring PDF Layout Ambiguity (Whitespace Collapse)

**What goes wrong:**
PDF text extraction collapses multi-column layouts into single-column text, merging unrelated content. For example, a two-column EFL table (left: "Base Charge $9.95", right: "TDU Delivery $0.04") becomes "Base Charge $9.95TDU Delivery $0.04" with no separation, causing LLM to misparse values or attribute charges incorrectly.

**Why it happens:**
PDFs use absolute positioning, not semantic structure. pypdf extracts text in reading order but cannot infer logical groupings. EFL documents frequently use tables with minimal spacing, and text extraction tools guess at word boundaries, often incorrectly.

**How to avoid:**
1. **Preserve layout in extraction** using pdfplumber's `extract_words()` with coordinates instead of pypdf's `extract_text()`
2. **Pass raw extracted text + coordinates to LLM** if using vision model (it can see layout)
3. **LLM prompt engineering**: Explicitly instruct model to "ignore layout artifacts, focus on semantic meaning"
4. **Post-extraction cleanup**: Normalize whitespace, split on known delimiters (e.g., "$" indicates new charge)
5. **Validate against expected structure**: Base charge, energy charge, and TDU charge should be separate fields

**Warning signs:**
- LLM extracts compound values (e.g., `"base_charge": "9.95 TDU Delivery 0.04"`)
- Missing fields that are visually present in PDF
- Charges assigned to wrong categories
- Inconsistent extraction between structurally similar PDFs from same provider

**Phase to address:**
Phase 1 (PDF Processing) — choose extraction library and approach; Phase 2 (LLM Integration) — prompt engineering and structure enforcement

---

### Pitfall 6: No Duplicate Detection Across Re-Runs

**What goes wrong:**
Running the pipeline multiple times (e.g., daily updates, error recovery) inserts duplicate plan records because there's no unique constraint or duplicate detection logic. Database grows unbounded with redundant entries, and analysis queries produce incorrect aggregates (double-counting plans).

**Why it happens:**
Power to Choose API returns plan listings with IDs, but those IDs may not be stable across API calls, or developers don't realize the same plan appears multiple times. Without a composite unique key (e.g., `plan_id + company_id + effective_date`), SQLite allows duplicates.

**How to avoid:**
1. **Composite UNIQUE constraint** on plans table:
```sql
CREATE TABLE plans (
  plan_id TEXT NOT NULL,
  company_id TEXT NOT NULL,
  effective_date DATE NOT NULL,
  -- other fields
  UNIQUE(plan_id, company_id, effective_date)
);
```
2. **Upsert pattern** using `INSERT OR REPLACE` / `INSERT OR IGNORE`
3. **Check PDF URL before download**: If `fact_sheet` URL already processed, skip
4. **Track processing runs** in separate table with timestamps to detect re-processing

**Warning signs:**
- Database size grows linearly with each pipeline run (not just new plans)
- Count of plans in DB >> count of plans from API
- Identical plans with different extraction timestamps
- Analysis shows implausible numbers (e.g., 10 identical plans from same company)

**Phase to address:**
Phase 3 (Schema Design) — UNIQUE constraints defined upfront; Phase 4 (Data Storage) — upsert logic implemented

---

### Pitfall 7: Free-Tier Model Context Window Overflow

**What goes wrong:**
Multi-page EFL PDFs (5-10 pages) with full text extracted exceed free-tier model context windows (nvidia/nemotron may have 4K-8K token limits). LLM truncates input silently, missing critical information on later pages (like early termination fees, contract terms), producing incomplete extractions that pass validation but are missing key data.

**Why it happens:**
Developers test with 2-3 page PDFs successfully, then encounter verbose 10-page documents with legal disclaimers. Token counting is not performed before LLM call, and LiteLLM may silently truncate rather than error.

**How to avoid:**
1. **Token counting before LLM call** using `tiktoken` or LiteLLM's `token_counter`
2. **Page-by-page extraction strategy**: Extract critical pages first (usually page 1-2), then append additional pages if under token budget
3. **Summarization for long documents**: Use two-pass approach — extract full text, then LLM summarizes to structured data
4. **Document length limits**: Skip PDFs > 20 pages (likely include ToS, not pure EFL)
5. **Log token usage per extraction** to detect approaching limits

```python
import tiktoken

enc = tiktoken.encoding_for_model("gpt-3.5-turbo")  # Approximation
token_count = len(enc.encode(pdf_text))
if token_count > 3000:  # Conservative limit for 4K window
    # Truncate or use multi-pass strategy
```

**Warning signs:**
- Structured output missing expected fields for longer PDFs
- Extraction quality drops for PDFs > 5 pages
- LLM responses end mid-sentence or incomplete JSON
- Token usage consistently at maximum for certain providers

**Phase to address:**
Phase 2 (LLM Integration) — token counting and truncation strategy must be implemented early

---

### Pitfall 8: TDU Charge Confusion (Pass-Through vs. Provider Charge)

**What goes wrong:**
EFL documents separate provider charges (base charge, energy charge) from TDU (Transmission/Distribution Utility) pass-through charges. If schema treats all charges identically, analysis incorrectly attributes TDU charges to the provider, making plans appear more expensive than they are. Users cannot compare provider pricing separately from regulated TDU fees.

**Why it happens:**
Domain-specific knowledge gap. Developers unfamiliar with Texas electricity market structure don't realize TDU charges are constant across providers for a given service area, while provider charges vary competitively. LLM extraction may not distinguish charge types without explicit prompting.

**How to avoid:**
1. **Separate schema tables/columns**:
```sql
CREATE TABLE charges (
  plan_id TEXT,
  charge_type TEXT CHECK(charge_type IN ('base', 'energy', 'tdu_delivery', 'tdu_other')),
  amount REAL,
  unit TEXT  -- 'fixed' or 'per_kwh'
);
```
2. **LLM prompt explicitly requests charge categorization**: "Separate provider charges from TDU pass-through charges"
3. **Validation rule**: TDU charges should be similar across plans for same zip code/TDU
4. **Display logic**: Show provider-only cost vs. total cost in UI

**Warning signs:**
- TDU charges vary wildly between providers in same service area (should be ~identical)
- Total cost calculations don't match Power to Choose website estimates
- Users complain about incorrect price comparisons
- All charges stored in single undifferentiated column

**Phase to address:**
Phase 3 (Schema Design) — charge categorization designed upfront; Phase 2 (LLM Integration) — prompt explicitly requests charge type distinction

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip Pydantic validation, store raw LLM JSON | Faster development, no schema design | Inconsistent data structures break analysis queries, no type safety | Never — validation is <50 lines, prevents data corruption |
| Process all PDFs in parallel with asyncio | Faster batch processing | Hits rate limits immediately, no progress tracking, hard to debug failures | Only if using paid tier with high rate limits |
| Store extracted text as single TEXT blob in DB | Simple schema, flexible | No structured queries possible, must re-extract for analysis, defeats purpose | Never — defeats entire project goal |
| Use generic "charge" field without categorization | Simpler extraction prompt | Cannot separate provider vs. TDU charges, comparisons incorrect | Never for production; acceptable for Phase 1 prototype |
| No duplicate detection, allow re-inserts | Simpler insertion logic, no upsert complexity | Database bloat, incorrect aggregates, wasted storage | Only during initial development with small test datasets |
| Manual batch processing (no queue/progress tracking) | Fewer dependencies, simpler code | Cannot resume on failure, manual monitoring required, no retry on error | Never for 100+ PDFs; acceptable for <10 PDF testing |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| OpenRouter via LiteLLM | Not setting timeout, requests hang indefinitely on slow free-tier models | Set `timeout=60` in litellm.completion() call, handle timeout exceptions |
| OpenRouter via LiteLLM | Assuming error codes match OpenAI's exactly | LiteLLM maps OpenRouter errors to OpenAI-style but may have gaps; catch generic `Exception` with logging |
| Power to Choose API | Assuming EFL URLs are permanent/stable | URLs may be CDN links that expire; download and cache PDFs immediately, store local paths |
| OpenRouter free-tier | Not checking model availability (free models can be removed/changed) | Implement fallback model list, check OpenRouter model list API periodically |
| pypdf extraction | Assuming `extract_text()` returns clean, parseable text | Text may have encoding issues, missing spaces, or be completely empty; validate length and sanity before LLM call |
| SQLite writes | Opening multiple write connections in parallel | SQLite locks database file for writes; use single writer with queue or WAL mode |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Full table scans without indexes | Queries slow as data grows; CPU usage high on analytical queries | Add indexes on WHERE clause columns, run ANALYZE | >500 plans in database, or complex JOIN queries |
| Storing extracted full text in every record | Database file size >> disk space, backups slow | Store extracted text only if needed for re-parsing; or store separately with plan_id FK | >1000 PDFs extracted (each ~10KB text = 10MB+ db bloat) |
| Synchronous PDF downloads blocking LLM calls | Pipeline waits for slow provider CDNs before extraction starts | Decouple download and extraction phases; download all PDFs first, then batch extract | >50 PDFs, especially if provider CDNs are slow |
| No connection pooling for LiteLLM calls | Each extraction creates new HTTP session, overhead adds up | Reuse httpx.AsyncClient if using async; LiteLLM handles this internally but verify | >100 extractions in single run |
| Unbounded memory for PDF content | Loading all PDFs into memory before processing | Stream processing: download → extract → store → discard; process one at a time | >100 PDFs or large multi-page documents |
| No batch insertion to SQLite | Individual INSERT per charge/tier line (5-10 INSERTs per plan) | Use transactions with BEGIN/COMMIT around batch; or bulk INSERT with executemany() | >100 plans, insertion time becomes bottleneck (disk I/O) |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing OpenRouter API key in code/repo | Key exposure → unauthorized usage, quota theft | Use environment variables, never commit .env files, rotate keys regularly |
| Not sanitizing PDF URLs before download | SSRF attack: malicious plan listing with internal URL (e.g., http://localhost) | Validate URLs are HTTPS and from known provider domains before download |
| Trusting LLM-extracted data without validation | LLM hallucinates negative prices or SQL injection attempts in extracted text | Pydantic validation with strict types; treat LLM output as untrusted user input |
| Exposing SQLite database file via web endpoint | Direct database access, data exfiltration | Never serve .db file directly; use API layer with query sanitization |
| No rate limiting on API endpoints that trigger extraction | Abuse: attacker triggers 1000s of expensive LLM calls, burns through API quota | Rate limit extraction endpoints; require authentication; queue extractions with backpressure |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Showing "extraction in progress" with no ETA or progress indicator | Users don't know if system is working or stuck | Show progress bar (X of Y PDFs processed), estimated time remaining |
| Displaying incomplete/failed extractions as valid plans | Users make decisions on incorrect data, trust erodes | Mark incomplete extractions as "pending manual review", show confidence score |
| Not explaining why some plans have detailed data and others don't | Users assume incomplete data is your fault, not provider's | Show "PDF extraction failed" badge with reason (e.g., "scanned document, manual review needed") |
| Comparing plans without separating TDU charges | Users think one provider is 50% more expensive when it's just TDU formatting difference | Show "Provider charges only" vs "Total including TDU" with toggle |
| No way to report incorrect extractions | Users find bad data, have no feedback mechanism, abandon tool | Add "Report incorrect data" button per plan, stores PDF URL + user comment for manual review |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **LLM Integration:** Often missing timeout configuration — verify litellm.completion() has explicit timeout=60 and exception handling
- [ ] **PDF Extraction:** Often missing empty text detection — verify that text length is checked before sending to LLM (don't waste credits on blank extractions)
- [ ] **Schema Design:** Often missing UNIQUE constraints — verify plans table has composite key to prevent duplicates
- [ ] **Retry Logic:** Often missing exponential backoff — verify using tenacity/backoff library, not manual sleep() in try/except
- [ ] **Data Validation:** Often missing post-LLM Pydantic validation — verify extracted JSON is validated before database insertion
- [ ] **Index Creation:** Often missing ANALYZE — verify PRAGMA optimize runs after schema creation and initial data load
- [ ] **Rate Limit Handling:** Often missing progress checkpointing — verify pipeline can resume from partial state without re-downloading/re-extracting
- [ ] **Error Logging:** Often missing PDF URL in error logs — verify that extraction failures log the specific plan_id + fact_sheet URL for debugging

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Duplicate plans in DB | LOW | Add UNIQUE constraint, run DELETE to remove duplicates keeping most recent, re-run upsert logic |
| Missing indexes causing slow queries | LOW | Add indexes with CREATE INDEX, run ANALYZE, re-test query performance with EXPLAIN QUERY PLAN |
| Rate limit exhaustion mid-batch | MEDIUM | Implement queue with progress tracking, resume from last successful extraction, add exponential backoff |
| Incorrect charge categorization | MEDIUM | Update LLM prompt to explicitly request charge types, re-extract all plans (keep old data for comparison) |
| Context window overflow for long PDFs | MEDIUM | Implement page-by-page extraction, re-extract affected plans (identifiable by missing fields) |
| Whitespace collapse corrupting extractions | HIGH | Switch extraction library (pypdf → pdfplumber), re-extract all plans with new approach |
| No scanned PDF detection | MEDIUM | Add detection logic, re-scan all PDFs to classify, route scanned PDFs to vision model or manual review |
| LLM output validation missing | HIGH | Implement Pydantic validation, audit all existing DB records for invalid data, mark suspicious records for re-extraction |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Scanned vs. text-based PDF detection failure | Phase 1: PDF Processing | Test with mixed PDF set (text + scanned), log classification results, verify >90% correct classification |
| Free-tier model rate limits without exponential backoff | Phase 2: LLM Integration | Batch test with 20 PDFs, intentionally hit rate limit, verify retry logic succeeds without manual intervention |
| SQLite schema without ANALYZE and missing indexes | Phase 3: Schema Design | Run EXPLAIN QUERY PLAN on all analytical queries, verify "SEARCH TABLE USING INDEX" not "SCAN TABLE" |
| Pricing tier extraction without structured schema validation | Phase 2: LLM Integration + Phase 4: Data Storage | 100% of extractions pass Pydantic validation before insert; zero null values in pricing_tiers |
| Ignoring PDF layout ambiguity (whitespace collapse) | Phase 1: PDF Processing | Manual review of 10 extractions, verify no compound values or missing fields due to layout issues |
| No duplicate detection across re-runs | Phase 3: Schema Design | Run pipeline twice on same dataset, verify DB has same row count before and after |
| Free-tier model context window overflow | Phase 2: LLM Integration | Test with longest known EFL PDF (10+ pages), verify no truncation or token count < model limit |
| TDU charge confusion (pass-through vs provider charge) | Phase 3: Schema Design + Phase 2: LLM Prompt Engineering | Compare extracted TDU charges across 3 plans for same zip code, verify similarity within 10% |

## Sources

**Official Documentation (MEDIUM-HIGH confidence):**
- SQLite Query Optimization: https://www.sqlite.org/optoverview.html (indexed query patterns, ANALYZE importance)
- SQLite FAQ: https://www.sqlite.org/faq.html (transaction batching, type affinity, performance)
- pypdf Documentation: https://pypdf.readthedocs.io/en/stable/user/extract-text.html (text extraction limitations, whitespace issues, memory constraints)
- LiteLLM Exception Mapping: https://docs.litellm.ai/docs/exception_mapping (error handling patterns)
- LiteLLM OpenRouter Provider: https://docs.litellm.ai/docs/providers/openrouter (configuration, no explicit gotchas documented)
- OpenAI Rate Limit Cookbook: https://github.com/openai/openai-cookbook/.../How_to_handle_rate_limits.ipynb (exponential backoff, jitter, retry patterns)

**Training Data (LOW-MEDIUM confidence):**
- Texas electricity market structure (TDU vs. provider charges) — verified via training knowledge of ERCOT market, not official documentation
- EFL document format variability — inferred from project context + general knowledge of utility document practices
- nvidia/nemotron model limitations — not verified in official docs (no documentation found), assumed similar to other free-tier LLMs

**Project Context (HIGH confidence):**
- Power to Choose API structure: Verified from existing codebase (api/main.py, ui/src/components/PlanTable.tsx)
- EFL PDF URLs from plan listings: Verified from existing code showing fact_sheet field

---
*Pitfalls research for: EFL PDF Parsing + LLM Extraction Pipeline*
*Researched: 2026-03-21*
