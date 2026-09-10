# Futures prop firm shortlist (for an automated NinjaTrader bot)

Researched 2026-09-10 from third-party review sites (most official help centers
blocked our fetcher). **Re-check each firm's own rules page before paying.**

## What we need (from docs/research/prop-firm-math.md)

1. Bots allowed on NinjaTrader - hard requirement.
2. No consistency rule in the evaluation.
3. EOD drawdown (not intraday trailing).
4. $50k size, cheap fee, sane funded payout rules.

## Verdict

| Firm | Bots OK? | NinjaTrader? | Eval consistency | Drawdown | Verdict |
|---|---|---|---|---|---|
| **Tradeify Growth 50K** | Yes, with conditions | Yes (Tradovate/Rithmic) | **None** | $2k EOD | **#1 pick** |
| **Lucid Flex 50K** | Yes (per reviews, confirm) | Yes | 50% (with cushion) | $2k EOD, no DLL | **#2 - best funded stage** |
| MyFundedFutures | Allowed since Jul 2025 (mixed reports) | Yes | 30-50% | EOD (Rapid EOD) | Backup |
| Take Profit Trader | Unclear | Yes | 50% | EOD in test, **intraday in PRO** | Skip |
| Topstep | Yes | **No - new Combines are TopstepX-only** | 50% | $2k EOD | Out |
| Apex | **No - automation prohibited** | Yes | None | EOD | Out |

## Tradeify Growth 50K

- $145 one-time, no activation fee. $3,000 target, $2,000 EOD trailing (breach is
  checked in real time). Pass in 1 day possible.
- Daily loss limit $1,250 - soft (pauses for the day, doesn't fail).
- Funded: 35% best-day consistency on payouts, five $150+ winning days per cycle,
  $53k balance buffer, 90/10 split, >50% of trades and profit from holds >10 sec.
- Bot rules: must be sole owner, **live video of you starting it on your own PC**,
  no HFT, **don't run the same bot at other prop firms**, no resold bot services.

## Lucid Flex 50K

- 50% eval consistency with a built-in cushion; if broken you keep trading, not fail.
- No daily loss limit. EOD drawdown. Flat by 4:45 PM ET.
- Funded: **no consistency rule, no payout buffer**, 90% split.
- Bots/scripts allowed; no HFT or microscalping (>50% of profit from trades <=5 sec).

## Sim check (tools/prop_sim, 73.3% WR, 0.5 RR, 3 trades/day)

| Rule set | $300 risk | $500 risk |
|---|---|---|
| No rules (baseline) | 82.8% | 69.1% |
| Tradeify ($1,250 daily loss limit) | 82.5% | 69.0% |
| Lucid (50% consistency) | 82.5% | - |

- With our small, low-R:R sizing, **neither rule hurts**: days are too small to break
  50% consistency or hit a $1,250 daily loss.
- So Lucid's eval consistency is no big deal for us, and its funded stage is easier
  (no payout consistency). Tradeify is still simplest to pass.
- $300 risk: median ~24 trading days to pass. $500: ~11 days, lower pass rate.

## Sources

- https://proptradingvibes.com/blog/tradeify-trading-rules-overview
- https://test-max.com/prop-firms/tradeify/
- https://help.tradeify.co/en/articles/10468318-guidelines-for-traders
- https://proptradingvibes.com/blog/lucid-trading-lucidflex-account
- https://support.lucidtrading.com/en/articles/12945790-lucidflex-evaluation-account
- https://algofutureslab.com/lucid-trading-review/
- https://pickmytrade.io/faq/prop-firm-automation
- https://www.quantvps.com/blog/myfundedfutures-now-permits-algo-trading-and-automation-tools-on-all-accounts
- https://proptradingvibes.com/blog/myfundedfutures-rapid-eod
- https://phidiaspropfirm.com/education/take-profit-trader-trailing-drawdown
- https://app.tradersforge.net/prop-firms/topstep
- https://proptradingvibes.com/blog/topstep-trading-combine-rules
- https://proptradingvibes.com/blog/apex-trader-funding-rules-overview
