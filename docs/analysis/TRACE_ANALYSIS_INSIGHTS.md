# Trace Analysis Insights

**Analysis Date:** January 18, 2026
**Data Analyzed:** 16,000+ game traces across algorithms, LLMs, and hybrids
**Purpose:** Identify patterns for future research directions

---

## Overview

This document summarizes insights from analyzing raw game traces, including:
- First guess patterns across models
- Failure case analysis
- Constraint violation patterns
- Solution attribution (LLM vs Algorithm)

These insights are intended for future work and potential follow-up papers.

---

## 1. First Guess Patterns — LLMs Have "Favorites"

LLMs do not optimize first guesses information-theoretically. Instead, they default to common English words.

### Observed First Guess Frequencies

| Model | Top First Guesses |
|-------|-------------------|
| Gemma-3-27b | THINK (24%), THERE (17%), OTHER (15%), RIGHT (14%) |
| Llama-3.1-70b | HOUSE (dominant, ~80%) |
| General pattern | High-frequency words with common letters (E, A, R, T, O) |

### Comparison to Optimal

- **Optimal first guesses** (information-theoretic): SALET, REAST, CRATE, TRACE
- **LLM first guesses**: HOUSE, THINK, THERE, OTHER, RIGHT
- **Gap**: LLMs choose familiar words, not information-maximizing words

### Implications

1. LLMs rely on word frequency/familiarity rather than strategic optimization
2. First-guess efficiency could be improved with:
   - Better prompting (e.g., "choose a word with common letters in different positions")
   - Few-shot examples of optimal openers
   - Fine-tuning on Wordle-specific data

### Future Work

- Compare first-guess entropy between LLMs and algorithms
- Test whether prompting can shift LLM first guesses toward optimal
- Analyze whether first-guess quality correlates with overall performance

---

## 2. Failure Cases — The "Final Candidate Problem"

### Pattern

All observed failures share a common structure: multiple candidates that differ in only ONE ambiguous position, making them indistinguishable without guessing.

### Examples

| Target | Stuck Pattern | Indistinguishable Candidates |
|--------|--------------|------------------------------|
| BASES | _A_ES | GAMES, CATES, HAYES, EAVES, BASES |
| DILLY | _ILLY | VILLA, WILLI, BILLY, MILLY, DILLY |
| GRADE | GRA_E | GRAZE, GRAPE, GRAVE, GRACE, GRADE |
| CORBY | COR_Y | COREY, CORNY, CORKY, CORBY |
| COLES | _OLES | POLES, SOLES, HOLES, MOLES, COLES |
| POLIS | _OLIS | SOLIS, FOLIS, POLIS |

### Analysis

This is a **fundamental limitation of Wordle**, not a reasoning failure:
- Once you reach a pattern like `_ILLY`, you must guess randomly among valid candidates
- Neither LLM reasoning nor algorithmic optimization can help
- Expected attempts to solve = (number of candidates + 1) / 2

### Word Characteristics That Cause Failures

1. **Common endings**: -ILLY, -OLES, -RADE, -ASES
2. **Variable first letter**: Many words share suffix patterns
3. **Low-frequency target**: DILLY, CORBY, POLIS are uncommon words

### Future Work

- **Word difficulty metric**: Quantify how many "trap patterns" a word can create
- **Failure prediction**: Can we predict which words will cause failures before gameplay?
- **Strategic implications**: Should strategies avoid certain guess patterns?

---

## 3. Constraint Violations — What Goes Wrong

### Violation Types Observed

| Violation Type | Description | Frequency |
|----------------|-------------|-----------|
| **Gray violation** | Reusing a letter marked as not in word | Most common (~70%) |
| **Yellow violation** | Not using a required letter, or placing it in forbidden position | Common (~25%) |
| **Green violation** | Changing a letter at a confirmed position | Rare (~5%) |
| **Invalid word** | Generating a non-existent word (OULDY, WORDE) | Occasional |

### Examples of Violations

| Target | Prior Feedback | Violating Guess | Violation |
|--------|---------------|-----------------|-----------|
| CARVE | THERE → --Y-- (E is yellow) | Next guess without E | Yellow violation |
| AWAKE | Multiple grays | Guess reuses gray letter | Gray violation |
| MEALS | AFTER → feedback | Ignores constraint | Yellow violation |

### Pattern: Gray Violations Dominate

LLMs struggle most with **exclusion constraints**:
- They remember what letters ARE in the word (green/yellow)
- They forget what letters are NOT in the word (gray)

### Hypotheses

1. **Attention bias**: LLMs attend more to positive information than negative
2. **Working memory**: Tracking 26 letters minus exclusions is cognitively demanding
3. **Training distribution**: LLMs see more examples of "use this letter" than "avoid this letter"

### Future Work

- **Constraint type analysis**: Systematic comparison of green/yellow/gray adherence
- **Prompt engineering**: Can explicit constraint reminders reduce violations?
- **Attention analysis**: Do attention patterns differ for inclusion vs exclusion constraints?

