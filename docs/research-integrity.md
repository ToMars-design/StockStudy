# Research integrity standard

Every result in StockStudy is held to this standard, whoever or whatever produced it: a
person, a notebook or an AI assistant. Where a rule can be enforced by code it is (tests,
hooks, CI); the rest are enforced in review, using the checklist at the end and the
`/research-review` skill.

## Why a standard

The scarce resource in quantitative investing is not model capacity but evaluation that can
be trusted; Arnott, Harvey & Markowitz (2019) set out a protocol in the same spirit.

- **The signal is faint.** The best machine-learning models in the literature explain well
  under 1% of the monthly variation in individual stock returns out of sample (Gu, Kelly &
  Xiu, 2020). A model that appears to do far better has almost certainly leaked information.
- **Search is cheap, so false discoveries are cheap.** Each variant tried on the same data is
  another draw from the noise; try enough and the best backtest looks excellent even when
  every variant is worthless (Bailey et al., 2014). AI assistants make trying variants nearly
  free, which makes this failure the default rather than the exception.
- **Published edges decay.** Anomaly returns are about a quarter lower out of sample and more
  than half lower after publication (McLean & Pontiff, 2016). Whether most published anomalies
  replicate at all is contested: Hou, Xue & Zhang (2020) find most fail conventional
  significance hurdles, while Jensen, Kelly & Pedersen (2023) find most survive a Bayesian
  reassessment. The disagreement is about the standard of evidence, which is why this
  document fixes ours in advance.
- **Incentives point the wrong way.** Researchers want positive results; vendors sell track
  records that are selected and revisable; an assistant trying to satisfy its user will
  optimise a backtest if asked. These rules exist to put a price on those incentives.

## Rules

### R1. No look-ahead

Every value used at time *t* must have been knowable at *t*.

- Common leaks: negative shifts; statistics fitted on the full sample (mean and standard
  deviation normalisation, min–max scaling, ranks, PCA, and any scaler or model fitted before
  the train/test split); centred rolling windows; backward fills and interpolation;
  left-labelled resampling.
- Execution lag: a signal built from day *d*'s close earns returns from *d + 1* onwards
  (`signal.shift(1) * returns` for close-to-close returns). Also rerun with one more day of
  delay: if performance collapses, the strategy depends on execution it cannot get.

**Enforced by** `stockstudy.lookahead.assert_no_lookahead`. Every function that builds a
feature, signal, or position from time-indexed data has a test that calls it. The check sees
only the data passed to it, so pass every time-indexed input (joined datasets included)
through that argument.

### R2. Timestamps mean availability

Index every observation by when an investor could first have known it, not by the period it
describes.

- Fundamentals: the filing or announcement date, not the fiscal period end. A December
  annual report is typically filed in February or March.
- Earnings released after the close affect the next session.
- Analyst estimates, ratings and index membership: as-of snapshots. Vendors revise history.
- Macroeconomic data: the first release (a vintage), not today's revised series.
- Joins: `pd.merge_asof(..., direction="backward")` on the availability timestamp; never
  `"forward"` or `"nearest"`.

**Enforced by** `stockstudy.pit`: facts carry an `available_at` date and can only be read
as of a date, keeping every reported version. SEC EDGAR facts become available the
business day after filing, because the filing date does not say whether a filing arrived
before or after the close. Other data-loading code documents its availability convention
in its docstring, and the R1 check covers any data passed through it.

### R3. Point-in-time universe

Test on the securities that existed and were investable at the time, including those later
delisted, acquired or bankrupt, together with their delisting returns (Shumway, 1997). A
universe built from today's index constituents bakes survivorship into every backtest.
Identify securities by permanent identifiers, because tickers change and get reused.

**Enforced by** review.

### R4. A language model's training cutoff contaminates backtests

A language model has read the news, prices and post-mortems for every period before its
training cutoff. Instructions to ignore that knowledge do not remove it from the weights, so
an LLM-derived signal evaluated before the cutoff mixes forecasting skill with memorised
outcomes (Glasserman & Lin, 2023; Sarkar & Vafa, 2024).

- Only periods strictly after the model's training cutoff count as out-of-sample evidence,
  as in Lopez-Lira & Tang (2023). Treat the published cutoff as optimistic and leave a
  margin of a few months.
- Disable web search, browsing and retrieval tools when generating signals for historical
  dates: a tool-using model can simply look up what happened.
- Earlier periods are for debugging pipelines, not for claims. Anonymising names and dates
  reduces leakage but does not remove it (Glasserman & Lin, 2023); models trained only on
  data up to a given date are the principled alternative (Drinkall et al., 2024).
- Record with every LLM-derived dataset: the exact model snapshot (never an alias that can
  change underneath you), its published training cutoff, the prompt and parameters, and the
  run date. Cache raw responses keyed on these, so results can be reproduced without
  re-querying.

**Enforced by** review.

### R5. Count every trial

Every configuration evaluated on data is a trial: features, parameters, universes, periods
and models, including those that did not work and those an assistant tried in passing. Log
them. Report every headline metric with the number of trials behind it, and deflate it, using
the Deflated Sharpe Ratio (Bailey & López de Prado, 2014) or a multiple-testing hurdle. For a
new factor that means a t-statistic of about 3 rather than 2 (Harvey, Liu & Zhu, 2016).

**Enforced by** review.

