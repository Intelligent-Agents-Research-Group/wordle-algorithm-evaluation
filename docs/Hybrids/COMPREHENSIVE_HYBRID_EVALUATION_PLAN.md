# Comprehensive Hybrid Evaluation Plan

**Date:** January 5, 2026
**Status:** Ready to Execute
**Total Games:** 4,500

---

## Executive Summary

This comprehensive evaluation tests hybrid LLM-algorithm strategies across:
- **2 prompting strategies:** Zero-shot and Chain-of-Thought (CoT)
- **3 algorithms:** CSS, VOI, and Random (filtered)
- **9 LLM models:** Diverse architectures from 8B to 70B parameters

**Goal:** Determine if hybrid approaches improve performance over pure algorithms, and whether this varies by algorithm type or prompting strategy.

---

## Evaluation Scope

### Previously Completed
-  **Stage 3 Zero-shot with CSS:** 9 models × 100 games = 900 games
  - Results in: `results/hybrids/stage3/`

### New Evaluations (This Run)

#### Part 1: Zero-shot Completions
- **VOI:** 9 models × 100 games = 900 games
- **Random:** 9 models × 100 games = 900 games
- **Subtotal:** 1,800 games

#### Part 2: CoT Evaluations
- **CSS:** 9 models × 100 games = 900 games
- **VOI:** 9 models × 100 games = 900 games
- **Random:** 9 models × 100 games = 900 games
- **Subtotal:** 2,700 games

### Grand Total
- **This run:** 4,500 games
- **Including completed:** 5,400 games (54 model-algorithm-prompt combinations)

---

## Models Tested

All evaluations use the same 9 models:

1. **codestral-22b** - 22B code-focused model
2. **gemma-3-27b-it** - 27B Google model
3. **granite-3.3-8b-instruct** - 8B IBM model
4. **llama-3.1-70b-instruct** - 70B Meta model
5. **llama-3.1-8b-instruct** - 8B Meta model
6. **llama-3.1-nemotron-nano-8B-v1** - 8B NVIDIA model
7. **llama-3.3-70b-instruct** - 70B Meta model (v3.3)
8. **mistral-7b-instruct** - 7B Mistral model
9. **mistral-small-3.1** - Mistral small model

---

## Algorithms Tested

### 1. CSS (Constraint Satisfaction Strategy)
- **Baseline:** 98% win rate, 3.79 avg attempts (pure algorithm)
- **Strategy:** Maximizes information gain through constraint satisfaction
- **Use case:** When you want optimal information-theoretic performance

### 2. VOI (Value of Information)
- **Baseline:** 99% win rate, 3.93 avg attempts (pure algorithm)
- **Strategy:** Maximizes expected information value
- **Use case:** Alternative to CSS with similar performance

### 3. Random (Filtered)
- **Baseline:** 91% win rate, 4.44 avg attempts (pure algorithm)
- **Strategy:** Random selection from valid candidates
- **Use case:** Lower bound / control condition

---

## Prompting Strategies

### Zero-shot
**Format:**
```
You are playing Wordle. Your goal is to guess a 5-letter word.

Previous guesses:
HOUSE: 🟩⬜⬜⬜🟩

Remaining possible words (15): HORSE, TERSE, ...

Based on the feedback, what should the next guess be?
Return ONLY a single 5-letter word in uppercase, nothing else.
Your guess:
```

### Chain-of-Thought (CoT)
**Format:**
```
You are an expert Wordle player. Use brief, structured reasoning.
Return output in this exact format:
THINKING: <your concise step-by-step reasoning>
FINAL: <ONE 5-letter guess only>

Feedback codes: G=green, Y=yellow, -=letter not in word

Previous attempts:
- Guess: HOUSE  Feedback: G--G
  Per letter: H:G  O:-  U:-  S:-  E:G

Allowed words remaining: 15
Candidate words: HORSE, TERSE, ...

Constraints:
• Do NOT repeat previous guesses.
• The FINAL line must be exactly ONE valid 5-letter word from the allowed list.
• Keep THINKING concise (1-5 short lines).
```

---

## Hybrid Strategy

**Type:** Alternating (LLM-first)

**Turn Assignment:**
- **Turn 1, 3, 5:** LLM makes the guess
- **Turn 2, 4, 6:** Algorithm (CSS/VOI/Random) makes the guess

**Rationale:**
- LLM provides intuitive, pattern-based guesses
- Algorithm provides information-theoretic optimization
- Alternating combines both strengths

**Fallback:** If LLM fails or returns invalid guess, falls back to algorithm

---

## Test Set

**Source:** Canonical test set (`wordlist/test_set.csv`)
**Size:** 100 words
**Stratification:**
- Tier 1 (high frequency): 34 words
- Tier 2 (medium frequency): 33 words
- Tier 3 (low frequency): 33 words

**Consistency:** Same 100 words used across ALL evaluations (algorithms, pure LLMs, hybrids)

---

## Research Questions

### Primary Questions
1. **Do hybrids improve over pure algorithms?**
   - Target: Beat CSS baseline (3.79 avg attempts)
   - Success metric: < 3.79 avg attempts

2. **Does algorithm choice matter for hybrids?**
   - Compare: CSS vs VOI vs Random when paired with LLM
   - Expected: CSS ≈ VOI > Random

