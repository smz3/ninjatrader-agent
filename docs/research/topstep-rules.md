# Topstep - every rule that matters for us (50K, Malaysia, own bot)

Pulled 2026-09-30 from Topstep's official help center (help.topstep.com, 57 articles,
most updated Aug-Sep 2026). Times are CT (Chicago). MYT = CT + 13h (CDT) / + 14h (CST).

## 1. Eligibility / identity

- Malaysia: **fully eligible** - not on the banned list, not on the "XFA only, no Live" list.
- Eligibility is by citizenship AND residency. Don't trade while travelling in a banned country.
- **No VPN, proxy, TOR, geo-masking** (Prohibited Conduct). VPN/VPS also breaks ID checks.
- ID check (IDV) required before your 2nd purchase: physical passport/MyKad + selfie. Can
  be re-asked any time.
- **One profile only.** A second profile = closure. New profile after a ban = closed, no refund.
- Card must be in your own name. Visa/MC/Amex/Discover, Apple/Google Pay. No PayPal.

## 2. Price (50K)

| | Standard path | No-activation-fee path |
|---|---|---|
| Combine | $49/month | $95/month |
| Reset | $49 | $95 |
| XFA activation | $149 once per XFA | $0 |

- **Confirmed on the checkout page (2026-10-02), 50K No Activation Fee + RTA:** $85/mo,
  **reset $85** (not $95), XFA activation free, **1 free Reset Credit every monthly
  rebill** (goes to your Reset Bank, same size/type, expires 1 year, use any time - no
  auto-reset on rebill since Aug 2025).
- Path can't be changed after purchase. Combine rebills every 30 days until passed or
  cancelled; cancel = gone for good. No time limit to pass.
- Adding the $1,000 DLL at checkout: $10 off No-Activation path + (limited offer) **doubles
  XFA payout cap** ($2k -> $4k Standard, $3k -> $6k Consistency). Only if added when buying
  the Combine, not later.
- Back2Funded (XFA lost before 1st payout): $599 for 50K, up to 2 times, within 30 days.
- Level 2 data $38/month (not needed for a bot on L1). API $29/mo, **$14.50 with code `topstep`**.
- Commissions (TopstepX, round turn): **ES $3.78, MES $1.22**, NQ $3.78, MNQ $1.22.

## 3. Trading Combine (evaluation) - 50K

