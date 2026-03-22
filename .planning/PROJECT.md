# Power to Choose - EFL Parser

## What This Is

A document processing pipeline that downloads Electricity Facts Labels (EFLs) and Terms of Service PDFs from Texas electricity providers, extracts structured data using LLM-powered OCR via OpenRouter, and stores the results in a SQLite database for analysis, insights, and simulation.

## Core Value

Accurately extract and store structured pricing, charges, and contract details from EFL PDFs so users can make informed electricity plan comparisons beyond what the Power to Choose website provides.

## Requirements

### Validated

- [x] Web UI that fetches and displays electricity plans from Power to Choose API
- [x] Filter controls for zip code, usage, plan type, company, price, term, renewable energy, rating
- [x] Dark mode support via system preference detection
- [x] Client-side filtering and sorting of plan data

### Active

- [ ] Download EFL PDFs from electricity provider URLs
- [ ] Extract text from EFL PDFs using LLM-powered OCR (nvidia/nemotron via OpenRouter)
- [ ] Parse extracted text into structured data (charges, prices, terms, fees, special conditions)
- [ ] Design and implement SQLite schema for storing parsed EFL data
- [ ] Integration with LiteLLM library for OpenRouter API access
- [ ] Store parsed results for later analysis, insights, and simulation

### Out of Scope

- Real-time EFL monitoring/change detection -- defer to v2
- Direct provider API integrations -- use PDF parsing approach
- User-facing UI for EFL data -- focus on backend pipeline first
- Multi-state support -- Texas only via Power to Choose

## Context

- Existing codebase: React + Vite frontend (ui/), Python FastAPI backend (api/)
- Backend already fetches plan listings from Power to Choose API
- Each plan listing includes URLs to EFL documents (PDFs hosted by providers)
- EFL documents contain: pricing tiers, base charges, TDU charges, contract terms, early termination fees, renewable energy percentages
- PDFs vary widely in format across providers -- some are text-based, some are scanned images
- The nvidia/nemotron-3-super-120b-a12b:free model is available through OpenRouter for free-tier usage

## Constraints

- **LLM Provider**: Must use OpenRouter with nvidia/nemotron model via LiteLLM library
- **Storage**: SQLite database for simplicity and portability
- **Backend**: Python (existing FastAPI backend)
- **Cost**: Use free-tier model to minimize API costs

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| LiteLLM for LLM integration | Unified interface to OpenRouter, easy provider switching | -- Pending |
| SQLite for storage | Simple, portable, no server needed, good for analysis queries | -- Pending |
| nvidia/nemotron for OCR+extraction | Free tier on OpenRouter, capable multimodal model | -- Pending |
| Single pipeline (download -> extract -> parse -> store) | Simple architecture, easy to debug and iterate | -- Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check -- still the right priority?
3. Audit Out of Scope -- reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-22 after initialization*