3. **Does prompting strategy matter for hybrids?**
   - Compare: Zero-shot vs CoT for each algorithm
   - Expected: Model-dependent (some prefer CoT, others zero-shot)

### Secondary Questions
4. **Which models benefit most from hybridization?**
5. **When does the LLM vs algorithm make each guess?**
6. **Do hybrids reduce variance compared to pure LLMs?**

---

## Expected Outcomes

### Hypothesis 1: Hybrids underperform pure algorithms
Based on Stage 3 zero-shot CSS results (4.08 avg attempts > 3.79 CSS baseline), we expect hybrids to generally underperform across all algorithms.

### Hypothesis 2: Algorithm ranking preserved
Even in hybrid form: CSS ≈ VOI > Random

### Hypothesis 3: CoT improves some models
Some models may perform better with CoT prompting, similar to pure LLM results.

### Hypothesis 4: Consistency across models
Similar to zero-shot CSS (σ = 0.17), we expect low variance across models within each algorithm-prompt combination.

---

## Execution Plan

### Script
`scripts/hybrids/run_comprehensive_evaluation.sh`

### Estimated Runtime
- **Per game:** ~30-60 seconds (includes LLM API calls)
- **Per model-algorithm combo:** ~50-100 minutes (100 games)
- **Total:** ~40-80 hours for all 4,500 games

### Overnight Strategy
Run overnight for multiple nights if needed. Script saves progress after each model-algorithm completion.

### Error Handling
- Automatic retry logic for LLM API failures
- Fallback to algorithm if LLM consistently fails
- Individual logs per model-algorithm combination
- Can resume from any failed run

---

## Output Structure

### Directory Structure
```
results/hybrids/
├── stage3/                    # Zero-shot results
│   ├── raw data/
│   │   ├── alternating_llm_first_<model>_*.csv          # CSS (existing)
│   │   ├── alternating_llm_first_<model>_voi_*.csv      # VOI (new)
│   │   └── alternating_llm_first_<model>_random_*.csv   # Random (new)
│   ├── summary stats/
│   │   └── summary_*.json
│   └── logs/
│       └── *.log
└── stage3-cot/                # CoT results
    ├── raw data/
    │   ├── alternating_llm_first_<model>_cot_*.csv          # CSS
    │   ├── alternating_llm_first_<model>_voi_cot_*.csv      # VOI
    │   └── alternating_llm_first_<model>_random_cot_*.csv   # Random
    ├── summary stats/
    │   └── summary_*_cot_*.json
    └── logs/
        └── *_cot_*.log
```

### File Naming Convention
- **CSV:** `alternating_llm_first_{model}_{algorithm}_{prompt}_{timestamp}.csv`
- **JSON:** `summary_alternating_llm_first_{model}_{algorithm}_{prompt}_{timestamp}.json`
- **Log:** `alternating_hybrid_{model}_{algorithm}_{prompt}_{timestamp}.log`

Where:
- `{algorithm}` = empty for CSS, `_voi` for VOI, `_random` for Random
- `{prompt}` = empty for zero-shot, `_cot` for CoT

---

## Analysis Plan

### After Completion

1. **Aggregate Results**
   - Collect all summary JSON files
   - Create comprehensive comparison tables
   - Calculate mean performance per algorithm-prompt combination

2. **Statistical Analysis**
   - Compare to pure algorithm baselines
   - Test for significant differences
   - Calculate effect sizes

3. **Visualization**
   - Performance by algorithm (CSS vs VOI vs Random)
   - Performance by prompting (Zero-shot vs CoT)
   - Performance by model
   - Interaction plots

4. **Documentation**
   - Update `docs/results.md` with comprehensive findings
   - Create summary file for advisor
   - Document key insights and conclusions

---

## Success Criteria

### Completion
-  All 45 model-algorithm-prompt combinations complete
-  All results saved and organized
-  No missing or corrupted data files

### Quality
-  All models achieve >85% win rate (validates methodology)
-  Results are reproducible (canonical test set)
-  Consistent with previous evaluations (zero-shot CSS matches)

### Scientific Value
-  Comprehensive coverage of algorithm × prompt space
-  Sufficient sample size (100 games each)
-  Fair comparison to baselines

---

## Risk Mitigation

### API Failures
- Automatic retry with exponential backoff
- Fallback to algorithm if LLM fails
- Logs capture all errors for debugging

### Long Runtime
- Script saves progress after each completion
- Can stop and resume at any point
- Parallel execution possible (manual)

### Model Availability
- 9 models already validated in previous runs
- No gpt-oss models (known to have API issues)

---

## Post-Evaluation Deliverables

1. **Comprehensive Results Document**
   - All 54 combinations (including completed CSS zero-shot)
   - Performance tables and visualizations
   - Statistical comparisons

2. **Summary for Advisor**
   - Key findings and insights
   - Comparison to pure approaches
   - Recommendations for publication

3. **Updated Documentation**
   - `docs/results.md` with complete hybrid section
   - `docs/HYBRID_EVALUATION_SUMMARY.md` updated
   - Methodology documentation

---

## Timeline

**Start:** January 5, 2026 (evening)
**Estimated Completion:** January 7-8, 2026 (depending on runtime)
**Analysis:** January 8-9, 2026
**Documentation:** January 9-10, 2026

---

**Script:** `scripts/hybrids/run_comprehensive_evaluation.sh`
**Command:** `./run_comprehensive_evaluation.sh`
**Status:** Ready to execute
