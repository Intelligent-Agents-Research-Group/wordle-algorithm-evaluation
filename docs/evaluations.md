# Algorithm Evaluations

## Overview

The evaluations system provides comprehensive testing and comparison of Wordle-solving algorithms. This system runs controlled experiments to measure performance across multiple strategies.

**Note:** Additional evaluation scripts will be added as the research progresses.

---

## Experimental Methodology

### Word Selection and Test Design

**Guess Pool (Candidate Words):**
- Algorithms can guess from the **full wordlist** (`wordlist/wordlist.txt`)
- Contains **5,629 five-letter English words**
- Organized by frequency tiers (Tier 1-4) based on Zipf scores
- Provides algorithms with realistic vocabulary to choose from

**Test Set (Target Words):**
- Algorithms are evaluated on a **fixed test set** (`wordlist/test_set.csv`)
- Contains **100 carefully selected words**:
  - 34 words from Tier 1 (high frequency, Zipf ≥ 4.0)
  - 33 words from Tier 2 (medium frequency, 3.0 ≤ Zipf < 4.0)
  - 33 words from Tier 3 (lower frequency, 2.5 ≤ Zipf < 3.0)
- Fixed seed (42) ensures reproducibility
- Same 100 words used for ALL evaluations (algorithms and LLMs)

### Why This Design?

1. **Realistic Gameplay:** Algorithms have access to full vocabulary (5,629 words), mimicking real Wordle where any valid word can be guessed
2. **Controlled Testing:** All methods tested on identical 100 target words enables fair, direct comparison
3. **Difficulty Analysis:** Tier distribution allows analysis of performance across word difficulty levels
4. **Reproducibility:** Fixed seed and version-controlled test set ensures experiments can be replicated
5. **Statistical Power:** 100 games provides sufficient data for paired statistical tests

### Experimental Protocol

**For each algorithm:**
1. Load full wordlist (5,629 words) as the candidate pool
2. Load test set (100 target words with tier labels)
3. For each of 100 target words:
   - Initialize game environment with target word
   - Algorithm selects guesses from candidate pool
   - Record all guesses, feedback, distances, and outcomes
   - Maximum 6 attempts per game
4. Save detailed results to CSV with all metrics
5. Compute summary statistics (win rate, avg attempts, by tier)

**Metrics Tracked:**
- Strategy name
- Game number and target word
- Word tier (difficulty level)
- Win/loss outcome
- Number of attempts to win
- Total reward accumulated
- For each guess (1-6):
  - Guess word
  - Feedback pattern (Green/Yellow/Gray)
  - Hamming distance to target
  - Levenshtein distance to target

---

## Canonical Test Set

### Purpose

All evaluations (algorithms and LLMs) use the **same 100 words in the same order** to ensure fair comparison. This enables:

- ✓ **Direct comparison:** "On word CRANE, CSS won in 3 attempts, Mistral in 4"
- ✓ **Paired statistical testing:** More powerful than independent samples
- ✓ **Reproducibility:** Fixed seed (42) ensures identical test sets
- ✓ **Tier analysis:** Performance comparison across word difficulty levels

### Composition

**File:** `wordlist/test_set.csv`

- **Total:** 100 words
- **Tier 1:** 34 words (high frequency, Zipf ≥ 4.0)
- **Tier 2:** 33 words (medium frequency, 3.0 ≤ Zipf < 4.0)
- **Tier 3:** 33 words (lower frequency, 2.5 ≤ Zipf < 3.0)

**Selection Method:** Random sampling with fixed seed (42) for reproducibility

**Example Words:**
- Game 1: PHOTO (Tier 1)
- Game 2: PARTY (Tier 1)
- Game 35: GENRE (Tier 2)
- Game 68: AGAVE (Tier 3)

### Generation

To regenerate or verify the canonical test set:

```bash
cd scripts
python3 generate_test_set.py
```

**Output:**
```
Canonical Test Set Summary
- 100 words total
- 34 from Tier 1, 33 from Tier 2, 33 from Tier 3
- Saved to: wordlist/test_set.csv
```

### Usage in Code

Both evaluation scripts automatically load the canonical test set:

