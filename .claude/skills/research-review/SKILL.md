---
name: research-review
description: Audit research code or a reported result against this repository's research-integrity standard (look-ahead, availability timestamps, survivorship, LLM training-cutoff contamination, trial counting, validation design, costs and baselines, reproducibility). Use before reporting any performance number, when reviewing a feature, signal, backtest, model-training or LLM-signal change, or when the user asks whether a result is real.
argument-hint: "[path, git ref or PR number; default: uncommitted changes]"
---

# Research review

Audit **$ARGUMENTS** against `docs/research-integrity.md`. If no target was given, audit the
uncommitted changes (`git diff HEAD`) and the code they call. Read the standard first; this
skill is the procedure for applying it.

The aim is to find the reasons a result could be wrong, not to confirm that it is right. If
you find nothing, say what you checked rather than that all is well.

## Procedure

1. **Map the pipeline.** List every data source, transformation, model and metric involved,
   with file and line. For each data source, find where its availability convention (R2) is
   stated. If it is stated nowhere, that is a finding.
2. **Run the executable checks.** Run `make check`. Then, for each function that builds a
   feature, signal, label or position from time-indexed data, find its
   `assert_no_lookahead` test (R1). Where one is missing, write it in `tests/` and run it.
   A missing test is a finding even if the new test passes.
3. **Trace time where the check cannot.** Look at datasets joined inside a transform rather
   than passed in, the lag between signal and traded return, train/test boundaries,
   preprocessing fitted before a split, and LLM calls: model snapshot against evaluation
   period, and whether web or search tools were enabled (R4).
4. **Count the trials.** Reconstruct how many configurations were evaluated from git
   history, logs, notebooks and this conversation (R5). If the count cannot be
   reconstructed, say so: the headline metric then cannot be deflated.
5. **Check the numbers against reality.** Costs, turnover, baselines and drawdowns (R7),
   and R8's thresholds for "too good".

## Report

Give one row per rule:

| Rule | Verdict | Evidence |
| ---- | ------- | -------- |
| R1 No look-ahead | pass / fail / not verifiable / n/a | file:line, test name, command output |

Then list:

- **Blocking findings**, most severe first, each with its fix.
- **What would change the conclusion**: the cheapest further check that could overturn it.
- **Trials**: the count, or why it is unknown.

A "pass" needs evidence. Missing evidence is "not verifiable", never "pass". Do not soften a
failure because the result is attractive, and do not suggest performance improvements: this
review is about validity only.
