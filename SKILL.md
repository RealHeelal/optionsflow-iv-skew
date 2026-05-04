---
name: "optionsflow-iv-skew"
description: "Analyze IV Skew by comparing Call IV vs Put IV across options chain - detects smart money directional bias as PUT HEAVY, CALL HEAVY, or NEUTRAL for OptionsFlow pre-entry analysis"
---

# IV Skew Analyzer Skill

## Purpose
Detect implied volatility skew to reveal smart money directional
positioning before any options trade.
Based on Blair Hull IV Skew methodology.

## When to Use
Call this skill when user runs:
- /analyze [TICKER]
- حلل [TICKER]
- /scan (auto for all watchlist tickers)

## How to Run
python iv_skew.py AAPL
python iv_skew.py TSLA 2025-05-16

## Output Interpretation
PUT HEAVY  (skew > +5%) = Smart money buying puts = bearish bias
CALL HEAVY (skew < -5%) = Smart money buying calls = bullish bias
NEUTRAL    (skew +-5%)  = No clear directional edge

## Integration with SOUL
- PUT HEAVY  → only recommend PUT contracts
- CALL HEAVY → only recommend CALL contracts
- NEUTRAL    → follow VWAP + Squeeze + ORB signals
- Always show in report: IV Skew [PUT HEAVY / NEUTRAL / CALL HEAVY]
