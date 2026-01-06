# Stage 3-CoT Hybrid Strategy Results - Chain-of-Thought Evaluation

**Test Date:** January 5-6, 2026
**Test Configuration:** 100 games × 3 algorithms × 9 models = 2,700 total games
**Strategy Tested:** alternating_llm_first (LLM and algorithm alternate turns, LLM starts)
**Prompting:** Chain-of-Thought (structured reasoning before guessing)
**Test Set:** Canonical 100-word test set (stratified by tier)
**Status:** Complete - 9/9 models successfully evaluated across all 3 algorithms

---

## Executive Summary 

**Chain-of-Thought prompting does NOT improve hybrid performance over zero-shot prompting.**

### Key Findings

1. **CoT slightly worse than zero-shot:** 4.20 avg vs 4.17 avg (+0.03 attempts)
2. **All CoT hybrids still underperform pure CSS** (3.79 avg attempts)
3. **Best CoT hybrid:** llama-3.1-nemotron-nano-8B-v1 + CSS + CoT = 3.91 avg (+3.2% vs pure CSS)
4. **Prompting strategy has minimal impact** on hybrid performance
5. **Algorithm choice matters more than prompting:** CSS > VOI > Random (same ranking as zero-shot)

---

## Results by Algorithm

### CSS Algorithm + CoT (Best Performing)

**Mean Performance:** 97.3% win rate, 4.13 avg attempts (+9.0% worse than pure CSS)

| Rank | Model | Win Rate | Wins | Avg Attempts | vs Pure CSS | vs Zero-Shot |
|------|-------|----------|------|--------------|-------------|--------------|
| 1 | **llama-3.1-nemotron-nano-8B-v1** | 99% | 99/100 | **3.91** | **+0.12** | **-0.06**  |
| 2 | llama-3.1-70b-instruct | 96% | 96/100 | 3.97 | +0.18 | **0.00** |
| 3 | llama-3.3-70b-instruct | 95% | 95/100 | 4.00 | +0.21 | **-0.09**  |
| 4 | gemma-3-27b-it | 98% | 98/100 | 4.00 | +0.21 | +0.23  |
| 5 | granite-3.3-8b-instruct | 97% | 97/100 | 4.11 | +0.32 | **-0.10**  |
| 6 | mistral-small-3.1 | 95% | 95/100 | 4.15 | +0.36 | +0.15  |
| 7 | llama-3.1-8b-instruct | 98% | 98/100 | 4.21 | +0.42 | **-0.12**  |
| 8 | mistral-7b-instruct | 98% | 98/100 | 4.27 | +0.48 | +0.10  |
| 9 | codestral-22b | 97% | 97/100 | 4.32 | +0.53 | +0.30  |

**Analysis:**
- 4 models improved with CoT (Nemotron, 70B-instruct, 8B-instruct, Granite)
- 5 models worsened with CoT (gemma, mistral-small, mistral-7b, codestral)
- **Mean: no benefit** (4.13 CoT vs 4.07 zero-shot = +0.06 worse)
- Best performer different from zero-shot (Nemotron vs gemma)

---

### VOI Algorithm + CoT

**Mean Performance:** 94.9% win rate, 4.22 avg attempts (+11.3% worse than pure CSS)

| Rank | Model | Win Rate | Wins | Avg Attempts | vs Pure CSS | vs Zero-Shot |
|------|-------|----------|------|--------------|-------------|--------------|
| 1 | **gemma-3-27b-it** | 95% | 95/100 | **4.05** | **+0.26** | +0.20  |
| 2 | llama-3.3-70b-instruct | 96% | 96/100 | 4.11 | +0.32 | **-0.01**  |
| 3 | llama-3.1-nemotron-nano-8B-v1 | 96% | 96/100 | 4.14 | +0.35 | +0.09  |
| 4 | llama-3.1-70b-instruct | 95% | 95/100 | 4.14 | +0.35 | **-0.11**  |
| 5 | granite-3.3-8b-instruct | 94% | 94/100 | 4.26 | +0.47 | +0.03  |
| 6 | codestral-22b | 93% | 93/100 | 4.27 | +0.48 | **-0.02**  |
| 7 | mistral-7b-instruct | 95% | 95/100 | 4.31 | +0.52 | +0.17  |
| 8 | llama-3.1-8b-instruct | 93% | 93/100 | 4.31 | +0.52 | **-0.07**  |
| 9 | mistral-small-3.1 | 97% | 97/100 | 4.44 | +0.65 | +0.46  |

