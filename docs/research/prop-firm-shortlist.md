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
| **Lucid Flex 50K** | **Yes (Lucid's own help center)** | Yes | 50% (with cushion) | $2k EOD, DLL optional | **#1 - only one open to Malaysia** |
| **Tradeify Growth 50K** | Yes, with conditions | Yes (Tradovate/Rithmic) | **None** | $2k EOD | **Out - Malaysia restricted** |
| MyFundedFutures | Allowed since Jul 2025 (mixed reports) | Yes | 30-50% | EOD (Rapid EOD) | Backup |
| Take Profit Trader | Unclear | Yes | 50% | EOD in test, **intraday in PRO** | Skip |
| Topstep | Yes | **No - new Combines are TopstepX-only** | 50% | $2k EOD | Out |
| Apex | **No - automation prohibited** | Yes | None | EOD | Out |

**DECIDED (user, 2026-09-10): Lucid - LucidDaily 50K, EOD eval drawdown, daily loss
limit ON ($1,200), personal profile.** Buy only once the bot is backtested.

Lucid commissions (round turn, help center): ES/NQ $3.50, MES/MNQ $1.00. Platforms:
NinjaTrader, TradingView, Tradovate, Tradesea, Sierra Chart. Standard Lucid accounts
connect NinjaTrader 8 with the **Tradovate login from the Lucid dashboard (CQG feed)**;
no documented Rithmic route for NinjaTrader (proptradingvibes, 2026-08-04). NinjaScript
bots allowed over it. Confirm with support at checkout.

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

## Lucid - verified on Lucid's own help center (2026-09-10)

Lucid's site 403s our fetcher, but `https://r.jina.ai/<article url>` returns the text.
Some tables on their pages are images, so payout min/max and the microscalping
threshold still come from third-party sites.

**Bots / setup**
- Automated strategies and trade copiers: **allowed**; you own any software errors.
- VPS: **fine**. VPN: allowed. Your connection problems don't get account adjustments
  (Lucid support chat, pasted by user).
- Banned: HFT, microscalping (third-party: >50% of profit from trades <=5 sec), hedging
  (incl. opposite/correlated positions across accounts **or across other prop firms**).
- Flat by 4:45 PM ET (auto-closed, not a breach). Opens Sun-Thu 6 PM ET.
- Inactivity: an account with no $1+ net P/L for 30 calendar days is **deleted**.

**LucidFlex 50K**
- Eval: $3,000 target, $2,000 EOD MLL, **max 2 minis / 20 micros** (not 4), no scaling.
- Consistency (eval only): biggest day / total profit <= 50%, small cushion (~$1,560
  on 50K). Break it = keep trading, not fail.
- DLL is picked at purchase and can't change: ON = $1,200 soft daily limit, ~$10
  cheaper; OFF = none.
- Funded scaling (end of day): profit $0-999 = 2 minis/20 micros, $1k-1,999 = 3/30,
  $2k+ = 4/40.
- MLL trails EOD from $48,000; locks at $50,100 once balance hits $52,100.
- Payouts: 90/10, 5 days at min profit per cycle + positive cycle net, request any
  day, funds within 2 business days, max doesn't grow with more payouts.
- **Lucid support confirmed (2026-09-10): max = 50% of profit made in that cycle**
  (not total account profit), cap $2,000. Cycle resets after each payout, so profit
  left behind never becomes withdrawable - it only adds cushion. Sweet spot: ~$4,000
  per cycle, then request. Max out of one account = 5 x $1,800 = ~$9,000.
- What happens to leftover sim profit when moved to LucidLive: **unknown** (support
  couldn't say).

**LucidLive (after up to 5 payouts, risk team's call)**
- All funded accounts with >=1 payout move live together; all sim accounts close;
  funded accounts with 0 payouts are refunded.
- 50K live: $2,000 EOD drawdown, starts 2 minis/20 micros, 3/30 at $2k profit,
  4/40 at $4k. No consistency. Daily payouts. No swing trades (Rithmic flat 4:15 PM ET).
- One-time live bonus: hit $2,100 on a 50K -> $2,000 bonus (90/10).
- Household: if one member is live, nobody else in the house can trade sim.
- **Live data/platform fees: not published.** Ask support.

**Accounts / payments**
- Buy evals by card only (Visa/MC/Amex/Discover/Diners/Maestro).
- Max 5 funded + 10 total accounts per household.
- Register personal OR business - **one profile forever, can't convert**. Business:
  put business name in First + Last Name; email compliance@lucidtrading.com proof of
  incorporation + proof of ownership + ID of 25%+ owners; then do business KYC with
  WorkMarket support separately. Business accounts must be paid as the business.
- User's only active bank account is the Malaysian sole prop *Quantum Capital
  Global*. A sole prop is SSM-registered, not incorporated -> **ask compliance
  whether the SSM certificate + SSM business profile count before registering.**
- Lucid support reply (2026-09-10): SSM docs **not confirmed** (doc types unspecified).
  Personal profile paid into the sole prop bank account: **no**.
- So: (A) get compliance to pre-approve the SSM docs in writing before creating a
  business profile, or (B) open a personal bank account and register personal.
  B is lower risk - the profile choice is permanent, and a sole prop gives no tax
  edge in Malaysia (its income is taxed as the owner's personal income anyway).

## Lucid plan comparison - which account to buy (2026-09-10, session 3)

Rules from Lucid's help center (via r.jina.ai); prices from proptradingvibes
(updated 2026-09-08, 30% code VIBES). All 50K, 90/10 split, $2,000 MLL.

| | Flex | Pro | Daily | Direct |
|---|---|---|---|---|
| Price (DLL on, list / code) | $136 / $95 | $172 / $120 | $136-165 / $95-116 | $520 / $364 |
| Eval | $3k target, 50% consistency (cushion) | $3k target, **no consistency** | $3k target, 50% consistency (cushion) | **none** (straight to funded) |
| Eval drawdown | EOD | EOD | pick EOD or intraday | - |
| Funded drawdown | EOD | EOD | **intraday always** | EOD |
| Funded contracts | 2 minis, scales to 4 | 4 minis | 4 minis | 4 minis |
| Funded consistency | none | **40%** of cycle profit | none | **20%** of cycle profit |
| Buffer before payouts | none | $52,100 balance | $52,100 balance | $52,100 + $3k goal, then $2.5k/cycle |
| Payout size | **50% of cycle profit**, cap $2k | all above buffer, cap $2k then $2.5k | all above buffer, no per-request cap | cap $2k (1-3), $2.5k (4-5) |
| Payout timing | 5 days of $150+ per cycle | 3-day cycle, $500 min goal | any day, +$1 since last payout | when goal + consistency met |
| Payouts before live | 5 | 5 | risk team's call; auto-live if one day hits $6k+ sim profit | 5 |
| Extra traps | leftover cycle profit never withdrawable | - | **red-folder news = hard breach** (flat 1 min before/after); sim profit above buffer capped at $15k when moved live, rest forfeited; no live bonus | 20% consistency = 5+ days/cycle |

DLL (soft, pauses for the day): Pro/Daily/Direct 50K = $1,200 fixed, then Pro/Direct
switch to 60% of peak EOD profit once past $52,100. Chosen at purchase, can't change.

**Fit for our bot** (rough, 73% WR / 0.5 RR / $300 risk / 3 trades a day):
- Expected edge ~$30/trade -> **~$90/day**. Days are lumpy: +$450 (3 wins), $0, -$450.
- Flex only pays out **50%** of what you earn in a cycle. Pro/Daily pay out ~all of it
  once past the one-time $2,100 buffer. Past ~$4.2k lifetime profit per account,
  Pro/Daily beat Flex; at $10k lifetime: Flex ~$5k vs Pro ~$7.9k gross.
- Pro's 40% consistency: a $450 best day needs a $1,125+ cycle -> ~2-week cycles. Fine.
- Daily is the most flexible, but funded intraday drawdown + hard news breach are
  extra ways for a bot bug to kill the account.
- Direct: $364 to skip an eval our sim passes ~83% of the time (~$115 expected
  eval cost on Flex/Pro). Not worth it.
- DLL ON: our worst normal day is -$900 (3 losses) < $1,200, so it never blocks us, it's
  cheaper, and it stops a runaway bot.
- Don't buy before the bot is backtested: 30 days with no $1+ net P/L **deletes** the
  account.

**Recommendation: LucidPro 50K, DLL ON.** 1 account first to prove the bot, then scale
to 5 funded (household max) with the copier. Runner-up: LucidDaily (EOD eval, DLL on)
if the bot gets a solid news filter.

Conflicts to re-check with Lucid support before buying:
- LucidFlex 50K eval max contracts - help center read earlier said 2 minis/20 micros;
  proptradingvibes (2026-09-08) says 4/40.
- Lucid summary pasted by user (2026-09-10) says LucidPro has "no simulated payout
  caps" and Flex pays "$500-$1,000 per request". Help center + proptradingvibes both
  show Pro 50K max $2,000 first / $2,500 after, and support earlier confirmed Flex 50K
  cap $2,000. Probably the summary means other sizes or lifetime caps - ask. The
  summary also leaves out Pro's 40% funded consistency.
- Decision still LucidPro 50K DLL ON either way (user asked for a call 2026-09-10).

## LucidDaily vs LucidPro 50K in full (2026-09-10, session 3)

User decided: **personal** profile (open a personal bank account for WorkMarket).

| | LucidDaily | LucidPro |
|---|---|---|
| Price, EOD eval + DLL on (list / code) | $160-165 / ~$112-116 | $172 / $120 |
| Eval drawdown | pick EOD or intraday | EOD |
| Eval consistency | 50% with cushion (doesn't matter for us) | none |
| Funded drawdown | **intraday**, trails open-profit peaks until locked at $50,100 | EOD, same lock |
| News | **red-folder USD news = hard breach** in funded (flat 1 min before to 1 min after); eval undocumented - assume same | no news rule |
| DLL (if on) | $1,200 fixed | $1,200, then scales up past $52,100 |
| Funded consistency | none | 40% of cycle profit |
| Payouts | any day, $500 min, **all above $52,100, no cap** | 3-day cycles, $500 goal, cap $2k then $2.5k |
| Payouts before live | no fixed count, risk team's call; auto-review if a day makes $8k+ | 5 |
| Moving live | sim profit above buffer paid out, capped at $15k total; **no live bonus** | live bonus ($2,000 on 50K, first-time live traders) |

Funded-stage sim (`python -m tools.prop_sim.funded`, 73.3% WR, 0.5 RR, $300 risk,
3/day, no costs, 5,000 runs; $ = gross withdrawn per account, blown accounts keep what
they already withdrew):

| Plan | 60 days: blown / $ out | 120 days: blown / moved live / $ out |
|---|---|---|
| Flex | 31% / $2,302 | 33% / 64% / $2,988 |
| Pro | **21%** / $3,035 | **28%** / 67% / $4,579 (+ live bonus) |
| Daily | 27% / **$3,297** | 43% / n/a / **$7,168** (never moved live in sim) |
| Daily, no intraday effect | 25% / $3,336 | 42% / n/a / $7,324 |

- The intraday drawdown barely matters for our bot (~2 pts more blown, ~$40).
- Daily blows up more because it pulls everything above $52,100 out, so the account
  sits on its minimum $2k cushion. Pro's caps + cycles leave more cushion.
- First payout: median day 21 on both; Flex day 12 but half the money.
- 120-day Daily number is inflated vs Pro: Pro stops at 5 payouts because it goes live
  (plus bonus); Daily keeps farming sim until Lucid decides.
- With $5/trade costs every plan drops hard (Pro 39% blown, $3,804) - our edge is thin
  (+0.1R), so task #2 must beat this.

**Verdict: close.** With a news filter, Daily = more cash, sooner cash-out, more
blow-ups. Pro = safer, live bonus, no hard-breach rule. Still leaning Pro for a
first, untested bot; Daily is fine once the bot is proven. Mixing is allowed (5 funded
per household total).

Daily eval config (prop_sim, 50% consistency, $300 risk): EOD eval 82.5% pass, ~$140
expected fees per pass ($115.50 each); intraday eval 80.8% pass, **~$118 per pass**
($95.20 each). Intraday sim ignores open-profit peaks, but the funded sim shows those
barely matter for us -> **if Daily, buy Intraday + DLL ON** (cheapest per pass).

Daily news filter needs: USD high-impact calendar (ask Lucid which one it uses), flatten
+ block entries a few minutes around each event, and a fallback - if the VPS or data
drops with a trade open at news time, the account is gone (Lucid doesn't adjust for
connection problems).

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
- Lucid help center (read via r.jina.ai): articles 11404634 registering-as-a-business,
  11404728 other-trading-activities, 11404729 allowed-trading-times, 11404742
  microscalping, 11404734 hedging, 11404736 HFT, 11404632 inactivity, 11404617 max
  accounts, 11404628 payment methods, 12890325 payout methods, 12945790/95/96/805/808/815
  LucidFlex eval/funded/payouts/consistency/scaling/drawdown, 16226050 customization,
  13425130 new live structure, 15245873 live scaling plan
- https://proptradingvibes.com/blog/lucid-trading-50k-account-rules (DLL price)
- Lucid help center (r.jina.ai), session 3: LucidPro 12890029/069/092/109/122/136,
  16226068; LucidDirect 12890148/164/178/185/192; LucidDaily 15996664, 15997244/266,
  15998336/425, 16085900, 16033858, 16010520
- https://proptradingvibes.com/blog/lucid-pro-vs-lucid-flex-vs-lucid-direct
- https://proptradingvibes.com/blog/lucid-trading-discount
- https://phidiaspropfirm.com/education/luciddaily (daily profit ceiling, via search)
