# Feature Landscape: EFL Document Parsing

**Domain:** Texas electricity plan document parsing and analysis
**Researched:** 2026-03-21
**Confidence:** MEDIUM (based on domain knowledge, existing plan data structure, and Texas electricity market requirements)

## Table Stakes

Features users expect from EFL parsing. Missing = data is incomplete or unusable for comparison.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Price per kWh extraction** | Core comparison metric, legally required in EFL | Medium | Must handle tiered pricing (500/1000/2000 kWh), variable rates, seasonal rates |
| **Base charge extraction** | Fixed monthly fee, critical for total cost calculation | Low | Usually single line item, but may be embedded in tables |
| **Contract term length** | Determines commitment period, affects early termination | Low | Usually explicit (1, 6, 12, 24, 36 months) |
| **Early termination fee (ETF)** | Major financial risk factor for consumers | Low | May be flat fee or per-month-remaining calculation |
| **TDU delivery charges** | Pass-through charges from utility, affects total cost | Medium | Often in footnotes or separate section, varies by TDU |
| **Renewable energy percentage** | Required PUCT disclosure, consumer decision factor | Low | Usually explicit percentage (0-100%) |
| **Plan type classification** | Fixed vs variable rate distinction | Low | Affects price stability and risk |
| **Minimum usage charges** | Penalty fees if usage below threshold | Medium | May have complex conditions or monthly minimums |
| **Provider contact info** | Company name, phone, website for enrollment | Low | Usually standardized in header/footer |
| **Plan name and ID** | Links parsed data back to source plan listing | Low | Unique identifier for database correlation |

## Differentiators

Features that enable advanced analysis and simulation. Not expected baseline, but high value-add.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Bill simulation engine** | Calculate estimated bill for any usage level | High | Requires accurate extraction of all charges, tiers, and conditions; enables personalized recommendations |
| **Time-of-use (TOU) rate extraction** | Parse peak/off-peak/super-peak pricing schedules | High | Complex table structures, multiple rate periods, seasonal variations |
| **Seasonal rate variations** | Extract summer vs winter pricing differences | High | Some plans have different rates by season; critical for annual cost projection |
| **Usage tier boundaries** | Identify exact kWh thresholds for rate changes | Medium | Enables precise cost modeling beyond 500/1000/2000 benchmarks |
| **Special terms extraction** | Capture bill credits, promotions, autopay discounts | High | Unstructured text, varies widely by provider; high value for "hidden value" discovery |
| **Rate escalation clauses** | Extract future price increase schedules | Medium | Multi-year plans may have year 2+ rate increases; often buried in fine print |
| **Cancellation policy details** | Extract conditions, notice requirements, refund terms | Medium | Beyond just ETF amount, full policy understanding |
| **Promotional credit tracking** | Identify first-month credits, sign-up bonuses, etc. | Medium | Affects true cost comparison; often time-limited |
| **Green energy source breakdown** | Wind vs solar vs other renewable percentages | Low | Beyond total %, shows renewable mix; increasingly requested data |
| **Historical pricing comparison** | Track plan price changes over time | Medium | Requires storing multiple EFL versions; detects provider patterns |
| **Contract auto-renewal terms** | Extract renewal conditions and rate changes | Medium | Critical for long-term cost planning |
| **Demand charge detection** | Identify commercial-style demand billing | Medium | Rare in residential but exists; requires different modeling |

## Anti-Features

Features to explicitly NOT build in initial pipeline.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Real-time PDF monitoring** | High complexity, low ROI in v1, most plans stable for weeks | Batch download on-demand or scheduled daily; store EFL URLs and fetch when needed |
| **OCR for handwritten content** | EFLs are professionally generated PDFs, never handwritten | Use standard PDF text extraction or multimodal LLM for scanned/image PDFs |
| **Multi-state support** | Texas-only per PROJECT.md constraints, other states have different formats | Hard-code Texas PUCT format assumptions; document for future expansion |
| **Terms of Service parsing** | Massive legal documents, low signal-to-noise, not standardized | Link to TOS URL only; flag for manual review if needed |
| **Provider logo extraction** | Already available in plan listing API, no added value | Use existing company_logo field from plan data |
| **Full document text search** | Over-engineered for v1, unclear user need | Store raw text as fallback, but focus on structured extraction |
| **Automatic plan recommendation** | Requires user usage data, preferences, risk tolerance | Provide comparison data; let users or future UI make recommendations |
| **Real-time pricing updates** | EFLs are static snapshots, not real-time data sources | Accept that data is point-in-time; version EFLs if re-parsing same plan |
| **Bill payment integration** | Out of scope, requires provider APIs and authentication | Focus on comparison/analysis only |
| **Customer review aggregation** | Unrelated to EFL parsing, different data source | Use existing rating_total/rating_count from plan API |

## Feature Dependencies

```
Price extraction
  ↓
Base charge extraction → Bill simulation engine
  ↓
TDU charge extraction

Contract term → Early termination fee extraction
                  ↓
                Cancellation policy details

Plan type classification → Rate escalation clause extraction
                             ↓
                           Historical pricing comparison

Time-of-use rate extraction → Seasonal rate variations
                                ↓
                              Bill simulation engine

Usage tier boundaries → Bill simulation engine

Special terms extraction → Promotional credit tracking
```

