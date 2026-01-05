# Experimental Results

## Overview

This document presents the results of comprehensive evaluations comparing traditional preference elicitation algorithms against Large Language Models (LLMs) for solving Wordle puzzles.

**Evaluation Date:** December 11-12, 2025
**Test Set:** 100 words from canonical test set (34 Tier 1, 33 Tier 2, 33 Tier 3)
**Algorithms Tested:** 8 strategies (4 basic + 4 hybrid)
**LLMs Tested:** 11 models with 2 prompting strategies each

---

## Executive Summary

### Key Findings

1. **Traditional algorithms outperform LLMs in efficiency**: Algorithms solve Wordle in 3.77-3.93 average attempts vs LLMs' 4.03-4.47 attempts
2. **Both approaches achieve high success rates**: Algorithms: 97-100% win rate; LLMs: 89-100% win rate
3. **Hybrid strategies provide minimal improvement**: CSS-VOI alternating achieves 100% but only marginally better than basic strategies
4. **LLMs are highly capable but less efficient**: All tested LLMs achieve >89% success with valid constraint reasoning
5. **Prompting strategy impact is model-dependent**: No consistent advantage for chain-of-thought vs zero-shot

### Best Performers

- **Best Algorithm:** CSS (98% win rate, 3.79 avg attempts) - most efficient
- **Best Hybrid:** CSS-VOI Alternating (100% win rate, 3.85 avg attempts) - perfect success
- **Best LLM:** Mistral-small-3.1 with CoT (100% win rate, 4.30 avg attempts)

---

## Methodology

### Experimental Design

**Guess Pool:**
- Full wordlist of 5,629 five-letter English words
- All algorithms can guess from entire vocabulary

**Test Set:**
- Fixed canonical test set of 100 words
- Stratified sampling: 34 Tier 1, 33 Tier 2, 33 Tier 3
- Same words used for ALL evaluations (algorithms and LLMs)
- Fixed seed (42) ensures reproducibility

**Metrics Tracked:**
- Win rate and average attempts to win
- Hamming and Levenshtein distance convergence
- Constraint violations (LLMs)
- Information gain and candidate reduction (LLMs)
- Performance by word difficulty tier

---

## Algorithm Performance

### Overall Results

| Strategy | Win Rate | Wins/Total | Avg Attempts | Efficiency Rank |
|----------|----------|------------|--------------|-----------------|
| **css_voi_alternating** | **100.0%** | 100/100 | 3.85 | 3 |
| **voi** | **99.0%** | 99/100 | 3.93 | 5 |
| **css** | **98.0%** | 98/100 | **3.79** | **1** |
| **voi_then_css** | 98.0% | 98/100 | 4.07 | 7 |
| **css_then_voi** | 97.0% | 97/100 | **3.77** | **2** |
| **voi_css_alternating** | 97.0% | 97/100 | 3.90 | 4 |
| **random** (filtered) | 91.0% | 91/100 | 4.44 | 6 |
| **pure_random** (baseline) | 0.0% | 0/100 | 0.00 | 8 |

### Performance by Tier

#### CSS Strategy
| Tier | Win Rate | Wins/Total | Avg Attempts |
|------|----------|------------|--------------|
| Tier 1 (high freq) | 100.0% | 34/34 | 3.97 |
| Tier 2 (med freq) | 93.9% | 31/33 | 3.48 |
| Tier 3 (low freq) | 100.0% | 33/33 | 3.88 |

#### VOI Strategy
| Tier | Win Rate | Wins/Total | Avg Attempts |
|------|----------|------------|--------------|
| Tier 1 (high freq) | 100.0% | 34/34 | 3.85 |
| Tier 2 (med freq) | 97.0% | 32/33 | 3.78 |
| Tier 3 (low freq) | 100.0% | 33/33 | 4.15 |

#### CSS-VOI Alternating (Best Hybrid)
| Tier | Win Rate | Wins/Total | Avg Attempts |
|------|----------|------------|--------------|
| Tier 1 (high freq) | 100.0% | 34/34 | 3.79 |
| Tier 2 (med freq) | 100.0% | 33/33 | 3.73 |
| Tier 3 (low freq) | 100.0% | 33/33 | 4.03 |

