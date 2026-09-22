# Iterative Reasoning in Large Language Models: A Wordle & Mastermind Testbed Study

**Kevin Scroggins**
**Date:** January 6, 2026 (Updated: February 19, 2026)
**Total Games:** 49,832 across 82+ experimental configurations
- Main experiments: 15,932 games (Wordle)
- Workshop experiments: 33,900 games (18,600 Wordle + 15,300 Mastermind)

---

## Abstract

We investigate the iterative reasoning capabilities of Large Language Models (LLMs) using Wordle and Mastermind as rigorous testbeds. Unlike prior work focusing on task completion, we measure **cognitive processes**: convergence to solutions, search space pruning, and information gain patterns. Across 49,832 games spanning pure algorithms, pure LLMs, and hybrid approaches, we find that:

1. LLMs demonstrate **92% search space reduction** on first attempts, showing exceptional initial constraint satisfaction reasoning
2. Information gain patterns follow **Bayesian principles**, with ~13 bits cumulative gain approaching the theoretical maximum
3. Hybrid LLM-algorithm systems achieve **270% of pure algorithm convergence rates**, demonstrating complementary strengths
4. **Zero-shot prompting** performs comparably to chain-of-thought, suggesting constraint satisfaction reasoning is inherent rather than emergent
5. **State ownership matters:** LLMs perform +7.7 pts better when generating their own initial state vs inheriting from algorithms (Mastermind)
6. **Error accumulation:** LLM effectiveness degrades from 73.9% → 25.0% over multiple turns when operating in inherited context

These findings provide strong evidence that LLMs possess robust iterative reasoning capabilities with systematic belief updating, but reveal a fundamental limitation: LLMs cannot fully "inhabit" reasoning trajectories they didn't create.

---

## 1. Introduction

### 1.1 Research Question

**How good are Large Language Models at iterative reasoning and belief updating?**

While LLMs have demonstrated impressive performance on various tasks, understanding their *cognitive processes* remains challenging. Most evaluations focus on task completion (accuracy, win rates) rather than the underlying reasoning patterns.

We address this gap by using Wordle as a testbed to measure:
- **Convergence patterns:** How distances to target solutions decrease with each iteration
- **Search space pruning:** How effectively approaches eliminate candidate solutions
- **Information gain:** Whether belief updating follows information-theoretic principles

### 1.2 Why Wordle?

Wordle provides an ideal testbed for studying iterative reasoning:

1. **Measurable convergence:** Hamming and Levenshtein distances quantify progress toward the solution
2. **Constrained search space:** 5,629 valid words, allowing precise measurement of pruning efficiency
3. **Iterative structure:** Each guess provides feedback, enabling turn-by-turn analysis
4. **Information-theoretic properties:** Theoretical maximum information (~12.5 bits) provides a baseline
5. **Constraint satisfaction:** Requires maintaining and updating beliefs based on feedback

### 1.3 Contributions

1. **First large-scale analysis** of LLM iterative reasoning using constraint satisfaction (15,932 games)
2. **Novel metrics:** Convergence rates, search space pruning efficiency, information gain patterns
3. **Comparative framework:** Pure algorithms, pure LLMs, and hybrid approaches
4. **Evidence of systematic reasoning:** LLMs demonstrate Bayesian belief updating, not random guessing

---

## 2. Experimental Design

### 2.1 Three Experimental Categories

#### Category 1: Pure Algorithms (Baseline)
- **Purpose:** Establish baseline convergence patterns
- **Approaches:** CSS, VOI, Random, and combinations
- **Games:** 800 total (100 per algorithm configuration)
- **Metrics:** Hamming/Levenshtein distance per round (1-6)

#### Category 2: Pure LLMs (Search Space Pruning)
- **Purpose:** Measure LLM constraint satisfaction and belief updating
- **Models:** 11 models (ranging from 7B to 120B parameters)
- **Prompting:** Zero-shot and Chain-of-Thought
- **Games:** 10,529 total across 26 configurations
- **Metrics:** Candidates before/after each attempt, information gain (bits)

#### Category 3: Hybrid LLM-Algorithm (Convergence Analysis)
- **Purpose:** Evaluate synergy and complementary strengths
- **Strategy:** Alternating (LLM on odd rounds, algorithm on even rounds)
- **Configurations:** 9 models × 3 algorithms × 2 prompting strategies
- **Games:** 5,403 total across 54 configurations
- **Metrics:** Distance convergence, strategy attribution per round

### 2.2 Test Set