```python
from test_set_loader import get_test_words_only

# Load all 100 words in canonical order
test_words = get_test_words_only()

# Use first N words for testing
test_words = get_test_words_only()[:10]  # First 10 for quick test
```

### Publication Benefits

This approach is publication-ready because:

1. **Reproducible:** Fixed seed, version-controlled test set
2. **Fair:** All methods tested on identical tasks
3. **Statistical:** Enables paired tests (matched samples)
4. **Transparent:** Test set is public and documented
5. **Balanced:** Representative sampling across difficulty levels

---

## Evaluation Scripts

### algorithms_evaluation.py

**Location:** `scripts/algorithms_evaluation.py`

**Purpose:** Comprehensive evaluation of both basic and hybrid strategies on identical word sets for fair comparison.

#### What It Does

- **Evaluates 8 strategies:** 4 basic + 4 hybrid/alternating strategies
  - **Basic:** CSS, VOI, Random, Pure Random
  - **Hybrid:** CSS→VOI, VOI→CSS, CSS-VOI alternating, VOI-CSS alternating
- **Runs 100 total games** using tiered word list approach:
  - 25 games from Tier 1 (most common words)
  - 25 games from Tier 2
  - 25 games from Tier 3
  - 25 games from Tier 4 (least common words)
- **All strategies tested on same words** for fair comparison
- **Dual distance metrics:** Hamming AND Levenshtein distances
- **Outputs detailed CSV** with comprehensive performance metrics
- **Reproducible:** Uses fixed random seed (42) for consistent word selection from each tier

#### Key Features

**Fair Comparison:**
- All strategies tested on identical target words
- Same word list and conditions for each strategy
- Reproducible results via seeded random selection

**Comprehensive Data Collection:**
- Records all 6 attempts (or until word is found)
- Tracks every guess, feedback, and dual distance metrics
- Calculates **both** Hamming and Levenshtein distances
- Records win/loss, attempts, and total reward
- Tests hybrid strategy behavior (switching and alternating patterns)

**Output Metrics:**
- Strategy name (basic or hybrid)
- Game number
- Target word
- Win/loss status
- Number of attempts
- Total reward accumulated
- All 6 guesses with feedback (G/Y/-), Hamming distance, and Levenshtein distance

#### CSV Output Format

The script generates timestamped CSV files: `all_strategies_comprehensive_YYYYMMDD_HHMMSS.csv`

**Columns:**
```
strategy, game_number, target_word, won, attempts, total_reward,
guess_1, feedback_1, hamming_1, levenshtein_1,
guess_2, feedback_2, hamming_2, levenshtein_2,
...
guess_6, feedback_6, hamming_6, levenshtein_6
```

**Example row:**
```csv
css,1,CRANE,True,4,7.8,SLATE,--Y--,4,3,CRONE,GYG--,1,1,CRANE,GGGGG,0,0,,,,,,,,,
```

#### Distance Calculations

**Hamming Distance:**
- Counts character differences at each position
- Only works for equal-length strings (perfect for 5-letter words)
- Distance of 0 = exact match
- Simple, fast comparison metric

**Levenshtein Distance:**
- Counts minimum edits (insertions, deletions, substitutions) needed
- More flexible than Hamming distance
- Distance of 0 = exact match
- Provides deeper insight into word similarity

Both metrics provide complementary views of guess quality and convergence patterns.

#### Summary Statistics

After completion, prints summary for each strategy:
- Total games played
- Games won
- Win rate (%)
- Average attempts per game
- Average reward per game

---

#### Hybrid Strategies

**Strategy Switching (CSS→VOI, VOI→CSS):**
- Uses first strategy for opening guess
- Switches to second strategy for remaining guesses
- Tests whether different opening strategies improve performance

**Alternating Strategies (CSS-VOI alternating, VOI-CSS alternating):**
- Alternates between strategies on each guess
- CSS-VOI: guess 1=CSS, 2=VOI, 3=CSS, etc.
- VOI-CSS: guess 1=VOI, 2=CSS, 3=VOI, etc.
- Tests whether combining approaches yields benefits

---

### llm_evaluation.py

**Location:** `scripts/llm_evaluation.py`

