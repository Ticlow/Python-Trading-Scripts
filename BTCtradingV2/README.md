## BTC Market Structure Scanner

A lightweight Python-based BTC market scanner designed to **identify directional context and confidence**, not to auto-trade.

This system is intentionally simple. It gives you *structure and bias*, not entries.

---

## Philosophy

- Market structure is **directional information**, not a signal  
- Confidence is **additive**, not binary  

---

## What This Script Does

- Scans BTC at fixed intervals
- The most recent candle is excluded unless its close time < current NY time
- Evaluates:
  - HTF bias (4H)
  - LTF bias (1H)
  - Market structure (HH/HL vs LH/LL)
  - Trending regime (EMA spread)
- Produces:
  - Confidence score
  - Inferred directional context
  - Human-readable reasoning

---

## What This Script Does **NOT** Do

- ❌ No entries  
- ❌ No exits  
- ❌ No position sizing  
- ❌ No prediction  

It tells you **whether the market is worth paying attention to** — nothing more.

---

## Confidence Scoring Logic

| Component | Condition | Score |
|---------|----------|-------|
| HTF Bias | Bull or Bear | +1 |
| LTF Bias | Aligns with HTF | +1 |
| Structure | Confirms direction | +1 |
| Structure | Opposes direction | -1 |
| Regime | EMA spread | +1 |

**Minimum confidence for directional output:** `3`

Anything below that intentionally prints `NONE`.

---

## Direction Resolution

```text
IF confidence >= 3:
    IF structure aligns with HTF:
        → TREND CONTINUATION (LONG / SHORT)
    IF structure opposes HTF:
        → PULLBACK (against HTF)
ELSE:
    → NONE