All experiments use the same canonical test set:
- **Size:** 100 words
- **Stratification:** Balanced across frequency tiers (Tier 1: 34, Tier 2: 33, Tier 3: 33)
- **Consistency:** Ensures fair comparison across all approaches

---

## 3. Results

### 3.1 Convergence Performance: Hybrids Excel

**Primary Finding:** Hybrid approaches converge **2.7x faster** than pure algorithms.

| Approach | Convergence Rate | Total % Decrease | vs Algorithm |
|----------|-----------------|------------------|--------------|
| Pure Algorithms | 0.30 Hamming/round | 33.3% | 100% |
| Hybrids (Zero-shot) | 0.82 Hamming/round | 90.0% | **270%** |
| Hybrids (CoT) | 0.85 Hamming/round | 91.6% | **281%** |

**Convergence Trajectories:**

```
Pure Algorithms:  4.53 → 2.17 → 3.02  (increases in late rounds)
Hybrids (Zero):   4.53 → 2.11 → 0.45  (monotonic convergence)
Hybrids (CoT):    4.62 → 2.19 → 0.39  (best final distance)
```

**Interpretation:**
- Pure algorithms plateau and even regress in late rounds (survivor bias - only hard cases remain)
- Hybrids show **monotonic convergence**, consistently approaching the solution
- The alternation pattern (LLM exploration + algorithm exploitation) drives superior convergence

### 3.2 Search Space Pruning: 92% First-Attempt Reduction

**Finding:** LLMs demonstrate exceptional initial constraint satisfaction reasoning.

#### First Attempt Performance
| Prompting | Initial Candidates | After First Guess | Reduction | Info Gain |
|-----------|-------------------|-------------------|-----------|-----------|
| Chain-of-Thought | 5,629 | 453 | **91.95%** | 5.16 bits |
| Zero-shot | 5,629 | 440 | **92.19%** | 5.18 bits |

**Across All Attempts:**
- Average reduction per attempt: 72-74%
- Cumulative information gain: ~13 bits (approaching theoretical max of 12.5 bits)
- Pattern: Diminishing returns as search space narrows (expected Bayesian behavior)

#### Information Gain Pattern

| Attempt | CoT (bits) | Zero-shot (bits) | Interpretation |
|---------|-----------|------------------|----------------|
| 1 | 5.16 | 5.18 | Massive initial reduction |
| 2 | 4.29 | 4.42 | Still high |
| 3 | 2.33 | 2.11 | Declining (expected) |
| 4 | 0.76 | 0.78 | Diminishing returns |
| 5 | 0.29 | 0.37 | Near convergence |
| 6 | 0.28 | 0.21 | Final refinement |

**Critical Insight:** Information gain follows the **expected Bayesian pattern** of diminishing returns as uncertainty reduces. This demonstrates systematic belief updating, not random guessing or heuristic shortcuts.

### 3.3 Zero-shot ≈ Chain-of-Thought

**Finding:** Zero-shot prompting performs comparably to (or better than) chain-of-thought for constraint satisfaction.

| Metric | Zero-shot | Chain-of-Thought | Difference |
|--------|-----------|------------------|------------|
| First-attempt pruning | 92.19% | 91.95% | +0.24 pp |
| Average pruning | 74.0% | 71.7% | +2.3 pp |
| Convergence rate | 0.82 | 0.85 | -3.7% |
| Cumulative info gain | 13.07 bits | 13.11 bits | -0.04 bits |

**Interpretation:**
- Chain-of-thought provides marginal improvement (+3.7% convergence)
- Zero-shot matches or exceeds CoT in search space pruning
- **Implication:** Constraint satisfaction reasoning appears to be inherent in LLMs, not requiring explicit reasoning prompts

### 3.4 Hybrid Strategy Alternation Pattern

**Strategy:** LLM on odd rounds (1, 3, 5), Algorithm on even rounds (2, 4, 6)

| Round | Strategy | Role | Benefit |
|-------|----------|------|---------|
| 1, 3, 5 | LLM | Exploration | Creative pattern discovery, strong initial pruning |
| 2, 4, 6 | Algorithm | Exploitation | Optimal information-theoretic moves |

**Why This Works:**
1. **LLM strengths:** Exceptional first-attempt reasoning (92% pruning), creative exploration
2. **Algorithm strengths:** Optimal single-step information gain, deterministic consistency
3. **Synergy:** Each approach benefits from constraints imposed by the other

