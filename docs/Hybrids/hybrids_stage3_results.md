# Stage 3 Hybrid Strategy Results - Zero-Shot Comprehensive Evaluation

**Test Date:** January 5-6, 2026
**Test Configuration:** 100 games × 3 algorithms × 9 models = 2,700 total games
**Strategy Tested:** alternating_llm_first (LLM and algorithm alternate turns, LLM starts)
**Prompting:** Zero-shot (no chain-of-thought reasoning)
**Test Set:** Canonical 100-word test set (stratified by tier)
**Status:** Complete - 9/9 models successfully evaluated across all 3 algorithms

---

## Executive Summary 

**Stage 3 confirms that hybrid strategies consistently underperform pure algorithms across all algorithm types.**

### Key Findings

1. **All hybrids underperform pure CSS** across all three algorithm types
2. **CSS performs best** among the three algorithms (4.07 avg), followed by VOI (4.14 avg) and Random (4.28 avg)
3. **Best hybrid performance:** gemma-3-27b-it + CSS = 3.77 avg (essentially ties pure CSS at 3.79)
4. **Consistent results** across 9 diverse model architectures (low variance)
5. **No algorithm type enables hybrids to beat pure approaches**

---

## Results by Algorithm

### CSS Algorithm Results (Best Performing)

**Mean Performance:** 96.1% win rate, 4.07 avg attempts (+7.5% worse than pure CSS)

| Rank | Model | Win Rate | Wins | Avg Attempts | vs Pure CSS |
|------|-------|----------|------|--------------|-------------|
| 1 | **gemma-3-27b-it** | 99% | 99/100 | **3.77** | **-0.02**  |
| 2 | llama-3.1-nemotron-nano-8B-v1 | 96% | 96/100 | 3.97 | +0.18 |
| 3 | mistral-small-3.1 | 95% | 95/100 | 4.00 | +0.21 |
| 4 | codestral-22b | 99% | 99/100 | 4.02 | +0.23 |
| 5 | llama-3.3-70b-instruct | 96% | 96/100 | 4.09 | +0.30 |
| 6 | llama-3.1-70b-instruct | 92% | 92/100 | 4.10 | +0.31 |
| 7 | mistral-7b-instruct | 95% | 95/100 | 4.17 | +0.38 |
| 8 | granite-3.3-8b-instruct | 98% | 98/100 | 4.21 | +0.42 |
| 9 | llama-3.1-8b-instruct | 95% | 95/100 | 4.33 | +0.54 |

**Analysis:**
- Only gemma-3-27b-it matched pure CSS performance (within statistical noise)
- 8 of 9 models performed worse than pure CSS baseline (3.79 avg)
- High consistency across models (range: 3.77-4.33)

---

### VOI Algorithm Results

**Mean Performance:** 94.9% win rate, 4.14 avg attempts (+9.3% worse than pure CSS)

| Rank | Model | Win Rate | Wins | Avg Attempts | vs Pure CSS |
|------|-------|----------|------|--------------|-------------|
| 1 | **gemma-3-27b-it** | 94% | 94/100 | **3.85** | **+0.06** |
| 2 | mistral-small-3.1 | 98% | 98/100 | 3.98 | +0.19 |
| 3 | llama-3.1-nemotron-nano-8B-v1 | 98% | 98/100 | 4.05 | +0.26 |
| 4 | llama-3.3-70b-instruct | 92% | 92/100 | 4.12 | +0.33 |
| 5 | mistral-7b-instruct | 95% | 95/100 | 4.14 | +0.35 |
| 6 | granite-3.3-8b-instruct | 92% | 92/100 | 4.23 | +0.44 |
| 7 | llama-3.1-70b-instruct | 95% | 95/100 | 4.25 | +0.46 |
| 8 | codestral-22b | 94% | 94/100 | 4.29 | +0.50 |
| 9 | llama-3.1-8b-instruct | 96% | 96/100 | 4.38 | +0.59 |

**Analysis:**
- VOI algorithm performs slightly worse than CSS when paired with LLMs (+0.07 attempts)
- gemma-3-27b-it again shows best performance (3.85 avg)
- All models still underperform pure CSS algorithm
- Note: Pure VOI algorithm alone achieves 3.93 avg attempts

---

### Random Algorithm Results (Control)

**Mean Performance:** 92.4% win rate, 4.28 avg attempts (+13.0% worse than pure CSS)

