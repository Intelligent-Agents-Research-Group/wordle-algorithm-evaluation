# Do Language Models Integrate Algorithmic Reasoning Signals?

## Motivation

A growing body of work on tool-augmented LLMs, program-of-thought prompting, and hybrid reasoning systems assumes that providing LLMs with structured reasoning signals (e.g., candidate rankings, entropy, information-theoretic scores) will improve their decision-making. This experiment directly tests that assumption.

We inject algorithmic analysis — top-k candidates ranked by VOI/CSS score plus entropy context — into LLM prompts during a controlled decision-making task (Wordle, Mastermind). A shuffled-ranking diagnostic separates genuine score reasoning from surface imitation of rank position.

## Research Questions

1. **Do LLMs integrate algorithmic reasoning signals into their decision-making, or do they ignore them?**
2. **When LLMs do respond to signals, do they reason over the underlying scores or merely imitate rank position?**
3. **Does signal integration vary systematically with model capacity?**

## Key Finding: Three Regimes of Signal Processing

Our Wordle experiments (7 models x 2 algorithms x 3 conditions x 100 games) reveal three distinct behavioral regimes:

### 1. Signal Integration (small models)

Models: `granite-3.3-8b-instruct`, `llama-3.1-8b-instruct`

- Follow rates of 6-51%
- Statistically significant improvement with VOI signals:
  - granite + VOI: 95% → 97% win rate, 4.38 → 3.95 avg attempts (p=0.0016, d=0.44)
  - llama-8b + VOI: 91% → 97% win rate, 4.29 → 4.10 avg attempts (p=0.014, d=0.30)
- llama-3.1-8b shows **score reasoning** in shuffled diagnostic (25% true-top-1 vs 0-1% displayed-top-1)

### 2. Surface Imitation (mid-range models)

Models: `codestral-22b`, `mistral-7b-instruct`

- Moderate follow rates (9-26%)
- No significant performance improvement
- codestral shows **rank imitation**: picks displayed-first word at 26% vs true-best at 13%
- Responds to the *structure* of the signal, not its *content*

### 3. Signal Rejection (large models)

Models: `llama-3.3-70b-instruct`, `llama-3.1-70b-instruct`

- **0% follow rate** — completely ignore algorithmic recommendations
- No significant performance difference between conditions
- Strong enough internal reasoning to disregard external signals entirely

## Experimental Design

### Conditions

| Condition | Description |
|-----------|-------------|
| `baseline` | Standard prompt, no algorithmic signals |
| `voi_informed` | Prompt includes Algorithm Analysis section with ranked candidates + entropy |
| `shuffled_ranking` | Same section but display order randomized (scores preserved) — diagnostic for imitation vs reasoning |

### Prompt Injection (Treatment)

```
Algorithm Analysis:
- Current entropy: X.X bits (Y candidates remaining)
- Top candidates ranked by information value:
    1. WORD1 (score: X.XX)
    2. WORD2 (score: X.XX)
    ...
- Algorithm's recommended guess: WORD1

Use this analysis as one input to your reasoning, but make your own decision.
Do NOT simply copy the algorithm's top pick — consider the candidates critically
and choose the word you believe will maximize information gain based on your own analysis.
```

### Parameters

| Parameter | Value |
|-----------|-------|
| Domain | Wordle (5-letter words), Mastermind (planned) |
| Models | 7 open-source LLMs via Navigator API |
| Games | 100 per run |
| Schedule | {1: "llm", 2: "algo", ..., 6: "algo"} |
| Algorithms | CSS (information gain), VOI (value of information) |
| Conditions | baseline, voi_informed, shuffled_ranking |
| Total runs | 7 models x 2 algorithms x 3 conditions = 42 per domain |

### Models

| Model | Parameters | Signal Behavior |
|-------|-----------|----------------|
| llama-3.3-70b-instruct | 70B | Signal rejection |
| llama-3.1-70b-instruct | 70B | Signal rejection |
| llama-3.1-8b-instruct | 8B | Signal integration (score reasoning) |
| granite-3.3-8b-instruct | 8B | Signal integration (highest follow rate) |
| codestral-22b | 22B | Surface imitation |
| mistral-7b-instruct | 7B | Mixed / imitation tendency |
| gemma-3-27b-it | 27B | Low engagement |