**Evidence of Synergy:**
- Pure algorithm convergence: 33%
- Pure LLM average: ~72% pruning per attempt
- Hybrid convergence: 90-92% (superior to either alone)

---

## 4. Discussion

### 4.1 Evidence of Iterative Reasoning Capability

Our results provide strong evidence that LLMs possess robust iterative reasoning capabilities:

✅ **92% first-attempt search space pruning** - Far exceeds random performance, demonstrates constraint satisfaction reasoning

✅ **~13 bits cumulative information gain** - Approaches theoretical maximum, showing systematic uncertainty reduction

✅ **Bayesian information gain pattern** - Diminishing returns across attempts follows expected information-theoretic principles

✅ **270% convergence improvement in hybrids** - Complementary strengths with algorithms demonstrate reasoning adds value

✅ **Monotonic convergence** - Consistent distance decrease across all rounds (vs algorithm volatility)

### 4.2 Implications for LLM Reasoning Research

**1. Constraint Satisfaction is Inherent**

The comparable performance of zero-shot and chain-of-thought prompting suggests that LLMs possess inherent constraint satisfaction reasoning capabilities. Explicit reasoning prompts provide marginal benefit (+3.7%), indicating this capability is fundamental rather than emergent from specific prompt engineering.

**2. Bayesian Belief Updating**

The information gain pattern (5.2 → 4.4 → 2.2 → <1 bits) precisely matches the expected Bayesian decline as uncertainty reduces. This is not consistent with:
- Random guessing (would show flat or erratic patterns)
- Simple heuristics (would not accumulate ~13 bits)
- Memorization (same test set, different starting points)

**3. Complementary Strengths with Algorithms**

The 270% convergence improvement in hybrid systems demonstrates:
- LLMs contribute unique value (not redundant with algorithms)
- Exploration-exploitation balance drives synergy
- Creative pattern discovery complements optimal information gain

**4. Testbed Methodology Reveals Cognitive Processes**

Win rates and task completion metrics would miss these insights:
- Pure algorithms: 98% win rate, but only 33% convergence
- Hybrids: 95% win rate, but 90% convergence

**Measuring cognitive processes** (convergence, pruning, information gain) reveals reasoning quality beyond task performance.

### 4.3 Limitations and Future Directions

**Limitations:**
1. **Single domain:** Wordle is well-defined constraint satisfaction; may not generalize to all reasoning tasks
2. **Variability:** LLMs show higher variance than algorithms (std: 19-22), though still systematic
3. **Late-round decline:** Pruning efficiency drops steeply (92% → 37%) in later attempts

**Future Directions:**
1. **Other constraint satisfaction domains:** Logic puzzles, planning problems, theorem proving
2. **Adaptive strategies:** Dynamic switching based on search space size or confidence
3. **Per-model analysis:** Investigate which architectural features correlate with reasoning quality
4. **Theoretical grounding:** Connect empirical patterns to theories of LLM computation

---

## 5. Workshop Extension: Generated vs Inherited State (Feb 2026)

### 5.1 Research Question

**Does handoff direction matter in hybrid LLM-algorithm systems?**

We extended our analysis to examine whether LLMs perform differently when they generate their own reasoning trajectory (LLM-first) versus inheriting and continuing from an algorithm-generated state (Algo-first).

### 5.2 Experimental Design

