# Wordle & Mastermind: Algorithm and LLM Evaluation

**Research Project:** Iterative Reasoning in Large Language Models
**Repository:** https://github.com/Intelligent-Agents-Research-Group/wordle-algorithm-evaluation
**Last Updated:** February 12, 2026

---

## Overview

This project evaluates iterative reasoning capabilities of Large Language Models (LLMs) using **Wordle** and **Mastermind** as testbeds. We analyze how LLMs and algorithms:
1. **Converge to solutions** - How distances to target decrease with each guess
2. **Prune search space** - How effectively approaches eliminate candidates
3. **Respect constraints** - Whether guesses use feedback from previous rounds
4. **Handle control handoff** - Whether hybrid LLM-algorithm systems introduce systematic costs

**Total Games Evaluated:** 45,000+ games across multiple configurations

### Two Testbeds

| Testbed | Search Space | Feedback Type | Key Characteristic |
|---------|-------------|---------------|-------------------|
| **Wordle** | 5,629 words | Green/Yellow/Gray | Semantic priors, word frequency |
| **Mastermind** | 1,296 codes | Black/White pegs | Pure constraint satisfaction |

Mastermind provides a complementary testbed without semantic biases, allowing us to isolate algorithmic reasoning from language knowledge.

---

## Project Structure

### 📊 Main Analysis Reports
All comprehensive analysis reports are in [`docs/analysis/`](docs/analysis/):

- **[COMPREHENSIVE_SUMMARY_STATISTICS.md](docs/analysis/COMPREHENSIVE_SUMMARY_STATISTICS.md)** - Complete overview of all experiments
- **[RESEARCH_NARRATIVE.md](docs/analysis/RESEARCH_NARRATIVE.md)** - Detailed research findings and insights
- **[CONVERGENCE_ANALYSIS_README.md](docs/analysis/CONVERGENCE_ANALYSIS_README.md)** - Methodology for convergence analysis
- **[convergence_summary.md](docs/analysis/convergence_summary.md)** - Summary of convergence findings
- **[CANDIDATE_ANALYSIS_REPORT.md](docs/analysis/CANDIDATE_ANALYSIS_REPORT.md)** - Search space pruning analysis
- **[CONSTRAINT_VIOLATION_REPORT.md](docs/analysis/CONSTRAINT_VIOLATION_REPORT.md)** - Feedback compliance analysis

### 📦 Export Packages for Sharing

1. **[search_space_pruning/](search_space_pruning/)** - Complete package showing how the word list shrinks from 5,629 → 1
   - Tracks candidates remaining after each guess
   - 6,303 games analyzed
   - Includes raw data + scripts + summary report

2. **[feedback_compliance_analysis/](feedback_compliance_analysis/)** - Complete package showing constraint violations
   - Tracks whether guesses respect previous feedback
   - 6,303 games analyzed
   - Includes raw data + scripts + summary report

### 📁 Data & Results

- **[results/](results/)** - Raw experimental data
  - `algorithms/` - Pure algorithm results (CSS, VOI, Random)
  - `llms/` - Pure LLM results (11 models × 2 prompting strategies)
  - `hybrids/` - Hybrid LLM-algorithm results (stage 1, 2, 3, 3-cot)

### 🔧 Code

- **[algorithms/](algorithms/)** - Algorithm implementations (CSS, VOI, Random)
- **[engines/](engines/)** - Wordle environment and agent framework
- **[scripts/](scripts/)** - Evaluation and analysis scripts

### 📖 Documentation

- **[docs/](docs/)** - General documentation
  - `algorithms.md` - Algorithm descriptions
  - `engines.md` - Engine documentation
  - `evaluations.md` - Evaluation methodology
  - `wordlist.md` - Word list information
  - `Hybrids/` - Hybrid experiment documentation

---

## Quick Start

### View Results

1. **Overall Summary:** [docs/analysis/COMPREHENSIVE_SUMMARY_STATISTICS.md](docs/analysis/COMPREHENSIVE_SUMMARY_STATISTICS.md)
2. **Research Findings:** [docs/analysis/RESEARCH_NARRATIVE.md](docs/analysis/RESEARCH_NARRATIVE.md)
3. **Search Space Pruning:** [search_space_pruning/README.md](search_space_pruning/README.md)
4. **Constraint Violations:** [feedback_compliance_analysis/README.md](feedback_compliance_analysis/README.md)

### Run Experiments

```bash
# Pure algorithms
python scripts/algorithms_evaluation.py

# Pure LLMs
python scripts/llm_evaluation.py

# Hybrids
python scripts/hybrids/alternating_hybrid.py
```

### Run Analysis

```bash
# Search space pruning
python scripts/calculate_candidates.py
python scripts/analyze_candidate_statistics.py

# Constraint violations
python scripts/calculate_constraint_violations.py
python scripts/analyze_constraint_violations.py

# Convergence analysis
python analyze_convergence.py
python plot_convergence_trajectories.py
```

---

## Key Findings

### 1. Search Space Pruning

**How effectively do approaches eliminate word candidates?**