**Purpose:** Evaluates Large Language Model (LLM) performance on Wordle using the Navigator UF API.

#### What It Does

- **Evaluates 1 LLM per execution** (designed to be run multiple times for different models)
- **Two prompting strategies:**
  - **Zero-shot:** Direct prompts asking for next guess
  - **Chain-of-thought (CoT):** Asks model to explain reasoning before guessing
- **Tests on standardized word set** (100 games by default, configurable)
- **Captures full reasoning traces** from LLM responses
- **Comprehensive metrics tracking** including constraint violations and information gain

#### Key Features

**LLM-Specific Analysis:**
- Captures chain-of-thought reasoning traces (for CoT prompting)
- Tracks constraint violations (does LLM violate known Wordle constraints?)
- Measures information gain per guess
- Validates guess quality (valid words vs. errors)
- API retry logic with exponential backoff

**Prompting Strategies:**

**Zero-shot:**
- Direct prompt: "Return the next guess"
- Minimal context, tests raw model ability
- Faster, lower token usage

**Chain-of-thought:**
- Structured output: `THINKING: <reasoning>` then `FINAL: <guess>`
- Captures model's reasoning process
- Better for understanding model strategy
- Example output:
  ```
  THINKING: Need letter E in position 5. Avoid H,O,U,S. Try CRANE.
  FINAL: CRANE
  ```

#### Metrics Tracked (Per Guess)

**Basic Metrics:**
- Win/loss status
- Attempts to win
- Guess validity (is it a real word from the list?)

**Information Theory:**
- Candidates before/after guess
- Candidate reduction rate
- Information gain (bits)

**Constraint Violations:**
- Green violations: Wrong letter in known-correct position
- Yellow violations: Missing known letter or in known-bad position
- Gray violations: Reusing letters known to be absent
- Total violation count per guess

**LLM Outputs:**
- Full prompt sent to model
- Chain-of-thought trace (reasoning)
- Raw API response
- Extracted guess

#### Output Files

**Per-model CSV:** `model_{model_name}_{prompt_type}_{timestamp}.csv`
- One row per guess attempt
- Includes all metrics, prompts, traces, and responses

**Summary JSON:** `summary_{model_name}_{prompt_type}_{timestamp}.json`
- Aggregate statistics: win rate, avg attempts, error counts
- Valid guess rate, avg information gain
- Constraint violation statistics

**Debug Folder** (optional, if `DEBUG_RESPONSES=1`):
- Raw API responses saved as individual text files
- Useful for troubleshooting model behavior

#### How to Run

```bash
# Set required environment variables
export MODEL='mistral-7b-instruct'
export PROMPT_TYPE='chain-of-thought'  # or 'zero-shot'
export NAVIGATOR_UF_API_KEY='your-api-key'

# Optional variables
export NAVIGATOR_API_ENDPOINT='https://api.navigator.uf.edu/v1'  # default
export NUM_TEST_GAMES='100'  # default: 3 for quick testing
export OUT_DIR='./results'  # output directory
export DEBUG_RESPONSES='1'  # save raw responses for debugging

# Run evaluation
cd scripts
python3 llm_evaluation.py
```

**Running Multiple Models:**

The script evaluates **1 LLM per execution**. To test multiple models, run multiple times:

```bash
# Mistral zero-shot
MODEL='mistral-7b-instruct' PROMPT_TYPE='zero-shot' python3 llm_evaluation.py

# Mistral chain-of-thought
MODEL='mistral-7b-instruct' PROMPT_TYPE='chain-of-thought' python3 llm_evaluation.py

# Llama zero-shot
MODEL='llama-2-70b' PROMPT_TYPE='zero-shot' python3 llm_evaluation.py
```

**Requirements:**
- Navigator UF API access and API key
- Word list file (`words`) accessible from script location
- Engines (WordleEnv, GuessingAgent) must be importable
- OpenAI Python library (for API client)

#### Use Cases

1. **LLM performance comparison:** Compare different models (Mistral, Llama, GPT, etc.)
2. **Prompting strategy comparison:** Zero-shot vs chain-of-thought effectiveness
3. **Reasoning analysis:** Examine model's chain-of-thought traces to understand strategy
4. **Constraint adherence:** Do LLMs follow Wordle rules correctly?
5. **Information efficiency:** How well do LLMs reduce candidate space?
6. **LLM vs Algorithm comparison:** Compare against traditional algorithms (CSS, VOI)

