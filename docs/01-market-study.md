# US equity market study: regime as of 24 Sep 2026

Data: Zacks Investment Research (prices are the 23 Sep 2026 close; metrics were refreshed 24 Sep). Macro comes from Zacks market commentary dated 23–24 Sep 2026. CPI comes from web search summaries of the BLS release; the primary source could not be fetched from this environment, so treat those figures as secondary. This is research, not investment advice.

---

## 1. The regime in one paragraph

This is a **supply-shock tightening regime**, and it is not a normal late-cycle one. Here are the pieces:

- **Energy:** The Iran war (now in its 7th month) has put Brent at about $100–105 and WTI at about $92–93.
- **Trade:** The US–China tariff war is in its 18th month.
- **The Fed:** Under Chair Warsh, it made its first 2026 hike (+25 bp) last week. CME FedWatch puts the odds of another hike in October at about 66%, up from 9% a month ago.
- **Bonds:** The 10-year Treasury yield hit **5.135%**, its highest since July 2007. The 2-year is at about 4.95%, so the curve is nearly flat at ~20 bp.
- **Labor:** Initial jobless claims were 197k, near six-decade lows.
- **Inflation:** Headline CPI is about 3.4% year on year, but core is about 2.4%, the lowest since 2021. Most of the headline number is energy.

Despite all this, the S&P 500 sits at **7,706**, about 1% off its high. SPY is up 12.2% year to date, and the Nasdaq set a record close on 22 Sep.

The key tension: **the Fed is raising rates against an energy shock while core inflation is falling.** Raising rates cannot produce more oil. It can only reduce demand. Historically, that pattern (1973–74, 2008 H1) ends in either a policy reversal or a recession. It rarely ends in a soft landing with a 5% 10-year yield.

## 2. What the tape is actually saying

**Breadth is poor under record index levels.** On 23 Sep, the Nasdaq printed 41 new 52-week highs against **186 new lows**. The S&P printed 14 highs against 33 lows. The index is being carried by a narrow cohort.

**Concentration is at structural extremes.** The top 10 holdings are 38% of SPY. NVDA alone is 8.4%, and NVDA + AAPL + MSFT make up 21%. An S&P 500 fund is therefore largely a bet on the AI capex cycle, even though it looks diversified. That matters for your plan: you are layering an AI tilt on top of a benchmark that already carries one.

**The AI trade has split in two.** Over 52 weeks:

| Winners (AI hardware) | 52w | Losers (AI-threatened incumbents) | 52w |
|---|---|---|---|
| Micron (MU) | **+563%** | ServiceNow (NOW) | −25% |
| AMD | +282% | S&P Global (SPGI) | −17% |
| ASML | +84% | American Express (AXP) | −11% |
| TSM | +59% | Microsoft (MSFT) | −2% |
| NVDA | +27% | Meta (META) | −2% |

