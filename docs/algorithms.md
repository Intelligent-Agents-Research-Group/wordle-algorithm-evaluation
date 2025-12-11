# Preference Elicitation Algorithms

## Overview

This document describes the four preference elicitation algorithms implemented for Wordle gameplay evaluation. These algorithms represent different approaches to constraint satisfaction and information-theoretic decision-making.

## Algorithm Descriptions

### 1. CSS Strategy (Constraint Satisfaction Search)
**File:** `css_strategy.py`

- **Algorithm:** Entropy-based information gain maximization
- **How it works:** Selects guesses that maximize expected information gain using Shannon entropy
- **Key method:** `_calculate_information_gain()` - calculates entropy reduction for each potential guess

This algorithm leverages information theory to make optimal guesses that maximally reduce the search space.

---

### 2. VOI Strategy (Value of Information)
**File:** `voi_strategy.py`

- **Algorithm:** Bayesian belief tracking with exploration/exploitation balance
- **How it works:** Maintains probability beliefs over candidates, balances information gain vs expected reward
- **Key methods:**
  - Bayesian belief updates
  - VOI calculation combining entropy and expected reward
  - Adaptive exploration→exploitation shift

Theoretically sophisticated approach that combines Bayesian reasoning with value-based decision making.

---

### 3. Random Strategy (Filtered Random)
**File:** `random_strategy.py`

- **Algorithm:** Constraint filtering + random selection
- **How it works:** Filters candidates based on feedback, then picks randomly
- **Key insight:** Tests whether proper constraint filtering alone is sufficient for good performance

Serves as a middle-ground baseline between pure random and optimized strategies.

---

### 4. Pure Random Strategy (Baseline)
**File:** `pure_random_strategy.py`

- **Algorithm:** Random guessing with NO filtering
- **How it works:** Completely ignores feedback, always guesses randomly
- **Purpose:** Control group to measure value of constraint satisfaction

Serves as a baseline to demonstrate the importance of incorporating feedback and constraint filtering.

---

## Performance Comparison

Performance metrics will be updated after running comprehensive tests across all word frequency tiers.

| Algorithm | Win Rate | Avg Attempts | Approach |
|-----------|----------|--------------|----------|
| CSS (Constraint Satisfaction Search) | TBD | TBD | Information gain maximization |
| Random (Filtered) | TBD | TBD | Constraint filtering + random |
| VOI (Value of Information) | TBD | TBD | Bayesian belief tracking |
| Pure Random (Baseline) | TBD | TBD | No filtering (control) |

## Testing Plan

- 25 games per word frequency tier (Tier 1-4)
- 100 total games per algorithm
- Metrics tracked: win rate, average attempts, performance by tier
- Comparison against LLM-based agents

## Next Steps

- Run comprehensive testing across all tiers
- Compare algorithm performance against LLM agents
- Analyze performance variation by word frequency tier
- Document insights and findings
