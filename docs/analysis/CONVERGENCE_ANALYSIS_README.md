# Convergence Analysis: LLM Iterative Reasoning Study

## Overview

This analysis investigates **how good LLMs are at iterative reasoning** by examining convergence patterns and search space pruning across three experimental categories:

1. **Pure Algorithms** (baseline)
2. **Pure LLMs** (chain-of-thought vs zero-shot)
3. **Hybrid Approaches** (LLM + algorithm alternation)

---

## Files Generated

### Analysis Scripts
- **`analyze_convergence.py`** - Main analysis script that processes all experimental data
- **`plot_convergence_trajectories.py`** - Visualization script for convergence patterns

### Results
- **`convergence_analysis.txt`** - Comprehensive text analysis (324 lines)
- **`convergence_summary.md`** - Executive summary with key findings
- **`convergence_trajectories.png/pdf`** - 9-panel visualization of convergence patterns
- **`llm_reasoning_patterns.png/pdf`** - 4-panel visualization of LLM reasoning behavior

---

## Key Findings

### 1. Convergence Performance

| Approach | Convergence Rate | Total Decrease | Relative to Algorithm |
|----------|-----------------|----------------|----------------------|
| **Pure Algorithms** | 0.30 Hamming/round | 33.3% | 100% (baseline) |
| **Hybrids (Zero-shot)** | 0.82 Hamming/round | 90.0% | **270.4%** |
| **Hybrids (CoT)** | 0.85 Hamming/round | 91.6% | **280.5%** |

**Interpretation**: Hybrids converge nearly 3x faster than pure algorithms, demonstrating that LLMs add substantial value to iterative reasoning.

---

### 2. Search Space Pruning (Pure LLMs)

#### Average Performance
- **Chain-of-Thought**: 71.7% reduction per attempt
- **Zero-shot**: 74.0% reduction per attempt

#### First Attempt
- **Chain-of-Thought**: 91.95% reduction (5,629 → 453 candidates)
- **Zero-shot**: 92.19% reduction (5,629 → 440 candidates)

#### Information Gain
- **Cumulative**: ~13 bits across 6 attempts
- **Pattern**: Diminishing returns (expected Bayesian behavior)
  - Attempt 1: ~5.2 bits
  - Attempt 2: ~4.4 bits
  - Attempt 3: ~2.2 bits
  - Attempts 4-6: <1 bit each

**Interpretation**: LLMs show strong initial reasoning (92% pruning) with systematic belief updating that follows expected information-theoretic patterns.

---

### 3. Convergence Trajectories

#### Pure Algorithms (N=800 games)
```
Round 1: 4.53 → Round 3: 2.17 → Round 6: 3.02
Problem: Distance increases in late rounds (survivor bias)
```

#### Hybrids - Zero-shot (N=2,700 games)
```
Round 1: 4.53 → Round 3: 2.11 → Round 6: 0.45
Achievement: Monotonic convergence to solution
```

#### Hybrids - CoT (N=2,703 games)
```
Round 1: 4.62 → Round 3: 2.19 → Round 6: 0.39
Achievement: Best final convergence (91.6% total)
```

**Interpretation**: Hybrids show consistent monotonic convergence, while pure algorithms struggle with difficult cases in later rounds.

---

### 4. Strategy Alternation Pattern

The hybrid approach follows strict alternation:
- **Odd rounds (1, 3, 5)**: LLM makes guess
- **Even rounds (2, 4, 6)**: Algorithm (CSS) makes guess

This ensures:
1. LLM provides exploratory/creative guesses
2. Algorithm provides optimal information-theoretic guesses
3. Complementary strengths are leveraged

---

## Research Question Answer

### How good are LLMs at iterative reasoning?

**Answer: Very good, with caveats.**

#### Evidence of Strong Iterative Reasoning:

1. **Systematic Belief Updating**
   - 92% search space reduction on first attempt
   - Maintains 70%+ pruning efficiency through attempts 2-3
   - Information gain follows expected Bayesian decline pattern

