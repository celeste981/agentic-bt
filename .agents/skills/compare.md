---
name: compare
description: Compare two or more symbols side by side with consistent metrics and narrative. Use when user asks for A vs B analysis or selection decisions.
---

# Compare Skill

## Goal
Produce a side-by-side comparison with a clear recommendation boundary.

## Workflow
1. Confirm symbols and comparison horizon.
2. Fetch each symbol with `market_ohlcv`.
3. Use `compute` to calculate the same indicator set for all symbols.
4. Read relevant memory and prior notes to avoid repeating known conclusions.
5. Build a comparison matrix:
   - trend
   - momentum
   - volatility
   - volume or liquidity signal
6. Write the result via `write`:
   - `notebook/research/compare-{symbols}-{date}.md`
7. Return summary with recommendation and invalidation conditions.

## Constraints
- Keep metric definitions identical across symbols.
- Mark uncertain conclusions explicitly.