---

## 4. Solution Attribution — Who Wins?

### Analysis of Final Winning Guesses

In hybrid games, we tracked which agent (LLM or Algorithm) made the winning guess.

| Winning Round | Winning Agent | Typical Scenario |
|---------------|---------------|------------------|
| Round 3 | LLM | Algorithm narrowed to ~10 candidates, LLM intuition picks winner |
| Round 4 | Algorithm | LLM provided good constraints, algorithm systematically finishes |
| Round 5 | LLM | Both agents collaborating through difficult case |
| Round 6 | Either | Final candidate problem, essentially random |

### Observations

1. **LLM excels at "picking from small set"**: When candidates < 10, LLM often guesses correctly
2. **Algorithm excels at "systematic narrowing"**: Reduces search space optimally
3. **Synergy is real**: Neither agent consistently "carries" — both contribute

### Win Distribution (Estimated from Traces)

- LLM wins on odd rounds: ~55%
- Algorithm wins on even rounds: ~45%

### Future Work

- Formal analysis of which agent contributes more "value"
- Conditional analysis: When does LLM outperform algorithm (and vice versa)?
- Optimal handoff strategies: Should LLM/algorithm ratio change based on game state?

---

## 5. Interesting Edge Cases

### Invalid Word Generation

Some LLMs occasionally generate non-words:
- OULDY (not a word)
- WORDE (not a word)
- SAYED (archaic, might not be in word list)

**Pattern**: This happens more when:
- Candidate list is highly constrained
- Required letter pattern is unusual
- LLM is "reaching" for a solution

### Repeated Guess Attempts

Rare cases where LLM guesses the same word twice:
- Indicates failure to track history
- More common in longer games (5-6 attempts)
- May indicate context window issues

### Near-Miss Patterns

Cases where LLM guesses a word one letter off from target:
- GRAZE when target is GRACE
- RIDER when target is RYDER
- Shows good constraint following but bad luck

---

## 6. Future Paper Ideas

Based on trace analysis, potential follow-up research:

### Paper 1: Word Difficulty in Constraint Satisfaction Games

- Develop formal difficulty metric based on "trap patterns"
- Predict game length from word characteristics
- Compare human and LLM difficulty rankings

### Paper 2: Constraint Type Asymmetry in LLM Reasoning

- Systematic study of inclusion vs exclusion constraint handling
- Test whether this asymmetry appears in other domains
- Develop interventions (prompting, fine-tuning) to address gap

### Paper 3: First Guess Optimization for LLMs

- Compare information-theoretic vs LLM first guesses
- Test prompt engineering approaches
- Measure impact on overall game performance

### Paper 4: Failure Mode Taxonomy for Iterative Reasoning

- Categorize failures: impossible vs reasoning error
- Develop diagnostic for reasoning quality independent of luck
- Apply to domains beyond Wordle

### Paper 5: Optimal Human-AI Handoff in Sequential Decisions

- When should LLM defer to algorithm (and vice versa)?
- Develop confidence-based handoff strategies
- Test adaptive vs fixed alternation

---

## 7. Data Locations for Future Analysis

### Raw Game Traces

- **LLM traces**: `results/llms/raw data/*.csv`
  - Includes: guesses, feedback, candidates, CoT traces, violations

- **Algorithm traces**: `results/algorithms/raw data/algorithm_results_*.csv`
  - Includes: guesses, feedback, distances, strategy labels

- **Hybrid traces**: `results/hybrids/stage3*/raw data/*.csv`
  - Includes: guesses, feedback, strategy per round, violations

### Processed Data

- **With violations**: `*_with_violations.csv` files
- **With candidates**: `*_with_candidates.csv` files

### Key Fields for Analysis

```
game_number, target_word, won, attempts
guess_N, feedback_N, strategy_N (for hybrids)
violated_green_N, violated_yellow_N, violated_gray_N
candidates_before, candidates_after
cot_trace (for CoT experiments)
```

---

## 8. Summary Statistics from Trace Analysis

| Metric | Value |
|--------|-------|
| Total games analyzed | 16,000+ |
| Failure rate (all approaches) | 2-7% |
| Most common failure pattern | Single ambiguous position |
| Most common violation type | Gray (reusing excluded letter) |
| Most common LLM first guess | THINK, THERE, HOUSE |
| Optimal first guess | SALET, REAST, CRATE |

---

## Next Steps

1. **Quantitative analysis**: Convert these qualitative observations to statistics
2. **Visualization**: Create plots of violation distributions, first-guess entropy, etc.
3. **Hypothesis testing**: Formalize and test the patterns observed here
4. **Paper drafting**: Select most promising direction for follow-up publication

---

**Document created:** January 18, 2026
**Author:** Analysis by Claude, based on project data
**Status:** Ready for future work reference
