# StockStudy
Leverage AI in stock investing.

A personal US stock portfolio: the research behind it, the model portfolio, and a small tool for tracking and adding to it.

## Documents

| File | Contents |
|---|---|
| [docs/01-market-study.md](docs/01-market-study.md) | Market regime as of Sep 2026: rates, oil, concentration, the AI split, valuation vs T-bills |
| [docs/02-portfolio-plan.md](docs/02-portfolio-plan.md) | 14-stock model portfolio (60% quality / 40% AI growth), what would break each thesis, account placement, operating rules |
| [docs/03-watchlist.md](docs/03-watchlist.md) | Screen results, why I overrode the screen, earnings calendar |

## Data

- `data/universe.csv`: candidate stocks with Zacks fundamentals (snapshot 23–24 Sep 2026). Refresh it quarterly.
- `data/target_portfolio.csv`: target weights, preferred account, and the role of each holding.
- `data/holdings.csv`: **your actual positions.** One row per lot: `ticker,account,shares`, where account is `roth` or `taxable`.
- `data/prices.csv` (optional): `ticker,price` rows that override the snapshot prices.

## Tool (Python 3.9+, standard library only)

```bash
python -m portfolio summary                        # fundamentals, exposures, stress tests of the target portfolio
python -m portfolio screen                         # rank the candidate universe by sleeve
python -m portfolio drift                          # holdings vs targets; flags drift beyond ±5pp
python -m portfolio contribute 650 --roth-room 7500  # plan this month's buys (no selling)
python -m unittest discover -s tests -t .          # run the tests
```

*Research and education only. This is not investment advice. The figures are point-in-time and will go stale.*
