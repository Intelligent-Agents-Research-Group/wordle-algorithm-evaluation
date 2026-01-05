# Hybrid LLM-Algorithm Strategies

This directory contains evaluation scripts for hybrid strategies that combine Large Language Models (LLMs) with traditional algorithms (CSS).

## Overview

These hybrid strategies test whether combining LLM intuition with algorithmic optimization improves Wordle-solving performance compared to pure approaches.

## Staged Testing Approach (Recommended)

To efficiently validate hybrid strategies before committing to full evaluation, we use a staged approach:

### Stage 1: Quick Validation ✨ **START HERE**
- **Purpose**: Determine if hybrids show promise
- **Test**: 3 models × 4 strategies × 10 games = 120 total games
- **Time**: ~2-3 hours
- **Cost**: Minimal (~$0.12-$0.36)
- **Models**: mistral-small-3.1, llama-3.3-70b-instruct, mistral-7b-instruct

**Run Stage 1:**
```bash
cd scripts/hybrid
./run_stage1_test.sh
```

**Analyze Results:**
```bash
python3 analyze_stage1_results.py
```

### Stage 2: Full Strategy Evaluation
- **When**: If Stage 1 shows any hybrid beats pure CSS (< 3.79 attempts)
- **Test**: Best 1-2 strategies × 2-3 models × 100 games
- **Time**: ~5-10 hours
- **Purpose**: Validate promising strategies with full test set

### Stage 3: Comprehensive Model Comparison
- **When**: If Stage 2 confirms hybrid advantage
- **Test**: Best strategy × all 11 models × 100 games
- **Time**: ~10-20 hours
- **Purpose**: Publication-ready comprehensive results

### Decision Tree

```
Stage 1 Results
    ├─ Any hybrid < 3.79 attempts? ──YES──> Stage 2 (full evaluation)
    │                                         │
    │                                         ├─ Still < 3.79? ──YES──> Stage 3 (all models)
    │                                         └─ No improvement ──────> Document findings
    │
    └─ No hybrid < 3.79? ────────────────────> Hybrids don't help, document
```

## Strategies

### 1. LLM-then-CSS (`llm_then_css.py`)
- **Approach**: LLM makes the first guess, CSS handles all remaining guesses
- **Hypothesis**: LLM's intuition for opening moves + CSS's optimal pruning
- **Use case**: Test if LLMs have good opening move selection

### 2. CSS-then-LLM (`css_then_llm.py`)
- **Approach**: CSS makes first 2 guesses (optimal opening), LLM handles remaining guesses
- **Hypothesis**: CSS's optimal opening + LLM's pattern recognition for closing
- **Use case**: Test if CSS openings help LLM performance
- **Configurable**: Set `CSS_TURNS` to change number of CSS guesses (default: 2)

### 3. Threshold-Based (`threshold_hybrid.py`)
- **Approach**: CSS when candidate pool > threshold, LLM when candidate pool ≤ threshold
- **Hypothesis**: CSS for optimal pruning when many options, LLM when few options remain
- **Use case**: Context-aware switching based on game state
- **Configurable**: Set `THRESHOLD` to change switching point (default: 50 candidates)

### 4. Alternating (`alternating_hybrid.py`)
- **Approach**: Alternates between LLM and CSS on each turn
- **Hypothesis**: Combining approaches on every turn provides complementary strengths
- **Use case**: Test if turn-by-turn alternation helps
- **Configurable**: Set `START_WITH=llm` or `START_WITH=css` to choose which goes first

## Usage

### Prerequisites

1. **API Key**: Set Navigator UF API key
   ```bash
   export NAVIGATOR_UF_API_KEY="your-api-key"
   ```

2. **Optional Configuration**:
   ```bash
   export NAVIGATOR_API_ENDPOINT="https://api.navigator.uf.edu/v1"  # default
   export MODEL="llama-3.3-70b-instruct"  # default model
   export NUM_GAMES="100"  # number of games (default: 100)
   ```

### Running Evaluations

#### 1. LLM-then-CSS
```bash
cd scripts/hybrid
python3 llm_then_css.py
```

Or with custom configuration:
```bash
MODEL="mistral-7b-instruct" NUM_GAMES="50" python3 llm_then_css.py
```

#### 2. CSS-then-LLM
```bash
cd scripts/hybrid
python3 css_then_llm.py
```