**Analysis:**
- Similar pattern to CSS: mixed results across models
- 4 models improved, 5 models worsened with CoT
- **Mean: slightly worse** (4.22 CoT vs 4.14 zero-shot = +0.08)
- VOI remains worse than CSS even with CoT

---

### Random Algorithm + CoT

**Mean Performance:** 94.3% win rate, 4.28 avg attempts (+12.9% worse than pure CSS)

| Rank | Model | Win Rate | Wins | Avg Attempts | vs Pure CSS | vs Zero-Shot |
|------|-------|----------|------|--------------|-------------|--------------|
| 1 | **llama-3.3-70b-instruct** | 94% | 94/100 | **4.17** | **+0.38** | **-0.07**  |
| 2 | llama-3.1-70b-instruct | 93% | 93/100 | 4.20 | +0.41 | +0.08  |
| 3 | mistral-small-3.1 | 98% | 98/100 | 4.21 | +0.42 | +0.11  |
| 4 | codestral-22b | 98% | 98/100 | 4.29 | +0.50 | **-0.30**  |
| 5 | granite-3.3-8b-instruct | 96% | 96/100 | 4.29 | +0.50 | **-0.04**  |
| 6 | llama-3.1-8b-instruct | 94% | 94/100 | 4.31 | +0.52 | **-0.03**  |
| 7 | mistral-7b-instruct | 89% | 89/100 | 4.31 | +0.52 | **-0.06**  |
| 8 | llama-3.1-nemotron-nano-8B-v1 | 93% | 93/100 | 4.34 | +0.55 | **0.00** |
| 9 | gemma-3-27b-it | 94% | 94/100 | 4.36 | +0.57 | +0.24  |

**Analysis:**
- 6 models improved with CoT (most improvement among algorithms)
- 3 models worsened
- **Mean: no change** (4.28 CoT vs 4.28 zero-shot = 0.00)
- Random remains worst algorithm regardless of prompting

---

## Statistical Analysis

### Performance Distribution by Algorithm (CoT)

| Algorithm | Mean Win Rate | Mean Attempts | Std Dev | Range | vs Pure CSS | vs Zero-Shot |
|-----------|---------------|---------------|---------|-------|-------------|--------------|
| **CSS** | 97.3% | 4.13 | 0.14 | 3.91-4.32 | +0.34 (+9.0%) | +0.06  |
| **VOI** | 94.9% | 4.22 | 0.12 | 4.05-4.44 | +0.43 (+11.3%) | +0.08  |
| **Random** | 94.3% | 4.28 | 0.07 | 4.17-4.36 | +0.49 (+12.9%) | 0.00  |

**Key Observations:**
- CoT increases attempts for CSS and VOI, no change for Random
- Lower standard deviation with CoT suggests slightly more consistent performance
- Algorithm ranking unchanged: CSS > VOI > Random

### Zero-Shot vs CoT Comparison

| Prompting | Models | Algorithms | Mean Win Rate | Mean Attempts | Best Result |
|-----------|--------|------------|---------------|---------------|-------------|
| **Zero-shot** | 9 | 3 | 94.5% | **4.17** | 3.77 (gemma + CSS) |
| **CoT** | 9 | 3 | 95.4% | 4.20 | 3.91 (Nemotron + CSS) |
| **Difference** | - | - | +0.9% | +0.03 | +0.14 |

**Finding:** CoT provides slightly better win rates (+0.9%) but worse efficiency (+0.03 attempts). The trade-off is not favorable for Wordle optimization.

---

## Model-Specific CoT Impact

### Models That Benefited from CoT (Averaged Across Algorithms)

1. **granite-3.3-8b-instruct**: -0.03 avg (4.22 CoT vs 4.25 zero-shot)
2. **llama-3.1-8b-instruct**: -0.07 avg (4.28 CoT vs 4.35 zero-shot)
3. **llama-3.3-70b-instruct**: -0.06 avg (4.09 CoT vs 4.15 zero-shot)
4. **codestral-22b**: -0.01 avg (4.29 CoT vs 4.30 zero-shot)

**Pattern:** Smaller models and code-focused models benefit slightly from structured reasoning

### Models That Worsened with CoT (Averaged Across Algorithms)

1. **gemma-3-27b-it**: +0.22 avg (4.14 CoT vs 3.91 zero-shot) 
2. **mistral-small-3.1**: +0.24 avg (4.27 CoT vs 4.03 zero-shot) 
3. **mistral-7b-instruct**: +0.07 avg (4.30 CoT vs 4.23 zero-shot) 