---

### Helper Scripts

#### test_single_model.sh

**Location:** `scripts/test_single_model.sh`

**Purpose:** Testing/debugging wrapper for single LLM evaluations with minimal games.

**Usage:**
```bash
cd scripts
./test_single_model.sh [MODEL] [PROMPT_TYPE] [NUM_GAMES]
```

**Parameters:**
- `MODEL` - Model name (default: `llama-3.3-70b-instruct`)
- `PROMPT_TYPE` - `zero-shot` or `chain-of-thought` (default: `zero-shot`)
- `NUM_GAMES` - Number of games to run (default: `3`)

**Features:**
- Enables debug mode automatically (saves raw API responses)
- Loads API key from `.env` if not set in environment
- Outputs to `./test_results/` directory
- Perfect for quick testing before running full evaluations

**Example:**
```bash
# Quick test with defaults (3 games, zero-shot)
./test_single_model.sh

# Test specific model with CoT
./test_single_model.sh mistral-7b-instruct chain-of-thought 10

# Full test run
./test_single_model.sh llama-3.3-70b-instruct chain-of-thought 100
```

---

#### run_all_models_cot.sh

**Location:** `scripts/run_all_models_cot.sh`

**Purpose:** Batch evaluation runner for multiple LLM models with chain-of-thought prompting.

**What It Does:**
- Runs 11 different LLM models sequentially
- Each model evaluated on 100 games
- All models use chain-of-thought prompting
- Saves individual logs for each model
- Estimated runtime: 3-4 hours total

**Models Evaluated:**
1. llama-3.3-70b-instruct
2. llama-3.1-70b-instruct
3. gpt-oss-120b
4. gemma-3-27b-it
5. codestral-22b
6. gpt-oss-20b
7. llama-3.1-8b-instruct
8. llama-3.1-nemotron-nano-8B-v1
9. mistral-7b-instruct
10. granite-3.3-8b-instruct
11. mistral-small-3.1

**Usage:**
```bash
cd scripts
./run_all_models_cot.sh
```

**Output:**
- Results: `./test_results/` (CSV and JSON files per model)
- Logs: `./evaluation_logs/` (execution logs per model)
- Each model gets timestamped output files

**Use Cases:**
- Comprehensive LLM comparison across many models
- Production evaluation runs
- Reproducible batch processing
- Overnight/long-running evaluations

---

#### run_all_models_zero_shot.sh

**Location:** `scripts/run_all_models_zero_shot.sh`

**Purpose:** Batch evaluation runner for multiple LLM models with zero-shot prompting.

**What It Does:**
- Runs 11 different LLM models sequentially
- Each model evaluated on 100 games
- All models use zero-shot prompting (no chain-of-thought)
- Saves individual logs for each model
- Estimated runtime: 3-4 hours total

**Models Evaluated:**
1. llama-3.3-70b-instruct
2. llama-3.1-70b-instruct
3. gpt-oss-120b
4. gemma-3-27b-it
5. codestral-22b
6. gpt-oss-20b
7. llama-3.1-8b-instruct
8. llama-3.1-nemotron-nano-8B-v1
9. mistral-7b-instruct
10. granite-3.3-8b-instruct
11. mistral-small-3.1

**Usage:**
```bash
cd scripts
./run_all_models_zero_shot.sh
```

**Output:**
- Results: `./test_results/` (CSV and JSON files per model)
- Logs: `./evaluation_logs/` (log files with `_zero_shot.log` suffix)
- Each model gets timestamped output files

**Use Cases:**
- Baseline LLM performance without reasoning traces
- Compare zero-shot vs chain-of-thought effectiveness
- Faster evaluation (zero-shot typically uses fewer tokens)
- Production evaluation runs

**Comparison with CoT:**
- Zero-shot prompting is typically faster (fewer tokens generated)
- No reasoning traces captured (simpler prompts)
- Good baseline for comparing against chain-of-thought performance
- Run both scripts to get complete comparison data