## Results Summary (Wordle)

### Performance: Baseline vs VOI-Informed

| Model | Algo | Baseline Win% | VOI Win% | Baseline Avg | VOI Avg | p-value | Cohen's d |
|-------|------|--------------|----------|-------------|---------|---------|-----------|
| granite-8b | VOI | 95% | 97% | 4.38 | 3.95 | **0.0016** | 0.44 |
| llama-8b | VOI | 91% | 97% | 4.29 | 4.10 | **0.014** | 0.30 |
| llama-3.3-70b | CSS | 99% | 97% | 4.05 | 3.86 | 0.347 | 0.13 |
| codestral | CSS | 98% | 95% | 3.97 | 4.05 | 0.176 | -0.17 |

12 of 14 paired comparisons were not statistically significant. The effect is concentrated in smaller models.

### Surface Imitation Diagnostic

| Model | Algo | TrueTop1% | DispTop1% | Verdict |
|-------|------|-----------|-----------|---------|
| llama-3.1-8b | CSS | 25% | 0% | **Score reasoning** |
| llama-3.1-8b | VOI | 25% | 1% | **Score reasoning** |
| codestral | CSS | 13% | 26% | **Rank imitation** |
| granite-8b | VOI | 17% | 25% | Imitation tendency |
| llama-70b variants | both | 0% | 0% | Signal rejection |

### Follow Rate by Model Capacity

| Model | Size | CSS Follow% | VOI Follow% |
|-------|------|------------|------------|
| granite-3.3-8b | 8B | 40% | 51% |
| codestral-22b | 22B | 22% | 26% |
| mistral-7b | 7B | 16% | 9% |
| gemma-3-27b | 27B | 8% | 10% |
| llama-8b | 8B | 1% | 6% |
| llama-70b variants | 70B | 0% | 0% |

## Statistical Analysis

- **Paired t-test**: Same target words across conditions (within-subjects)
- **Effect size**: Cohen's d
- **Surface imitation diagnostic**: Compare TrueTop1% vs DispTop1% in shuffled condition
- **Follow rate analysis**: By model, algorithm, and entropy level

## Planned Extensions

### Mastermind Domain (Implemented)
Replicate the three-condition experiment in Mastermind to demonstrate the finding generalizes beyond Wordle. Same experimental structure, adapted for Mastermind's code-breaking mechanics.

**Key differences from Wordle:**
- 4-character color codes (RGBYOW) instead of 5-letter words
- Search space: 1,296 codes (classic) vs ~13,000 words
- Feedback: Black/White pegs instead of Green/Yellow/Gray
- 10 rounds instead of 6
- Schedule: LLM round 1, algorithm rounds 2-10

**Scripts:**
- `voi_integration/scripts/voi_informed_mastermind.py` — Main experiment script
- `voi_integration/scripts/run_voi_mastermind_experiment.sh` — Full experiment matrix (48 runs)
- `voi_integration/scripts/analyze_mastermind_results.py` — Statistical analysis

**Expected outcome:** If the three-regime taxonomy (integration, imitation, rejection) is a genuine property of LLM reasoning rather than a Wordle-specific artifact, we should observe similar behavioral patterns in Mastermind despite the very different task structure.

### CoT Reasoning Traces
Run selected models (granite, codestral, llama-70b) with chain-of-thought prompting to observe whether models *reference* the algorithmic signal in their reasoning chains. This provides qualitative evidence of integration vs. imitation.

## Connection to Broader Research

This work contributes to several active debates:

1. **Do LLMs reason or simulate reasoning?** — Our shuffled-ranking diagnostic provides a clean test
2. **Tool-augmented LLM design** — Providing tools/signals doesn't guarantee they'll be used
3. **Hybrid AI systems** — The capacity-dependent effect has implications for which models benefit from algorithmic augmentation
4. **Scaling laws for reasoning** — Signal integration behavior changes qualitatively with model size

## Target Venues

- AAMAS 2027 (main track or extended abstract)
- AAAI 2027 (main track)