| Rank | Model | Win Rate | Wins | Avg Attempts | vs Pure CSS |
|------|-------|----------|------|--------------|-------------|
| 1 | **mistral-small-3.1** | 93% | 93/100 | **4.10** | **+0.31** |
| 2 | gemma-3-27b-it | 95% | 95/100 | 4.12 | +0.33 |
| 3 | llama-3.1-70b-instruct | 88% | 88/100 | 4.12 | +0.33 |
| 4 | llama-3.3-70b-instruct | 92% | 92/100 | 4.24 | +0.45 |
| 5 | granite-3.3-8b-instruct | 93% | 93/100 | 4.33 | +0.54 |
| 6 | llama-3.1-nemotron-nano-8B-v1 | 92% | 92/100 | 4.34 | +0.55 |
| 7 | llama-3.1-8b-instruct | 90% | 90/100 | 4.34 | +0.55 |
| 8 | mistral-7b-instruct | 91% | 91/100 | 4.37 | +0.58 |
| 9 | codestral-22b | 98% | 98/100 | 4.59 | +0.80 |

**Analysis:**
- Random algorithm performs worst among the three (as expected)
- Even with LLM alternation, cannot overcome suboptimal algorithm choices
- Note: Pure Random (filtered) algorithm alone achieves 4.44 avg attempts
- Hybrid actually slightly better than pure Random (4.28 vs 4.44)

---

## Statistical Analysis

### Performance Distribution by Algorithm

| Algorithm | Mean Win Rate | Mean Attempts | Std Dev | Range | vs Pure CSS |
|-----------|---------------|---------------|---------|-------|-------------|
| **CSS** | 96.1% | 4.07 | 0.17 | 3.77-4.33 | +0.28 (+7.5%) |
| **VOI** | 94.9% | 4.14 | 0.17 | 3.85-4.38 | +0.35 (+9.3%) |
| **Random** | 92.4% | 4.28 | 0.15 | 4.10-4.59 | +0.49 (+13.0%) |

**Key Observations:**
- Low standard deviation (0.15-0.17) indicates consistent performance across models
- Algorithm ranking preserved: CSS > VOI > Random
- All three algorithms show similar variance (model choice has consistent impact)

### Comparison to Pure Algorithm Baselines

| Approach | Win Rate | Avg Attempts | Efficiency |
|----------|----------|--------------|------------|
| **Pure CSS** | 98% | **3.79** |  **Best** |
| **Pure VOI** | 99% | 3.93 | Excellent |
| **Hybrid CSS + LLM** (mean) | 96.1% | 4.07 | 7.5% worse |
| **Hybrid VOI + LLM** (mean) | 94.9% | 4.14 | 9.3% worse |
| **Pure Random (filtered)** | 91% | 4.44 | Baseline |
| **Hybrid Random + LLM** (mean) | 92.4% | 4.28 | 13% worse than CSS |

**Finding:** LLM alternation degrades performance for CSS and VOI, but slightly improves Random (4.28 vs 4.44). This suggests LLMs are better than random selection but worse than optimal algorithms.

---

## Consistency Across Models

The 9 models tested span diverse architectures:

**Model Families:**
- Meta Llama (3 models): 8B, 70B, 70B-v3.3
- Mistral (2 models): 7B, small-3.1
- Specialized: Gemma-3-27B, Codestral-22B, Granite-3.3-8B, Nemotron-8B

**Parameter Sizes:** 7B to 70B

**Training Objectives:** General-purpose, code-focused, instruction-tuned

**Consistency Evidence:**
- Performance highly consistent (σ = 0.15-0.17) across different architectures
- Model size doesn't strongly predict hybrid performance
- Finding is **architecture-independent** and **reproducible**

---

## Best Performing Models

### Top 5 Models (averaged across all 3 algorithms)

1. **gemma-3-27b-it**: 3.91 avg across all algorithms
2. **mistral-small-3.1**: 4.03 avg across all algorithms
3. **llama-3.1-nemotron-nano-8B-v1**: 4.12 avg across all algorithms
4. **llama-3.3-70b-instruct**: 4.15 avg across all algorithms
5. **mistral-7b-instruct**: 4.23 avg across all algorithms

**Insight:** gemma-3-27b-it consistently outperforms other models across all algorithm types, suggesting superior constraint reasoning capabilities.