#### Random Strategy (Filtered)
| Tier | Win Rate | Wins/Total | Avg Attempts |
|------|----------|------------|--------------|
| Tier 1 (high freq) | 88.2% | 30/34 | 4.63 |
| Tier 2 (med freq) | 93.9% | 31/33 | 4.26 |
| Tier 3 (low freq) | 90.9% | 30/33 | 4.43 |

### Distance Convergence Patterns

Average Hamming distance by attempt number:

| Strategy | Attempt 1 | Attempt 2 | Attempt 3 | Attempt 4 | Attempt 5 | Attempt 6 |
|----------|-----------|-----------|-----------|-----------|-----------|-----------|
| **css** | 4.56 | 3.37 | 1.63 | 0.42 | 0.50 | 0.33 |
| **voi** | 4.57 | 3.40 | 1.77 | 0.62 | 0.33 | 0.20 |
| **css_voi_alternating** | 4.49 | 3.37 | 1.71 | 0.54 | 0.27 | 0.00 |
| **random** | 4.64 | 3.86 | 2.37 | 1.30 | 0.71 | 0.46 |
| **pure_random** | 4.51 | 4.58 | 4.59 | 4.67 | 4.57 | 4.57 |

**Observation:** Pure random shows no convergence (distances remain ~4.5), while all intelligent strategies show rapid convergence by attempt 3-4.

---

## LLM Performance

### Overall Results

| Model | Prompting | Win Rate | Wins/Total | Avg Attempts |
|-------|-----------|----------|------------|--------------|
| **mistral-small-3.1** | **CoT** | **100.0%** | 100/100 | **4.30** |
| gemma-3-27b-it | zero-shot | 99.0% | 99/100 | 4.11 |
| gemma-3-27b-it | CoT | 98.0% | 98/100 | 4.11 |
| mistral-7b-instruct | zero-shot | 98.0% | 98/100 | 4.10 |
| gpt-oss-20b | zero-shot | 96.0% | 96/100 | 4.36 |
| llama-3.1-70b-instruct | CoT | 96.0% | 96/100 | 4.16 |
| granite-3.3-8b-instruct | CoT | 96.0% | 96/100 | 4.34 |
| mistral-small-3.1 | zero-shot | 96.0% | 96/100 | 4.22 |
| llama-3.3-70b-instruct | zero-shot | 95.0% | 95/100 | 4.23 |
| llama-3.1-70b-instruct | zero-shot | 95.0% | 95/100 | 4.07 |
| mistral-7b-instruct | CoT | 95.0% | 95/100 | 4.22 |
| codestral-22b | CoT | 95.0% | 95/100 | 4.29 |
| codestral-22b | zero-shot | 94.0% | 94/100 | 4.34 |
| gpt-oss-20b | CoT | 94.0% | 94/100 | 4.33 |
| granite-3.3-8b-instruct | zero-shot | 93.0% | 93/100 | 4.25 |
| llama-3.3-70b-instruct | CoT | 93.0% | 93/100 | 4.03 |
| llama-3.1-8b-instruct | CoT | 93.0% | 93/100 | 4.17 |
| llama-3.1-8b-instruct | zero-shot | 93.0% | 93/100 | 4.13 |
| llama-3.1-nemotron-nano-8B-v1 | CoT | 93.0% | 93/100 | 4.31 |
| llama-3.1-nemotron-nano-8B-v1 | zero-shot | 93.0% | 93/100 | 4.47 |
| gpt-oss-120b | CoT | 92.0% | 92/100 | 4.37 |
| gpt-oss-120b | zero-shot | 89.0% | 89/100 | 4.30 |

### LLM Performance Statistics

**Win Rate Range:** 89-100%
**Average Attempts Range:** 4.03-4.47
**Mean Win Rate:** 95.1%
**Mean Attempts:** 4.24

