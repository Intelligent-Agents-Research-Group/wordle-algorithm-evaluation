# Feedback Compliance Analysis - Export Package

**Generated:** January 6, 2026
**Purpose:** Analyze whether approaches respect constraints from previous feedback

---

## Overview

This package contains analysis of **feedback compliance** - tracking whether each guess respects the constraints revealed by previous feedback in Wordle games.

**Total Games Analyzed:** 6,303 games
- Pure Algorithms: 800 games
- Hybrids (Zero-shot): 2,700 games
- Hybrids (Chain-of-Thought): 2,803 games

---

## What is a Constraint Violation?

A **constraint violation** occurs when a guess ignores information from previous feedback:

### Violation Types

1. **Green Violation**
   - Previous feedback showed letter X must be at position Y
   - Current guess has a different letter at position Y
   - Example: Round 1 shows 'A' is green at position 0, but Round 2 guesses "BEATS" (missing 'A' at position 0)

2. **Yellow Violation**
   - Previous feedback showed letter X is in the word but not at position Y
   - Current guess either: (a) doesn't include letter X, or (b) puts X at position Y again
   - Example: Round 1 shows 'R' is yellow at position 2, but Round 2 doesn't include 'R' at all

3. **Gray Violation**
   - Previous feedback showed letter X is NOT in the word
   - Current guess includes letter X
   - Example: Round 1 shows 'Y' is gray (not in word), but Round 2 guesses "PARTY"

### Real Example

```
Round 1: HOUSE → Feedback: -Y--- (O is yellow, others gray)
Round 2: PARTY → VIOLATION!
  - Gray violation: Used H, U, S, E (all marked as not in word)
  - Yellow violation: Missing O or placed O at position 1 again
```

---

## What's Included

### 1. **CONSTRAINT_VIOLATION_REPORT.md**
Summary report showing average violations per round for all strategies.

**Key Metrics:**
- Violations by type (green/yellow/gray)
- Percentage of guesses with violations
- Overall average violations per guess

### 2. **algorithms/**
Pure algorithm data with constraint violation tracking.

**File:** `algorithm_results_with_violations.csv`