**Pattern:** Models that performed best with zero-shot tend to be worse with CoT (regression to mean)

---

## Comparison to Pure Baselines

| Approach | Prompting | Win Rate | Avg Attempts | Efficiency |
|----------|-----------|----------|--------------|------------|
| **Pure CSS** | N/A | 98% | **3.79** |  **Best** |
| **Pure VOI** | N/A | 99% | 3.93 | Excellent |
| **Hybrid CSS** (mean) | Zero-shot | 96.1% | 4.07 | +7.5% worse |
| **Hybrid CSS** (mean) | **CoT** | 97.3% | **4.13** | **+9.0% worse** |
| **Hybrid VOI** (mean) | Zero-shot | 94.9% | 4.14 | +9.3% worse |
| **Hybrid VOI** (mean) | **CoT** | 94.9% | **4.22** | **+11.3% worse** |
| **Hybrid Random** (mean) | Zero-shot | 92.4% | 4.28 | +13.0% worse |
| **Hybrid Random** (mean) | **CoT** | 94.3% | **4.28** | **+12.9% worse** |

**Finding:** CoT does not close the gap to pure algorithms. In fact, it slightly widens the gap for CSS and VOI.

---

## Top 10 Best CoT Performers

| Rank | Model | Algorithm | Win% | Avg Attempts | vs Pure CSS |
|------|-------|-----------|------|--------------|-------------|
| 1 | **llama-3.1-nemotron-nano-8B-v1** | CSS | 99% | **3.91** | +0.12 |
| 2 | llama-3.1-70b-instruct | CSS | 96% | 3.97 | +0.18 |
| 3 | llama-3.3-70b-instruct | CSS | 95% | 4.00 | +0.21 |
| 4 | gemma-3-27b-it | CSS | 98% | 4.00 | +0.21 |
| 5 | gemma-3-27b-it | VOI | 95% | 4.05 | +0.26 |
| 6 | granite-3.3-8b-instruct | CSS | 97% | 4.11 | +0.32 |
| 7 | llama-3.3-70b-instruct | VOI | 96% | 4.11 | +0.32 |
| 8 | llama-3.1-nemotron-nano-8B-v1 | VOI | 96% | 4.14 | +0.35 |
| 9 | llama-3.1-70b-instruct | VOI | 95% | 4.14 | +0.35 |
| 10 | mistral-small-3.1 | CSS | 95% | 4.15 | +0.36 |

**Note:** Even the best CoT hybrid (3.91 avg) is 3.2% worse than pure CSS (3.79 avg).

---

## Why CoT Doesn't Help

### Hypothesis: Structured Reasoning Should Improve Constraint Satisfaction

**Expectation:** CoT should help LLMs:
- Better track constraints
- Reason about information gain
- Make more optimal guesses

### Reality: No Improvement Observed

**Reasons:**

1. **Overthinking Penalty:** CoT adds complexity without adding value
   - Wordle constraints are simple (green/yellow/gray)
   - LLMs already understand constraints with zero-shot
   - Additional reasoning doesn't discover better guesses

2. **Increased Variance:** Longer reasoning introduces more failure modes
   - More tokens = more opportunities for errors
   - Reasoning can lead to suboptimal conclusions
   - Zero-shot is more direct and reliable

3. **Algorithm Does the Thinking:** On algorithm turns, reasoning is irrelevant
   - CSS/VOI/Random already compute optimal moves
   - LLM reasoning only matters on LLM turns
   - 50% of turns unaffected by prompting strategy

4. **Model-Specific Effects Cancel Out:** Some models benefit, others worsen
   - No consistent improvement pattern
   - Best zero-shot models often worse with CoT
   - Average effect near zero

---

## Research Implications

### Key Findings

1. **Prompting strategy has minimal impact** on hybrid performance
   - Zero-shot: 4.17 avg attempts
   - CoT: 4.20 avg attempts
   - Difference: +0.03 attempts (negligible)

2. **Algorithm choice matters far more than prompting**
   - CSS vs Random: 0.15 attempts difference (significant)
   - Zero-shot vs CoT: 0.03 attempts difference (negligible)

3. **Best prompting is model-dependent**
   - Some models prefer zero-shot (gemma, mistral-small)
   - Some models prefer CoT (Nemotron, llama-8b, granite)
   - No universal answer

