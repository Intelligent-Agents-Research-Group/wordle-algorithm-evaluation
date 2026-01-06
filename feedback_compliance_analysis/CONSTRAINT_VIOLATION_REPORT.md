# Constraint Violation Analysis Report

**Generated:** January 6, 2026

This report shows whether guesses respect feedback from previous rounds.

---

## What is a Constraint Violation?

A violation occurs when a guess ignores information from previous feedback:

- **Green Violation**: Wrong letter at a position marked as correct
- **Yellow Violation**: Missing a required letter or placing it at a forbidden position
- **Gray Violation**: Using a letter that was marked as not in the word

**Example:**
```
Round 1: HOUSE → Feedback: Y is gray (not in word)
Round 2: PARTY → VIOLATION! Used Y despite feedback
```

---

## Pure LLMs

LLM constraint violations are already tracked in the existing data.

## Pure Algorithms

### Violations by Strategy

| Strategy | Games | Overall Avg Violations |
|----------|-------|------------------------|
| pure_random | 100 | 4.134 |
| random | 100 | 0.000 |
| css | 100 | 0.000 |
| voi | 100 | 0.000 |
| css_then_voi | 100 | 0.000 |
| voi_then_css | 100 | 0.000 |
| css_voi_alternating | 100 | 0.000 |
| voi_css_alternating | 100 | 0.000 |

**Key Finding:** Pure algorithms are designed to respect constraints perfectly, so they should show 0 violations.


---

## Hybrids - Zero-shot Prompting

LLM makes guesses on odd rounds (1, 3, 5), algorithm on even rounds (2, 4, 6)

### Violations by Algorithm

| Algorithm | Games | Overall Avg Violations |
|-----------|-------|------------------------|
| CSS | 900 | 0.039 |
| VOI | 900 | 0.055 |
| RANDOM | 900 | 0.075 |

---

## Hybrids - Chain-of-Thought Prompting

LLM makes guesses on odd rounds (1, 3, 5), algorithm on even rounds (2, 4, 6)

### Violations by Algorithm

| Algorithm | Games | Overall Avg Violations |
|-----------|-------|------------------------|
| RANDOM | 900 | 0.051 |
| VOI | 900 | 0.052 |
| CSS | 903 | 0.038 |

---

## Key Insights

1. **Algorithms**: Should have 0 violations (they're designed to respect all constraints)
2. **LLMs**: May have violations when they fail to track previous feedback
3. **Hybrids**: Compare LLM rounds (1, 3, 5) vs Algorithm rounds (2, 4, 6)
4. **Violation rate**: Percentage of guesses that violated at least one constraint

**Interpretation:** Higher violation rates suggest the approach is not effectively using feedback from previous rounds.

---

**Data Sources:**
- Pure Algorithms: 800 games
- Hybrids Zero-shot: 2,700 games
- Hybrids CoT: 2,800 games