| Approach | First Guess Reduction | Notes |
|----------|----------------------|-------|
| CSS Algorithm | 96.7% (5,629 → 188) | Best single approach |
| VOI Algorithm | 92.7% (5,629 → 411) | Strong information gain |
| LLM Zero-shot | 94.5% (5,629 → 308) | Surprisingly effective |
| LLM Chain-of-Thought | 92.5% (5,629 → 423) | Slightly worse than zero-shot |

**Insight:** LLMs approach algorithmic efficiency in search space pruning, achieving 92-94% reduction on first guess.

### 2. Convergence to Solutions

**How fast do approaches reach the answer?**

| Approach | Convergence Rate | Total Distance Decrease |
|----------|------------------|------------------------|
| Pure Algorithms | 0.30 Hamming/round | 33.3% |
| Hybrids (Zero-shot) | 0.82 Hamming/round | 90.0% (**270% of algorithm**) |
| Hybrids (CoT) | 0.85 Hamming/round | 91.6% (**280% of algorithm**) |

**Insight:** Hybrids converge 2.7× faster than pure algorithms, demonstrating synergy between LLM exploration and algorithmic exploitation.

### 3. Feedback Compliance

**Do approaches respect constraints from previous rounds?**

| Approach | Violation Rate | Notes |
|----------|---------------|-------|
| CSS/VOI Algorithms | 0.0% | Perfect compliance by design |
| Pure LLMs | 2.9% | Occasional gray violations |
| Hybrid LLM rounds | 6-8% | More violations in hybrid context |
| Hybrid Algorithm rounds | 0.0% | Perfect compliance |

**Insight:** LLMs mostly respect constraints but have occasional lapses, especially when alternating with algorithms.

---

## Experiment Categories

### Category 1: Pure Algorithms (Baseline)
**800 games** - 7 strategies × 100 games

Algorithms tested: CSS, VOI, Random, CSS-then-VOI, VOI-then-CSS, CSS-VOI-alternating, VOI-CSS-alternating

**Best:** CSS-then-VOI (3.77 avg attempts, 97% win rate)

### Category 2: Pure LLMs
**2,200 games** - 11 models × 2 prompting strategies × 100 games

Models tested: GPT variants, Llama variants, Mistral variants, Gemma, Granite, Codestral

**Best:** Mistral-small-3.1 zero-shot (4.03 avg attempts, 91% win rate)

### Category 3: Hybrid LLM-Algorithm
**5,400 games** - 9 models × 3 algorithms × 2 prompting strategies × 100 games

Strategy: LLM on odd rounds (1, 3, 5), Algorithm on even rounds (2, 4, 6)

**Best:** Gemma-3-27b-it + CSS + zero-shot (3.77 avg attempts, 99% win rate)

---

## Recent Updates

### February 12, 2026 — Mastermind Extension & Workshop Experiments

**Mastermind as Second Testbed:**
- Added Mastermind environment (`engines/mastermind_env.py`)
- Implemented CSS and VOI strategies for Mastermind
- Supports Classic (6 colors, RGBYOW) and Extended (8 colors, +PK) variants
- 1,296 possible codes vs Wordle's 5,629 words

**Critical Bug Fixes (5 total):**
1. Removed all algorithm fallback code — LLM failures now properly recorded
2. Fixed candidate display (was showing only count, now shows sample of 30)
3. Added explicit instruction: "Your guess MUST be from the remaining possible codes"
4. Fixed Mastermind color descriptions for Classic vs Extended variants
5. **Invalid guess handling** — Invalid guesses now mark game as lost (previously crashed)

**Experiments Running (Evening Update):**
Both Wordle and Mastermind experiments running in parallel with all fixes applied.

| Progress | Mastermind Classic | Wordle |
|----------|-------------------|--------|
| Completed | 19/56 (34%) | 19/56 (34%) |
| Current | A3: L_to_C_alt | A3: L_to_C_alt |
| Pending | C_to_L, V_to_L (critical) | C_to_L, V_to_L (critical) |

**Preliminary Results (excluding nemotron model):**

| Config | Mastermind | Wordle |
|--------|------------|--------|
| L_to_C (LLM→CSS) | 100% | 94-98% |
| L_to_V (LLM→VOI) | 100% | 91-96% |
| L_to_C_alt | 100% | 99% |

**Model Exclusion:** `llama-3.1-nemotron-nano-8B-v1` excluded from analysis (0% win rate due to API issues).

### January 6, 2026 — Analysis Packages

1. **Search Space Pruning Analysis**
   - Calculated candidates remaining after each guess for all 6,303 games
   - Created export package: `search_space_pruning/`
   - Generated comprehensive report with pruning statistics

2. **Feedback Compliance Analysis**
   - Calculated constraint violations for all 6,303 games
   - Tracked violations by type (green/yellow/gray)
   - Created export package: `feedback_compliance_analysis/`
   - Generated comprehensive report with violation statistics

3. **Documentation Consolidation**
   - Moved all analysis reports to `docs/analysis/`
   - Created master README with project overview
   - Organized export packages for easy sharing

