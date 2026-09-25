# Model portfolio and operating rules

**Mandate** (from your answers): a flexible 7–10-year horizon; you can hold through a −40% year; under $10k to start plus $300–1,000/month; Roth first, overflow to taxable; mostly individual stocks, 12–15 names, reviewed quarterly; a blend of 60% Buffett-style quality and 40% AI growth.

Prices and metrics are from Zacks as of 23–24 Sep 2026. The weights live in `data/target_portfolio.csv`. Re-run `python -m portfolio summary` after changing them.

## 1. Target holdings (14 names, max 10%)

### Quality core: 60%

| Ticker | Weight | Account | P/E F2 | Why it's here | What breaks the thesis |
|---|---|---|---|---|---|
| BRK.B | 10% | Taxable | n/a (P/E TTM 22.8×) | The Buffett proxy in one ticker. Pays no dividend, so it creates no tax drag in taxable. Its cash pile earns ~5% at current rates | Post-Buffett capital allocation turns empire-building; big acquisitions above 1.5× book |
| MSFT | 8% | Taxable | 21.5× | Enterprise AI distribution plus Azure. Flat for 52 weeks while semis tripled, so the de-rating is already in the price | Copilot/Azure AI growth falls below 20% while capex keeps rising, i.e. return on AI capex declining |
| GOOGL | 7% | Taxable | 23.0× | Lowest PEG (0.98) among the megacaps; search cash flows plus TPUs plus Cloud; 51% ROE | Search share loss to agents shows up in paid clicks; a regulatory breakup |
| V | 7% | Taxable | 24.1× | A toll road on consumer spending: 55% operating margin, capital-light | Agentic commerce routes payments over account-to-account or stablecoin rails. Watch how agent checkout is implemented |
| KO | 7% | Roth | 25.0× | You asked for it. It has real pricing power (27.8% operating margin), but at 26.8× F1 it is priced like a bond. **Build it slowly; don't chase** | Volume declines of 2%+ for 2 quarters; the yield staying below 2.5% means it's still expensive |
| CB | 6% | Roth | 11.6× | Berkshire's own insurance pick. 1.6× book, beta 0.37, and float reinvests at 5% | Combined ratio above 95% for a full year (underwriting discipline lost) |
| AXP | 5% | Roth | 14.9× | Berkshire holding, closed-loop network, affluent customers; −18% YTD | Card-member loss rates climbing above 3% (the rate-hike cycle hitting credit) |
| MCO | 5% | Taxable | 25.2× | Ratings duopoly with Berkshire as a holder. High rates force refinancing, and refinancing needs ratings | AI-native credit analytics erode ratings fees (the same fear already hit SPGI, −22% YTD) |
| CVX | 5% | Roth | 14.0× | **A hedge, not a thesis.** It is the one holding that rises in an oil shock, the main threat to the other 13. Also a Berkshire holding; 3.5% yield | Resolution of the Iran war takes Brent below $75. Then it's a normal 12× oil major and can be cut to 2–3% |

### AI growth: 40%

| Ticker | Weight | Account | P/E F2 | Why it's here | What breaks the thesis |
|---|---|---|---|---|---|
| NVDA | 10% | Roth | 14.7× | The compute monopoly: 56% net margin, Zacks Rank #1, 96% ROE. Cheap if FY28 estimates hold | Hyperscaler capex guidance flat or down; gross margin below 70% (custom ASICs taking share) |
| TSM | 9% | Roth | 21.1× | Every leading-edge chip (NVDA, AVGO, AMD, Apple) goes through it. Top of the growth screen; PEG 0.99 | Taiwan Strait escalation (see the stress test); US/Japan fabs cutting pricing power |
| AMZN | 8% | Roth | 23.7× | AWS plus retail plus ads. It gains from AI whether capex booms or AI gets cheaper | AWS growth below the Azure/GCP gap for 3+ quarters |
| AVGO | 7% | Roth | 18.6× | Custom AI accelerators plus networking; a hedge *within* AI against NVDA share loss | Loss of a top-3 custom-silicon customer |
| META | 6% | Roth | 21.7× | The AI application layer (Muse); ad cash flow funds the capex | Muse fails to monetize while capex is above 40% of revenue |

**Explicitly excluded, with reasons:**

| Ticker | Reason |
|---|---|
| MU | 5.7× forward is a cyclical-peak signature; memory is a commodity |
| AMD | 82× F1, +282% in 52 weeks |
| ANET | 50× F1 |
| CRWD | 209× F1, Zacks Rank #4 |
| COST | 40× F1 for ~10% growth |
| PEP | Zacks Rank #4, debt/equity 1.9, 5.5% long-term growth; the 4.6% yield already signals that dividend risk is being priced in |