---

## How to Run Evaluations

### Running Algorithm Evaluation

```bash
cd scripts
python3 algorithms_evaluation.py
```

**Requirements:**
- Tiered word list (`tiered_wordlist.txt` or equivalent) accessible from script location
- All algorithm strategies (CSS, VOI, Random, PureRandom) must be importable
- Engines (WordleEnv) must be accessible
- SimpleAgent and HybridAgent classes handle strategy wrapping

### Running LLM Evaluation

See the **llm_evaluation.py** section above for detailed instructions on running LLM evaluations with environment variables.

---

## Analysis and Visualization Tools

### Summary Statistics Generation

**Script:** `scripts/generate_summary_stats.py`

**Purpose:** Generate comprehensive summary statistics from algorithm evaluation results.

**What it generates:**
- **JSON file** (`summary_stats_{timestamp}.json`) - Machine-readable statistics for programmatic analysis
- **Text file** (`summary_stats_{timestamp}.txt`) - Human-readable formatted report

**Metrics calculated:**
- Overall performance (win rate, avg attempts, min/max attempts)
- Tier-based performance breakdown (performance by word difficulty)
- Distance convergence patterns (average Hamming/Levenshtein by attempt)

**Usage:**
```bash
cd scripts
python3 generate_summary_stats.py [results_csv_path]
```

If no path is provided, automatically uses the most recent `algorithm_results_*.csv` from `results/algorithms/`.

**Output location:** `results/algorithms/`

---

### Visualization Generation

Two complementary scripts generate publication-quality graphs:

#### **1. generate_graphs.py** - Comprehensive Multi-Panel Graphs

Generates 4 comprehensive visualizations combining multiple metrics:

**Graphs generated:**
1. **overall_performance.png** - Win rate and average attempts (side-by-side)
2. **tier_performance.png** - Performance grouped by word difficulty tier
3. **distance_convergence.png** - Hamming and Levenshtein convergence (combined)
4. **attempt_distribution.png** - Box plot showing attempt distributions

**Usage:**
```bash
cd scripts
python3 generate_graphs.py [results_csv_path]
```

#### **2. generate_focused_graphs.py** - Individual Focused Graphs

Generates 5 individual, focused visualizations for specific metrics:

**Graphs generated:**
1. **mean_hamming_per_turn.png** - Mean Hamming distance for each turn (1-6)
2. **mean_levenshtein_per_turn.png** - Mean Levenshtein distance for each turn (1-6)
3. **avg_attempts_by_strategy.png** - Average attempts to win by strategy
4. **hamming_reduction_per_turn.png** - Average Hamming distance reduction per turn
5. **levenshtein_reduction_per_turn.png** - Average Levenshtein distance reduction per turn

**Usage:**
```bash
cd scripts
python3 generate_focused_graphs.py [results_csv_path]
```

**Output location:** `results/algorithms/plots/`

**Requirements:**
- `matplotlib` and `seaborn` (listed in `requirements.txt`)
- Install via: `pip install -r requirements.txt`

**Features:**
- Publication-quality 300 DPI PNG images
- Consistent color schemes across graphs
- Value labels on bar charts
- Grid lines and legends for readability
- Automatic detection of most recent results

---

### Results Directory Structure

```
results/
├── algorithms/
│   ├── algorithm_results_{timestamp}.csv   # Detailed game-by-game data
│   ├── summary_stats_{timestamp}.json      # Machine-readable statistics
│   ├── summary_stats_{timestamp}.txt       # Human-readable report
│   └── plots/                              # All generated graphs
│       ├── overall_performance.png
│       ├── tier_performance.png
│       ├── distance_convergence.png
│       ├── attempt_distribution.png
│       ├── mean_hamming_per_turn.png
│       ├── mean_levenshtein_per_turn.png
│       ├── avg_attempts_by_strategy.png
│       ├── hamming_reduction_per_turn.png
│       └── levenshtein_reduction_per_turn.png
│
└── llms/
    ├── model_{name}_{type}_{timestamp}.csv  # LLM evaluation results
    ├── summary_{name}_{type}_{timestamp}.json
    └── plots/                                # LLM-specific graphs
```