**Key Finding:** CSS, VOI, and other intelligent algorithms have **0 violations** (they're designed to perfectly respect all constraints). The "pure_random" strategy has many violations because it doesn't track constraints.

### 3. **hybrids_zero_shot/**
Hybrid LLM-algorithm data with zero-shot prompting (27 files).

**Format:** `alternating_llm_first_<model>_<algorithm>_<timestamp>_with_violations.csv`

**Strategy:** LLM guesses on odd rounds (1, 3, 5), algorithm on even rounds (2, 4, 6)

**Key Finding:** Algorithm rounds (2, 4, 6) have 0 violations, LLM rounds (3, 5) have some violations.

### 4. **hybrids_cot/**
Hybrid LLM-algorithm data with chain-of-thought prompting (28 files).

**Format:** `alternating_llm_first_<model>_<algorithm>_cot_<timestamp>_with_violations.csv`

**Key Finding:** Similar pattern to zero-shot - algorithm rounds perfect, LLM rounds have occasional violations.

### 5. **scripts/**
Python scripts used to generate this analysis.

- `calculate_constraint_violations.py` - Processes raw game data to calculate violations
- `analyze_constraint_violations.py` - Generates summary report

---

## Data Format

Each CSV file contains the original game data PLUS these new columns for each round (2-6):

**Note:** Round 1 is excluded because the first guess can't violate anything (no prior feedback exists).

| Column | Description |
|--------|-------------|
| `violated_green_N` | Number of green constraint violations in round N |
| `violated_yellow_N` | Number of yellow constraint violations in round N |
| `violated_gray_N` | Number of gray constraint violations in round N |
| `total_violations_N` | Total violations in round N (sum of above) |

**Example:**
```
Round 3: violated_green_3=0, violated_yellow_3=1, violated_gray_3=2, total_violations_3=3
```
This means Round 3 had 3 total violations: 1 yellow violation and 2 gray violations.

---

## Key Findings

### Pure Algorithms

| Strategy | Overall Avg Violations |
|----------|------------------------|
| CSS, VOI, css_then_voi, etc. | 0.000 |
| pure_random | 4.134 |

**Insight:** Intelligent algorithms (CSS, VOI) perfectly respect all constraints. The "pure_random" strategy violates constraints because it selects randomly without tracking feedback.

### Pure LLMs (Existing Data)

- **Total guesses:** 10,529
- **Average violations per guess:** 0.030
- **Guesses with violations:** 2.9%
- **Almost all violations are gray violations** (using letters marked as not in word)

**Insight:** LLMs mostly respect constraints but occasionally use letters that were marked as gray.

### Hybrids - Zero-shot

| Round | Who Guessed | Avg Violations | % with Violations |
|-------|-------------|----------------|-------------------|
| 2 | Algorithm | 0.000 | 0.0% |
| 3 | LLM | 0.223 | 8.2% |
| 4 | Algorithm | 0.000 | 0.0% |
| 5 | LLM | 0.058 | 1.7% |
| 6 | Algorithm | 0.000 | 0.0% |

**Insight:**
- Algorithm rounds have perfect compliance (0 violations)
- LLM rounds have occasional violations, especially in Round 3 (8.2% of guesses)
- Violations decrease in later rounds (8.2% → 1.7%)

### Hybrids - Chain-of-Thought

| Round | Who Guessed | Avg Violations | % with Violations |
|-------|-------------|----------------|-------------------|
| 2 | Algorithm | 0.000 | 0.0% |
| 3 | LLM | 0.180 | 6.3% |
| 4 | Algorithm | 0.000 | 0.0% |
| 5 | LLM | 0.056 | 1.2% |
| 6 | Algorithm | 0.000 | 0.0% |

**Insight:** Similar pattern to zero-shot, but slightly better (6.3% vs 8.2% in Round 3).

---

## Comparison: LLM Violations by Context

| Context | Avg Violations per LLM Guess | Notes |
|---------|------------------------------|-------|
| Pure LLM | 0.030 | All guesses are LLM |
| Hybrid Zero-shot (Round 3) | 0.223 | LLM after algorithm guess |
| Hybrid CoT (Round 3) | 0.180 | LLM after algorithm guess |

**Interesting:** LLMs have MORE violations in hybrid mode (Round 3) than in pure mode. This suggests they may struggle more when alternating with algorithms.

---

## How to Use This Data

### Quick Start
1. Read `CONSTRAINT_VIOLATION_REPORT.md` for aggregated statistics
2. Explore individual CSV files for game-by-game analysis
3. Run scripts to regenerate analysis if needed

### Example Analysis Questions
- Do LLMs respect feedback as well as algorithms?
- Which types of constraints are most often violated (green/yellow/gray)?
- Does prompting strategy (zero-shot vs CoT) affect constraint compliance?
- Do violations decrease in later rounds as the word space narrows?

### Reproduction
To regenerate this analysis:
```bash
python scripts/calculate_constraint_violations.py  # Processes CSVs
python scripts/analyze_constraint_violations.py    # Generates report
```

---

## Interpretation

### What Low Violations Mean
- The approach is effectively using feedback from previous rounds
- Strong constraint satisfaction reasoning
- Good "memory" of what has been ruled out

### What High Violations Mean
- The approach is ignoring or forgetting previous feedback
- Weak constraint tracking
- May indicate the approach is "guessing randomly"

**Critical Insight:** Violations are a direct measure of whether an approach is actually doing iterative reasoning. High violation rates suggest the approach is not systematically using feedback.

---

## Contact

For questions about this analysis, contact the research team.

**Repository:** https://github.com/Intelligent-Agents-Research-Group/wordle-algorithm-evaluation