- Profit target **$3,000**. Max loss limit (MLL) **$2,000**, trails on END-OF-DAY balance,
  locks at $50,000 once reached. But breach is checked **live incl. open P/L** - touch it
  intraday = liquidated (final fill above the line doesn't save you).
- **Consistency: best day must be < 55% of profit** -> keep best day under **$1,650**.
  Hard line, no rounding. Go over -> target rises to best day / 0.55. Best day locks 3:10 PM CT.
  Extra profit the same day makes it worse - fix only on later days.
- Min 2 days. Max 5 minis / 50 micros (10:1).
- Daily loss limit optional ($1,000, set at purchase = fixed). Hitting it = done for the
  day, not a fail.
- Profits don't carry to the XFA. Unlimited Combines at once.

## 4. Express Funded Account (XFA) - the "funded" stage, still simulated

- Balance starts at **$0**. MLL starts at **-$2,000**, trails up on EOD balance, locks at $0.
  After the 1st payout MLL = $0 for good. Breach = account closed permanently.
- Max **5 XFAs** at once. **Inactive 30+ days = may be closed.**
- **Scaling plan** (max contracts grows with balance, never mid-session). 50K tiers are
  shown on the dashboard / Risk Settings, not in the article text - third-party figures:
  < $1,500 = 2 lots, $1,500 = 3, $2,000+ = 5. **Verify on the dashboard.** Over the limit
  for 10+ s = review.
- Pick payout path at activation (can't change):
  - **Standard:** 5 winning days of $150+ -> request 50% of balance, cap **$2,000**
    ($4,000 with the DLL offer).
  - **Consistency:** 3 trading days + best day <= 40% of profit -> 50%, cap **$3,000**
    ($6,000 with DLL offer).
- Split **90/10**. Min payout $125. Must be net positive since last payout.
- Payout day doesn't count toward the next cycle. Winning days lock at 4:00 PM CT.

### 4a. Standard vs Consistency - deep dive (checked 2026-10-02)

Our pick: 50K, No Activation Fee, Responsible Trading Advantage (= $1,000 DLL added at
Combine checkout). Sources: help.topstep.com payout policy (8284233, updated 2026-10-01),
XFA parameters (8284215, updated 2026-08-05), DLL article (10490293, updated 2026-06-30).

- **Responsible Trading Advantage (RTA):** add the $1,000 DLL at Combine checkout ->
  $85/mo instead of $95 (reset also $85), $50 off Back2Funded, and (limited time, since 2026-06-02, no end
  date) doubled per-request caps. The DLL is fixed and **carries into the XFA**. Hit it =
  flatten, orders cancelled, no trades until 5 PM CT, account still fine.
- Path chosen **once at XFA activation, can't change** (official article; some third-party
  sites wrongly say "per payout").

| 50K + RTA | Standard | Consistency |
|---|---|---|
| Qualify | 5 winning days of $150+ net (not consecutive) AND "maintain your balance between payouts" = net profit since last payout >= $0.01 (1st payout exempt) | 3+ trading days (1+ trade each) AND best day <= 40% of net profit |
| Request | 50% of balance, cap **$4,000** | 50% of balance, cap **$6,000** |
| Cap starts to bite at | balance > $8,000 | balance > $12,000 |
| Losing days | don't matter (only count wins) | lower total profit -> push ratio over 40% |
| One big day | fine | blocks payout until other days catch up |
| Split / min | 90/10 (first $10k lifetime 100% for new dashboard users), min $125 | same |

- Consistency % = largest single-day net profit / total net profit **since last payout**.
  Not rounded: 40.01% fails. Over 40% = not eligible yet, not a breach.
  Example: $3,000 profit -> best day max $1,200.
- After **any** payout: MLL = $0 for good, day count restarts, balance drops by the
  payout -> scaling plan can drop you back to 2 lots, and the leftover balance is your
  only cushion before $0.
- **Key point for us:** both paths pay 50% of balance. The cap only matters with a big
  balance ($8k+ / $12k+), which a 50K bot rarely builds in one cycle. So the real
  difference is the qualify rule, not the money.
- **Leaning Standard for a bot:** losing days and one outlier winning day don't block it;
  just needs 5 days of $150+. Consistency only wins if the bot's days are very even and
  we want payouts every ~3 days.
- Don't withdraw too early: e.g. $1,000 balance -> take $500 -> $500 left above a $0 MLL.
  Build cushion first (~$2k-3k+ balance), then request.
- **Rough sim (2026-10-02, 4,000 runs x 120 days, made-up day profiles, 50K + RTA,
  EOD-only MLL check):** steady trader (65% green, +$300/-$250): Standard ~$9.2k vs
  Consistency ~$9.4k paid - a tie. Lumpy trader (50% green, big-day tail): Standard
  ~$3.0k vs Consistency ~$2.2k - Standard wins. No-edge trader: both lose. Biggest lever
  was the withdraw buffer, not the path: waiting for $2k-4k balance before requesting cut
  blow-ups from ~68% to ~3% (steady profile). Re-run with real daily P/L before choosing.
- Separate rule: the **Combine** still has its own 55% consistency (best day < $1,650 on a
  $3,000 target) no matter which XFA path you pick.

## 5. Live Funded Account (LFA) - real money, BOTS END HERE

- Call-up to Live is at Risk Team's discretion. **You can't decline - go Live or lose the XFAs.**
  All XFAs close when you go Live. Only 1 LFA.
- **No API / no bots / no trade copier in Live.** Our bot has to become manual trading here.
- Start: 20% of combined XFA balance (min $10k) to trade, 80% held back, released 25% per
  $3,000 profit (50K). Balance < $1,000 = closed.
- Live DLL $2,000 (50K), 5 lots max. Pro market data $133/mo per exchange (Topstep pays 1).
- Payouts: 5 winning days of $150+, 50% no cap. After 30 winning days = daily payouts up to 100%.
- Can be "shoulder-tapped" back to an XFA for YOLO behaviour.

## 6. Hours / products

- **Flat by 3:10 PM CT every day** (= 4:10 AM MYT in CDT). Risk starts flattening 3:08 PM CT.
  No overnight, no weekend holds. Reopen 5:00 PM CT. Trading day = 5 PM - 3:10 PM CT.
- ES, MES, NQ, MNQ etc. allowed. No forex. Holiday hours differ (see holiday article).

## 7. News

- **No news-flat rule** (unlike Lucid funded). Slippage is your problem, no refunds.
- **CPI exception:** no NEW ES/NQ (mini) positions 5 min before to 5 min after CPI; micros
  capped at **3** (50K) in that window. Pending orders won't fill then.
- **Banned: trading your max position size straight into a major news event.**
- During extreme volatility Topstep can temporarily cut position limits per product.

## 8. Bots / platform - the parts that affect our plan

- Bots allowed in Combine + XFA **only through the TopstepX / ProjectX API** (REST + WebSocket,
  Python OK). One API key covers all accounts. No sandbox - test on a Practice account.
- **All order traffic must come from your own device. VPS / VPN / remote servers = banned**
  ("can result in suspension or removal"). A server may only store data, backtest, log.
- **Quantower via TopstepX does NOT include Strategy Manager / Strategy Runner** (the bot
  runner) - needs a paid Quantower license, if it's allowed at all. Better route: run our
  bot in **Python straight on the ProjectX API** from the home PC.
- Only **1 live session across devices** - logging in on your phone kicks the PC off
  (tabs on the same PC/browser are fine). Check whether an API session counts too.
- No help or refunds for bot errors or malfunctions.
- Trade copier OK across Combine/XFA (up to $750K buying power), not Live.

## 9. Banned conduct (can mean no payout / closure)

- Cross-account hedging (long in one, short in another, incl. ES vs MES).
- Account stacking (blow one, switch, repeat). Excessive Combine/Reset buying.
- "Unfair technology": HFT, SIM-fill exploits - hundreds of trades/day, trades lasting
  seconds, **tight brackets / auto-breakeven used to farm SIM fills**, gap stray fills.
  Keep trade count low and holds in minutes.
- Orders outside best bid/offer. Slow/external data feeds.
- Holding a position within 2% of CME price limit.
- Trading for others, sharing accounts, coordinated trading with friends.
- Chargebacks. "Anything else Topstep decides" (sole discretion).

## 10. Payout to Malaysia

- Only option for us: **Wire/SWIFT, $30 fee, 5-10 business days** (+1-3 days approval).
  Wise is only for China/Canada/UK right now.
- **Must be a bank account in YOUR own name.** Our only account is the sole-prop
  "Quantum Capital Global" -> **ask Topstep support before buying** whether that counts,
  or open a personal account.
- W-8BEN form (non-US) at payout.

## Our plan in one line

Home PC + UPS + phone hotspot, Python bot on ProjectX API, 50K Combine with the $1,000 DLL
(for the doubled payout cap), keep best day < $1,650, flat by 3:10 PM CT, low trade count,
never size up into news. Bot income stops at the Live call-up.

Sources (help.topstep.com/en/articles/...): 8284197 Combine params, 8284215 XFA params,
8284204 MLL, 10490293 DLL, 8284208 consistency, 8284233 payout policy, 10296582 prohibited
conduct, 10305426 prohibited strategies, 11187768 API access, 8284116 eligibility,
8284211 economic releases, 13613539 risk adjustments/CPI, 8284223 scaling plan, 8284206
hours/products, 8284179 Quantower, 12578731 IDV, 8284213 commissions, 8284217 activation,
14289835 pricing, 8284121 subscriptions, 10657969 LFA params, 13747178 call-up/down,
12060405 Back2Funded, 14645398 Pro account, 8284225 2% price limit, 11748475 live risk
expansion, 13747047 hedging, 14434175 TopstepX, 8284229 LFA costs.
