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
| **Lucid Flex 50K** | Yes (per reviews, confirm) | Yes | 50% (with cushion) | $2k EOD, no DLL | **#1 - only one open to Malaysia** |
| **Tradeify Growth 50K** | Yes, with conditions | Yes (Tradovate/Rithmic) | **None** | $2k EOD | **Out - Malaysia restricted** |
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

## Costs + Malaysia payouts (researched 2026-09-10, session 2)

**Blocker: Tradeify lists Malaysia as a restricted country** (pickapropfirm, data
updated 2026-09-10; funded.now; search snippets of Tradeify's own help page). An
older Feb 2026 list didn't have it, so it looks newly added. We can't open or get
paid on a Tradeify account as Malaysian residents -> **Tradeify is out** unless
their support says otherwise.

**Lucid does allow Malaysia** (not on its 81-entry list, checked 2026-07-29), but
since 2026-08-26 Malaysia residents **can't take crypto payouts** - WorkMarket only.

| Cost | Lucid Flex 50K | Tradeify Growth 50K |
|---|---|---|
| Upfront (eval) | $130-149 list, ~$65-90 with promo codes | $145 list, ~$73 with promo |
| Monthly | None (one-time, no expiry) | None (one-time) |
| Activation | None | None |
| Reset | Buy a new eval | Buy a new eval |
| Data | $0 if you certify CME **Non-Professional**; $112/exchange/mo if Pro | $0 |
| NinjaTrader | $0 (NT 8.1+ needs no license for prop accounts) | $0 |
| Commission (round turn) | MNQ ~$1.00, NQ ~$3.50 | MNQ ~$1.82, NQ ~$5.76 |
| Malaysia | **Allowed** | **Restricted** |

Lucid Flex funded payouts (50K): 90/10 split, min $500, cap 50% of cycle profit up to
$2,000 per payout, needs 5 days of $150+ profit per cycle, no consistency, no buffer.
Max 5 payouts, then moved to LucidLive (data costs there not published - ask).
Watch: MLL locks at $50,100 once balance passes $52,100 and withdrawals don't reset
it, so pulling profit eats your cushion.

Lucid payout rails for a Malaysian:

| Rail | Works for MY? | Speed | Cost |
|---|---|---|---|
| Plaid | No (US only) | - | - |
| Crypto | **No** (banned for MY since 2026-08-26) | - | - |
| WorkMarket -> bank (SWIFT, paid in USD) | Yes | ~2-4 business days | ~$10-25 wire/intermediary + ~1-2% FX at your MY bank |
| WorkMarket -> PayPal -> bank | Yes | ~5-8 days | ~3-4% FX spread + fees - worst option |

- Best path: WorkMarket bank transfer into a **USD-capable account** (e.g. a
  Malaysian bank foreign-currency account, or a multi-currency account like
  Wise/Revolut/YouTrip if WorkMarket accepts its details) so you pick when to
  convert to MYR instead of eating the bank's default rate.
- Min payout $500 -> the fixed $10-25 wire fee is small (2-5%) at that size.

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
- https://pickapropfirm.com/futures/prop-firms/tradeify/
- https://funded.now/restricted-countries/tradeify
- https://funded.now/restricted-countries/lucid-trading
- https://www.surgefunded.com/tradeify-supported-and-restricted-countries/
- https://proptradingvibes.com/blog/lucid-trading-restricted-countries
- https://proptradingvibes.com/blog/lucid-trading-payout-methods
- https://proptradingvibes.com/blog/lucid-trading-payout-rules
- https://proptradingvibes.com/blog/tradeify-rise-payouts
- https://saveonpropfirms.com/blog/lucid-trading-lucidflex-guide
- https://damnpropfirms.com/account-plans/lucid-trading-flex-50000/
- https://support.lucidtrading.com/en/articles/11508978-approved-products-and-commissions
- https://daytradingz.com/tradeify-review/
- https://crosstrade.io/docs/getting-started/prop-firm-connection-guide
- https://workmarket.zendesk.com/hc/en-us/articles/18410846928151-Payment-Accounts-Overview-Bank-Hyperwallet-PayPal-Wisely