These are on the watchlist (`03-watchlist.md`), not banned.

## 2. What you are actually holding (from `python -m portfolio summary`)

| Metric | Portfolio | Note |
|---|---|---|
| Forward P/E (F1 / F2) | 21.4× / 18.9× | Harmonic weighting. Earnings yield 4.67% / 5.28% |
| Beta | 1.12 | Slightly more volatile than the market |
| Dividend yield | 0.83% | Low, by design, which is tax-efficient |
| Consensus long-term EPS growth | 15.8% | Analyst consensus runs optimistic; haircut it to about 10–12% |
| AI-linked exposure | **55%** | ai_semis 26% plus ai_platform 29%, against ~35–40% in the S&P 500 |
| Financials plus insurance | 23% | This is the Buffett tilt |

**Stress tests** (instant shocks; the assumptions are in `portfolio/core.py`):

| Scenario | Portfolio loss |
|---|---|
| AI capex digestion (2022-style) | −28% |
| Stagflation / rate shock (10y at 6%, Brent at $130) | −24% |
| Taiwan Strait blockade | −25% |
| 2008-style credit recession | **−41.5%** |

The GFC scenario sits right at your −40% tolerance. That is intentional: your answers imply the portfolio should survive a 1-in-20-year event without you being forced to sell. If that number feels wrong once you see it written down, the lever is the growth sleeve. Moving 10pp from NVDA to CB cuts about 2.5pp (GFC) to 5pp (AI capex) from the scenarios.

## 3. Account placement

The 2026 IRA contribution limit is **$7,500**, about $625/month. Income phase-outs apply, so confirm your eligibility.

- **Roth IRA:** the growth sleeve plus the dividend payers (KO, CVX, CB, AXP). The highest expected returns and all dividends compound tax-free there. **All trimming happens in the Roth**, where selling triggers no tax.
- **Taxable:** BRK.B, MSFT, GOOGL, V, MCO. All are low- or no-yield buy-and-hold names you should rarely need to sell. Gains stay unrealized, and if you ever sell after a year they get long-term capital-gains treatment.
- At $300–625/month, everything goes to the Roth. Above $625/month, the extra goes to taxable. `contribute --roth-room` handles the routing.

## 4. Deployment

1. **Initial capital:** invest one third per month over 3 months, starting now. Consider buying NVDA/TSM/AVGO only after they report (TSM 15 Oct, NVDA 18 Nov, AVGO 10 Dec). Buying just before earnings adds binary risk to a brand-new position for no benefit.
2. **Monthly:** `python -m portfolio contribute 650 --roth-room <remaining Roth room this year>`. The plan buys only the names that are underweight, so **each contribution also rebalances the portfolio without selling anything**.
3. **KO specifically:** add only in months when its yield is ≥2.7% (price about ≤$78) or when the planner calls for it. You chose it; the discipline is not overpaying for it.

## 5. Operating rules (quarterly, after earnings season: late Jan / Apr / Jul / Oct)

1. Run `python -m portfolio drift`. **Rebalance band:** ±5pp absolute. Inside the band, let new contributions do the correcting. Outside it, trim in the Roth only.
2. For each holding, check the "breaks the thesis" column. **Sell on a broken thesis, not on price.** A −30% move with the thesis intact is a buy under rule 1.
3. Refresh `data/universe.csv` (prices, P/Es, Zacks Rank) and re-run `screen`. A replacement needs a clear edge over the holding it displaces. Otherwise you are just adding turnover.
4. **Hard caps:** no single name above 12%; AI-linked total at most 60%; financials plus insurance at most 30%.
5. Keep a one-line **decision journal** entry for every buy and sell (date, ticker, reason). After 2–3 years it is the only honest way to learn whether stock picking is adding value over an S&P 500 fund. If it isn't, switching the core to an index fund is the rational move.

## 6. Pressure points you should argue with

- **The benchmark problem:** a 55% AI weight plus the megacap core puts your *active* bet at only about 15–20pp away from the S&P 500. With 14 names you take on idiosyncratic risk for a portfolio that still mostly tracks the index. That trade-off is only worth it if the non-index tilts (insurers, CVX, the underweight in AAPL/TSLA) are views you actually hold.
- **Buffett-style investing in 2026:** Berkshire's moats were built on brands and distribution. Agentic AI attacks exactly those. This plan leans the Buffett sleeve toward *balance-sheet* moats (insurance float, networks, ratings) over *brand* moats. KO is the exception you requested.
- **The single biggest correlated risk** is not AI valuation. It is the **rate path**. At a 5.1% 10-year yield, a further +100 bp re-rates everything long-duration (stocks whose value rests mostly on distant earnings) at once, both sleeves included. CVX and CB are the only positions that like higher yields.
