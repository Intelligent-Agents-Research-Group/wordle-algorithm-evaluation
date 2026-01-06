# Search Space Pruning Analysis - Export Package

**Generated:** January 6, 2026
**Purpose:** Share search space pruning analysis with advisor

---

## Overview

This package contains analysis of **search space pruning** - tracking how many valid word candidates remain after each guess in Wordle games across all experiments (algorithms and hybrids).

**Total Games Analyzed:** 6,303 games
- Pure Algorithms: 800 games
- Hybrids (Zero-shot): 2,700 games
- Hybrids (Chain-of-Thought): 2,803 games

---

## What's Included

### 1. **CANDIDATE_ANALYSIS_REPORT.md**
Summary report showing average candidates remaining after each round for all strategies.

**Key Metrics:**
- Candidates before each round
- Candidates after each round
- Reduction rate (% eliminated)

### 2. **algorithms/**
Pure algorithm data with candidate counts.

**File:** `algorithm_results_with_candidates.csv`

**Strategies included:**
- CSS (Constraint Satisfaction Search)
- VOI (Value of Information)
- Random
- Hybrid combinations (css_then_voi, voi_then_css, etc.)

### 3. **hybrids_zero_shot/**
Hybrid LLM-algorithm data with zero-shot prompting (27 files).

**Format:** `alternating_llm_first_<model>_<algorithm>_<timestamp>_with_candidates.csv`

**Strategy:** LLM guesses on odd rounds (1, 3, 5), algorithm on even rounds (2, 4, 6)

**Models:** 9 different LLMs tested
**Algorithms:** CSS, VOI, Random

### 4. **hybrids_cot/**
Hybrid LLM-algorithm data with chain-of-thought prompting (28 files).

**Format:** `alternating_llm_first_<model>_<algorithm>_cot_<timestamp>_with_candidates.csv`

**Strategy:** Same alternating pattern as zero-shot, but with CoT prompting

### 5. **scripts/**
Python scripts used to generate this analysis.

- `calculate_candidates.py` - Processes raw game data to calculate candidate counts
- `analyze_candidate_statistics.py` - Generates summary report

---

## Data Format

Each CSV file contains the original game data PLUS these new columns for each round (1-6):

| Column | Description |
|--------|-------------|
| `candidates_before_N` | Number of valid words before round N guess |
| `candidates_after_N` | Number of valid words after receiving feedback from round N |
| `reduction_rate_N` | Percentage of candidates eliminated in round N |

**Example:**
```
Round 1: candidates_before_1=5629, candidates_after_1=188, reduction_rate_1=96.65%
Round 2: candidates_before_2=188, candidates_after_2=10, reduction_rate_2=91.23%
Round 3: candidates_before_3=10, candidates_after_3=2, reduction_rate_3=65.27%
```

---

## Key Findings

### Pure Algorithms - First Guess Efficiency

| Strategy | Starting | After Round 1 | Reduction |
|----------|----------|---------------|-----------|
| CSS | 5,629 | 188 | 96.7% |
| VOI | 5,629 | 411 | 92.7% |
| Random | 5,629 | 505 | 91.0% |

**Insight:** CSS is most efficient at pruning search space on first guess.

### Hybrids - LLM Performance on First Guess

| Approach | Starting | After Round 1 | Reduction |
|----------|----------|---------------|-----------|
| Zero-shot + CSS | 5,629 | 308 | 94.5% |
| CoT + CSS | 5,629 | 423 | 92.5% |

**Insight:** LLMs are less efficient than pure CSS but still achieve >92% reduction.

### Convergence Pattern

All approaches follow a similar pattern:
1. **Round 1:** Massive reduction (91-97%)
2. **Round 2:** Strong reduction (87-93%)
3. **Round 3-6:** Diminishing reductions as candidates approach 1 (the answer)

---

## How to Use This Data

### Quick Start
1. Read `CANDIDATE_ANALYSIS_REPORT.md` for aggregated statistics
2. Explore individual CSV files for game-by-game analysis
3. Run scripts to regenerate analysis if needed

### Example Analysis Questions
- How does search space pruning differ between CSS and VOI?
- Do LLMs prune the search space differently than algorithms?
- What's the average convergence rate by strategy?
- How does prompting (zero-shot vs CoT) affect candidate elimination?

### Reproduction
To regenerate this analysis:
```bash
python scripts/calculate_candidates.py      # Processes CSVs
python scripts/analyze_candidate_statistics.py  # Generates report
```

---

## Contact

For questions about this analysis, contact the research team.

**Repository:** https://github.com/Intelligent-Agents-Research-Group/wordle-algorithm-evaluation