---

## Experimental Design

### Controlled Variables
- **Same target words:** All strategies play the same 100 games (25 per tier)
- **Tiered word selection:** Balanced representation across word frequency levels
- **Same word list:** Identical candidate pool for all strategies
- **Same conditions:** 6 max attempts, same reward structure

### Measured Variables
- Win rate (overall and per tier)
- Average attempts (overall and per tier)
- Total reward
- Guess-to-target distance progression (Hamming and Levenshtein)
- Strategy behavior patterns (via guess history)
- Performance variation across word frequency tiers

### Reproducibility
- Fixed random seed (42) ensures same target words across runs
- Timestamped output files preserve all experimental data
- Detailed CSV allows post-hoc analysis

---

## Analysis Use Cases

The detailed CSV output enables various analyses:

1. **Performance comparison:** Win rates and efficiency across all 8 strategies
2. **Tier-based analysis:** How word frequency affects algorithm performance
3. **Hybrid strategy evaluation:** Do strategy combinations outperform single strategies?
4. **Learning curves:** How both distance metrics decrease over attempts
5. **Distance metric comparison:** Hamming vs Levenshtein convergence patterns
6. **Strategy patterns:** Which opening guesses each algorithm prefers (by tier)
7. **Failure analysis:** Which words/tiers are hardest for each strategy
8. **Reward optimization:** Which strategy (basic or hybrid) maximizes total reward
9. **Strategy switching impact:** Does switching strategies mid-game help or hurt?
10. **Difficulty scaling:** Do all strategies struggle equally on Tier 4 vs Tier 1?

---

## Integration with Research

This evaluation system supports the larger research goal of:
- Comparing preference elicitation algorithms (basic and hybrid)
- Testing whether strategy combinations improve performance
- Measuring dual distance metrics for deeper insight
- Testing LLM performance against traditional and hybrid algorithms
- Analyzing how word frequency (tiers) affects difficulty
- Measuring exploration vs exploitation trade-offs
- Understanding when strategy switching is beneficial

---

## Hybrid LLM-Algorithm Evaluations

### Overview

Hybrid strategies combine Large Language Models with traditional algorithms (CSS) to test whether integrating LLM intuition with algorithmic optimization improves Wordle-solving performance.

**Location:** `scripts/hybrid/`

### Hybrid Strategies

Four hybrid approaches are evaluated:

1. **LLM-then-CSS**: LLM makes first guess, CSS handles remaining guesses
2. **CSS-then-LLM**: CSS makes first 2 guesses (optimal opening), LLM handles rest
3. **Threshold-Based**: CSS when candidates > threshold, LLM when ≤ threshold (default: 50)
4. **Alternating**: Alternates between LLM and CSS on each turn

### Staged Testing Approach

To efficiently validate hybrid strategies, evaluations follow a staged approach:

#### **Stage 1: Quick Validation** ✨ Recommended starting point
- **Purpose**: Determine if any hybrid shows promise
- **Configuration**:
  - 3 models: mistral-small-3.1, llama-3.3-70b-instruct, mistral-7b-instruct
  - 4 strategies: All hybrid approaches
  - 10 games per combination (120 total games)
- **Time**: ~2-3 hours
- **Cost**: Minimal (~$0.12-$0.36 in API calls)
- **Output**: `results/hybrids/stage1/`

**Run Stage 1:**
```bash
cd scripts/hybrid
./run_stage1_test.sh
```

**Analyze Results:**
```bash
python3 analyze_stage1_results.py
```

#### **Stage 2: Full Strategy Evaluation**
- **When**: If Stage 1 shows hybrid < 3.79 avg attempts (beats pure CSS)
- **Configuration**: Best 1-2 strategies × 2-3 models × 100 games
- **Time**: ~5-10 hours
- **Purpose**: Validate with full canonical test set

#### **Stage 3: Comprehensive Model Comparison**
- **When**: If Stage 2 confirms hybrid advantage
- **Configuration**: Best strategy × all 11 models × 100 games
- **Time**: ~10-20 hours
- **Purpose**: Publication-ready comprehensive comparison

### Decision Criteria

