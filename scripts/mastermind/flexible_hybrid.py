#!/usr/bin/env python3
"""
Flexible Hybrid Strategy for Mastermind: Schedule-Based Engine

Uses a round-to-strategy schedule dict mapping rounds 1-10 to a strategy name.
This enables arbitrary handoff, alternation, and multi-phase hybrid configurations.

Supports the same hybrid patterns from the workshop paper (Groups A, B, C):
- Group A: Handoff patterns (L→C, C→L, etc.)
- Group B: k-Handoff sweeps (Lk→CSS, CSSk→L, etc.)
- Group C: Alternation patterns

Note: Group D (repair hybrids) are NOT included per research design.

Examples:
    L->C: {1: "llm", 2: "css", 3: "css", ...}
    L*2->V: {1: "llm", 2: "llm", 3: "voi", ...}
    C->L: {1: "css", 2: "llm", 3: "llm", ...}
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

from mastermind_env import MastermindEnv
from mastermind_css_strategy import MastermindCSSStrategy
from mastermind_voi_strategy import MastermindVOIStrategy
from mastermind_random_strategy import MastermindRandomStrategy
from test_set_loader import get_test_codes


# Valid strategy names for schedules
VALID_STRATEGIES = {"llm", "css", "voi", "random"}

# Maximum rounds for Mastermind
MAX_ROUNDS = 10

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
    "claude-4-sonnet": ("anthropic", "claude-sonnet-4-20250514"),
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


def _create_algo_strategy(name: str, num_pegs: int = 4):
    """Create an algorithm strategy instance by name."""
    if name == "css":
        return MastermindCSSStrategy(num_pegs=num_pegs)
    elif name == "voi":
        return MastermindVOIStrategy(num_pegs=num_pegs)
    elif name == "random":
        return MastermindRandomStrategy(num_pegs=num_pegs)
    else:
        raise ValueError(f"Unknown algorithm: {name}")


class MastermindFlexibleHybridStrategy:
    """
    Hybrid strategy using a round-to-strategy schedule for Mastermind.
    Each round (1-10) maps to a strategy name: 'llm', 'css', 'voi', or 'random'.
    """

    def __init__(self, schedule: Dict[int, str], num_pegs: int = 4,
                 model_name: str = "llama-3.3-70b-instruct",
                 temperature: float = 0.7, prompt_type: str = "zero-shot",
                 colors: str = "RGBYOW"):
        self.schedule = schedule
        self.num_pegs = num_pegs
        self.model_name = model_name
        self.temperature = temperature
        self.prompt_type = prompt_type.lower()
        self.colors = colors  # Valid colors for this variant
        self.turn_number = 0
        self.api_base = os.getenv("NAVIGATOR_API_ENDPOINT", "https://api.ai.it.ufl.edu/v1")

        # Validate schedule
        for rnd, strat in schedule.items():
            if strat not in VALID_STRATEGIES:
                raise ValueError(f"Invalid strategy '{strat}' for round {rnd}. Must be one of {VALID_STRATEGIES}")

        # Initialize all needed algorithm strategies (deduplicate)
        algo_names = {s for s in schedule.values() if s != "llm"}
        self.algo_strategies = {name: _create_algo_strategy(name, num_pegs) for name in algo_names}

        # Pick a primary algorithm for belief updates (prefer css > voi > random)
        priority = ["css", "voi", "random"]
        self._primary_algo = None
        for p in priority:
            if p in self.algo_strategies:
                self._primary_algo = self.algo_strategies[p]
                break
        # If no algorithm in schedule (all LLM), use CSS as default for belief updates
        if self._primary_algo is None:
            self._primary_algo = MastermindCSSStrategy(num_pegs=num_pegs)

    def update_belief(self, candidates: List[str], guess: str, feedback: Tuple[int, int]) -> List[str]:
        """Update candidates based on feedback - delegates to primary algorithm."""
        return self._primary_algo.update_belief(candidates, guess, feedback)

    def get_guess(self, candidates: List[str], history: List[Tuple[str, Tuple[int, int]]], attempt: int = None) -> str:
        """Get next guess based on the schedule for the current round.

        Args:
            candidates: Remaining valid candidates
            history: List of (guess, feedback) tuples for valid guesses only
            attempt: Actual attempt number (1-indexed). If None, uses len(history)+1.
                     Use explicit attempt when invalid guesses occur to keep schedule aligned.
        """
        # Use explicit attempt if provided, otherwise fall back to history length
        self.turn_number = attempt if attempt is not None else len(history) + 1
        # Default to first algo in schedule if round exceeds schedule length
        default_algo = next((s for s in self.schedule.values() if s != "llm"), "css")
        strategy_name = self.schedule.get(self.turn_number, default_algo)

        if strategy_name == "llm":
            return self._get_llm_guess(candidates, history)
        else:
            algo = self.algo_strategies[strategy_name]
            return algo.select_guess(candidates, history)

    def get_strategy_label(self, turn: int) -> str:
        """Return the human-readable label for which strategy is used on a given turn."""
        default_algo = next((s for s in self.schedule.values() if s != "llm"), "css")
        name = self.schedule.get(turn, default_algo)
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
        max_tok = 16384 if self.model_name in REASONING_MODELS else 200
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

    def _get_llm_guess(self, candidates: List[str], history: List[Tuple[str, Tuple[int, int]]]) -> str:
        """Get guess from LLM with retry logic. Returns None on failure (no fallback)."""
        prompt = self._build_prompt(candidates, history)

        # Check for direct API routing first
        direct = _get_direct_api_config(self.model_name)

        last_error = None
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
                # LLM returned natural language instead of a code - add correction nudge
                valid_colors = "".join(self.colors) if self.colors else "RGBYOW"
                prompt = (
                    f"Your previous response was not a valid Mastermind code. "
                    f"Valid colors are: {valid_colors}\n"
                    f"You MUST respond with ONLY a {self.num_pegs}-character code "
                    f"using those color letters. Nothing else.\n"
                    f"Example: {valid_colors[:self.num_pegs]}\n"
                    f"Your guess: "
                )
                raise RuntimeError(f"LLM returned no valid code from response: {text[:100]}")
            except Exception as e:
                last_error = e
                print(f"LLM API attempt {attempt+1}/5 failed: {e}")
                if attempt < 4:
                    time.sleep(2 ** attempt + random.uniform(0, 1))

        # All retries exhausted - return None to mark game as lost (no fallback)
        print(f"LLM failed after 5 attempts - marking game as lost")
        return None

    def _build_prompt(self, candidates: List[str], history: List[Tuple[str, Tuple[int, int]]]) -> str:
        """Build prompt for LLM (supports both zero-shot and CoT)."""
        # Build color description based on valid colors for this variant
        color_names = {
            'R': 'Red', 'G': 'Green', 'B': 'Blue', 'Y': 'Yellow',
            'O': 'Orange', 'W': 'White', 'P': 'Purple', 'K': 'blacK'
        }
        colors_desc = ", ".join(f"{c}={color_names[c]}" for c in self.colors)

        if self.prompt_type == "cot":
            prompt = (
                f"You are an expert Mastermind player. The secret code is {self.num_pegs} colors.\n"
                f"Colors: {colors_desc}\n\n"
                "Use brief, structured reasoning.\n"
                "Return output in this exact format:\n"
                "THINKING: <your concise step-by-step reasoning>\n"
                f"FINAL: <ONE {self.num_pegs}-character code only>\n\n"
                "Feedback codes:\n"
                "- Black pegs: correct color in correct position\n"
                "- White pegs: correct color in wrong position\n\n"
            )

            if history:
                prompt += "Previous attempts:\n"
                for guess, (black, white) in history:
                    prompt += f"- Guess: {guess}  Feedback: {black} Black, {white} White\n"

            if len(candidates) <= 50:
                candidates_str = ", ".join(candidates)
            else:
                sample = candidates[:30] + ["..."] + candidates[-20:]
                candidates_str = ", ".join(sample)

            prompt += (
                f"\nPossible codes remaining: {len(candidates)}\n"
                f"Sample candidates: {candidates_str}\n\n"
                "Constraints:\n"
                "• Do NOT repeat previous guesses.\n"
                f"• ONLY use these {len(self.colors)} colors: {self.colors}\n"
                f"• The FINAL line must be exactly ONE valid {self.num_pegs}-character code.\n"
                "• Keep THINKING concise (1-5 short lines)."
            )
        else:
            prompt = (
                f"You are playing Mastermind. Your goal is to guess a secret {self.num_pegs}-color code.\n"
                f"Colors: {colors_desc}\n\n"
            )

            if history:
                prompt += "Previous guesses:\n"
                for guess, (black, white) in history:
                    prompt += f"{guess}: {black} Black pegs, {white} White pegs\n"
                prompt += "\n"

            if len(candidates) <= 30:
                prompt += f"Remaining possible codes ({len(candidates)}): {', '.join(candidates)}\n\n"
            else:
                # Always show a sample so LLM knows which codes are valid
                sample = random.sample(candidates, min(30, len(candidates)))
                prompt += f"Remaining possible codes ({len(candidates)}, showing sample): {', '.join(sample)}\n\n"

            prompt += "Based on the feedback, what should the next guess be?\n"
            prompt += f"IMPORTANT: Your guess MUST be from the remaining possible codes shown above.\n"
            prompt += f"Return ONLY a single {self.num_pegs}-character code in uppercase, nothing else.\n"
            prompt += "Your guess: "

        return prompt

    def _extract_guess(self, text: str, history: List[Tuple[str, Tuple[int, int]]], candidates: List[str]) -> str:
        """Extract code from LLM response.

        Extracts any N-letter code from the response. Invalid guesses (wrong colors,
        not in candidate set, etc.) are still accepted and recorded - constraint
        violations are computed post-hoc by analysis scripts.
        """
        if not text:
            return None

        used = {g for g, _ in history}

        valid_chars = set(self.colors) if self.colors else None

        if self.prompt_type == "cot":
            pattern = rf'FINAL\s*:\s*([A-Za-z]{{{self.num_pegs}}})\b'
            final_match = re.search(pattern, text, re.IGNORECASE)
            if final_match:
                code = final_match.group(1).upper()
                if code not in used and (not valid_chars or all(c in valid_chars for c in code)):
                    return code

        # Find all potential codes (any N-letter sequence)
        pattern = rf'\b[A-Za-z]{{{self.num_pegs}}}\b'
        codes = re.findall(pattern, text.upper())

        # Return first code not already used AND composed of valid colors
        for code in codes:
            if code not in used and (not valid_chars or all(c in valid_chars for c in code)):
                return code

        return None


# ----------------- Guessing Agent -----------------

class MastermindGuessingAgent:
    """Agent that uses the flexible hybrid strategy to play Mastermind."""

    def __init__(self, candidates: List[str], strategy):
        self.all_candidates = list(candidates)
        self.strategy = strategy
        self.candidates = list(candidates)
        self.history = []

    def reset(self):
        """Reset agent for new game."""
        self.candidates = list(self.all_candidates)
        self.history = []
        self.strategy.turn_number = 0

    def select_guess(self, attempt: int = None):
        """Select next guess using strategy.

        Args:
            attempt: Actual attempt number (1-indexed). Pass this to keep
                     schedule aligned when invalid guesses don't update history.
        """
        return self.strategy.get_guess(self.candidates, self.history, attempt)

    def update(self, guess: str, feedback: Tuple[int, int]):
        """Update agent state after guess."""
        self.history.append((guess, feedback))
        self.candidates = self.strategy.update_belief(self.candidates, guess, feedback)


# ----------------- Hybrid Configurations -----------------

def get_hybrid_configs():
    """
    Return all hybrid configurations from Groups A, B, C (excluding Group D repair hybrids).

    Adapted for Mastermind's 10-round format.
    """
    configs = {}

    # Group A: Handoff Patterns
    # L_to_C: LLM r1, then CSS
    configs['L_to_C'] = {i: "llm" if i == 1 else "css" for i in range(1, MAX_ROUNDS + 1)}

    # L_to_V: LLM r1, then VOI
    configs['L_to_V'] = {i: "llm" if i == 1 else "voi" for i in range(1, MAX_ROUNDS + 1)}

    # C_to_L: CSS r1, then LLM
    configs['C_to_L'] = {i: "css" if i == 1 else "llm" for i in range(1, MAX_ROUNDS + 1)}

    # V_to_L: VOI r1, then LLM
    configs['V_to_L'] = {i: "voi" if i == 1 else "llm" for i in range(1, MAX_ROUNDS + 1)}

    # L_to_C_then_V: LLM r1, CSS r2-5, VOI r6-10
    configs['L_to_C_then_V'] = {1: "llm"}
    for i in range(2, 6):
        configs['L_to_C_then_V'][i] = "css"
    for i in range(6, MAX_ROUNDS + 1):
        configs['L_to_C_then_V'][i] = "voi"

    # L_to_V_then_C: LLM r1, VOI r2-5, CSS r6-10
    configs['L_to_V_then_C'] = {1: "llm"}
    for i in range(2, 6):
        configs['L_to_V_then_C'][i] = "voi"
    for i in range(6, MAX_ROUNDS + 1):
        configs['L_to_V_then_C'][i] = "css"

    # Group B: k-Handoff Sweeps
    # Lk_to_css: LLM for k rounds, then CSS
    for k in [1, 2, 3]:
        configs[f'L{k}_to_css'] = {i: "llm" if i <= k else "css" for i in range(1, MAX_ROUNDS + 1)}
        configs[f'L{k}_to_voi'] = {i: "llm" if i <= k else "voi" for i in range(1, MAX_ROUNDS + 1)}

    # cssk_to_L: CSS for k rounds, then LLM
    for k in [1, 2, 3]:
        configs[f'css{k}_to_L'] = {i: "css" if i <= k else "llm" for i in range(1, MAX_ROUNDS + 1)}
        configs[f'voi{k}_to_L'] = {i: "voi" if i <= k else "llm" for i in range(1, MAX_ROUNDS + 1)}

    # Group C: Alternation Patterns
    # alt_css_start: CSS, LLM, CSS, LLM, ...
    configs['alt_css_start'] = {i: "css" if i % 2 == 1 else "llm" for i in range(1, MAX_ROUNDS + 1)}

    # alt_voi_start: VOI, LLM, VOI, LLM, ...
    configs['alt_voi_start'] = {i: "voi" if i % 2 == 1 else "llm" for i in range(1, MAX_ROUNDS + 1)}

    # alt_llm_start_css: LLM, CSS, LLM, CSS, ...
    configs['alt_llm_start_css'] = {i: "llm" if i % 2 == 1 else "css" for i in range(1, MAX_ROUNDS + 1)}

    # alt_llm_start_voi: LLM, VOI, LLM, VOI, ...
    configs['alt_llm_start_voi'] = {i: "llm" if i % 2 == 1 else "voi" for i in range(1, MAX_ROUNDS + 1)}

    return configs


# ----------------- Main Evaluation -----------------

def run_evaluation(num_games: int = 100, variant: str = "classic",
                   model_name: str = "llama-3.3-70b-instruct",
                   schedule: Dict[int, str] = None, config_name: str = "flexible",
                   prompt_type: str = "zero-shot", verbose: bool = False):
    """Run evaluation with a schedule-based hybrid strategy."""

    if schedule is None:
        schedule = {i: "llm" if i == 1 else "css" for i in range(1, MAX_ROUNDS + 1)}

    print("=" * 80)
    print(f"MASTERMIND FLEXIBLE HYBRID EVALUATION: {config_name}")
    print("=" * 80)
    print(f"Variant: {variant}")
    print(f"Model: {model_name}")
    print(f"Prompt Type: {prompt_type}")
    print(f"Schedule: {json.dumps(schedule)}")
    print(f"Games: {num_games}")
    print("=" * 80)

    # Initialize environment
    env = MastermindEnv(variant=variant)
    info = env.get_info()
    print(f"Colors: {info['colors']} ({info['num_colors']} colors)")
    print(f"Search space: {info['search_space']} codes")
    print("=" * 80)

    # Initialize strategy and agent
    strategy = MastermindFlexibleHybridStrategy(
        schedule=schedule, num_pegs=env.num_pegs,
        model_name=model_name, temperature=0.7, prompt_type=prompt_type,
        colors=info['colors']
    )
    agent = MastermindGuessingAgent(env.get_all_candidates(), strategy)

    # Get FIXED test set (same targets across all configs for fair comparison)
    test_targets = get_test_codes(variant, num_games)
    print(f"Using fixed test set (seed=42): {len(test_targets)} targets")

    # Results storage
    results = []
    wins = 0
    total_attempts = 0

    for game_num, target in enumerate(test_targets, 1):
        env.reset(target=target)  # Use fixed target, not random
        agent.reset()

        if verbose:
            print(f"\nGame {game_num}/{num_games}: Target = {target}")

        game_result = {
            'game_number': game_num,
            'target_code': target,
            'won': False,
            'attempts': 0,
            'guesses': [],
            'feedbacks': [],
            'strategy_used': [],
            'candidates_remaining': []
        }

        for attempt in range(1, env.max_attempts + 1):
            guess = agent.select_guess(attempt)  # Pass attempt to keep schedule aligned
            if not guess:
                if verbose:
                    print(f"  Attempt {attempt}: No valid guess available")
                break

            strategy_used = strategy.get_strategy_label(attempt)

            # Try to make the guess - may fail if LLM returns invalid colors
            try:
                feedback, reward = env.guess(guess)
                feedback_str = f"{feedback[0]}B{feedback[1]}W"
                agent.update(guess, feedback)
            except ValueError as e:
                # Invalid guess (wrong colors, etc.) - record it but don't update belief
                feedback_str = "INVALID"
                if verbose:
                    print(f"  Attempt {attempt} [{strategy_used}]: {guess} -> INVALID (constraint violation: {e})")

            game_result['guesses'].append(guess)
            game_result['feedbacks'].append(feedback_str)
            game_result['strategy_used'].append(strategy_used)
            game_result['candidates_remaining'].append(len(agent.candidates))
            game_result['attempts'] = attempt

            if feedback_str != "INVALID" and verbose:
                print(f"  Attempt {attempt} [{strategy_used}]: {guess} -> {feedback_str} ({len(agent.candidates)} remaining)")

            if guess == target:
                game_result['won'] = True
                wins += 1
                total_attempts += attempt
                if verbose:
                    print(f"  Won in {attempt} attempts!")
                break

        if not game_result['won'] and verbose:
            print(f"  Failed to find code")

        results.append(game_result)

        if game_num % 20 == 0:
            print(f"  Progress: {game_num}/{num_games} games ({wins} wins so far)")

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
        script_dir = Path(__file__).parent.parent.parent
        output_dir = script_dir / 'results' / 'mastermind' / 'hybrids' / variant
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prompt_suffix = "_cot" if prompt_type == "cot" else ""

    # Use config_name for file naming
    safe_config = config_name.replace(" ", "_").replace("/", "_")
    csv_file = output_dir / f"{safe_config}_{model_name}{prompt_suffix}_{timestamp}.csv"

    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)

        header = ['game_number', 'target_code', 'won', 'attempts']
        for i in range(1, MAX_ROUNDS + 1):
            header.extend([f'guess_{i}', f'feedback_{i}', f'strategy_{i}', f'candidates_{i}'])
        writer.writerow(header)

        for result in results:
            row = [result['game_number'], result['target_code'], result['won'], result['attempts']]
            for i in range(MAX_ROUNDS):
                if i < len(result['guesses']):
                    row.extend([
                        result['guesses'][i],
                        result['feedbacks'][i],
                        result['strategy_used'][i] if i < len(result['strategy_used']) else '',
                        result['candidates_remaining'][i] if i < len(result['candidates_remaining']) else ''
                    ])
                else:
                    row.extend(['', '', '', ''])
            writer.writerow(row)

    # Save summary JSON
    summary = {
        'strategy': 'flexible_hybrid',
        'config_name': config_name,
        'variant': variant,
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


def list_configs():
    """Print all available hybrid configurations."""
    configs = get_hybrid_configs()
    print("Available hybrid configurations (Groups A, B, C - no repair):\n")

    print("Group A - Handoff Patterns:")
    for name in ['L_to_C', 'L_to_V', 'C_to_L', 'V_to_L', 'L_to_C_then_V', 'L_to_V_then_C']:
        if name in configs:
            print(f"  {name}: {configs[name]}")

    print("\nGroup B - k-Handoff Sweeps:")
    for name in ['L1_to_css', 'L2_to_css', 'L3_to_css', 'L1_to_voi', 'L2_to_voi', 'L3_to_voi',
                 'css1_to_L', 'css2_to_L', 'css3_to_L', 'voi1_to_L', 'voi2_to_L', 'voi3_to_L']:
        if name in configs:
            print(f"  {name}")

    print("\nGroup C - Alternation Patterns:")
    for name in ['alt_css_start', 'alt_voi_start', 'alt_llm_start_css', 'alt_llm_start_voi']:
        if name in configs:
            print(f"  {name}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Mastermind Flexible Hybrid Evaluation')
    parser.add_argument('--list-configs', action='store_true', help='List all available configurations')
    parser.add_argument('--config', type=str, default=None, help='Configuration name')
    parser.add_argument('--variant', type=str, choices=['classic', 'extended'], default='classic')
    parser.add_argument('--model', type=str, default=None)
    parser.add_argument('--num-games', type=int, default=None)
    parser.add_argument('--prompt-type', type=str, choices=['zero-shot', 'cot'], default=None)
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    if args.list_configs:
        list_configs()
        sys.exit(0)

    # Environment variables override argparse (for shell script compatibility)
    model_name = os.getenv("MODEL", args.model or "llama-3.3-70b-instruct")
    num_games = int(os.getenv("NUM_GAMES", args.num_games or 100))
    prompt_type = os.getenv("PROMPT_TYPE", args.prompt_type or "zero-shot")
    config_name = os.getenv("CONFIG_NAME", args.config or "L_to_C")

    # Get schedule from predefined configs or environment
    configs = get_hybrid_configs()
    schedule_str = os.getenv("SCHEDULE")

    if schedule_str:
        raw = json.loads(schedule_str)
        schedule = {int(k): v for k, v in raw.items()}
    elif config_name in configs:
        schedule = configs[config_name]
    else:
        print(f"Unknown config: {config_name}")
        print("Use --list-configs to see available configurations")
        sys.exit(1)

    # Check API key if LLM is in schedule - required, no fallback
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
        variant=args.variant,
        model_name=model_name,
        schedule=schedule,
        config_name=config_name,
        prompt_type=prompt_type,
        verbose=args.verbose
    )