### Analysis Scripts Added

- `scripts/calculate_candidates.py` - Calculate search space pruning
- `scripts/analyze_candidate_statistics.py` - Generate pruning report
- `scripts/calculate_constraint_violations.py` - Calculate constraint violations
- `scripts/analyze_constraint_violations.py` - Generate violation report

---

## Data Files

### With Candidate Counts
- `results/algorithms/raw data/algorithm_results_with_candidates.csv`
- `results/hybrids/stage3/raw data/*_with_candidates.csv` (27 files)
- `results/hybrids/stage3-cot/raw data/*_with_candidates.csv` (28 files)

### With Constraint Violations
- `results/algorithms/raw data/algorithm_results_with_violations.csv`
- `results/hybrids/stage3/raw data/*_with_violations.csv` (27 files)
- `results/hybrids/stage3-cot/raw data/*_with_violations.csv` (28 files)

---

## Next Steps

### Immediate (Workshop Paper)
1. ✅ Fix all experiment bugs (fallback, candidate display, invalid guess handling)
2. 🔄 Complete Wordle + Mastermind experiments (34% done, C_to_L pending)
3. ⏳ Exclude nemotron model from statistical analysis
4. ⏳ Run statistical analysis comparing L→C vs C→L (handoff cost hypothesis)
5. ⏳ Draft workshop paper manuscript with dual-testbed validation

### For Main Publication
1. Review analysis reports in `docs/analysis/`
2. Share export packages with advisor
3. Prepare visualizations from trajectory plots
4. Draft paper using findings from comprehensive summary

### For Further Analysis
1. Per-model convergence patterns
2. Word difficulty effects on reasoning
3. Constraint violation patterns over time
4. Adaptive hybrid strategies based on search space size

---

## Contact

**Repository:** https://github.com/Intelligent-Agents-Research-Group/wordle-algorithm-evaluation
**Research Group:** Intelligent Agents Research Group

---

## File Organization Summary

```
wordle/
├── README.md (this file)
│
├── docs/
│   ├── analysis/                    # Main analysis reports
│   │   ├── COMPREHENSIVE_SUMMARY_STATISTICS.md
│   │   ├── RESEARCH_NARRATIVE.md
│   │   ├── CONVERGENCE_ANALYSIS_README.md
│   │   ├── convergence_summary.md
│   │   ├── CANDIDATE_ANALYSIS_REPORT.md
│   │   └── CONSTRAINT_VIOLATION_REPORT.md
│   │
│   ├── Hybrids/                     # Hybrid experiment docs
│   ├── algorithms.md
│   ├── engines.md
│   ├── evaluations.md
│   └── wordlist.md
│
├── workshop/                        # Workshop paper on hybrid degradation
│   ├── docs/
│   │   └── workshop_hybrid_degradation_findings.md
│   ├── scripts/                     # Flexible hybrid evaluation
│   └── results/                     # Workshop experiment results
│
├── results/                         # Raw experimental data
│   ├── algorithms/                  # Pure algorithm results
│   ├── llms/                        # Pure LLM results
│   ├── hybrids/                     # Wordle hybrid results
│   ├── mastermind/                  # Mastermind results
│   │   └── hybrids/                 # Mastermind hybrid experiments
│   └── workshop/                    # Workshop Wordle experiments
│
├── engines/
│   ├── wordle_env.py               # Wordle environment
│   └── mastermind_env.py           # Mastermind environment (NEW)
│
├── algorithms/
│   ├── css_strategy.py             # CSS for Wordle
│   ├── voi_strategy.py             # VOI for Wordle
│   ├── mastermind_css_strategy.py  # CSS for Mastermind (NEW)
│   └── mastermind_voi_strategy.py  # VOI for Mastermind (NEW)
│
├── scripts/
│   ├── hybrids/                     # Wordle hybrid scripts
│   └── mastermind/                  # Mastermind scripts (NEW)
│
├── search_space_pruning/            # Export package 1
├── feedback_compliance_analysis/    # Export package 2
└── wordlist/                        # Word lists
```

## Workshop Paper

The workshop paper investigates: **"Does hybridizing LLMs with classical decision-theoretic algorithms improve iterative reasoning, or does control handoff introduce systematic costs?"**

**Hypothesis:** Control handoff from algorithm to LLM introduces systematic costs due to state inconsistency.

**Evidence from prior experiments (old_css + CSS):**
- L→C (LLM first, then CSS): **97.5%** win rate
- C→L (CSS first, then LLM): **91.1%** win rate
- **Gap: 6.4 percentage points** — supports asymmetric handoff cost hypothesis
- Constraint violations spike under alternation (0.28/game vs 0.04-0.16 for pure LLM)

**Current experiments (February 12, 2026):**
- Fresh run with all bug fixes applied (no fallback, proper invalid guess handling)
- Testing both Wordle (5,629 words) and Mastermind Classic (1,296 codes)
- ~34% complete, C_to_L configs pending (~run 41-48)
- Will validate hypothesis with methodologically clean data

See `workshop/docs/workshop_hybrid_degradation_findings.md` for full details.
