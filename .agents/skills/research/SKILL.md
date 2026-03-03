---
name: research
description: Build a focused investment research note for one symbol or company. Use when user asks for in-depth analysis, thesis, or data-backed conclusions.
---

# Research Skill

## Goal
Produce a concise, evidence-backed research note and save it to `notebook/research/`.

## Workflow
1. Identify target symbol and the user's objective.
2. Call `market_ohlcv` to fetch recent price data.
3. Call `compute` to calculate key indicators in one batch (trend, momentum, volatility, volume).
4. Read recent memory from `memory.md` and relevant prior notes under `notebook/research/`.
5. Synthesize:
   - market structure
   - bullish and bearish cases
   - key risks
   - decision confidence
6. Save report with `write` to:
   - `notebook/research/{symbol}/{date}.md`
7. If a major new takeaway appears, append/update `memory.md` with `edit` or `write`.

## Output template
- Snapshot
- Indicator table
- Thesis
- Risks and invalidation points
- Next actions