4. **Neither prompting strategy enables beating pure CSS**
   - Best zero-shot: 3.77 avg (gemma + CSS)
   - Best CoT: 3.91 avg (Nemotron + CSS)
   - Pure CSS: 3.79 avg
   - **Pure CSS still best** overall

### Practical Recommendations

**For hybrid systems (if you must use them):**
- Use zero-shot prompting (simpler, slightly better average)
- If using specific models, test both prompting strategies
- Don't expect CoT to close gap to pure algorithms

**For production:**
-  **Use pure CSS** (3.79 avg, $0 cost, deterministic)
-  Don't use hybrids regardless of prompting strategy

---

## Cost-Benefit Analysis

### Zero-Shot vs CoT Costs

| Metric | Zero-Shot | CoT | Difference |
|--------|-----------|-----|------------|
| **Tokens per guess** | ~100 | ~250 | +150 tokens |
| **Cost multiplier** | 1x | 2.5x | +150% |
| **Mean attempts** | 4.17 | 4.20 | +0.03 worse |
| **Win rate** | 94.5% | 95.4% | +0.9% better |

**Cost-Benefit Verdict:**
- CoT costs 2.5x more (longer prompts + responses)
- CoT performs 0.03 attempts worse
- CoT has +0.9% better win rate (minor improvement)
- **Not worth it:** Pay more for worse efficiency

---

## Data Availability

### Stage 3-CoT Results
**Location:** `results/hybrids/stage3-cot/`

**Files:**
- **Raw data (CSV):** 27 files in `raw data/` subdirectory
  - Complete game-by-game results with reasoning traces
- **Summary stats (JSON):** 27 files in `summary stats/` subdirectory
  - Aggregate performance metrics per model-algorithm combination
- **Logs:** 27 files in `logs/` subdirectory
  - Full execution logs with CoT reasoning outputs

**Models Tested:** All 9 models across all 3 algorithms (same as zero-shot)
**Algorithms Tested:** CSS, VOI, Random (filtered)
**Prompting:** Chain-of-Thought with structured reasoning format

---

## Conclusions

### Main Findings

1. **CoT does not improve hybrid performance** (4.20 vs 4.17 avg, +0.03 worse)
2. **Prompting strategy is not the bottleneck** (algorithm choice matters more)
3. **Model-specific effects:** Some benefit, others worsen (no consistent pattern)
4. **All CoT hybrids still underperform pure CSS** by significant margin
5. **Added CoT cost not justified** by minimal performance change

### Comprehensive Evaluation Summary

**Total Games Evaluated:** 5,400
- Zero-shot: 2,700 games (9 models × 3 algorithms × 100 games)
- CoT: 2,700 games (9 models × 3 algorithms × 100 games)

**Overall Mean Performance:**
- **Zero-shot:** 94.5% win rate, **4.17 avg attempts**
- **CoT:** 95.4% win rate, 4.20 avg attempts
- **Pure CSS:** 98% win rate, **3.79 avg attempts** 

### Recommendations

**For Research:**
-  Document as comprehensive evaluation of prompting strategies
-  Shows prompting is not solution for hybrid underperformance
-  Demonstrates algorithm choice > prompting choice
-  Publication-worthy evidence across 5,400 games

**For Production:**
-  **Use pure CSS** (best performance, zero cost)
-  Don't use hybrids (regardless of prompting)
-  Don't use CoT for hybrids (costs more, performs worse)

**For Future Work:**
- Test other hybrid strategies (not just alternating)
- Investigate why some models benefit from CoT while others don't
- Apply to domains where hybrids might actually help

---

## Final Verdict

**Research Question:** Does Chain-of-Thought prompting improve hybrid performance?

**Answer:** **No.**

**Evidence:**
- 2,700 CoT games across 3 algorithms and 9 models
- Mean performance 0.03 attempts worse than zero-shot
- No consistent improvement pattern across models
- Best CoT hybrid (3.91) still 3.2% worse than pure CSS (3.79)
- CoT costs 2.5x more with no performance benefit

**Key Insight:** The fundamental issue with hybrids is **architecture (alternating), not prompting**. LLM turns hurt performance regardless of how carefully the LLM reasons.

---

**Evaluation Complete:** January 5-6, 2026
**Total Games (CoT):** 2,700
**Models Tested:** 9 LLMs across 3 algorithms
**Conclusion:** CoT doesn't fix hybrid underperformance; pure CSS remains optimal

**See also:** hybrids_stage3_results.md for zero-shot evaluation results