The market is pricing AI as **a transfer of economic rent** (profit above what competition would allow) away from the owners of software, data and distribution moats, and toward whoever supplies the compute. The Meta "Muse" episode this month shows this in practice. Zacks reported that Muse is seen as a challenge to "banks, consumer businesses and online shopping platforms", and AMZN (−2%) and GOOGL (−3.8%) fell after blocking it from their shopping platforms. **Agentic commerce** (AI agents that shop and pay on a user's behalf) is a direct threat to the moats the Buffett style relies on: brand, habitual checkout, payment-network defaults. Keep this in mind for the V/AXP positions in the plan.

**Staples are being bought as bonds, not as businesses.** KO is +26% YTD at 26.8× forward earnings, and its 2.4% yield is below its own 5-year average of 2.9%. Meanwhile PEP (−9%) and General Mills (−24%) are being sold. The market is separating pricing power (KO: 27.8% operating margin) from volume-dependent snack businesses. One possible reason is GLP-1 weight-loss drugs cutting snack volumes. That is my hypothesis; the data doesn't show it directly. Zacks ranks Consumer Staples **16th of 16 sectors**.

## 3. Valuation vs. the risk-free alternative

The number that matters most in this regime is the **equity risk premium** (ERP): the extra return stocks are expected to earn over risk-free bonds.

- A **2-year Treasury or T-bill yields about 4.9–5.0%**, with no drawdown risk. That is your hurdle rate: any stock has to be expected to beat it.
- The model portfolio in `02-portfolio-plan.md` has a **forward earnings yield of 4.67%** on current-year (F1) earnings, or **5.28%** on next-year (F2) earnings. The aggregate P/E is computed harmonically by `python -m portfolio summary`.
- So on F2 earnings, the portfolio's ERP over the 10-year is **about +0.15 percentage points**. Before counting growth, that is essentially zero. The whole case for owning stocks over T-bills here rests on **earnings growth** (consensus long-term EPS growth for the portfolio is about 15.8%) and on those estimates being right.

The second-order point: **consensus estimates for AI hardware are extrapolations of a capex cycle.** NVDA revenue estimates go from about $406B in FY27 to **$672B in FY28**. At that FY28 EPS, NVDA is 14.7×, which looks cheap. But that multiple only holds if hyperscaler capex keeps rising another 65%. MU trading at 5.7× forward earnings is the classic **cyclical peak signature**: commodity producers look cheapest at peak earnings. The mechanical screen in this repo ranks MU highly for exactly that reason. I overrode it.

**Incentives behind the data you'll see:**
- **Sell-side ratings:** The average broker rating on every megacap is 1.1–1.4, where 1 is strong buy. NVDA gets 50 buys against 1 sell. Investment-banking and trading relationships make these ratings close to meaningless as a signal.
- **Zacks Rank:** It is built from estimate revisions and is informative over weeks to months. It says nothing about a 7–10-year thesis.
- **Target prices:** They trail the stock price; they don't lead it.

## 4. Distorted numbers to be aware of

- **Alphabet (GOOGL) and Amazon (AMZN)** have current-year EPS estimates *above* next-year estimates (GOOGL 20.51 → 14.71; AMZN 13.01 → 10.52). GOOGL's last quarter beat by 216%. That points to large non-operating gains in 2026, most likely marks on private stakes (my inference). **Use F2 P/E** (GOOGL 23.0×, AMZN 23.7×), not F1.
- **Berkshire (BRK.B)** has no consensus F2 or long-term growth estimate. Its EPS includes investment gains, so book value or operating earnings are better anchors.
- **Micron (MU)** figures are fiscal years ending August. F1 is FY27.

## 5. Implications for the portfolio (the decisions these drove)

1. **Don't try to time the market, but spread the entry.** With the ERP near zero and the Fed hiking, move the initial capital in over **3 months** rather than all at once. Monthly contributions then act as ongoing DCA (dollar-cost averaging).
2. **Hedge the one macro variable that hurts the rest of the book:** an energy shock. **CVX at 5%** gains (+20%) in the stagflation scenario. Every 1% moved into CVX from a typical holding improves that scenario by about 0.4pp.
3. **Prefer insurers and float over consumer-brand moats inside the quality sleeve.** CB (12×) and BRK.B reinvest float at 5%. Their moats (underwriting discipline, capital) are less exposed to agentic disintermediation than brands and checkout defaults.
4. **Own AI through its toll-takers and cash-generative platforms, not the momentum names.** NVDA, TSM, AVGO, AMZN, META, plus MSFT and GOOGL in the core. Excluded: AMD (82× F1), CRWD (209×), MU (cyclical peak), ANET (50×).
5. **State the AI concentration openly.** The target portfolio is **55% AI-linked** (ai_semis 26% plus ai_platform 29%), against roughly 35–40% in the S&P 500. That is your chosen overweight. The stress tests show what it costs.

## Sources

- [Stock Market News for Sep 24, 2026 — Zacks](https://www.zacks.com/stock/news/2995035/stock-market-news-for-sep-24,-2026) (published 09/24/2026)
- [Stock Market News for Sep 23, 2026 — Zacks](https://www.zacks.com/stock/news/2994299/stock-market-news-for-sep-23,-2026) (09/23/2026)
- [Jobless Claims Decreased More Than Expected — Zacks](https://www.zacks.com/stock/news/2995235/jobless-claims-decreased-more-than-expected) (09/24/2026)
- [Fed Governor Michael Barr's Speech in Focus — Zacks](https://www.zacks.com/stock/news/2994553/fed-governor-michael-barr's-speech-in-focus) (09/23/2026)
- SPY holdings and fund metrics — [Zacks SPY](https://www.zacks.com/stock/quote/SPY), holdings as of 2026-09-24
- CPI (secondary, via search): [BLS CPI release](https://www.bls.gov/news.release/cpi.nr0.htm), [CNBC Aug 2026 CPI](https://www.cnbc.com/2026/09/11/cpi-inflation-report-august-2026.html)
- Per-ticker metrics: https://www.zacks.com/stock/quote/&lt;TICKER&gt; for every ticker in `data/universe.csv`
