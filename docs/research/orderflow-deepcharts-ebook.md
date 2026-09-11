# Order flow ebook (DeepCharts) - full breakdown + what to backtest

Source: *"How to track Institutional Flows - A full guide to Orderflow Analysis"*,
DeepCharts (deepcharts.com), 32 pages. Shared by the user in chat and read
2026-09-11. The PDF itself isn't in the repo.

**Rule (user, 2026-09-11): if we don't have the data to test an idea, go find the
historical data and backtest it properly. Don't drop the idea.** See section 11.

## Conclusion

- **What it is:** a free sales ebook for DeepCharts' paid charting tools. Under
  their brand names it's a standard order flow course (auction market theory,
  volume profile, footprint, big-trade filter, order book heatmap). The ideas
  are real and widely used.
- **What it isn't:** proof of an edge. It has no win rates, no backtests and no
  exact numbers. Page 28 says so itself: *"a simplified educational framework,
  not a complete operational strategy with robust risk management."* It also has
  math errors (section 8), so treat every claim as untested.
- **We don't need DeepCharts.** NinjaTrader 8's Order Flow+ pack has an
  equivalent for all 5 tools (section 9).
- **Best fit for us: Range mode.** Price fails outside the value area of the
  first 30 minutes of the NY session, then goes back to the POC. Mean reversion
  = high win rate, small wins, so it fits task #2 (high-WR low-RR). It uses the
  same opening window as the planned ORB tests, so the two can share code.
- **Also worth testing (separately):**
  - Discovery mode / "3 step" trend model: lower WR, bigger wins. Not for task
    #2 unless the numbers surprise us.
  - Big-trade "trapped / effective" filter: an add-on to Range mode and to ORB.
  - Order book heatmap ideas (magnet clusters, book refill): need historical
    order book data. Buy/source it (section 11), test last.
- **Before any of it can be a bot:** every vague word ("absorption", "trapped",
  "follow-through", "acceptance", "big trade") needs a number. Candidate
  definitions are in section 10.

## Page map

| Pages | Section | Content |
|---|---|---|
| 1 | Cover | Title, DeepCharts screenshots |
| 2 | Intro | Pitch: information gap between retail and "professional operators"; price alone won't last; order flow shows their footprint |
| 3 | See beyond the candlestick | Price is the *result* of orders clashing; read volume, not just candles |
| 4 | The Truth? | Order flow data is public; "big players move slow, they leave traces" |
| 5-9 | Orders matching algorithm | Limit vs market orders, the order book, how price moves, slippage |
| 10-13 | Deep Print | Footprint (bid x ask per price), delta, aggression vs absorption |
| 14-19 | Deep Profile | Volume profile, value area, failed auction vs breakout, low volume nodes, value migration |
| 20-22 | Deep Trades | Big-trade bubbles, effective buyers vs trapped sellers |
| 23-24 | Range / Discovery mode | The two trading modes (mean reversion vs trend) |
| 25-28 | 3 Step Strategy | Trend-following model: profile -> absorption -> aggression |
| 29-31 | DeepDom | Order book heatmap: liquidity magnets, book surprises (refill, spoofing) |
| 32 | Outro | "Stop trying to predict. Start reacting." + ad |

## 1. The basics - how price actually moves (p5-9)

- **Two order types:**
  - **Limit orders (passive)** sit in the order book (DOM, depth of market) at a
    chosen price and wait. Sell limits sit above the last price, buy limits
    below it. They can be added or pulled anytime, so they show *intent*, not
    commitment.
  - **Market orders (aggressive)** execute instantly at whatever price is
    available. You don't choose the price, but you're guaranteed a fill.
- **A trade = a market order meets an opposite limit order.**
- **Best ask** = the lowest sell limit (first seller a market buy hits).
  **Best bid** = the highest buy limit. The gap between them = the **spread**.
- **Price moves when market orders use up all the limit orders at the best
  bid/ask.** Then price jumps to the next level. "Market orders are the
  attackers, limit orders are the wall."
