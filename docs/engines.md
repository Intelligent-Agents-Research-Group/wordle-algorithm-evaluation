# Game Engines

## Overview

The game engines provide the core infrastructure for running Wordle experiments. The system consists of two main components that work together: the game environment and the guessing agent.

---

## Components

### 1. WordleEnv (wordle_env.py) - Wordle Environment

**Purpose:** The actual Wordle game implementation that manages game state, rules, and reward structure.

**Code:** Lines 1-100 contain core game logic

#### Key Features

**Game Management:**
- Randomly selects target words from provided word list
- Tracks attempts (max 6 by default)
- Maintains game history
- Manages game state (done/not done)

**Reward System:**
- **Progressive Penalties:** Base penalty of -1.0 that increases by 50% with each attempt
  - Attempt 1: -1.0
  - Attempt 2: -1.5
  - Attempt 3: -2.0
  - etc.
- **Feedback Rewards:**
  - Green letter (correct position): +0.5
  - Yellow letter (wrong position): +0.2
- **Success Reward:** +10.0 for finding the target word
- Tracks cumulative reward throughout the game

**Feedback Generation:**
- Provides feedback using standard Wordle color system: **Green/Yellow/Gray**
- Returns feedback array: `["G", "Y", "-", "G", "Y"]`
  - `G` = **Green** (correct letter, correct position)
  - `Y` = **Yellow** (correct letter, wrong position)
  - `-` = **Gray** (letter not in word)
- Properly handles duplicate letters

#### Key Methods

| Method | Description |
|--------|-------------|
| `reset()` | Starts new game with random target word |
| `guess(word)` | Processes a guess, returns (feedback, reward) |
| `_generate_feedback(guess)` | Generates Wordle feedback for a guess |
| `get_total_reward()` | Returns cumulative reward for the game |
| `get_penalty_for_attempt(n)` | Calculates penalty for attempt number n |

#### Usage Example
```python
env = WordleEnv(word_list)
target = env.reset()
feedback, reward = env.guess("CRANE")
```

---

### 2. GuessingAgent (guessing_agent.py) - Generic Agent Wrapper

**Purpose:** Strategy-agnostic wrapper that coordinates between any strategy and the game environment.

#### Key Features

**Generic Agent Capabilities:**
- Wraps any strategy and manages candidate filtering
- Tracks game history across all guesses
- Coordinates between strategy and environment
- Accumulates rewards throughout gameplay
- Delegates decision-making to the strategy

**Strategy Integration:**
- Strategy-agnostic interface - works with any algorithm
- Accepts any strategy object from the algorithms folder
- Strategy must implement:
  - `update_belief(candidates, guess, feedback)` - filter candidates based on feedback
  - `select_guess(candidates, history)` - choose next guess

#### Key Methods

| Method | Description |
|--------|-------------|
| `reset()` | Resets agent state for new game |
| `select_guess()` | Asks strategy to select next guess |
| `update(guess, feedback, reward)` | Updates beliefs and history after a guess |
| `get_total_reward()` | Returns cumulative reward |

#### Usage Example
```python
from algorithms.css_strategy import CSSStrategy

strategy = CSSStrategy()
agent = GuessingAgent(word_list, strategy)
guess = agent.select_guess()
agent.update(guess, feedback, reward)
```

---

## System Architecture

```
┌─────────────────┐
│  WordleEnv      │
│  (Game Logic)   │
│                 │
│  - Target word  │
│  - Feedback     │
│  - Rewards      │
└────────┬────────┘
         │
         │ guess → feedback, reward
         │
┌────────▼────────┐
│ GuessingAgent   │
│ (Player)        │
│                 │
│  - Candidates   │
│  - History      │
└────────┬────────┘
         │
         │ delegates to
         │
┌────────▼────────┐
│   Strategy      │
│   (Algorithm)   │
│                 │
│  - CSS          │
│  - VOI          │
│  - Random       │
│  - Pure Random  │
└─────────────────┘
```

## Reward Structure Rationale

The reward system is designed to:
1. **Penalize inefficiency:** Progressive penalties encourage faster solutions
2. **Reward information gain:** Feedback rewards incentivize gathering useful information
3. **Maximize success:** Large success reward prioritizes winning over speed
4. **Enable RL training:** Reward structure supports reinforcement learning experiments

## Integration with Algorithms

All strategies in the `algorithms/` folder implement the required interface:
- `update_belief()` - Constraint satisfaction / belief updating
- `select_guess()` - Decision making / guess selection

The agent acts as a bridge between the environment and the strategy, allowing any algorithm to play Wordle through a consistent interface.
