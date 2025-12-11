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

## How to Run

```bash
cd scripts
python3 algorithms_evaluation.py
```

**Requirements:**
- Tiered word list (`tiered_wordlist.txt` or equivalent) accessible from script location
- All algorithm strategies (CSS, VOI, Random, PureRandom) must be importable
- Engines (WordleEnv) must be accessible
- SimpleAgent and HybridAgent classes handle strategy wrapping

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
