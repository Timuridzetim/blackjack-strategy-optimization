# Blackjack Strategy Optimization

**Status: planning — implementation not started**

A reproducible Python research project investigating fixed stopping-threshold strategies in a *simplified* game of blackjack using absorbing Markov chains and Monte Carlo simulation.

This project builds on an earlier IB Mathematics: Analysis and Approaches HL exploration. The original report is a starting point, **not** a verified implementation or a source of final results.

## Research question

How does the player's fixed stopping threshold affect the probability of winning and the expected net return, and how closely do Monte Carlo estimates agree with an absorbing Markov-chain model?

## Initial model specification

The initial analytical baseline will use these assumptions:

- A standard card-value distribution: values 2–9 each occur with probability 1/13; ten-valued cards with probability 4/13; aces with probability 1/13.
- Every ace counts as **1** (no soft hands).
- The player and dealer each start with two cards.
- The player hits while their hand total is below threshold `k`, then stands, unless they bust.
- The dealer hits below 17 and stands at 17 or above.
- No splits, doubles, insurance or special natural-blackjack payout.
- Win and loss pay +1 and −1 unit respectively; a tie (push) pays 0.
- The analytical Markov model draws with replacement, keeping card probabilities constant.
- Finite-deck sampling without replacement is a **separate experiment** with an explicitly stated shuffle policy.

These simplifications **do not represent optimal real-casino blackjack**. The experiments will distinguish (1) maximizing the probability of a win from (2) maximizing expected net return.

## Planned methods

1. **Absorbing Markov chains** — transition matrices, the fundamental matrix `N = (I - Q)^{-1}`, and exact absorption probabilities under the chosen assumptions.
2. **Monte Carlo simulation** — independent infinite-deck and finite-deck sampling implementations, fixed seeds and documented experimental settings.
3. **Statistical validation** — convergence analysis, sampling uncertainty, confidence intervals, and comparisons across thresholds.
4. **Reproducibility** — automated tests, explicit dependencies, run instructions, and programmatically generated figures.

## Project status and roadmap

No calculations, code, plots or performance claims are published here yet. Work is tracked in GitHub Issues:

- [#1 — Markov model and mathematical validation](https://github.com/Timuridzetim/blackjack-strategy-optimization/issues/1)
- [#2 — Monte Carlo simulators](https://github.com/Timuridzetim/blackjack-strategy-optimization/issues/2)
- [#3 — Statistical experiments and figures](https://github.com/Timuridzetim/blackjack-strategy-optimization/issues/3)
- [#4 — Documentation and v1.0 release](https://github.com/Timuridzetim/blackjack-strategy-optimization/issues/4)

## Development workflow

Development changes will be proposed in feature branches and reviewed through pull requests. Reproducible code, tests, and confirmed results will be added in subsequent iterations.

## License

MIT — see [LICENSE](LICENSE).