- **Their DOM example:**

  | Price | Resting size |
  |---|---|
  | 105 | 78 sellers |
  | 104 | 64 sellers |
  | 103 | 56 sellers |
  | 102 | 42 sellers |
  | 101 | 33 sellers (best ask) |
  | **100** | **last price** |
  | 99 | 41 buyers (best bid) |
  | 98 | 33 buyers |
  | 97 | 51 buyers |
  | 96 | 60 buyers |
  | 95 | 72 buyers |

- **95 market buys arrive:** 33 fill at 101, 42 at 102, and the last 20 at 103.
  103 is left with 36. Filling across several prices instead of one = **slippage**.
  - **The book's text is wrong here:** it says "20 at 56" and "the new price is
    102". Correct: 20 at **103**, new price **103**. The picture is right.
- **Why this matters:** a big player can't hit "Buy Market" with 10,000
  contracts. It would sweep through the book, push price up and wreck their
  average entry. So they split orders and buy over time, and that leaves traces
  in the order flow.

## 2. Deep Print = footprint chart (p10-13)

- **Looks inside each candle** and shows, at every price, how many contracts
  traded:
  - **Left column:** market sells that hit the bid (aggressive sellers).
  - **Right column:** market buys that lifted the ask (aggressive buyers).
- **Delta** = market buys minus market sells at each price. Shown as bars
  (green = more buying, purple = more selling). Their "Deep Delta" indicator
  sums it per candle: "who's pressing harder on the accelerator".
- **Aggression (p13, top):** aggressive buyers dominate a key level with heavy
  volume (e.g. 145 buys vs 0 sells, 112 vs 5), **and price then goes up.** That's
  real pressure that moves price ("momentum injection").
- **Absorption (p13, bottom):** "failed aggression". Heavy selling at the lows
  (e.g. 189 sells vs 12 buys, 128 vs 3), strongly negative delta, **but price
  won't go lower**. The candle leaves a long lower wick and closes green.
  Hidden passive buyers (limit orders) soaked up all the selling, so it's a
  bullish sign.

## 3. Deep Profile = volume profile (p14-19)

- **Volume profile** = total contracts traded at each price over a chosen time
  window.
- **Their claim:** volume follows a bell curve (Gaussian); most trading sits near
  the middle, and 1 standard deviation = "precisely 68%" of volume. See section
  8 for why that's shaky.
- **Value area** (VAH = top, VAL = bottom) = the zone holding about 68-70% of the
  volume. It's where big players are comfortable, liquidity is deep, slippage is
  low, and price spends most of its time.
- **POC (point of control)** = the single price with the most volume ("fair
  price").
- **"Price action models - range or breakout - are all rooted in how price
  behaves relative to a value area."**
- **Best reference = a fixed profile:** the previous day, or **the first 30
  minutes of the New York session**.
- **Pattern 1 - Failed auction (p17):** price reaches the VAH or VAL, tries to
  break out, fails. Trade the move back toward the POC. Look for sellers being
  absorbed at the VAL, or buyers being absorbed at the VAH.
- **Pattern 2 - Breakout (p17):** price reaches the VAH/VAL with aggressive
  orders that keep going. Trade the breakout. Look for aggressive selling with
  continuation at the VAL, or aggressive buying at the VAH.
- **Low volume nodes (LVN, p18):** prices inside the profile with very little
  trading = "no price acceptance", an imbalance. Price either slices through
  them fast or bounces off them fast. It rarely sits there.
- **Follow the money (p19):**
  - Track how the daily value areas move (**value migration**) to read the
    bigger trend and find key levels.
  - Confirm breakouts with the profile to filter out fake-outs. Their example: a
    fake-out above value that snaps back = failed auction, then a **value shift**
    lower.
  - LVNs between old and new value areas act as the breakout/failed-auction
    levels.

## 4. Deep Trades = big-trade bubbles (p20-22)

- **The problem:** thousands of trades a minute, most of them noise.
- **The filter:** only show trades above a **size threshold** as a bubble on the
  chart (green = big buy, purple = big sell). The idea: these are the moments
  big players committed money. **The book never gives the threshold.**
- **Effective buyers (p22):** big buys, then candles close in their favor and
  price drifts their way. The market rewarded them.
- **Trapped sellers (p22):** big sells at the lows, but price doesn't follow.
  They're stuck short in a losing position.
- **The rule:** "**Buy with follow-up = buy zone. Sell without follow-up = buy
  zone.**" (Mirror it for shorts: sell with follow-up or buy without follow-up
  = sell zone.)