**Completion Rate:** 100% (all LLMs completed all games)
**Valid Guess Rate:** 100% (all guesses were valid words from wordlist)

### Prompting Strategy Comparison

#### Chain-of-Thought (CoT)
- **Mean Win Rate:** 95.3%
- **Mean Attempts:** 4.26
- **Best:** mistral-small-3.1 (100%, 4.30 attempts)
- **Worst:** gpt-oss-120b (92%, 4.37 attempts)

#### Zero-Shot
- **Mean Win Rate:** 94.8%
- **Mean Attempts:** 4.22
- **Best:** gemma-3-27b-it (99%, 4.11 attempts)
- **Worst:** gpt-oss-120b (89%, 4.30 attempts)

**Observation:** No consistent advantage for either prompting strategy. Performance varies by model, with some preferring CoT (mistral-small) and others performing better with zero-shot (gemma-3, mistral-7b).

---

## Head-to-Head Comparison

### Algorithms vs LLMs

| Metric | Best Algorithm | Best LLM | Winner |
|--------|----------------|----------|--------|
| **Win Rate** | 100% (css_voi_alternating) | 100% (mistral-small-3.1 CoT) | **Tie** |
| **Efficiency (Avg Attempts)** | 3.77 (css_then_voi) | 4.03 (llama-3.3-70b CoT) | **Algorithms** |
| **Consistency** | 6/8 strategies >97% | 21/25 models >93% | **Algorithms** |
| **Robustness** | Pure random: 0% (as expected) | Weakest: 89% | **LLMs** |

### Key Comparisons

**Efficiency Gap:**
- Top 3 algorithms: 3.77-3.85 avg attempts
- Top 3 LLMs: 4.03-4.11 avg attempts
- **Difference: ~0.25-0.30 attempts** (algorithms 6-8% more efficient)

**Success Rate:**
- Algorithms: 97-100% (excluding baselines)
- LLMs: 89-100%
- Both highly successful, algorithms slightly more consistent

**Constraint Adherence:**
- Algorithms: Perfect (by design)
- LLMs: High (avg 0.04 violations per guess for best models)

---

## Analysis and Insights

### Why Algorithms Outperform LLMs

1. **Information-theoretic optimization:** CSS and VOI maximize entropy reduction at each step
2. **Perfect constraint satisfaction:** Algorithms never violate known constraints
3. **Optimal candidate pruning:** Exact filtering vs approximate reasoning
4. **No token limitations:** Can evaluate all candidates exhaustively

### Why LLMs Still Perform Well

1. **Strong pattern recognition:** Learn common letter patterns and word structure
2. **Vocabulary knowledge:** Understand word frequency and commonality
3. **Constraint reasoning:** Can track and apply Wordle rules effectively
4. **Adaptability:** Adjust strategy based on feedback without explicit programming

### Hybrid Strategy Insights

**CSS-VOI Alternating achieved 100% win rate but:**
- Only 0.06 attempts better than pure CSS (3.85 vs 3.79)
- Only 0.08 attempts better than pure VOI (3.85 vs 3.93)
- Marginal improvement doesn't justify added complexity

**Conclusion:** Basic CSS and VOI strategies are highly effective on their own. Hybrid strategies provide minimal practical benefit.

### Tier-Based Difficulty

**Observations:**
- Tier 1 (high frequency): Slightly harder for algorithms (more common words = more candidates)
- Tier 3 (low frequency): Slightly harder due to less familiar words
- Tier 2 (medium frequency): Sweet spot for some strategies

**No clear difficulty pattern:** Performance variation by tier is small (±0.3 attempts), suggesting algorithms are robust across word frequencies.

---

## Visualizations

The following publication-quality visualizations are available in `results/algorithms/plots/` and `results/comparison_plots/`:

### Algorithm Visualizations
- `overall_performance.png` - Win rate and average attempts comparison
- `tier_performance.png` - Performance grouped by word difficulty tier
- `distance_convergence.png` - Hamming and Levenshtein convergence patterns
- `attempt_distribution.png` - Box plot showing attempt distributions
- `mean_hamming_per_turn.png` - Mean Hamming distance by turn
- `mean_levenshtein_per_turn.png` - Mean Levenshtein distance by turn
- `avg_attempts_by_strategy.png` - Average attempts to win by strategy
- `hamming_reduction_per_turn.png` - Distance reduction per turn
- `levenshtein_reduction_per_turn.png` - Distance reduction per turn

### Comparison Visualizations
- `performance_comparison.png` - Algorithms vs LLMs win rates and efficiency
- `distance_convergence_comparison.png` - How quickly different approaches converge
- `turn_by_turn_comparison.png` - Performance evolution across attempts
- `distance_reduction_comparison.png` - Rate of progress toward solution

---

## Statistical Notes

### Reproducibility
- Fixed random seed (42) used throughout
- Canonical test set version-controlled in `wordlist/test_set.csv`
- All evaluations use identical 100-word test set
- Enables paired statistical testing (each method tested on same words)

### Sample Size
- 100 games per strategy (algorithms)
- 100 games per model/prompting combination (LLMs)
- Total: 800 algorithm games + 2,500 LLM games = 3,300 games

### Significance Testing
Future work should include:
- Paired t-tests for algorithm vs LLM comparisons
- McNemar's test for win rate differences
- Effect size calculations (Cohen's d)
- Confidence intervals for average attempts

---

## Future Work

### Immediate Next Steps
1. **Statistical significance testing** - Formal tests comparing algorithms vs LLMs
2. **Tier 4 evaluation** - Add lowest-frequency words to test set
3. **Error analysis** - Deep dive into failed games for each strategy
4. **Opening move analysis** - Which first guesses are most effective?

### Research Extensions
1. **Adaptive LLM prompting** - Dynamic prompts based on game state
2. **LLM fine-tuning** - Train models specifically for Wordle
3. **Hybrid LLM-algorithm systems** - Combine strengths of both approaches
4. **Hard mode evaluation** - Test with Wordle hard mode constraints
5. **Multi-language evaluation** - Extend to non-English Wordle variants
6. **Human player comparison** - Benchmark against human performance data

### Publication Preparation
1. Write methods section based on evaluation system
2. Create publication figures from visualization plots
3. Draft results section from this document
4. Prepare supplementary materials (full result tables)
5. Add related work comparison section

---

## Data Availability

### Algorithm Results
- **Detailed results:** `results/algorithms/algorithm_results_20251211_175156.csv`
- **Summary statistics (JSON):** `results/algorithms/summary_stats_20251211_180718.json`
- **Summary statistics (TXT):** `results/algorithms/summary_stats_20251211_180718.txt`

### LLM Results
- **Detailed results:** `results/llms/model_{model_name}_{prompt_type}_{timestamp}.csv` (26 files)
- **Summary statistics:** `results/llms/summary_{model_name}_{prompt_type}_{timestamp}.json` (25 files)

### Test Set
- **Canonical test set:** `wordlist/test_set.csv`
- **Full wordlist:** `wordlist/wordlist.txt`
- **Tiered wordlist:** `wordlist/tiered_wordlist.txt`

---

## Conclusion

This comprehensive evaluation demonstrates that **traditional preference elicitation algorithms (CSS, VOI) outperform state-of-the-art LLMs in Wordle-solving efficiency** while maintaining higher success rates. However, LLMs show impressive capability with 89-100% win rates despite being less optimal, suggesting strong emergent reasoning abilities.

The **6-8% efficiency gap** between algorithms (3.8 attempts) and LLMs (4.2 attempts) reflects fundamental differences: algorithms leverage exact information-theoretic optimization while LLMs rely on learned patterns and approximate reasoning.

**Key takeaway:** For structured constraint satisfaction problems like Wordle, purpose-built algorithms remain superior, but LLMs demonstrate remarkable general-purpose problem-solving ability without domain-specific optimization.

---

**Generated:** January 2026
**Evaluation Period:** December 11-12, 2025
**Total Games Evaluated:** 3,300 games across 33 methods