### R6. Validate out of time; use the hold-out once

- Never split time-series data into random folds. Use walk-forward validation, or purged and
  embargoed k-fold cross-validation when labels overlap in time (López de Prado, 2018,
  ch. 7).
- Fit every preprocessing step (scalers, imputers, feature selection) inside each training
  fold.
- Fix a final hold-out period before research starts. Evaluate on it once, record the result
  whatever it is, and do not tune afterwards. A hold-out that has influenced a decision has
  become training data.

**Enforced by** review.

### R7. Net of costs, against baselines

- Report returns net of explicit transaction-cost and slippage assumptions, stated in the
  results (for example, 10 basis points per side), together with turnover and, for short
  positions, borrow costs.
- Compare with simple baselines on the same universe and period: the market index, an
  equal-weighted portfolio and 12-1 momentum. A strategy that does not beat them net of costs
  is not a result, however sophisticated the model behind it.
- Report drawdowns and the distribution of returns, not only the mean and the Sharpe ratio.

**Enforced by** review.

### R8. Too good is a bug

Treat these as bug reports until proven otherwise: a Sharpe ratio above about 2 after costs
for a diversified daily equity strategy, daily directional accuracy above about 55% across a
broad universe, out-of-sample R² of several percent on individual stock returns, or an
equity curve with no meaningful drawdowns. Hunt for the leak before reporting the number.

**Enforced by** review.

### R9. Reproducible by construction

- Results come from code in `src/` run from a clean checkout with `uv.lock`. Notebooks call
  library functions rather than holding the logic.
- Randomness is seeded explicitly with `np.random.default_rng(seed)`; the lint rules reject
  numpy's legacy global generator.
- Record the data snapshot alongside results: source, query, retrieval date, row count and
  a content hash.
- Never commit market data. Most vendor licences forbid redistribution, and this repository
  is public.

**Enforced by** the lockfile, lint rules, `.gitignore` and the large-file hook; the rest in
review.

## Review checklist

Answer each item with evidence (a file and line, a test name, command output), not assertion.
Absence of evidence means "not verifiable", never "pass".

- [ ] **R1**: every new feature, signal or position builder has an `assert_no_lookahead`
      test; execution lag is applied and survives one more day of delay.
- [ ] **R2**: every data source documents its availability timestamps; joins are backward
      as-of joins.
- [ ] **R3**: the universe is point-in-time and includes delisted securities.
- [ ] **R4**: LLM-derived claims use only periods after the model's training cutoff, with
      tools disabled; the model snapshot is recorded.
- [ ] **R5**: the number of trials is stated and the headline metric is deflated.
- [ ] **R6**: no random splits; preprocessing is fitted within folds; the hold-out is
      untouched, or its single use is recorded.
- [ ] **R7**: results are net of stated costs, with baselines and drawdowns.
- [ ] **R8**: nothing is too good to be true, or the leak hunt is documented.
- [ ] **R9**: results reproduce from a clean checkout; seeds and the data snapshot are
      recorded.

## References

- Arnott, R., Harvey, C. R., & Markowitz, H. (2019). A backtesting protocol in the era of
  machine learning. *The Journal of Financial Data Science*, 1(1), 64–74.
- Bailey, D. H., Borwein, J. M., López de Prado, M., & Zhu, Q. J. (2014). Pseudo-mathematics
  and financial charlatanism: The effects of backtest overfitting on out-of-sample
  performance. *Notices of the American Mathematical Society*, 61(5), 458–471.
- Bailey, D. H., & López de Prado, M. (2014). The deflated Sharpe ratio: Correcting for
  selection bias, backtest overfitting, and non-normality. *The Journal of Portfolio
  Management*, 40(5), 94–107.
- Drinkall, F., Rahimikia, E., Pierrehumbert, J. B., & Zohren, S. (2024). Time Machine GPT.
  *Findings of the Association for Computational Linguistics: NAACL 2024*.
- Glasserman, P., & Lin, C. (2023). Assessing look-ahead bias in stock return predictions
  generated by GPT sentiment analysis. arXiv:2309.17322.
- Gu, S., Kelly, B., & Xiu, D. (2020). Empirical asset pricing via machine learning. *The
  Review of Financial Studies*, 33(5), 2223–2273.
- Harvey, C. R., Liu, Y., & Zhu, H. (2016). …and the cross-section of expected returns. *The
  Review of Financial Studies*, 29(1), 5–68.
- Hou, K., Xue, C., & Zhang, L. (2020). Replicating anomalies. *The Review of Financial
  Studies*, 33(5), 2019–2133.
- Jensen, T. I., Kelly, B., & Pedersen, L. H. (2023). Is there a replication crisis in
  finance? *The Journal of Finance*, 78(5), 2465–2518.
- López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley.
- Lopez-Lira, A., & Tang, Y. (2023). Can ChatGPT forecast stock price movements? Return
  predictability and large language models. arXiv:2304.07619.
- McLean, R. D., & Pontiff, J. (2016). Does academic research destroy stock return
  predictability? *The Journal of Finance*, 71(1), 5–32.
- Sarkar, S. K., & Vafa, K. (2024). Lookahead bias in pretrained language models. Working
  paper, SSRN.
- Shumway, T. (1997). The delisting bias in CRSP data. *The Journal of Finance*, 52(1),
  327–340.