## MVP Recommendation

Prioritize (Phase 1):
1. **Price per kWh extraction** - Core comparison capability
2. **Base charge extraction** - Required for accurate cost calculation
3. **Contract term and ETF** - High-impact consumer decision factors
4. **TDU delivery charges** - Completes total cost picture
5. **Plan type and renewable %** - Basic classification and filtering

Prioritize (Phase 2 - Enable Analysis):
6. **Bill simulation engine** - Major differentiator, requires Phase 1 data
7. **Usage tier boundaries** - Improves simulation accuracy
8. **Special terms extraction** - High value, high complexity, can iterate

Defer to Phase 3+ (Advanced Features):
- **Time-of-use rate extraction** - Complex, smaller plan subset, needs TOU plan detection first
- **Seasonal rate variations** - Lower frequency, can calculate from examples
- **Rate escalation clauses** - Important but not blocking, affects multi-year plans only
- **Historical pricing comparison** - Requires time-series data accumulation

## Extraction Challenges by Feature

| Feature | Parsing Challenge | Mitigation Strategy |
|---------|------------------|---------------------|
| Price per kWh | Tiered tables, multiple formats, footnote references | LLM prompt engineering with examples; validate against plan API prices |
| TDU charges | Often in fine print or footnotes, varies by utility | Named entity recognition for TDU names; consistent section identification |
| Special terms | Unstructured prose, conditional language, edge cases | Extract full text block; classify with LLM; flag uncertainty for review |
| Time-of-use rates | Complex multi-dimensional tables (time × season) | Structured output schema; iterative extraction with validation |
| Bill credits | Embedded in various sections, time-limited conditions | Pattern matching for dollar amounts and time references; structured extraction |
| Rate escalation | Hidden in legal language, year-over-year changes | Search for "year", "month", future dates; flag plans with multi-year terms |

## Data Quality Requirements

| Feature Category | Accuracy Target | Validation Method |
|-----------------|----------------|-------------------|
| Pricing data (price/base/TDU) | 99%+ accuracy | Cross-reference with plan API data; flag mismatches > 5% |
| Contract terms (term/ETF) | 95%+ accuracy | Validate against common values; flag outliers for review |
| Classification (plan type/renewable %) | 90%+ accuracy | Confidence scoring; manual review for low-confidence extractions |
| Special terms | 80%+ recall | Optimize for catching terms; false positives acceptable for review |
| Advanced features (TOU/seasonal) | 85%+ accuracy | Limited plan subset; validation against provider websites |

## Feature Prioritization Rationale

**Phase 1 focus (table stakes):**
- Enables basic cost comparison (primary use case)
- High accuracy achievable with current LLM capabilities
- Clear validation path against existing plan API data
- Low parsing complexity, high ROI

**Phase 2 focus (bill simulation):**
- Unlocks personalized recommendations
- Depends on accurate Phase 1 extractions
- High user value for non-standard usage patterns
- Competitive differentiator vs. Power to Choose website

**Phase 3+ (advanced analysis):**
- Smaller plan subset (TOU, seasonal plans less common)
- Higher parsing complexity, more error-prone
- Can iterate based on user demand
- Requires more sophisticated validation

## Confidence Assessment

| Feature Area | Confidence Level | Reasoning |
|------------|-----------------|-----------|
| Table stakes features | HIGH | Standard PUCT requirements, observed in existing plan data, well-documented domain |
| Bill simulation value | HIGH | Clear user need for personalized cost estimates, competitive gap vs. Power to Choose |
| TOU/seasonal complexity | MEDIUM | Know these features exist, but format variability uncertain without EFL samples |
| Special terms extraction | MEDIUM | High variability expected, LLM capability assumption, needs validation |
| Accuracy targets | MEDIUM | Estimated based on LLM capabilities and domain complexity, needs real-world testing |

## Open Questions for Implementation

1. **EFL format variability:** How much do table structures vary across providers? (Needs sample collection)
2. **TDU charge standardization:** Are TDU charges consistent enough to extract reliably? (Test with real EFLs)
3. **LLM extraction accuracy:** Can nvidia/nemotron reliably extract structured data from diverse PDF formats? (Needs prototyping)
4. **Validation data availability:** Can we validate extractions against Power to Choose API data? (Check API coverage)
5. **Storage schema:** What level of normalization for charges/tiers/conditions? (Architecture decision)

## Sources

- **Existing codebase:** `/Users/atlantis/workspace/power2choose/ui/src/types/plan.ts`, `PlanTable.tsx` (current plan data structure)
- **Project requirements:** `.planning/PROJECT.md` (EFL parsing goals and constraints)
- **Domain knowledge:** Texas PUCT EFL requirements, electricity market structure (training data, MEDIUM confidence)
- **Power to Choose API:** Observed plan data fields (fact_sheet URLs, pricing_details, special_terms)

**Note:** Confidence marked MEDIUM overall because actual EFL PDF samples were not analyzed. Recommend collecting 10-20 representative EFLs across providers to validate feature list and parsing complexity assumptions before roadmap finalization.
