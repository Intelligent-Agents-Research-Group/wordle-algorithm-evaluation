#!/usr/bin/env python3
"""
Flexible Hybrid Strategy: Schedule-Based Engine

Uses a round-to-strategy schedule dict mapping rounds 1-6 to a strategy name.
This enables arbitrary handoff, alternation, and multi-phase hybrid configurations.

Examples:
    L->C: {1: "llm", 2: "css", 3: "css", 4: "css", 5: "css", 6: "css"}
    L*2->V: {1: "llm", 2: "llm", 3: "voi", 4: "voi", 5: "voi", 6: "voi"}
    C->L: {1: "css", 2: "llm", 3: "llm", 4: "llm", 5: "llm", 6: "llm"}

Configured via SCHEDULE env var (JSON string) and CONFIG_NAME for file naming.
"""

import os
import csv
import time
import json
import random
import re
import sys
from datetime import datetime
from typing import List, Tuple, Dict
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'engines'))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'algorithms'))
sys.path.insert(0, str(Path(__file__).parent.parent))

from wordle_env import WordleEnv
from test_set_loader import get_test_words_only
from css_strategy import CSSStrategy
from voi_strategy import VOIStrategy
from random_strategy import RandomStrategy
from css_true_strategy import CSSTrueStrategy


# Valid strategy names for schedules
VALID_STRATEGIES = {"llm", "css", "css_true", "voi", "random"}

# Models that require the GPT API key (frontier models via Navigator)
GPT_API_MODELS = {
    "gpt-5", "gpt-5-mini", "gpt-4.1", "gpt-4.1-mini", "gpt-4o", "gpt-4o-mini",
    "claude-3-opus", "claude-3.7-sonnet", "claude-4-sonnet", "claude-4.5-sonnet",
    "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"
}

# Direct API routing: model_name -> (provider, api_model_id)
# If a personal API key is set, these models bypass Navigator entirely.
DIRECT_API_MODELS = {
    "gpt-5": ("openai", "gpt-5"),
}


def _get_direct_api_config(model_name: str):
    """Check if a model should use a direct API key instead of Navigator.

    Returns (provider, api_key, model_id) if direct key is available, else None.
    """
    if model_name not in DIRECT_API_MODELS:
        return None
    provider, model_id = DIRECT_API_MODELS[model_name]
    if provider == "openai":
        key = os.getenv("GPT_API_KEY")
        if key:
            return (provider, key, model_id)
    elif provider == "anthropic":
        key = os.getenv("CLAUDE_API_KEY")
        if key:
            return (provider, key, model_id)
    return None


def _get_api_key_for_model(model_name: str) -> str:
    """Get the appropriate Navigator API key based on model name.

    Frontier models (GPT, Claude, Gemini) use NAVIGATOR_UF_GPT_API_KEY.
    Open source models (Llama, Mistral, etc.) use NAVIGATOR_UF_API_KEY.
    """
    if model_name in GPT_API_MODELS:
        key = os.getenv("NAVIGATOR_UF_GPT_API_KEY")
        if not key:
            raise RuntimeError(f"NAVIGATOR_UF_GPT_API_KEY not set (required for {model_name})")
        return key
    else:
        key = os.getenv("NAVIGATOR_UF_API_KEY")
        if not key:
            raise RuntimeError(f"NAVIGATOR_UF_API_KEY not set (required for {model_name})")
        return key


def _create_algo_strategy(name: str):
    """Create an algorithm strategy instance by name."""
    if name == "css":
        return CSSStrategy()
    elif name == "css_true":
        return CSSTrueStrategy()
    elif name == "voi":
        return VOIStrategy()
    elif name == "random":
        return RandomStrategy()
    else:
        raise ValueError(f"Unknown algorithm: {name}")


