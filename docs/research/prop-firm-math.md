# Prop Firm Math - research notes

Source: YouTube `H-PL14KEa5A` - "Prop Firm Math: How to Consistently Pass Challenges".
Condensed from a transcript the user supplied on 2026-09-10. Numbers below are the
creator's claims, not verified. Test them with `python -m tools.prop_sim`.

## Core thesis

- Passing a challenge is a **variance** problem, not a profitability problem.
- On a $50k account your real capital is the drawdown ($2k). The $3k target = 150% of it.
- Creator cites a 12.4% pass rate across 100k+ traders.

## Account choice

| Account | Max DD | Target | Target / DD |
|---|---|---|---|
| $50k futures | $2,000 (4%) | $3,000 (6%) | 1.5 |
| Bigger accounts (typical) | ~3% | ~6% | ~2.0 (creator: "50% harder") |

- $50k is cheap -> less emotional attachment -> easier to execute.

## The three levers: win rate, R:R, size

- Breakeven win rate = `1 / (1 + RR)` -> 1:1 needs >50%, 1:2 needs >33%.
- Win rate and R:R move opposite ways. Same edge, very different variance:
  - 90% WR / 0.7 RR (expectancy 0.53R): tiny losing streaks, best-vs-worst spread 1.37.
  - Low WR / high RR, same expectancy: avg losing streak ~10.9 trades, spread 4.8,
    some 100-day runs lose money purely from variance.
- Creator blew 7 challenges following "always 1:2 / 1:3" advice.

## Position sizing

- 1% of $50k = $500 = **25% of the real $2k capital**.
- Creator's matrix:
  - <50% WR at 1:3 -> must risk <=0.25% (~$125). Safe but very slow.
  - ~73% WR at 0.5 RR -> can risk ~1.75% (~$800-875) with 65%+ pass rate, fast.
- Size should come from your WR/RR (variance), not a fixed 1% rule.

## Rule traps

- **EOD / trailing drawdown**: threshold trails new equity highs. One high-RR trade a day
  gets squeezed; 3-5 high-WR trades a day trail smoother.
- **Consistency rule** (best day <= 40-50% of total profit): creator says dropping it adds
  12-15 points of pass rate. -> Pick evals without one.

## Creator's EV table (100 evals, $60 fee, $800 avg payout)

| Strategy | Setup | Pass | Payout | ROI |
|---|---|---|---|---|
| A - zero edge | 0.5 RR, 66.7% WR, 1.5% risk, with consistency | ~30% | ~40% | positive |
| A - zero edge | same, no consistency, 1-day pass | - | - | ~100% |
| B - real edge, high RR | 1:3, 27.5% WR, with consistency | 16.9% | 22.2% | **-60%** |
| C - slight edge, high WR | 0.5 RR, 1.5% risk | ~63% | ~67% | **~460%** |

## Creator's checklist

1. Stop targeting R:R above 1:2.
2. Aim for 60-70% win rate at 0.5-1 R:R.
3. $50k futures account, low fee, **no consistency rule**.
4. Size each trade from the strategy's variance.

## Our caveats

- The video is a **risk / sizing framework, not an entry signal**. We still need a setup
  that really produces a high win rate at low R:R.
- **Costs hurt low R:R most.** At 0.5 RR a fixed commission + slippage is a big slice of
  a small win. Zero edge + costs = negative edge.
- High-WR / low-RR systems can hide **fat-tail losses** (stop slippage, news spikes). One
  outsized loss vs a $2k drawdown ends the eval.
- "Zero edge still profitable" works by exploiting the eval's capped downside (lose fee,
  win payout). Funded-stage rules (payout consistency, buffers, caps) matter as much as
  eval rules.
- Our sim uses closed-trade P&L, so it is optimistic for **intraday** trailing drawdown
  (open-profit peaks count there).

## Our sim results (tools/prop_sim, 2026-09-10)

Setup: $50k, $2k EOD DD, $3k target, 60-day limit, 3 trades/day, 5000 runs per cell.
Every row has the **same edge (+0.10R)**; only R:R / win rate / size change.

| RR | WR | $150 | $300 | $500 | $800 | $1000 |
|---|---|---|---|---|---|---|
| 0.5 | 73.3% | 49% | **83%** | 69% | 59% | 57% |
| 0.7 | 64.7% | 52% | 72% | 60% | 54% | 49% |
| 1.0 | 55.0% | 56% | 61% | 50% | 50% | 45% |
| 2.0 | 36.7% | 54% | 47% | 42% | 45% | 43% |
| 3.0 | 27.5% | 49% | 42% | 40% | 41% | 40% |

What we learned:

- **Video's main claim holds.** Same edge: 0.5 RR @ $300 = 83% pass vs 3 RR = ~40-50%.
- **Bigger size is not better.** 0.5 RR peaks around $300 risk, then falls.
  ($150 only looks bad because it runs out of days, not because it blows up.)
- **Consistency rule (50%)** doesn't touch low R:R but crushes high R:R
  (3 RR @ $1000: 40% -> 22%).
- **Zero edge still passes ~30-35%** at any combo - matches the video's ~30%.
- **Costs are the killer for small low-R:R trades.** $10/trade: 0.5 RR @ $150 drops
  49% -> 8%; @ $300 drops 83% -> 65%. Win size must be big vs costs.
- **More trades/day helps small size.** 5/day: 0.5 RR @ $150 = 86%.
- **Intraday trailing DD** costs ~2-6 points vs EOD (and more in real life).

Working target for our strategy: **0.5-0.7 RR, ~65-75% WR after costs, risk ~$300-500
(15-25% of DD) per trade, 3-5 trades/day, EOD-drawdown firm with no consistency rule.**
