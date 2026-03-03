---
name: review
description: Run a periodic review of past observations and outcomes. Use when user asks for weekly or monthly recap, post-mortem, or learning summary.
---

# Review Skill

## Goal
Generate a structured retrospective and store it under `notebook/reports/`.

## Workflow
1. Confirm review window (for example: this week, this month, custom range).
2. Read `memory.md` for recent observations and decisions.
3. Read relevant notebooks in `notebook/research/` and `notebook/reports/`.
4. Use `compute` if metrics are needed (returns, volatility shift, drawdown context).
5. Produce sections:
   - what happened
   - what was predicted correctly
   - what was missed
   - process improvements
6. Save with `write` to:
   - `notebook/reports/review-{period}-{date}.md`
7. Optionally update `memory.md` with durable lessons.

## Constraints
- Separate facts from hindsight interpretation.
- Keep action items specific and testable.