## 5. The two trading modes (p23-24)

Volume profile (where value is) + big trades (who's committed) combined:

**Range mode - mean reversion (price inside the value area, in balance)**

| Question | Answer |
|---|---|
| Look for | Trapped traders at the VAL or VAH |
| Stop | Beyond the absorption (below it for longs, above it for shorts) |
| Target | The POC, or the opposite VAH/VAL |

**Discovery mode - trend following (value area breaks with acceptance and
effective aggression)**

| Question | Answer |
|---|---|
| Look for | "Reward traders" (rewarded traders) on a VAL/VAH breakout |
| Stop | On the POC, or beyond the aggression |
| Target | Let it run: trailing stop, previous session POC |

## 6. The "3 Step" trend-following model (p25-28)

- **Best on directional markets like ES or NQ.** Shown as a long example.
- **Step 1 - Fixed profile (bias timeframe, e.g. 5 min):**
  - Take a clear directional move and build a profile from its low to its high.
  - A POC near the top = the new higher price is accepted, institutions are
    trading there.
  - **Focus on the low volume node inside the move paired with the strongest
    positive delta.** (Their example: LVN of 12 contracts sitting next to delta
    rows of +25 and +23.) That's where price moved fast on real buying.
- **Step 2 - Absorption (wait for a retest):**
  - Wait for price to come back to that zone. It's below the POC (fair price), so
    it's "at a discount".
  - With a long bias, you want to see **sellers absorbed or trapped** there:
    the sellers who drove the pullback hit a wall of buy limits.
  - Drop to a lower timeframe (e.g. 1 min) for the final trigger.
- **Step 3 - Aggression (the trigger):**
  - Big market buys push price **and it follows through**.
  - Confirm with a sharp, wide candle delta, or a break of a level that held
    before. (Their example: breaking a level where buyers had been absorbed
    earlier = strong signal.) More seller absorption above it = "cherry on top".
  - **Entry:** at the new higher absorption. **Stop:** below the earlier lows
    where sellers were absorbed.
- **Their disclaimer:** educational framework only, not a full strategy with
  risk management; futures are risky.

## 7. DeepDom = order book heatmap (p29-31)

- **Shows where limit orders sit now and where they sat in the past** (a heatmap
  of the order book over time). Bubbles on top = aggressive orders filling that
  passive liquidity. Their screenshots are ES (6,600-6,870 area, contract
  ES-202606).
- **Magnet (p30):** big, stable, well-structured clusters of limit orders tend
  to pull price toward them, because big players know they can fill there with
  little slippage.
- **Book surprise (p31):** the size resting in the book changes suddenly.
  - **Spoofing** (fake orders placed to be pulled) is one kind. It's illegal.
  - **Book refill** (their example): aggressive buyers lift two clusters of sell
    limits, price pulls back, then **passive orders suddenly reappear at the
    exact level where the aggression happened**. That level then holds as
    support.

## 8. Errors and marketing claims to ignore

- **p9 math:** "20 at 56, new price 102" should be "20 at 103, new price 103".
- **p15 statistics:**
  - Shows 68% / 95% / **97.5%** for 1/2/3 standard deviations. 3 SD is **99.7%**.
  - "Volume follows a Gaussian model" is an oversimplification. Real profiles are
    often skewed or have two humps (double distribution).
  - "Precisely 68%": the value area is a **convention**, usually 70%, not a law.
- **"Institutions":** a big print could be anyone. Real institutions usually
  split their orders (icebergs, algos), so single big prints undercount them.
- **"Data is publicly available" (p4):** mostly true, but CME data still needs a
  data subscription (non-pro is cheap/free through Lucid).
- **No statistics anywhere:** no win rate, RR, sample size or backtest.

## 9. Their tools -> NinjaTrader 8 equivalents

| DeepCharts | What it shows | NinjaTrader 8 (Order Flow+) |
|---|---|---|
| Deep Print | Bid x ask at each price inside a candle | Order Flow Volumetric Bars |
| Deep Delta | Buys minus sells per candle | Order Flow Cumulative Delta |
| Deep Profile | Volume at each price, value area, POC | Order Flow Volume Profile |
| Deep Trades | Bubbles on big trades | Order Flow Trade Detector |
| DeepDom | Order book heatmap over time | Market Depth Map |

- **To check:** Order Flow+ comes with NinjaTrader's paid license tiers. Confirm
  whether the free prop-firm (Lucid/Tradovate) license unlocks it. If not, the
  bot can compute everything itself in NinjaScript from tick data anyway.

## 10. Turning it into bot rules - what needs a number

Nothing here is codeable until these are pinned down. Candidate definitions to
test (sweep the parameters, don't guess):

| Vague term | Candidate definition |
|---|---|
| Value area % | 70% (also test 68%) |
| Opening profile window | 9:30-10:00 ET (book); also test the ORB windows 9:15-9:30 and 9:30-9:45 |
| Big trade | Single print >= N ES contracts (sweep e.g. 20 / 50 / 100), or top X% of trade sizes over the last N days |
| Absorption (long) | Within k ticks of VAL: bar delta <= -X, but the bar closes back inside value / no new low beyond y ticks for z bars |
| Trapped traders | Big trade at an extreme, then price moves >= m ticks against it within n bars |
| Aggression / follow-through | Bar delta >= X, close beyond the level, next 1-2 bars continue |
| Acceptance (breakout) | N bars (or minutes) closing outside the value area |
| Low volume node | Price bins in the profile with volume < p% of the POC's volume |
| Stop / target | Per the tables in sections 5-6, in ticks, plus a max stop size so risk fits $300 funded / $800-1,000 eval |

Always apply: ES costs ($3.50 round turn + slippage), the red-folder news
filter (flat around USD high-impact news), and the $1,200 daily loss limit.

## 11. Data needed + where to get it

**Rule: missing data = go source it. Don't skip the test.** Check prices and how
far back the history goes before buying.

| Data | Needed for | Where to get it |
|---|---|---|
| Tick-by-tick trades with aggressor side (buy vs sell) | Volume profile, delta, footprint, big trades, absorption, all of sections 2-6 | NinjaTrader 8 historical tick data (downloads when connected; 1-tick data + Tick Replay for some order-flow indicators); Databento `GLBX.MDP3` (`trades` / `tbbo` schemas, history back to ~2010); CME DataMine; FirstRate Data; Tick Data LLC; Portara |
| Order book depth history (Level 2) | Heatmap magnets, book refill, spoofing, section 7 | NinjaTrader 8 Market Replay downloads (Level 1 + Level 2, limited history window, verify); Databento `mbp-10` (top 10 levels) or `mbo` (every order); CME DataMine market depth / MBO |

- **NinjaTrader's Strategy Analyzer can't replay order book depth.** Depth-based
  tests either run on the Playback connection with Market Replay data (slow, real
  time-ish) or offline in Python on Databento data.
- Tick-based tests (everything except section 7) can run in Strategy Analyzer or
  offline in Python.

## 12. Test order

1. **Range mode** on the 9:30-10:00 ET profile (failed auction -> POC). Task #2
   candidate. Tick data only.
2. **Discovery mode / 3-step trend model.** Separate track, expect lower WR.
3. **Big-trade trapped/effective filter** as an add-on to #1 and to ORB. Does
   it raise the win rate enough to pay for the fewer trades?
4. **Order book heatmap** (magnet, refill). Needs Level 2 history, so it goes
   last.

For each: win rate, average RR, expectancy after costs, trades/day, max drawdown.
Then feed the real numbers into `tools/prop_sim` (eval ~$800-1,000 risk, funded
~$200-300).