class FlexibleHybridStrategy:
    """
    Hybrid strategy using a round-to-strategy schedule.
    Each round (1-6) maps to a strategy name: 'llm', 'css', 'css_true', 'voi', or 'random'.
    """

    def __init__(self, schedule: Dict[int, str], model_name: str = "llama-3.3-70b-instruct",
                 temperature: float = 0.7, prompt_type: str = "zero-shot"):
        self.schedule = schedule
        self.model_name = model_name
        self.temperature = temperature
        self.prompt_type = prompt_type.lower()
        self.turn_number = 0
        self.api_base = os.getenv("NAVIGATOR_API_ENDPOINT", "https://api.navigator.uf.edu/v1")

        # Validate schedule
        for rnd, strat in schedule.items():
            if strat not in VALID_STRATEGIES:
                raise ValueError(f"Invalid strategy '{strat}' for round {rnd}. Must be one of {VALID_STRATEGIES}")

        # Initialize all needed algorithm strategies (deduplicate)
        algo_names = {s for s in schedule.values() if s != "llm"}
        self.algo_strategies = {name: _create_algo_strategy(name) for name in algo_names}

        # Pick a primary algorithm for belief updates (prefer css > voi > css_true > random)
        priority = ["css", "voi", "css_true", "random"]
        self._primary_algo = None
        for p in priority:
            if p in self.algo_strategies:
                self._primary_algo = self.algo_strategies[p]
                break
        # If no algorithm in schedule (all LLM), use CSS as default for belief updates
        if self._primary_algo is None:
            self._primary_algo = CSSStrategy()

    def update_belief(self, candidates: List[str], guess: str, feedback: List[str]) -> List[str]:
        """Update candidates based on feedback - delegates to primary algorithm."""
        return self._primary_algo.update_belief(candidates, guess, feedback)

    def get_guess(self, candidates: List[str], history: List[Tuple[str, List[str]]], attempt: int = None) -> str:
        """Get next guess based on the schedule for the current round.

        Args:
            candidates: Remaining valid candidates
            history: List of (guess, feedback) tuples for valid guesses only
            attempt: Actual attempt number (1-indexed). If None, uses len(history)+1.
                     Use explicit attempt when invalid guesses occur to keep schedule aligned.
        """
        # Use explicit attempt if provided, otherwise fall back to history length
        self.turn_number = attempt if attempt is not None else len(history) + 1
        strategy_name = self.schedule.get(self.turn_number, "llm")

        if strategy_name == "llm":
            return self._get_llm_guess(candidates, history)
        else:
            algo = self.algo_strategies[strategy_name]
            return algo.select_guess(candidates, history)

    def get_strategy_label(self, turn: int) -> str:
        """Return the human-readable label for which strategy is used on a given turn."""
        name = self.schedule.get(turn, "llm")
        return name.upper()

    def _call_anthropic(self, prompt: str, api_key: str, model_id: str) -> str:
        """Call Anthropic API directly. Returns response text."""
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model_id,
            max_tokens=1024,
            temperature=self.temperature,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    def _call_openai(self, prompt: str, api_key: str, model_id: str, base_url: str = None) -> str:
        """Call OpenAI-compatible API. Returns response text."""
        import openai
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        client = openai.OpenAI(**kwargs)
        REASONING_MODELS = {"gpt-oss-120b", "gpt-5"}
        max_tok = 16384 if self.model_name in REASONING_MODELS else 150
        # OpenAI's newer reasoning models require max_completion_tokens and don't support temperature
        is_direct_reasoning = (not base_url and self.model_name in REASONING_MODELS)
        tok_param = {"max_completion_tokens": max_tok} if is_direct_reasoning else {"max_tokens": max_tok}
        call_kwargs = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            **tok_param
        }
        if not is_direct_reasoning:
            call_kwargs["temperature"] = self.temperature
        response = client.chat.completions.create(**call_kwargs)
        content = response.choices[0].message.content
        if content is None:
            content = getattr(response.choices[0].message, 'reasoning_content', None) or ""
        return content

    def _get_llm_guess(self, candidates: List[str], history: List[Tuple[str, List[str]]]) -> str:
        """Get guess from LLM with retry logic."""
        try:
            prompt = self._build_prompt(candidates, history)

            # Check for direct API routing first
            direct = _get_direct_api_config(self.model_name)

            for attempt in range(5):
                try:
                    if direct:
                        provider, api_key, model_id = direct
                        if provider == "anthropic":
                            text = self._call_anthropic(prompt, api_key, model_id).strip()
                        else:
                            text = self._call_openai(prompt, api_key, model_id).strip()
                    else:
                        text = self._call_openai(
                            prompt,
                            _get_api_key_for_model(self.model_name),
                            self.model_name,
                            base_url=self.api_base
                        ).strip()

                    guess = self._extract_guess(text, history, candidates)
                    if guess:
                        return guess
                    # LLM returned invalid guess - log and retry
                    print(f"LLM API attempt {attempt+1}/5 failed: LLM returned invalid guess from response: {text[:100]}")
                except Exception as e:
                    print(f"LLM API attempt {attempt+1}/5 failed: {e}")

                if attempt < 4:
                    time.sleep(2 ** attempt + random.uniform(0, 1))

            # All retries exhausted - return None to mark game as lost (no fallback)
            print(f"LLM failed after 5 attempts - marking game as lost")
            return None

        except Exception as e:
            # Initialization failed - return None to mark game as lost (no fallback)
            print(f"LLM initialization failed: {e} - marking game as lost")
            return None

    def _build_prompt(self, candidates: List[str], history: List[Tuple[str, List[str]]]) -> str:
        """Build prompt for LLM (supports both zero-shot and CoT)."""
        if self.prompt_type == "cot":
            prompt = (
                "You are an expert Wordle player. Use brief, structured reasoning.\n"
                "Return output in this exact format:\n"
                "THINKING: <your concise step-by-step reasoning>\n"
                "FINAL: <ONE 5-letter guess only>\n\n"
                "Feedback codes: G=green (correct letter, correct position), "
                "Y=yellow (correct letter, wrong position), -=letter not in word.\n\n"
            )

            if history:
                prompt += "Previous attempts:\n"
                for guess, feedback in history:
                    fb_str = ''.join(feedback)
                    guess_upper = guess.upper()
                    letter_breakdown = "  ".join(
                        [f"{guess_upper[i]}:{fb_str[i]}" for i in range(min(len(guess_upper), len(fb_str)))])
                    prompt += f"- Guess: {guess}  Feedback: {fb_str}\n"
                    prompt += f"  Per letter: {letter_breakdown}\n"

            if len(candidates) <= 50:
                candidates_str = ", ".join(candidates)
            else:
                sample = candidates[:30] + ["..."] + candidates[-20:]
                candidates_str = ", ".join(sample)

            prompt += (
                f"\nAllowed words remaining: {len(candidates)}\n"
                f"Candidate words: {candidates_str}\n\n"
                "Constraints:\n"
                "• Do NOT repeat previous guesses.\n"
                "• The FINAL line must be exactly ONE valid 5-letter word from the allowed list.\n"
                "• Keep THINKING concise (1-5 short lines)."
            )
        else:
            prompt = "You are playing Wordle. Your goal is to guess a 5-letter word.\n\n"

            if history:
                prompt += "Previous guesses:\n"
                for guess, feedback in history:
                    feedback_str = ''.join(
                        ['🟩' if f == 'G' else '🟨' if f == 'Y' else '⬜' for f in feedback])
                    prompt += f"{guess}: {feedback_str}\n"
                prompt += "\n"

            if len(candidates) <= 30:
                prompt += f"Remaining possible words ({len(candidates)}): {', '.join(candidates)}\n\n"
            else:
                # Always show a sample so LLM knows which words are valid
                sample = random.sample(candidates, min(30, len(candidates)))
                prompt += f"Remaining possible words ({len(candidates)}, showing sample): {', '.join(sample)}\n\n"

            prompt += "Based on the feedback, what should the next guess be?\n"
            prompt += "IMPORTANT: Your guess MUST be from the remaining possible words shown above.\n"
            prompt += "Return ONLY a single 5-letter word in uppercase, nothing else.\n"
            prompt += "Your guess: "

        return prompt

    def _extract_guess(self, text: str, history: List[Tuple[str, List[str]]], candidates: List[str]) -> str:
        """Extract valid 5-letter word from LLM response."""
        if not text:
            return None

        used = {g for g, _ in history}

        if self.prompt_type == "cot":
            final_match = re.search(r'FINAL\s*:\s*([A-Za-z]{5})\b', text, re.IGNORECASE)
            if final_match:
                word = final_match.group(1).upper()
                if word not in used:
                    return word

        words = re.findall(r'\b[A-Za-z]{5}\b', text.upper())

        for word in words:
            if word not in used and word in candidates:
                return word

        for word in words:
            if word not in used:
                return word

        return None


