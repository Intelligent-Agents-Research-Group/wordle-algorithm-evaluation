# Information Cost of Constraint Violations

## Overview

We analyze whether LLM guesses that violate feedback constraints still provide useful information for narrowing the solution space. Across 2,434 LLM-only Wordle games (10,529 total guesses, 8,095 from round 2 onward), we compare the information gain of constraint-violating guesses against compliant ones.

## Key Findings

Of all round 2+ guesses, 3.8% (309 guesses) violated at least one feedback constraint. These violations carry a measurable information cost:

- **Violated guesses yield 33.5% less information** (1.56 bits vs. 2.34 bits per guess), meaning each violating guess recovers roughly two-thirds the information of a compliant one.
- **Violated guesses produce 2.46 redundant signals per guess** compared to 1.47 for compliant guesses. By reusing letters already marked gray or re-confirming known green positions, violating guesses waste nearly one additional feedback slot on information the agent already has.
- **Violated guesses eliminate far fewer candidates** (24.4 vs. 143.2 on average), reducing the candidate pool by 49.2% compared to 62.6% for compliant guesses.

## Per-Model Breakdown

| Model | Violations | Info Gain (V) | Info Gain (C) | Loss | Redundant Signals |
|-------|:---------:|:------------:|:------------:|:----:|:-----------------:|
| codestral-22b | 40 | 1.19b | 2.35b | -49.4% | 2.85 |
| gemma-3-27b-it | 30 | 1.83b | 2.39b | -23.4% | 2.53 |
| gpt-oss-120b | 25 | 1.57b | 2.30b | -31.7% | 2.52 |
| gpt-oss-20b | 31 | 1.97b | 2.29b | -14.1% | 2.19 |
| granite-3.3-8b | 19 | 1.24b | 2.38b | -47.8% | 2.37 |
| llama-3.1-70b | 11 | 1.26b | 2.32b | -45.8% | 2.55 |
| llama-3.1-8b | 12 | 0.83b | 2.29b | -64.0% | 3.17 |
| nemotron-nano-8b | 34 | 1.35b | 2.37b | -43.1% | 2.09 |
| llama-3.3-70b | 22 | 2.06b | 2.30b | -10.6% | 2.45 |
| mistral-7b | 39 | 1.70b | 2.41b | -29.2% | 2.31 |
| mistral-small-3.1 | 46 | 1.61b | 2.42b | -33.5% | 2.46 |

## Interpretation

Constraint violations are not catastrophic — violating guesses still provide positive information gain (1.56 bits on average) and still eliminate roughly half the candidate space. However, they are significantly less efficient than compliant guesses. The primary mechanism is redundancy: by reusing eliminated letters, the LLM wastes feedback slots on already-known information rather than probing new regions of the hypothesis space. This suggests that LLMs do not fully internalize the constraint-satisfaction structure of iterative feedback, even when they are otherwise capable solvers.

## Data

- **Input:** 2,434 LLM-only Wordle games across 11 models (zero-shot and chain-of-thought)
- **Output:** `violation_info_gain_per_round.csv` (10,529 rows), `violation_info_gain_summary.csv`
- **Script:** `scripts/violation_information_gain.py`
