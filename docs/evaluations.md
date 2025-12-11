# Algorithm Evaluations

## Overview

The evaluations system provides comprehensive testing and comparison of Wordle-solving algorithms. This system runs controlled experiments to measure performance across multiple strategies.

**Note:** Additional evaluation scripts will be added as the research progresses.

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

## Additional Evaluations

More evaluation scripts will be added here as development continues.

**Planned additions:**
- Tier-based evaluation (25 games per tier)
- LLM agent evaluation
- Statistical significance testing
- Visualization and analysis scripts