# ----------------- Guessing Agent -----------------

class GuessingAgent:
    """Agent that uses the flexible hybrid strategy to play Wordle."""

    def __init__(self, word_list, strategy):
        self.word_list = word_list
        self.strategy = strategy
        self.candidates = list(word_list)
        self.history = []

    def reset(self):
        """Reset agent for new game."""
        self.candidates = list(self.word_list)
        self.history = []
        self.strategy.turn_number = 0

    def select_guess(self, attempt: int = None):
        """Select next guess using strategy.

        Args:
            attempt: Actual attempt number (1-indexed). Pass this to keep
                     schedule aligned when invalid guesses don't update history.
        """
        return self.strategy.get_guess(self.candidates, self.history, attempt)

    def update(self, guess, feedback, reward):
        """Update agent state after guess."""
        if feedback and isinstance(feedback[0], int):
            str_feedback = ['G' if f == 2 else 'Y' if f == 1 else '-' for f in feedback]
        else:
            str_feedback = feedback

        self.history.append((guess, str_feedback))
        self.candidates = self.strategy.update_belief(self.candidates, guess, str_feedback)


# ----------------- Distance Metrics -----------------

def hamming_distance(word1: str, word2: str) -> int:
    """Calculate Hamming distance between two words."""
    return sum(c1 != c2 for c1, c2 in zip(word1.upper(), word2.upper()))