2. **Convergence Performance**
   - Achieves 90%+ total convergence when combined with algorithms
   - Shows monotonic distance decrease (vs algorithm volatility)
   - CoT provides modest improvement (+3.7% over zero-shot)

3. **Search Space Management**
   - Average 72-74% search space reduction per attempt
   - Cumulative ~13 bits information gain
   - Both zero-shot and CoT show similar effectiveness

#### Limitations:

1. **Higher Variability**
   - More inconsistent than pure algorithms (std: 19-22)
   - Pruning efficiency declines steeply in later rounds

2. **CoT Marginal Benefit**
   - Only +3.7% improvement over zero-shot
   - Suggests task may not benefit much from explicit reasoning
   - Zero-shot LLMs already reason well in constraint satisfaction

---

## Dataset Summary

| Category | Files | Games | Key Metric |
|----------|-------|-------|------------|
| **Pure Algorithms** | 1 | 800 | Hamming/Levenshtein distance by round |
| **Pure LLMs (CoT)** | 14 | 5,330 | Search space pruning, info gain |
| **Pure LLMs (Zero-shot)** | 12 | 5,199 | Search space pruning, info gain |
| **Hybrids (Zero-shot)** | 27 | 2,700 | Distance convergence, strategy mix |
| **Hybrids (CoT)** | 28 | 2,703 | Distance convergence, strategy mix |
| **TOTAL** | **82** | **15,932** | - |

---

## Metrics Explained

### Convergence Metrics

1. **Hamming Distance**: Number of letter positions that differ between guess and target
   - Example: "CRANE" vs "TRACE" = 2 (C→T, E→E positions differ)

2. **Levenshtein Distance**: Minimum edit operations (insert/delete/replace) needed
   - Similar to Hamming but allows insertions/deletions

3. **Convergence Rate**: Average decrease in distance per round
   - Higher = faster approach to solution

4. **Total % Decrease**: (Initial distance - Final distance) / Initial distance × 100
   - Measures overall convergence efficiency

### Search Space Metrics

1. **Candidates Before/After**: Number of valid words before/after applying constraints
   - Shows how much uncertainty is reduced

2. **Reduction %**: (Candidates eliminated / Candidates before) × 100
   - Higher = more effective pruning

3. **Information Gain (bits)**: log2(Candidates before / Candidates after)
   - Measures uncertainty reduction in information-theoretic terms
   - Total uncertainty in Wordle ≈ log2(5,629) ≈ 12.46 bits

---

## Methodology

### Data Sources

1. **Algorithms**: `/Users/kevin/Desktop/wordle/results/algorithms/raw data/`
   - Single CSV with distance metrics per round

2. **LLMs**: `/Users/kevin/Desktop/wordle/results/llms/raw data/`
   - 26 CSVs (14 CoT, 12 zero-shot)
   - Long format with attempt-level metrics

3. **Hybrids**: `/Users/kevin/Desktop/wordle/results/hybrids/stage3*/raw data/`
   - 55 CSVs (27 zero-shot, 28 CoT)
   - Distance metrics + strategy used per round

### Analysis Process

1. **Load and Parse Data**
   - Read all CSVs across three categories
   - Extract distance/pruning metrics by round/attempt

2. **Aggregate Metrics**
   - Calculate mean/std for each round
   - Group by prompting strategy (CoT vs zero-shot)
   - Compute convergence rates

3. **Comparative Analysis**
   - Compare convergence trajectories
   - Analyze search space pruning patterns
   - Evaluate information gain accumulation

4. **Visualization**
   - Create 9-panel convergence overview
   - Create 4-panel LLM reasoning analysis

---

## Reproducing the Analysis

### Prerequisites
```bash
pip install pandas numpy matplotlib seaborn
```

### Run Analysis
```bash
# Generate full text analysis
python /Users/kevin/Desktop/wordle/analyze_convergence.py

# Generate visualizations
python /Users/kevin/Desktop/wordle/plot_convergence_trajectories.py
```