**Baseline Comparisons:**
- Pure CSS: 98% win rate, **3.79 avg attempts** ← Target to beat
- Pure LLMs: 89-100% win rate, 4.03-4.47 avg attempts

**Stage 1 → Stage 2:** Proceed if any hybrid achieves < 3.79 avg attempts

**Stage 2 → Stage 3:** Proceed if hybrid consistently < 3.79 across models

**If hybrids don't improve:** Document findings that hybrids don't provide benefit

### Output Format

Hybrid evaluations produce the same output format as other evaluations:

**CSV Files** (`results/hybrids/`):
```
{strategy}_{model}_{timestamp}.csv
```
Contains:
- Game number, target word, win/loss, attempts
- All guesses with feedback, Hamming and Levenshtein distances
- Strategy used for each guess (for threshold and alternating strategies)

**Summary JSON** (`results/hybrids/`):
```
summary_{strategy}_{model}_{timestamp}.json
```
Contains:
- Strategy name and configuration (threshold, css_turns, start_with)
- Total games, wins, win rate
- Average attempts when won
- Timestamp

### Environment Variables

| Variable | Description | Default | Strategies |
|----------|-------------|---------|------------|
| `NAVIGATOR_UF_API_KEY` | API key (required) | - | All |
| `MODEL` | LLM model name | `llama-3.3-70b-instruct` | All |
| `NUM_GAMES` | Games to evaluate | 100 | All |
| `CSS_TURNS` | CSS turns before LLM switch | 2 | css_then_llm |
| `THRESHOLD` | Candidate count for switching | 50 | threshold_hybrid |
| `START_WITH` | First strategy (`llm` or `css`) | `llm` | alternating_hybrid |

### Individual Script Usage

Each hybrid strategy can be run independently:

```bash
cd scripts/hybrid

# LLM-then-CSS
python3 llm_then_css.py

# CSS-then-LLM (customizable)
CSS_TURNS=3 python3 css_then_llm.py

# Threshold-based (customizable)
THRESHOLD=30 python3 threshold_hybrid.py

# Alternating (customizable)
START_WITH=css python3 alternating_hybrid.py
```

### Research Questions

1. **Do hybrids outperform pure approaches?**
   - Can any hybrid beat CSS's 3.79 avg attempts?
   - Do hybrids achieve better win rates than LLMs?

2. **Which hybrid strategy is most effective?**
   - Opening-focused (LLM-then-CSS)?
   - Closing-focused (CSS-then-LLM)?
   - Context-aware (threshold-based)?
   - Balanced (alternating)?

3. **When is each approach beneficial?**
   - Early game (opening moves)?
   - Late game (closing with few candidates)?
   - Throughout (alternating)?

4. **Model dependence:**
   - Do better LLMs make better hybrids?
   - Do weaker LLMs benefit more from CSS support?

5. **Cost-benefit trade-off:**
   - Is slight performance gain worth LLM API costs?
   - Which strategy minimizes LLM calls while maximizing performance?

### Implementation Details

**Common Features:**
- All use canonical test set (100 words)
- LLM calls include retry logic with exponential backoff
- Automatic fallback to CSS if LLM fails
- Both Hamming and Levenshtein distances tracked
- Results compatible with existing analysis tools

**Strategy Classes:**
- `LLMThenCSSStrategy`: Simple turn-based switch
- `CSSThenLLMStrategy`: Configurable CSS opening length
- `ThresholdHybridStrategy`: Dynamic switching based on candidate count
- `AlternatingHybridStrategy`: Turn-by-turn alternation

### Integration with Results Documentation

After completing hybrid evaluations, update `docs/results.md` with:
- Hybrid strategy performance tables
- Comparison to pure algorithms and LLMs
- Analysis of when hybrids are beneficial
- Cost-benefit analysis
- Recommendations for production use

---

## Additional Evaluations

More evaluation scripts will be added here as development continues.

**Completed:**
- Algorithm evaluations (8 strategies)
- LLM evaluations (11 models × 2 prompting types)
- Hybrid LLM-algorithm evaluations (4 strategies, staged approach)

**Future additions:**
- Statistical significance testing between approaches
- Advanced visualization and analysis scripts
- Cross-task evaluation (other word games)
