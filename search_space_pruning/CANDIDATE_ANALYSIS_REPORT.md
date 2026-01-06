# Candidate Count Analysis Report

**Generated:** January 6, 2026

This report shows how many valid word candidates remain after each guess.

---

## Pure Algorithms

Starting with 5,629 possible words, how do pure algorithms prune the search space?

### Summary Table

| Strategy | Round 1 | Round 2 | Round 3 | Round 4 | Round 5 | Round 6 |
|----------|---------|---------|---------|---------|---------|----------|
| pure_random | 496 | 102 | 20 | 8 | 4 | 2 |
| random | 505 | 40 | 6 | 2 | 2 | 1 |
| css | 188 | 10 | 2 | 1 | 2 | 1 |
| voi | 411 | 12 | 2 | 1 | 1 | 1 |
| css_then_voi | 169 | 8 | 2 | 1 | 1 | 2 |
| voi_then_css | 320 | 12 | 2 | 1 | 1 | 1 |
| css_voi_alternating | 178 | 9 | 2 | 1 | 1 | 1 |
| voi_css_alternating | 171 | 9 | 2 | 1 | 2 | 1 |

### Reduction Rates

| Strategy | Round 1 | Round 2 | Round 3 | Round 4 | Round 5 | Round 6 |
|----------|---------|---------|---------|---------|---------|----------|
| pure_random | 91.2% | 74.6% | 58.5% | 32.4% | 22.9% | 16.4% |
| random | 91.0% | 87.5% | 70.2% | 49.7% | 31.4% | 26.0% |
| css | 96.7% | 91.2% | 65.3% | 30.5% | 24.7% | 39.3% |
| voi | 92.7% | 93.8% | 63.4% | 37.3% | 15.4% | 15.0% |
| css_then_voi | 97.0% | 90.8% | 60.3% | 26.9% | 22.1% | 23.8% |
| voi_then_css | 94.3% | 92.0% | 66.0% | 28.3% | 23.6% | 16.7% |
| css_voi_alternating | 96.8% | 91.6% | 63.2% | 29.0% | 23.5% | 20.0% |
| voi_css_alternating | 97.0% | 89.7% | 62.4% | 27.0% | 16.5% | 36.2% |

---

## Hybrids - Zero-shot Prompting

LLM makes guesses on odd rounds (1, 3, 5), algorithm on even rounds (2, 4, 6)

### Summary by Algorithm

| Algorithm | Games | Round 1 | Round 2 | Round 3 | Round 4 | Round 5 | Round 6 |
|-----------|-------|---------|---------|---------|---------|---------|----------|
| CSS | 900 | 308 | 14 | 4 | 2 | 1 | 1 |
| VOI | 900 | 304 | 22 | 5 | 2 | 2 | 2 |
| RANDOM | 900 | 368 | 34 | 7 | 3 | 2 | 2 |

### Reduction Rates by Algorithm

| Algorithm | Round 1 | Round 2 | Round 3 | Round 4 | Round 5 | Round 6 |
|-----------|---------|---------|---------|---------|---------|----------|
| CSS | 94.5% | 91.0% | 60.2% | 40.9% | 23.9% | 25.8% |
| VOI | 94.6% | 87.3% | 63.2% | 42.8% | 28.2% | 24.2% |
| RANDOM | 93.5% | 84.8% | 65.9% | 43.3% | 33.2% | 25.9% |

---

## Hybrids - Chain-of-Thought Prompting

LLM makes guesses on odd rounds (1, 3, 5), algorithm on even rounds (2, 4, 6)

### Summary by Algorithm

| Algorithm | Games | Round 1 | Round 2 | Round 3 | Round 4 | Round 5 | Round 6 |
|-----------|-------|---------|---------|---------|---------|---------|----------|
| RANDOM | 900 | 465 | 42 | 6 | 2 | 2 | 1 |
| CSS | 903 | 423 | 15 | 3 | 2 | 1 | 1 |
| VOI | 900 | 437 | 27 | 5 | 2 | 2 | 1 |

### Reduction Rates by Algorithm

| Algorithm | Round 1 | Round 2 | Round 3 | Round 4 | Round 5 | Round 6 |
|-----------|---------|---------|---------|---------|---------|----------|
| RANDOM | 91.7% | 87.0% | 70.6% | 45.6% | 33.2% | 22.8% |
| CSS | 92.5% | 92.9% | 62.0% | 40.2% | 24.1% | 21.7% |
| VOI | 92.2% | 88.7% | 68.1% | 43.1% | 28.9% | 26.2% |

---

## Key Insights

1. **Starting point:** All approaches begin with 5,629 possible candidates
2. **First guess:** Observe how effectively each approach prunes the initial search space
3. **Convergence:** Track how quickly candidates decrease toward 1 (the answer)
4. **Strategy differences:** Compare how CSS, VOI, and Random differ in pruning patterns
5. **Hybrid effects:** See how LLM+algorithm alternation affects search space reduction

---

**Data Sources:**
- Pure Algorithms: 800 games (7 strategies × 100 games)
- Hybrids Zero-shot: 2,700 games (9 models × 3 algorithms × 100 games)
- Hybrids CoT: 2,800 games (9 models × 3 algorithms × 100 games + extras)