def levenshtein_distance(word1: str, word2: str) -> int:
    """Calculate Levenshtein distance between two words."""
    if len(word1) < len(word2):
        return levenshtein_distance(word2, word1)
    if len(word2) == 0:
        return len(word1)

    previous_row = range(len(word2) + 1)
    for i, c1 in enumerate(word1):
        current_row = [i + 1]
        for j, c2 in enumerate(word2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


# ----------------- Main Evaluation -----------------

def run_evaluation(num_games=100, model_name="llama-3.3-70b-instruct",
                   schedule=None, config_name="flexible", prompt_type="zero-shot"):
    """Run evaluation on canonical test set with a schedule-based hybrid strategy."""

    if schedule is None:
        schedule = {1: "llm", 2: "css", 3: "css", 4: "css", 5: "css", 6: "css"}

    print("=" * 80)
    print(f"FLEXIBLE HYBRID EVALUATION: {config_name}")
    print("=" * 80)
    print(f"Model: {model_name}")
    print(f"Prompt Type: {prompt_type}")
    print(f"Schedule: {json.dumps(schedule)}")
    print(f"Games: {num_games}")
    print("=" * 80)

    # Load word list and test set
    script_dir = Path(__file__).parent.parent.parent
    with open(script_dir / 'wordlist' / 'wordlist.txt', 'r') as f:
        word_list = [line.strip().upper() for line in f if line.strip()]

    test_words = get_test_words_only()[:num_games]

    # Initialize strategy and agent
    strategy = FlexibleHybridStrategy(
        schedule=schedule, model_name=model_name,
        temperature=0.7, prompt_type=prompt_type
    )
    agent = GuessingAgent(word_list, strategy)

    # Results storage
    results = []
    wins = 0
    total_attempts = 0

    for game_num, target_word in enumerate(test_words, 1):
        print(f"\nGame {game_num}/{num_games}: Target = {target_word}")

        env = WordleEnv([target_word])
        env.reset()
        agent.reset()

        game_result = {
            'game_number': game_num,
            'target_word': target_word,
            'won': False,
            'attempts': 0,
            'guesses': [],
            'feedbacks': [],
            'hamming_distances': [],
            'levenshtein_distances': [],
            'strategy_used': []
        }

        for attempt in range(1, 7):
            guess = agent.select_guess(attempt)  # Pass attempt to keep schedule aligned
            if not guess:
                print(f"  Attempt {attempt}: No valid guess available")
                break

            feedback, reward = env.guess(guess)
            agent.update(guess, feedback, reward)

            ham_dist = hamming_distance(guess, target_word)
            lev_dist = levenshtein_distance(guess, target_word)
            feedback_str = ''.join(feedback)

            strategy_used = strategy.get_strategy_label(attempt)
            game_result['strategy_used'].append(strategy_used)

            print(f"  Attempt {attempt} [{strategy_used}]: {guess} -> {feedback_str} (H:{ham_dist}, L:{lev_dist})")

            game_result['guesses'].append(guess)
            game_result['feedbacks'].append(feedback_str)
            game_result['hamming_distances'].append(ham_dist)
            game_result['levenshtein_distances'].append(lev_dist)
            game_result['attempts'] = attempt

            if all(f == "G" for f in feedback):
                game_result['won'] = True
                wins += 1
                total_attempts += attempt
                print(f"  Won in {attempt} attempts!")
                break

        if not game_result['won']:
            print(f"  Failed to find word")

        results.append(game_result)

    # Calculate statistics
    win_rate = wins / num_games if num_games > 0 else 0
    avg_attempts = total_attempts / wins if wins > 0 else 0

    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    print(f"Games played: {num_games}")
    print(f"Wins: {wins}")
    print(f"Win rate: {win_rate * 100:.1f}%")
    print(f"Average attempts (when won): {avg_attempts:.2f}")
    print("=" * 80)

    # Save results
    output_dir_env = os.getenv("OUTPUT_DIR")
    if output_dir_env:
        output_dir = Path(output_dir_env)
    else:
        output_dir = script_dir / 'results' / 'workshop'
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prompt_suffix = "_cot" if prompt_type == "cot" else ""

    # Use config_name for file naming
    safe_config = config_name.replace(" ", "_").replace("/", "_")
    csv_file = output_dir / f"{safe_config}_{model_name}{prompt_suffix}_{timestamp}.csv"

    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)

        header = ['game_number', 'target_word', 'won', 'attempts']
        for i in range(1, 7):
            header.extend([f'guess_{i}', f'feedback_{i}', f'hamming_{i}', f'levenshtein_{i}', f'strategy_{i}'])
        writer.writerow(header)

        for result in results:
            row = [result['game_number'], result['target_word'], result['won'], result['attempts']]
            for i in range(6):
                if i < len(result['guesses']):
                    row.extend([
                        result['guesses'][i],
                        result['feedbacks'][i],
                        result['hamming_distances'][i],
                        result['levenshtein_distances'][i],
                        result['strategy_used'][i] if i < len(result['strategy_used']) else ''
                    ])
                else:
                    row.extend(['', '', '', '', ''])
            writer.writerow(row)

    # Save summary JSON
    summary = {
        'strategy': 'flexible_hybrid',
        'config_name': config_name,
        'model_name': model_name,
        'prompt_type': prompt_type,
        'schedule': {str(k): v for k, v in schedule.items()},
        'total_games': num_games,
        'wins': wins,
        'win_rate': win_rate,
        'avg_attempts_when_won': avg_attempts,
        'timestamp': timestamp
    }

    json_file = output_dir / f"summary_{safe_config}_{model_name}{prompt_suffix}_{timestamp}.json"
    with open(json_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\nResults saved to:")
    print(f"  {csv_file}")
    print(f"  {json_file}")

    return results, summary


if __name__ == "__main__":
    model_name = os.getenv("MODEL", "llama-3.3-70b-instruct")
    num_games = int(os.getenv("NUM_GAMES", "100"))
    prompt_type = os.getenv("PROMPT_TYPE", "zero-shot")
    config_name = os.getenv("CONFIG_NAME", "flexible")

    # Parse schedule from env var (JSON string)
    schedule_str = os.getenv("SCHEDULE")
    if schedule_str:
        raw = json.loads(schedule_str)
        schedule = {int(k): v for k, v in raw.items()}
    else:
        # Default: LLM round 1, CSS rounds 2-6
        schedule = {1: "llm", 2: "css", 3: "css", 4: "css", 5: "css", 6: "css"}

    # Check API key if LLM is in schedule
    if "llm" in schedule.values():
        if _get_direct_api_config(model_name):
            pass  # Direct API key available
        elif model_name in GPT_API_MODELS:
            if not os.getenv("NAVIGATOR_UF_GPT_API_KEY"):
                print(f"ERROR: NAVIGATOR_UF_GPT_API_KEY not set (required for {model_name})")
                sys.exit(1)
        else:
            if not os.getenv("NAVIGATOR_UF_API_KEY"):
                print(f"ERROR: NAVIGATOR_UF_API_KEY not set (required for {model_name})")
                sys.exit(1)

    run_evaluation(
        num_games=num_games,
        model_name=model_name,
        schedule=schedule,
        config_name=config_name,
        prompt_type=prompt_type
    )