### Expected Output
- `convergence_analysis.txt` - Full numerical results
- `convergence_trajectories.png/pdf` - Main visualization
- `llm_reasoning_patterns.png/pdf` - LLM-specific analysis

---

## Visualization Guide

### Convergence Trajectories (9 panels)

**Panel A-B**: Distance trajectories by round (Hamming & Levenshtein)
- Shows how each approach converges to solution
- Pure algorithms show increase in rounds 5-6 (survivor bias)
- Hybrids show monotonic convergence

**Panel C**: Convergence rate comparison
- Bar chart of average distance decrease per round
- Hybrids achieve 2.7-2.8x algorithm rate

**Panel D**: Search space reduction (log scale)
- LLM candidate counts before/after each attempt
- Shows dramatic first-attempt reduction (92%)

**Panel E**: Pruning efficiency by attempt
- Percentage of candidates eliminated each attempt
- Shows declining efficiency (expected pattern)

**Panel F**: Information gain per attempt
- Bits of uncertainty reduced each attempt
- Follows expected Bayesian decline

**Panel G**: Cumulative information gain
- Running total of information accumulated
- Approaches theoretical maximum (~12.5 bits)

**Panel H**: Total convergence efficiency
- Percentage decrease from initial to final distance
- Hybrids achieve 90%+ vs algorithms' 33%

**Panel I**: Relative performance
- Performance as percentage of algorithm baseline
- Hybrids: 270-280% of algorithm performance

### LLM Reasoning Patterns (4 panels)

**Panel A**: Candidates eliminated per attempt
- Absolute number of candidates pruned
- Log scale shows exponential decrease

**Panel B**: Pruning efficiency comparison (CoT vs Zero-shot)
- Side-by-side bars for each attempt
- Shows minimal difference between strategies

**Panel C**: Information gain distribution
- Bar chart of bits gained per attempt
- Shows front-loaded information accumulation

**Panel D**: Efficiency decline rate
- How quickly pruning effectiveness decreases
- Reveals when LLMs struggle (later rounds)

---

## Implications

### For LLM Research
1. **Iterative reasoning capability confirmed**: LLMs show systematic belief updating
2. **CoT benefit is task-dependent**: Marginal improvement in well-defined constraint tasks
3. **Zero-shot competence**: Strong performance without explicit reasoning prompts

### For Hybrid Systems
1. **Complementary strengths**: LLMs + algorithms outperform either alone
2. **Alternating strategies work**: Simple round-robin alternation is effective
3. **Synergy exists**: 270% performance vs algorithm baseline

### For Wordle Strategy
1. **LLM first-guess value**: 92% search space reduction is excellent
2. **Algorithmic mid-game**: CSS excels at exploiting constraints
3. **Hybrid optimal**: Combine creative exploration with optimal exploitation

---

## Future Directions

1. **Finer-grained analysis**
   - Per-model convergence patterns
   - Algorithm strategy comparison (CSS vs VOI vs Random)
   - Word difficulty effects on convergence

2. **Additional metrics**
   - Constraint violation rates
   - Guess optimality scores
   - Adaptive strategy selection

3. **Alternative hybrid strategies**
   - Dynamic switching based on search space size
   - LLM confidence-based delegation
   - Multi-agent consensus approaches

---

## Citation

If you use this analysis, please cite:

```
Convergence Analysis: LLM Iterative Reasoning in Wordle
Dataset: 15,932 games across 82 experimental configurations
Date: January 2026
Repository: /Users/kevin/Desktop/wordle/
```

---

## Contact & Questions

For questions about this analysis or access to the underlying data:
- Full results: `/Users/kevin/Desktop/wordle/convergence_analysis.txt`
- Summary: `/Users/kevin/Desktop/wordle/convergence_summary.md`
- Visualizations: PNG/PDF files in the same directory

---

Generated: 2026-01-06
Last Updated: 2026-01-06