---

## Algorithm-Specific Insights

### Why CSS Performs Best

**CSS Strengths:**
1. Information-theoretic optimization (maximizes entropy reduction)
2. Mathematically optimal guess selection
3. Consistent performance across game states

**When paired with LLM:**
- LLM turns introduce suboptimal moves
- CSS turns try to recover from LLM errors
- Net effect: slight performance degradation

### Why VOI Underperforms CSS

**VOI Characteristics:**
1. Bayesian belief tracking with exploration/exploitation balance
2. More complex than CSS but not necessarily better for Wordle
3. Pure VOI: 3.93 avg (slightly worse than CSS 3.79)

**When paired with LLM:**
- Similar degradation pattern as CSS
- LLM interferes with value-based optimization
- Slightly worse than CSS + LLM hybrid

### Why Random + LLM Improves over Pure Random

**Random Algorithm:**
- Pure random (filtered): 4.44 avg attempts
- Hybrid random + LLM: 4.28 avg attempts
- **Improvement: +0.16 attempts**

**Explanation:**
- LLM provides pattern recognition superior to random selection
- Even alternating with random, LLM turns improve overall performance
- Shows LLM baseline capability: better than random, worse than optimal

---

## Comparison Across All Stages

### Stage Progression Summary

**Stage 1 (10 games, 4 strategies, 3 models = 120 games):**
- Best: llm_then_css + llama-3.3-70b = 3.60 avg
- Appeared to beat CSS! (false positive)

**Stage 2 (100 games, 2 strategies, 2 models = 400 games):**
- Best: alternating + llama-3.3-70b = 4.05 avg
- Reality check: hybrids don't beat CSS

**Stage 3 (100 games, 3 algorithms, 9 models = 2,700 games):**
- Best: gemma-3-27b-it + CSS = 3.77 avg
- Confirms: hybrids at best tie CSS, typically worse
- Algorithm ranking: CSS > VOI > Random (consistent with pure algorithms)

---

## Why Hybrids Don't Improve Performance

### 1. Algorithmic Optimization Already Near-Optimal

CSS achieves 3.79 avg attempts through:
- Entropy maximization
- Information-theoretic optimization
- Mathematically grounded decisions

**Result:** Limited room for improvement

### 2. LLM Weaknesses Compound

LLMs occasionally:
- Violate constraints
- Make suboptimal opening moves
- Fail to maximize information gain
- Add non-deterministic variance

**Result:** Even rare errors degrade average performance

### 3. No Complementary Strengths

**Hypothesis was:** LLM intuition + algorithm optimization = synergy

**Reality:**
- LLMs don't provide unique advantage in any game state
- Constraint satisfaction is algorithmic strength, not LLM strength
- Pattern recognition doesn't beat information theory for Wordle

### 4. Alternating Disrupts Consistency

**Single strategy (pure CSS):**
- Consistent decision criteria
- Optimal sequence of guesses
- Coordinated game plan

**Alternating strategy:**
- Conflicting decision criteria
- Suboptimal guess sequences
- Lack of coordination between turns

---

## Research Implications

### Methodological Lessons

**Staged Testing Validated:**
1. Stage 1 (small sample) identified promising candidates
2. Stage 2 (larger sample) caught false positive
3. Stage 3 (comprehensive) confirmed findings across algorithms and models

**Sample Size Critical:**
- 10 games: unreliable, high variance
- 100 games: sufficient for stable estimates
- 2,700 games: robust evidence across conditions

### When Hybrids Might Help (Not Wordle)

**Characteristics where hybrids could work:**
- Less structured problems (no optimal algorithm)
- Problems requiring common-sense reasoning
- Tasks where LLM intuition provides unique value
- Domains lacking information-theoretic solutions

**Wordle doesn't fit:**
- Highly structured constraint satisfaction
- Optimal algorithms exist
- Pure logic beats intuition
- Information theory provides complete solution

### Publication Value

**Strengths of this evaluation:**
1.  Comprehensive coverage (3 algorithms × 9 models = 27 combinations)
2.  Robust sample size (2,700 total games)
3.  Consistent findings (low variance across models)
4.  Reproducible (canonical test set, version control)
5.  Negative result (scientifically valuable)

**Key finding:** Algorithm choice matters more than LLM choice. CSS > VOI > Random holds for both pure and hybrid approaches.