We added Mastermind as a second testbed (1,296 codes vs Wordle's 5,629 words) and ran 33,900 additional games:
- **Wordle:** 18,600 games across 25 configurations
- **Mastermind:** 15,300 games across 17 configurations
- **Models:** 7 LLMs (excluding nemotron due to API issues)
- **Handoff patterns:** L_to_C, C_to_L, k-round variants, alternation patterns

### 5.3 Key Results

**State Ownership Effect:**

| Testbed | LLM Generates R1 | Algo Generates R1 | Gap |
|---------|------------------|-------------------|-----|
| Mastermind (Group A) | 100.0% | 92.3% | **+7.7 pts** |
| Wordle (Group A) | 96.5% | 94.6% | +1.9 pts |

**Error Accumulation Pattern:**

In Algo-First configs, LLM effectiveness degrades across sequential turns:

| LLM Turn | Candidate Reduction |
|----------|---------------------|
| Turn 1 | 73.9% |
| Turn 2 | 69.0% |
| Turn 3 | 53.2% |
| Turn 4 | 25.0% |

**Critical Insight:** Per-turn LLM quality is SIMILAR across conditions (~70%), but accumulated errors cause outcome differences. The problem isn't single-guess quality — it's **maintaining coherent strategy over multiple turns when the LLM didn't create the initial reasoning frame**.

### 5.4 Operationalized Metrics

| Abstract Concept | Measurable Proxy | Differentiating? |
|------------------|------------------|------------------|
| State Ownership | Win rate by who generates R1 | **Yes (+7.7 pts)** |
| Reconstruction Difficulty | Error accumulation over turns | **Yes (73.9%→25%)** |
| Reasoning Trajectory | Distance smoothness | No (~100% both) |
| Coherence | Green letter retention | No (~100% both) |

### 5.5 Implications

1. **Practical:** If building hybrid LLM-algorithm systems, always let the LLM go first
2. **Theoretical:** LLMs maintain implicit reasoning state that is disrupted when external moves are injected
3. **Mechanistic:** LLMs cannot fully "inhabit" a reasoning trajectory they didn't create

This is analogous to:
- Writing your own code vs debugging someone else's
- Telling your own story vs continuing someone else's mid-sentence
- Solving a puzzle yourself vs taking over mid-solve

---

## 6. Conclusion

We set out to answer: **How good are LLMs at iterative reasoning?**

**Answer: Very good — with important caveats.**

LLMs demonstrate:
- **92% initial search space pruning** - Exceptional constraint satisfaction
- **Systematic Bayesian belief updating** - Information gain follows theoretical principles
- **Robust zero-shot reasoning** - Inherent capability, not prompt-dependent
- **Complementary strengths with algorithms** - 270% convergence improvement in hybrid systems

However, our workshop extension reveals a fundamental limitation:
- **State ownership matters** - +7.7 pts advantage when LLM generates initial state
- **Error accumulation** - LLM effectiveness degrades 73.9% → 25.0% over multiple inherited turns
- **Cannot inhabit external trajectories** - LLMs struggle to maintain coherence in reasoning they didn't create

These findings advance our understanding of LLM cognitive capabilities beyond task completion metrics. By measuring convergence, pruning, and information gain, we reveal systematic reasoning processes that align with information-theoretic principles.

**Key insights:**
1. LLMs possess inherent iterative reasoning capabilities that complement algorithmic optimization
2. For hybrid systems: **always let the LLM go first** — algorithms can clean up LLM mistakes, but LLMs cannot coherently continue from algorithm-chosen states
3. The problem isn't per-turn quality (similar across conditions), but maintaining coherent strategy over multiple turns when the reasoning context was externally generated

---

## 7. Data Availability

All data, code, and analysis scripts are available:

**Raw Data:** 49,832 games across 82+ configurations

*Main Experiments (15,932 games):*
- Pure Algorithms: `results/algorithms/raw data/`
- Pure LLMs: `results/llms/raw data/` (26 files)
- Hybrids: `results/hybrids/stage3*/raw data/` (55 files)

*Workshop Experiments (33,900 games):*
- Wordle: `results/workshop/group_*/*/raw_data/` (212 files, 18,600 games)
- Mastermind: `results/mastermind/hybrids/classic/group_*/*/raw_data/` (177 files, 15,300 games)

**Analysis:**
- Convergence analysis: `convergence_analysis.txt` (full numerical results)
- Summary: `convergence_summary.md`
- Methodology: `CONVERGENCE_ANALYSIS_README.md`
- Workshop findings: `workshop/docs/workshop_hybrid_degradation_findings.md`
- Comprehensive statistics: `docs/analysis/COMPREHENSIVE_SUMMARY_STATISTICS.md`

**Visualizations:**
- `convergence_trajectories.png/pdf` (9-panel overview)
- `llm_reasoning_patterns.png/pdf` (4-panel LLM analysis)

**Code:**
- Analysis: `analyze_convergence.py`
- Visualization: `plot_convergence_trajectories.py`
- Hybrid implementation: `scripts/hybrids/alternating_hybrid.py`, `scripts/hybrids/flexible_hybrid.py`
- Mastermind engine: `engines/mastermind_env.py`

**Repository:** https://github.com/Intelligent-Agents-Research-Group/wordle-algorithm-evaluation

---

## 8. Acknowledgments

This work was conducted as part of research on LLM reasoning capabilities. All experiments used the Navigator UF API for LLM access. Algorithmic implementations are based on standard constraint satisfaction and information-theoretic optimization principles.

---

**Generated:** January 6, 2026 (Updated: February 19, 2026)
**Contact:** Kevin Scroggins
**Institution:** Intelligent Agents Research Group
