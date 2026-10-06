# StockStudy

Research toolkit for applying AI to equity investing, built so that its results can be
trusted.

[![CI](https://github.com/ToMars-design/StockStudy/actions/workflows/ci.yml/badge.svg)](https://github.com/ToMars-design/StockStudy/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue.svg)

> **Disclaimer.** This repository is for research and education. Nothing in it is
> investment advice or a recommendation to buy or sell any security, and past or simulated
> performance does not predict future returns.

## Why

AI has made generating and testing trading ideas nearly free. It has not made it any easier
to tell a real edge from an artefact. Most impressive backtests are explained by look-ahead
bias, survivorship, a language model that already knows how the story ended, or the sheer
number of variants tried.

StockStudy is built evaluation-first. Before any strategy exists, it defines what counts as
evidence, in the [research-integrity standard](docs/research-integrity.md), and enforces as
much of that standard as possible with code.

## Status

Early stage. In place: the toolchain, the research standard, the Claude Code configuration
that holds AI assistance to that standard, the executable look-ahead guard, and
point-in-time US company fundamentals from SEC EDGAR. Price data, features and models come
next, and each must meet the standard to be merged.

## Quick start

Requires [uv](https://docs.astral.sh/uv/) and `make`.

```bash
git clone https://github.com/ToMars-design/StockStudy.git
cd StockStudy
make install   # locked environment + git hooks
make check     # lint, type-check and test: exactly what CI runs
```

## Example: catching look-ahead bias

`assert_no_lookahead` fails any transform whose output at time *t* changes when only the
data after *t* is dropped or perturbed:

```python
import numpy as np
import pandas as pd

from stockstudy.lookahead import assert_no_lookahead

rng = np.random.default_rng(0)
prices = pd.Series(
    100 * np.exp(rng.normal(0, 0.01, 250).cumsum()),
    index=pd.bdate_range("2024-01-01", periods=250),
    name="close",
)

assert_no_lookahead(lambda p: p.pct_change(20), prices)  # trailing 20-day return: passes
assert_no_lookahead(lambda p: (p - p.mean()) / p.std(), prices)  # full-sample z-score: fails
```

```text
LookAheadError: outputs at or before 2024-01-01 changed when the inputs after it were dropped: first difference at 2024-01-01, column 'close': -0.9056479712268821 originally, nan when dropped
```

[`tests/test_lookahead.py`](tests/test_lookahead.py) doubles as a catalogue of common leaks
(negative shifts, full-sample statistics, centred windows, backward fills, left-labelled
resampling, per-ticker panel leaks) and their causal alternatives.

## Data: point-in-time fundamentals from SEC EDGAR

Every US-listed company files its financial statements with the SEC, which publishes each
reported figure together with the filing that reported it. StockStudy keeps every version,
so a figure that was later restated still shows its original value on dates before the
restatement was filed, as investors saw it then.

The SEC requires automated requests to identify a contact, read here from an environment
variable:

```bash
export SEC_USER_AGENT="Your Name you@example.com"
uv run python -m stockstudy.edgar AAPL MSFT   # downloads and records each company's facts
```

```python
import pandas as pd

from stockstudy.edgar import EdgarClient
from stockstudy.pit import latest_value

client = EdgarClient()  # reads SEC_USER_AGENT
facts = client.company_facts(client.tickers()["AAPL"])  # or a CIK directly: 320193
revenue = latest_value(
    facts,
    pd.bdate_range("2015-01-01", "2025-12-31"),
    concept="RevenueFromContractWithCustomerExcludingAssessedTax",
    period="annual",
)  # daily, indexed by (date, cik): the latest annual revenue known on each date
```

A figure filed on day *D* counts as known from the next business day, because the filing
date does not say whether it arrived before or after the close. Every download is saved
under `data/raw/edgar/` (git-ignored), named by retrieval time and content hash.

Limits: structured data starts in 2009–2011; companies tag the same item differently
(revenue alone has several tags); and the SEC's ticker list covers current companies only,
so it must not be used to build a historical universe.

## Project layout

```text
.
├── CLAUDE.md                   Rules Claude Code follows in this repository
├── .claude/                    Claude Code settings, session hook, /research-review skill
├── docs/
│   └── research-integrity.md   The evidence standard every result is held to
├── src/stockstudy/             Library code: typed, tested, importable
│   ├── lookahead.py            Executable look-ahead check
│   ├── pit.py                  Point-in-time store: what was known, from when
│   └── edgar.py                SEC EDGAR client for company fundamentals
├── tests/                      pytest suite (doctests in src/ run too)
├── Makefile                    The quality gates; CI runs the same targets
├── pyproject.toml              Metadata, dependencies and tool configuration
├── uv.lock                     Exact versions of every dependency
└── .github/                    CI workflow and Dependabot configuration
```

## Development

| Command          | What it does                                                   |
| ---------------- | -------------------------------------------------------------- |
| `make install`   | Create the locked environment and install the git hooks        |
| `make fmt`       | Format code and apply safe lint fixes                          |
| `make check`     | Lint, type-check and test: what CI runs                        |
| `make test`      | Tests and doctests with coverage (at least 90% required)       |
| `uv add <pkg>`   | Add a dependency and update `uv.lock` (never edit it by hand)  |

The git hooks format and lint staged code, strip notebook outputs, and block private keys
and files over 500 KB. Code conventions live in [CLAUDE.md](CLAUDE.md), which applies to
human contributors as much as to Claude.

## Working with Claude Code

The repository holds Claude Code to the same standard as a careful researcher. The rules
are layered by how strongly they are enforced:

- **Guidance: [`CLAUDE.md`](CLAUDE.md).** Read at the start of every session: commands,
  conventions, the research rules, and how to report results.
- **Procedure: `/research-review`** ([skill](.claude/skills/research-review/SKILL.md)).
  Audits a backtest, feature or model change against each rule, with evidence.
- **Enforcement: tests, git hooks, CI and [settings](.claude/settings.json).** Checks that
  cannot be argued with: the look-ahead tests, the lint and type gates, and no read access
  to `.env` files.

In Claude Code on the web, a session-start hook installs the locked environment and the git
hooks, so `make check` works from the first message.

## License

[Apache-2.0](LICENSE).
