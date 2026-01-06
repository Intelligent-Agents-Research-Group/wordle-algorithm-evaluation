# Convergence Analysis Summary: LLM Iterative Reasoning Ability

## Research Question
**How good are LLMs at iterative reasoning?**

We measure this through:
1. Convergence to answer (how distances decrease with each guess)
2. Search space pruning (how many candidates are eliminated)

---

## Key Findings

### 1. Convergence Rate Comparison

| Category | Hamming Decrease/Round | Total % Decrease | Efficiency vs Algorithm |
|----------|------------------------|------------------|------------------------|
| **Pure Algorithms** | 0.3017 | 33.32% | 100% (baseline) |
| **Hybrids (Zero-shot)** | 0.8159 | 90.04% | **270.4%** |
| **Hybrids (CoT)** | 0.8462 | 91.55% | **280.5%** |

**Key Insight**: Hybrids converge 2.7x faster than pure algorithms, showing that LLMs provide significant value in the iterative reasoning process.

---

### 2. Distance Convergence Trajectory

#### Pure Algorithms (N=800 games)
```
Round 1: 4.53 → Round 3: 2.17 → Round 6: 3.02 (Hamming)
Total improvement: 1.51 units (33.3%)
```

#### Hybrids - Zero-shot (N=2,700 games)
```
Round 1: 4.53 → Round 3: 2.11 → Round 6: 0.45 (Hamming)
Total improvement: 4.08 units (90.0%)
```

#### Hybrids - CoT (N=2,703 games)
```
Round 1: 4.62 → Round 3: 2.19 → Round 6: 0.39 (Hamming)
Total improvement: 4.23 units (91.6%)
```

**Key Insight**: Hybrids show monotonic convergence to the answer, while pure algorithms show an increase in distance at rounds 5-6 (likely due to survivor bias - only difficult games remain).

---

### 3. Search Space Pruning (Pure LLMs)

#### Chain-of-Thought (N=5,330 games)
| Attempt | Candidates Before | Candidates After | % Reduction | Info Gain (bits) |
|---------|-------------------|------------------|-------------|------------------|
| 1 | 5,629 | 453 | **91.95%** | 5.16 |
| 2 | 454 | 30 | **93.39%** | 4.29 |
| 3 | 31 | 3 | **90.48%** | 2.33 |
| 4 | 3 | 1 | 68.21% | 0.76 |
| 5 | 1 | 1 | 49.51% | 0.29 |
| 6 | 1 | 0 | 36.75% | 0.28 |

**Average: 71.71% reduction per attempt**

#### Zero-shot (N=5,199 games)
| Attempt | Candidates Before | Candidates After | % Reduction | Info Gain (bits) |
|---------|-------------------|------------------|-------------|------------------|
| 1 | 5,629 | 440 | **92.19%** | 5.18 |
| 2 | 440 | 29 | **93.56%** | 4.42 |
| 3 | 30 | 3 | **88.68%** | 2.11 |
| 4 | 4 | 1 | 71.25% | 0.78 |
| 5 | 1 | 1 | 53.78% | 0.37 |
| 6 | 1 | 0 | 44.28% | 0.21 |

**Average: 73.96% reduction per attempt**

**Key Insights**:
- LLMs excel at initial pruning (92% in first attempt)
- Pruning efficiency declines as search space narrows (expected)
- Zero-shot slightly outperforms CoT in pruning efficiency (73.96% vs 71.71%)
- Both show diminishing information gain (expected Bayesian behavior)

---

### 4. Cumulative Information Gain

Both prompting strategies accumulate ~13 bits of information across 6 attempts:

- **Chain-of-thought**: 13.11 bits total
- **Zero-shot**: 13.07 bits total

This represents reduction from 5,629 candidates (log2(5629) ≈ 12.46 bits of uncertainty) to the single correct answer.

---

### 5. Strategy Alternation Patterns (Hybrids)

The hybrid approach follows a strict alternation:
- **Odd rounds (1, 3, 5)**: LLM makes guess
- **Even rounds (2, 4, 6)**: Algorithm (CSS) makes guess

This alternation ensures:
1. LLM provides creative/exploratory guesses
2. Algorithm provides optimal information-theoretic guesses
3. Each agent benefits from the other's constraints

---

## Answering the Research Question

### How good are LLMs at iterative reasoning?

**Evidence of Strong Iterative Reasoning:**

1. **Systematic Belief Updating**
   - LLMs show 92% search space reduction on first guess
   - Maintain 70%+ pruning efficiency through attempts 2-3
   - Cumulative information gain follows expected Bayesian pattern

2. **Convergence Performance**
   - When combined with algorithms, achieve 90%+ convergence (vs 33% for pure algorithms)
   - Show monotonic distance decrease across all rounds
   - CoT improves convergence by 3.7% over zero-shot

3. **Search Space Management**
   - Average 72-74% search space reduction per attempt
   - Information gain decreases appropriately as uncertainty reduces
   - Both zero-shot and CoT show similar pruning effectiveness

**Limitations:**

1. **Pruning Consistency**
   - Higher variability than pure algorithms (std: 19-22 vs algorithm consistency)
   - Efficiency declines more steeply in later rounds

2. **CoT Impact**
   - CoT shows marginal improvement in convergence rate (+3.7%)
   - Slightly lower pruning consistency than zero-shot
   - May add reasoning overhead without proportional benefit

---

## Conclusion

**LLMs demonstrate strong iterative reasoning ability**, evidenced by:
- Efficient search space pruning (92% first attempt, 72% average)
- Systematic information gain accumulation (~13 bits)
- Superior convergence when combined with algorithms (270% of baseline)

**The hybrid approach significantly outperforms pure algorithms**, suggesting that:
1. LLM reasoning complements algorithmic optimization
2. Iterative belief updating in LLMs is robust and systematic
3. The combination leverages both creative exploration (LLM) and optimal exploitation (algorithm)

**Chain-of-thought prompting provides modest benefits** (+3.7% convergence improvement), suggesting that:
- Explicit reasoning may help maintain consistency
- The benefit is marginal in this well-defined constraint satisfaction task
- Zero-shot LLMs already demonstrate strong iterative reasoning without explicit prompting

---

## Data Sources

- **Pure Algorithms**: 800 games across 4 algorithms
- **Pure LLMs**: 10,529 games across 26 model configurations (14 CoT, 12 zero-shot)
- **Hybrids (Zero-shot)**: 2,700 games across 27 configurations (9 models × 3 algorithm strategies)
- **Hybrids (CoT)**: 2,703 games across 28 configurations (9 models × 3 algorithm strategies)

**Total games analyzed**: 15,932 Wordle games

---

Generated: 2026-01-06
Analysis script: `/Users/kevin/Desktop/wordle/analyze_convergence.py`
Full results: `/Users/kevin/Desktop/wordle/convergence_analysis.txt`
