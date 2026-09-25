# CLAUDE.md

How to work in this repository. Written for Claude Code; it applies equally to human
contributors.

## Project

StockStudy researches how AI (machine learning and language models) can be applied to
equity investing. What it produces is **evidence that survives scrutiny**, not impressive
backtests. It is at the foundation stage: the toolchain, the research standard and the
look-ahead guard exist; data pipelines, features and models do not yet.

## Commands

```bash
make install                      # locked environment (uv sync --locked) + git hooks
make check                        # everything CI runs; must pass before work is done
make fmt                          # ruff format + safe lint fixes
uv run pytest tests/test_lookahead.py -k panel   # focused test run
uv add <pkg>                      # runtime dependency (uv add --dev for tooling)
```

Never edit `uv.lock` by hand. Coverage below 90% fails `make test`.

## Layout

- `src/stockstudy/`: library code, typed and tested. All logic that produces a result
  lives here.
- `tests/`: pytest, one `test_<module>.py` per module. Doctests in `src/` run too.
- `docs/research-integrity.md`: the research standard, rules R1–R9. Read it before
  changing research code.
- `notebooks/` (create when needed): exploration only. Notebooks import from `stockstudy`,
  and a git hook strips their outputs.
- `data/`: local only and git-ignored. Never commit market data.

## Research rules (non-negotiable)

The short form of `docs/research-integrity.md`:

1. **No look-ahead.** Every function that builds a feature, signal or position from
   time-indexed data has a test calling `stockstudy.lookahead.assert_no_lookahead`. Never
   weaken, skip or delete such a test to make code pass; fix the code.
2. **Timestamps mean availability** (filing date, not period end). As-of joins look
   backward only. A signal from day *d* earns returns from *d + 1*.
3. **Point-in-time universe**, delisted securities included.
4. **LLM training cutoff.** LLM-derived signals count as evidence only for periods after the
   model's training cutoff, generated with web and search tools off. Record the exact
   model snapshot.
5. **Count every trial**, including the variants you try while exploring, and report the
   count with every headline metric.
6. **Out-of-time validation only**; never random splits. Do not evaluate on, tune against or
   report the hold-out period unless the user explicitly asks for its one-time use.
7. **Net of costs, against baselines.**
8. **Too good is a bug.** Hunt for the leak before reporting the number.

## Reporting results

- Lead with what could make the result wrong, then give the number.
- Every performance figure states its period, universe, number of trials, cost assumptions
  and baseline comparison.
- Never call a strategy a recommendation or say that it "works"; say what the evidence
  does and does not support.
- Never invent or estimate prices, fundamentals, returns or citations. Every number comes
  from data in this repository or a named source; if it is not available, say so.
- If a request would break a research rule ("tune it until the Sharpe is above 2",
  "normalise over the whole sample"), name the rule and propose the compliant version.
- Run `/research-review` before reporting any performance number, and when reviewing
  research code.

## Code conventions

- Python 3.13+, fully typed: `mypy --strict` and ruff must pass. A `# type: ignore` needs an
  error code.
- Google-style docstrings on public functions, including what the function assumes about
  time (for example, "indexed by availability date").
- Pure functions: data in, data out. No hidden I/O, globals, or mutation of inputs.
- Randomness takes an explicit seed or `np.random.Generator`.
- Names make time direction visible. Features describe the past (`ret_20d`, `vol_60d`);
  labels look forward and start with `fwd_` (`fwd_ret_5d`). A `fwd_` column is never a
  model input.
- Intraday timestamps are timezone-aware; daily data is indexed by session date.
- No `print` in library code (use `logging`). Secrets come from environment variables,
  never from code or notebooks.
- Warnings are errors in tests. Fix their cause instead of filtering them.

## Workflow

- Work is done when `make check` passes. If it cannot pass, say what fails and why.
- Keep changes scoped: no drive-by reformatting or refactoring of unrelated code.
- Commits are small, with an imperative subject line of at most 72 characters and a body
  that explains why.
- When a convention changes, update this file and `docs/` in the same change.