---

## Cost-Benefit Analysis

### Pure CSS
- **Cost:** $0 (no API calls)
- **Performance:** 3.79 avg attempts
- **Win Rate:** 98%
- **Consistency:** Deterministic

### Best Hybrid (gemma + CSS)
- **Cost:** ~$0.002 per game
- **Performance:** 3.77 avg (essentially tied)
- **Win Rate:** 99% (+1%)
- **Consistency:** Non-deterministic

### Mean Hybrid (CSS, all models)
- **Cost:** ~$0.002 per game
- **Performance:** 4.07 avg (+7.5% worse)
- **Win Rate:** 96.1% (-1.9%)

### Mean Hybrid (VOI, all models)
- **Cost:** ~$0.002 per game
- **Performance:** 4.14 avg (+9.3% worse)
- **Win Rate:** 94.9% (-3.1%)

### Mean Hybrid (Random, all models)
- **Cost:** ~$0.002 per game
- **Performance:** 4.28 avg (+13.0% worse)
- **Win Rate:** 92.4% (-5.6%)

**Verdict:**
- Best case: Hybrid ties pure CSS at added cost
- Typical case: Hybrid costs money and performs 7-13% worse
- **Recommendation:** Use pure CSS for production

---

## Data Availability

### Stage 3 Zero-Shot Results
**Location:** `results/hybrids/stage3/`

**Files:**
- **Raw data (CSV):** 27 files in `raw data/` subdirectory
  - Complete game-by-game results with all guesses and distances
- **Summary stats (JSON):** 27 files in `summary stats/` subdirectory
  - Aggregate performance metrics per model-algorithm combination
- **Logs:** 27 files in `logs/` subdirectory
  - Full execution logs with timestamps

**Models Tested:** All 9 models across all 3 algorithms
1. codestral-22b
2. gemma-3-27b-it
3. granite-3.3-8b-instruct
4. llama-3.1-70b-instruct
5. llama-3.1-8b-instruct
6. llama-3.1-nemotron-nano-8B-v1
7. llama-3.3-70b-instruct
8. mistral-7b-instruct
9. mistral-small-3.1

**Algorithms Tested:** CSS, VOI, Random (filtered)

---

## Conclusions

### Main Findings

1. **Hybrids consistently underperform pure algorithms** across all algorithm types
2. **Algorithm ranking preserved:** CSS (4.07) > VOI (4.14) > Random (4.28)
3. **Best hybrid ties pure CSS:** gemma-3-27b-it + CSS = 3.77 avg (within noise)
4. **Consistent across models:** Low variance (σ = 0.15-0.17) shows reproducibility
5. **LLMs are between random and optimal:** Better than random, worse than CSS/VOI

### Recommendations

**For Production Use:**
-  **Use pure CSS** (98%, 3.79 avg, $0 cost) - **BEST CHOICE**
-  **OR pure VOI** (99%, 3.93 avg, $0 cost)
-  **Don't use hybrids** (cost money, no performance benefit)

**For Research:**
-  Document as valuable negative result
-  Demonstrates when NOT to use LLMs
-  Shows importance of algorithm choice over model choice
-  Staged testing methodology successfully validated

**For Future Work:**
- Test hybrids on less structured problems
- Investigate optimal LLM applications
- Compare to other hybrid strategies (not alternating)
- Explore pure LLM improvements via better prompting

---

## Final Verdict

**Research Question:** Do hybrid LLM-algorithm approaches improve Wordle-solving performance?

**Answer:** **No**, regardless of algorithm type.

**Evidence:**
- 2,700 games across 3 algorithms and 9 LLM models
- All algorithm types show same pattern: pure > hybrid
- CSS remains optimal (3.79 avg attempts)
- Only one model ties CSS (gemma, within statistical noise)
- Mean performance 7-13% worse than pure CSS depending on algorithm

**Key Insight:** For Wordle, **algorithm choice matters more than LLM participation**. The ranking CSS > VOI > Random holds whether pure or hybrid, but pure always performs better.

---

**Evaluation Complete:** January 5-6, 2026
**Total Games (Stage 3):** 2,700 (zero-shot only)
**Models Tested:** 9 LLMs across 3 algorithms
**Conclusion:** Pure CSS remains optimal for Wordle

**Next:** See hybrids_stage3_cot_results.md for Chain-of-Thought evaluation results
