---
name: scan
description: Scan symbols against explicit criteria and produce a shortlist. Use when user asks for screening, ranking, or candidate discovery.
---

# Scan Skill

## Goal
Evaluate multiple symbols using shared criteria and save ranked output.

## Workflow
1. Confirm candidate universe and scan criteria.
2. For each symbol:
   - call `market_ohlcv`
   - call `compute` to produce comparable metrics
3. Rank symbols by criteria and explain tradeoffs.
4. Save result table and commentary with `write`:
   - `notebook/reports/scan-{date}.md`
5. If needed, store stable preferences in `memory.md`.

## Output template
- Universe and criteria
- Ranked table
- Top candidates with rationale
- Rejection reasons
- Follow-up checklist