With custom CSS turns:
```bash
MODEL="llama-3.3-70b-instruct" CSS_TURNS="3" python3 css_then_llm.py
```

#### 3. Threshold-Based
```bash
cd scripts/hybrid
python3 threshold_hybrid.py
```

With custom threshold:
```bash
MODEL="llama-3.3-70b-instruct" THRESHOLD="30" python3 threshold_hybrid.py
```

#### 4. Alternating
```bash
cd scripts/hybrid
python3 alternating_hybrid.py
```

Starting with CSS instead of LLM:
```bash
START_WITH="css" python3 alternating_hybrid.py
```

## Output

All scripts save results to `results/hybrids/`:

### CSV Files
Detailed game-by-game results with:
- Game number and target word
- Win/loss status and attempts
- All guesses with feedback
- Hamming and Levenshtein distances
- Which strategy was used for each guess (where applicable)

Example: `llm_then_css_llama-3.3-70b-instruct_20250112_143022.csv`

### JSON Files
Summary statistics:
- Strategy name and configuration
- Total games, wins, win rate
- Average attempts when won
- Timestamp

Example: `summary_llm_then_css_llama-3.3-70b-instruct_20250112_143022.json`

## Environment Variables Reference

| Variable | Description | Default | Used By |
|----------|-------------|---------|---------|
| `NAVIGATOR_UF_API_KEY` | API key for Navigator UF (required) | - | All |
| `NAVIGATOR_API_ENDPOINT` | API endpoint URL | `https://api.navigator.uf.edu/v1` | All |
| `MODEL` | LLM model name | `llama-3.3-70b-instruct` | All |
| `NUM_GAMES` | Number of games to evaluate | `100` | All |
| `CSS_TURNS` | Number of CSS turns before switching | `2` | css_then_llm |
| `THRESHOLD` | Candidate count for switching | `50` | threshold_hybrid |
| `START_WITH` | Starting strategy (`llm` or `css`) | `llm` | alternating_hybrid |

## Implementation Details

### Common Features
- All scripts use the canonical test set (100 words from `wordlist/test_set.csv`)
- LLM calls include retry logic with exponential backoff
- Fallback to CSS if LLM fails or returns invalid guess
- Both Hamming and Levenshtein distances tracked
- Results compatible with existing analysis scripts

### Strategy Classes
Each script defines a hybrid strategy class:
- `LLMThenCSSStrategy`
- `CSSThenLLMStrategy`
- `ThresholdHybridStrategy`
- `AlternatingHybridStrategy`

All implement:
- `update_belief()`: Delegates to CSS for constraint satisfaction
- `get_guess()`: Implements switching logic between LLM and CSS
- Retry and fallback logic for robust operation

## Expected Performance

### Hypotheses to Test
1. **LLM-then-CSS**: May improve if LLMs have strong opening moves
2. **CSS-then-LLM**: Should inherit CSS's strong opening performance
3. **Threshold**: May optimize for both large-pool (CSS strength) and small-pool (LLM strength) scenarios
4. **Alternating**: May benefit from complementary approaches, or suffer from lack of consistency

### Comparison Baseline
- **Pure CSS**: 98% win rate, 3.79 avg attempts
- **Pure LLM (best)**: 100% win rate, 4.03 avg attempts (mistral-small-3.1 CoT)
- **Goal**: Win rate ≥ 98%, attempts < 3.79 (beat pure CSS)

## Research Questions

1. Do hybrids outperform pure approaches?
2. Which hybrid strategy is most effective?
3. How does switching frequency affect performance?
4. When is each approach (LLM vs CSS) most beneficial?
5. Do different LLMs benefit differently from hybridization?

## Next Steps

After running evaluations:
1. Compare results against pure algorithms and LLMs
2. Analyze when each strategy is used (for threshold/alternating)
3. Test different threshold values and CSS turn counts
4. Evaluate with different LLM models
5. Update `docs/results.md` with hybrid findings

## Notes

- **API Costs**: Each game requires N LLM calls (where N = number of LLM turns). Plan accordingly.
- **Runtime**: Expect ~1-2 seconds per LLM call. 100 games may take 10-30 minutes depending on strategy.
- **Robustness**: All scripts include fallback to CSS if LLM fails, ensuring completion.
- **Reproducibility**: Uses same canonical test set as other evaluations for fair comparison.
