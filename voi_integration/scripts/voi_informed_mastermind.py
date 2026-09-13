#!/usr/bin/env python3
"""
VOI-Informed Integration Hybrid Strategy for Mastermind

Implements Option 4 for Mastermind: the LLM receives the algorithm's top-k
candidates ranked by VOI/CSS score + entropy context in its prompt.

Three conditions:
  - baseline: Standard schedule (no VOI signals)
  - voi_informed: Same schedule but with VOI signals injected into LLM prompts
  - shuffled_ranking: Signals with randomized display order (scores preserved)

Configured via env vars:
  MODEL          - LLM model name (default: llama-3.3-70b-instruct)
  NUM_GAMES      - Number of games to play (default: 100)
  PROMPT_TYPE    - "zero-shot" or "cot" (default: zero-shot)
  SCHEDULE       - JSON round-to-strategy mapping
  CONFIG_NAME    - Label for output files
  ALGORITHM      - Algorithm for scoring: "css" or "voi" (default: css)
  CONDITION      - "baseline", "voi_informed", or "shuffled_ranking" (default: voi_informed)
  TOP_K          - Number of top candidates to show LLM (default: 5)
  OUTPUT_DIR     - Output directory (default: voi_integration/results/mastermind)
  VARIANT        - "classic" or "extended" (default: classic)
"""

import os
import csv
import time
import json
import math
import random
import re
import sys
from datetime import datetime
from typing import List, Tuple, Dict, Optional
from pathlib import Path

# Add parent directories to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'engines'))
sys.path.insert(0, str(PROJECT_ROOT / 'algorithms'))
sys.path.insert(0, str(PROJECT_ROOT / 'scripts' / 'mastermind'))

from mastermind_env import MastermindEnv
from mastermind_css_strategy import MastermindCSSStrategy
from mastermind_voi_strategy import MastermindVOIStrategy
from test_set_loader import get_test_codes

# Models that require the GPT API key (frontier models)
GPT_API_MODELS = {
    "gpt-5", "gpt-5-mini", "gpt-4.1", "gpt-4.1-mini", "gpt-4o", "gpt-4o-mini",
    "claude-3-opus", "claude-3.7-sonnet", "claude-4.5-sonnet",
    "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"
}

# Models that use NAVIGATOR_UF_API_KEY1
KEY1_MODELS = {"claude-4-sonnet"}

VALID_STRATEGIES = {"llm", "css", "voi"}

MAX_ROUNDS = 10


def _get_api_key_for_model(model_name: str) -> str:
    if model_name in KEY1_MODELS:
        key = os.getenv("NAVIGATOR_UF_API_KEY1")
        if not key:
            raise RuntimeError(f"NAVIGATOR_UF_API_KEY1 not set (required for {model_name})")
        return key
    elif model_name in GPT_API_MODELS:
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
    if name == "css":
        return MastermindCSSStrategy(num_pegs=num_pegs)
    elif name == "voi":
        return MastermindVOIStrategy(num_pegs=num_pegs)
    else:
        raise ValueError(f"Unknown algorithm: {name}")


class VOIInformedMastermindStrategy:
    """
    Hybrid strategy with VOI-informed integration for Mastermind.

    On LLM turns, the algorithm's top-k candidates (ranked by score) and
    current entropy are injected into the prompt, giving the LLM shared
    reasoning context rather than operating blindly.

    In baseline condition, this section is omitted (standard prompt only).
    """

    def __init__(self, schedule: Dict[int, str], num_pegs: int = 4,
                 model_name: str = "llama-3.3-70b-instruct",
                 temperature: float = 0.7, prompt_type: str = "zero-shot",
                 algorithm: str = "css", condition: str = "voi_informed",
                 top_k: int = 5, colors: str = "RGBYOW"):
        self.schedule = schedule
        self.num_pegs = num_pegs
        self.model_name = model_name
        self.temperature = temperature
        self.prompt_type = prompt_type.lower()
        self.algorithm = algorithm.lower()
        self.condition = condition.lower()
        self.top_k = top_k
        self.colors = colors
        self.turn_number = 0
        self.api_base = os.getenv("NAVIGATOR_API_ENDPOINT", "https://api.ai.it.ufl.edu/v1")

        for rnd, strat in schedule.items():
            if strat not in VALID_STRATEGIES:
                raise ValueError(f"Invalid strategy '{strat}' for round {rnd}. Must be one of {VALID_STRATEGIES}")

        # Initialize algorithm strategies
        algo_names = {s for s in schedule.values() if s != "llm"}
        self.algo_strategies = {name: _create_algo_strategy(name, num_pegs) for name in algo_names}

        # Scoring algorithm (for VOI signals)
        self.scoring_algo = _create_algo_strategy(self.algorithm, num_pegs)

        # Primary algorithm for belief updates
        priority = ["css", "voi"]
        self._primary_algo = None
        for p in priority:
            if p in self.algo_strategies:
                self._primary_algo = self.algo_strategies[p]
                break
        if self._primary_algo is None:
            self._primary_algo = self.scoring_algo

        # Per-turn VOI metadata
        self.last_turn_metadata = {}

    def update_belief(self, candidates: List[str], guess: str, feedback: Tuple[int, int]) -> List[str]:
        return self._primary_algo.update_belief(candidates, guess, feedback)

    def get_guess(self, candidates: List[str], history: List[Tuple[str, Tuple[int, int]]], attempt: int = None) -> str:
        self.turn_number = attempt if attempt is not None else len(history) + 1
        strategy_name = self.schedule.get(self.turn_number, "llm")

        # Reset per-turn metadata
        self.last_turn_metadata = {
            'algo_top1': '',
            'algo_scores': '',
            'entropy_at_turn': '',
            'llm_followed_algo': '',
            'displayed_top1': '',
            'llm_picked_displayed_top1': ''
        }

        if strategy_name == "llm":
            # Compute VOI signals
            algo_scores = self._get_algo_scores(candidates, history)
            entropy = math.log2(len(candidates)) if len(candidates) > 1 else 0.0

            self.last_turn_metadata['algo_top1'] = algo_scores[0][0] if algo_scores else ''
            self.last_turn_metadata['algo_scores'] = json.dumps(
                [(c, round(s, 4)) for c, s in algo_scores])
            self.last_turn_metadata['entropy_at_turn'] = round(entropy, 4)

            # Get LLM guess (with or without VOI signals)
            inject_signals = self.condition in ("voi_informed", "shuffled_ranking")
            if inject_signals and self.condition == "shuffled_ranking":
                display_scores = list(algo_scores)
                random.shuffle(display_scores)
            else:
                display_scores = algo_scores

            guess = self._get_llm_guess(candidates, history,
                                        algo_scores=display_scores if inject_signals else None,
                                        entropy=entropy if inject_signals else None)

            # Track whether LLM followed algo's true top-1
            if guess and algo_scores:
                self.last_turn_metadata['llm_followed_algo'] = (guess == algo_scores[0][0])
            else:
                self.last_turn_metadata['llm_followed_algo'] = ''

            # Track displayed top-1
            if self.condition == "shuffled_ranking" and display_scores:
                self.last_turn_metadata['displayed_top1'] = display_scores[0][0]
                if guess:
                    self.last_turn_metadata['llm_picked_displayed_top1'] = (guess == display_scores[0][0])
            elif inject_signals and display_scores:
                self.last_turn_metadata['displayed_top1'] = display_scores[0][0]

            return guess
        else:
            algo = self.algo_strategies[strategy_name]
            return algo.select_guess(candidates, history)

    def get_strategy_label(self, turn: int) -> str:
        name = self.schedule.get(turn, "llm")
        if name == "llm" and self.condition in ("voi_informed", "shuffled_ranking"):
            return f"LLM_{self.condition.upper()}"
        return name.upper()

    def _get_algo_scores(self, candidates: List[str], history: List[Tuple[str, Tuple[int, int]]]) -> List[Tuple[str, float]]:
        """Get top-k scored candidates from the scoring algorithm."""
        if len(candidates) <= 1:
            return [(candidates[0], 1.0)] if candidates else []

        # Ensure VOI strategy has beliefs initialized
        if isinstance(self.scoring_algo, MastermindVOIStrategy):
            if not hasattr(self.scoring_algo, 'beliefs') or not self.scoring_algo.beliefs:
                self.scoring_algo.initialize_beliefs(candidates)

        return self.scoring_algo.score_candidates(candidates, history, self.top_k)

    def _get_llm_guess(self, candidates: List[str], history: List[Tuple[str, Tuple[int, int]]],
                       algo_scores: Optional[List[Tuple[str, float]]] = None,
                       entropy: Optional[float] = None) -> Optional[str]:
        """Get guess from LLM with retry logic."""
        try:
            import openai
            client = openai.OpenAI(
                api_key=_get_api_key_for_model(self.model_name),
                base_url=self.api_base
            )

            prompt = self._build_prompt(candidates, history, algo_scores, entropy)

            def api_call():
                return client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.temperature,
                    max_tokens=200
                )

            for attempt in range(5):
                try:
                    response = api_call()
                    text = response.choices[0].message.content.strip()
                    guess = self._extract_guess(text, history, candidates)
                    if guess:
                        return guess
                    print(f"LLM API attempt {attempt+1}/5 failed: invalid guess from response: {text[:100]}")
                except Exception as e:
                    print(f"LLM API attempt {attempt+1}/5 failed: {e}")

                if attempt < 4:
                    time.sleep(2 ** attempt + random.uniform(0, 1))

            print("LLM failed after 5 attempts - marking game as lost")
            return None

        except Exception as e:
            print(f"LLM initialization failed: {e} - marking game as lost")
            return None

    def _build_prompt(self, candidates: List[str], history: List[Tuple[str, Tuple[int, int]]],
                      algo_scores: Optional[List[Tuple[str, float]]] = None,
                      entropy: Optional[float] = None) -> str:
        if self.prompt_type == "cot":
            return self._build_cot_prompt(candidates, history, algo_scores, entropy)
        else:
            return self._build_zero_shot_prompt(candidates, history, algo_scores, entropy)

    def _build_algo_analysis_section(self, algo_scores: List[Tuple[str, float]],
                                     entropy: float, num_candidates: int) -> str:
        """Build the Algorithm Analysis section for prompt injection."""
        section = "\nAlgorithm Analysis:\n"
        section += f"- Current entropy: {entropy:.1f} bits ({num_candidates} codes remaining)\n"
        section += "- Top candidates ranked by information value:\n"
        for i, (code, score) in enumerate(algo_scores, 1):
            section += f"    {i}. {code} (score: {score:.2f})\n"
        if algo_scores:
            section += f"- Algorithm's recommended guess: {algo_scores[0][0]}\n"
        section += (
            "\nUse this analysis as one input to your reasoning, but make your own decision. "
            "Do NOT simply copy the algorithm's top pick — consider the candidates critically "
            "and choose the code you believe will maximize information gain based on your own analysis.\n"
        )
        return section

    def _build_zero_shot_prompt(self, candidates: List[str], history: List[Tuple[str, Tuple[int, int]]],
                                algo_scores: Optional[List[Tuple[str, float]]] = None,
                                entropy: Optional[float] = None) -> str:
        color_names = {
            'R': 'Red', 'G': 'Green', 'B': 'Blue', 'Y': 'Yellow',
            'O': 'Orange', 'W': 'White', 'P': 'Purple', 'K': 'blacK'
        }
        colors_desc = ", ".join(f"{c}={color_names[c]}" for c in self.colors)

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
            sample = random.sample(candidates, min(30, len(candidates)))
            prompt += f"Remaining possible codes ({len(candidates)}, showing sample): {', '.join(sample)}\n\n"

        # Inject VOI signals if provided
        if algo_scores is not None and entropy is not None:
            prompt += self._build_algo_analysis_section(algo_scores, entropy, len(candidates))
            prompt += "\n"

        prompt += "Based on the feedback, what should the next guess be?\n"
        prompt += f"IMPORTANT: Your guess MUST be from the remaining possible codes shown above.\n"
        prompt += f"Return ONLY a single {self.num_pegs}-character code in uppercase, nothing else.\n"
        prompt += "Your guess: "
        return prompt

    def _build_cot_prompt(self, candidates: List[str], history: List[Tuple[str, Tuple[int, int]]],
                          algo_scores: Optional[List[Tuple[str, float]]] = None,
                          entropy: Optional[float] = None) -> str:
        color_names = {
            'R': 'Red', 'G': 'Green', 'B': 'Blue', 'Y': 'Yellow',
            'O': 'Orange', 'W': 'White', 'P': 'Purple', 'K': 'blacK'
        }
        colors_desc = ", ".join(f"{c}={color_names[c]}" for c in self.colors)

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
            f"Sample candidates: {candidates_str}\n"
        )

        # Inject VOI signals if provided
        if algo_scores is not None and entropy is not None:
            prompt += self._build_algo_analysis_section(algo_scores, entropy, len(candidates))

        prompt += (
            "\nConstraints:\n"
            "- Do NOT repeat previous guesses.\n"
            f"- ONLY use these {len(self.colors)} colors: {self.colors}\n"
            f"- The FINAL line must be exactly ONE valid {self.num_pegs}-character code.\n"
            "- Keep THINKING concise (1-5 short lines)."
        )
        return prompt

    def _extract_guess(self, text: str, history: List[Tuple[str, Tuple[int, int]]], candidates: List[str]) -> Optional[str]:
        if not text:
            return None

        used = {g for g, _ in history}

        if self.prompt_type == "cot":
            pattern = rf'FINAL\s*:\s*([A-Za-z]{{{self.num_pegs}}})\b'
            final_match = re.search(pattern, text, re.IGNORECASE)
            if final_match:
                code = final_match.group(1).upper()
                if code not in used:
                    return code

        # Find all potential codes
        pattern = rf'\b[A-Za-z]{{{self.num_pegs}}}\b'
        codes = re.findall(pattern, text.upper())

        # Prefer codes in candidate set
        for code in codes:
            if code not in used and code in candidates:
                return code

        # Accept any valid-length code not already used
        for code in codes:
            if code not in used:
                return code

        return None


# ----------------- Guessing Agent -----------------

class MastermindVOIInformedAgent:
    """Agent that uses the VOI-informed hybrid strategy to play Mastermind."""

    def __init__(self, candidates: List[str], strategy):
        self.all_candidates = list(candidates)
        self.strategy = strategy
        self.candidates = list(candidates)
        self.history = []

    def reset(self):
        self.candidates = list(self.all_candidates)
        self.history = []
        self.strategy.turn_number = 0
        # Reset scoring algo beliefs for VOI
        if isinstance(self.strategy.scoring_algo, MastermindVOIStrategy):
            if hasattr(self.strategy.scoring_algo, 'beliefs'):
                self.strategy.scoring_algo.beliefs = {}

    def select_guess(self, attempt: int = None):
        return self.strategy.get_guess(self.candidates, self.history, attempt)

    def update(self, guess: str, feedback: Tuple[int, int]):
        self.history.append((guess, feedback))
        self.candidates = self.strategy.update_belief(self.candidates, guess, feedback)

        # Keep scoring algo's beliefs in sync
        if isinstance(self.strategy.scoring_algo, MastermindVOIStrategy):
            if not self.strategy.scoring_algo.beliefs:
                self.strategy.scoring_algo.initialize_beliefs(self.candidates)
            self.strategy.scoring_algo.update_belief(
                list(self.strategy.scoring_algo.beliefs.keys()), guess, feedback)


# ----------------- Main Evaluation -----------------

def run_evaluation(num_games=100, variant="classic",
                   model_name="llama-3.3-70b-instruct",
                   schedule=None, config_name="voi_informed", prompt_type="zero-shot",
                   algorithm="css", condition="voi_informed", top_k=5):
    """Run VOI-informed hybrid evaluation on Mastermind canonical test set."""

    if schedule is None:
        algo = algorithm if algorithm in VALID_STRATEGIES else "css"
        schedule = {1: "llm"}
        for i in range(2, MAX_ROUNDS + 1):
            schedule[i] = algo

    print("=" * 80)
    print(f"MASTERMIND VOI-INFORMED HYBRID EVALUATION: {config_name}")
    print("=" * 80)
    print(f"Model: {model_name}")
    print(f"Variant: {variant}")
    print(f"Algorithm: {algorithm.upper()}")
    print(f"Condition: {condition}")
    print(f"Prompt Type: {prompt_type}")
    print(f"Top-K: {top_k}")
    print(f"Schedule: {json.dumps({str(k): v for k, v in schedule.items()})}")
    print(f"Games: {num_games}")
    print("=" * 80)

    # Initialize environment
    max_attempts = int(os.getenv("MAX_ATTEMPTS", "10"))
    env = MastermindEnv(variant=variant, max_attempts=max_attempts)
    info = env.get_info()
    print(f"Colors: {info['colors']} ({info['num_colors']} colors)")
    print(f"Search space: {info['search_space']} codes")
    print("=" * 80)

    # Get test set
    test_targets = get_test_codes(variant, num_games)
    print(f"Using fixed test set (seed=42): {len(test_targets)} targets")

    # Initialize strategy and agent
    strategy = VOIInformedMastermindStrategy(
        schedule=schedule, num_pegs=env.num_pegs,
        model_name=model_name, temperature=0.7, prompt_type=prompt_type,
        algorithm=algorithm, condition=condition, top_k=top_k,
        colors=info['colors']
    )
    agent = MastermindVOIInformedAgent(env.get_all_candidates(), strategy)

    results = []
    wins = 0
    total_attempts = 0

    for game_num, target in enumerate(test_targets, 1):
        print(f"\nGame {game_num}/{num_games}: Target = {target}")

        env.reset(target=target)
        agent.reset()

        game_result = {
            'game_number': game_num,
            'target_code': target,
            'won': False,
            'attempts': 0,
            'guesses': [],
            'feedbacks': [],
            'strategy_used': [],
            'candidates_remaining': [],
            'algo_top1': [],
            'algo_scores': [],
            'entropy_at_turn': [],
            'llm_followed_algo': [],
            'displayed_top1': [],
            'llm_picked_displayed_top1': []
        }

        for attempt in range(1, env.max_attempts + 1):
            guess = agent.select_guess(attempt)
            if not guess:
                print(f"  Attempt {attempt}: No valid guess available")
                break

            # Capture VOI metadata before updating state
            meta = dict(strategy.last_turn_metadata)

            strategy_label = strategy.get_strategy_label(attempt)

            # Try to make the guess
            try:
                feedback, reward = env.guess(guess)
                feedback_str = f"{feedback[0]}B{feedback[1]}W"
                agent.update(guess, feedback)
            except ValueError as e:
                feedback_str = "INVALID"
                feedback = None
                print(f"  Attempt {attempt} [{strategy_label}]: {guess} -> INVALID ({e})")

            game_result['guesses'].append(guess)
            game_result['feedbacks'].append(feedback_str)
            game_result['strategy_used'].append(strategy_label)
            game_result['candidates_remaining'].append(len(agent.candidates))
            game_result['algo_top1'].append(meta.get('algo_top1', ''))
            game_result['algo_scores'].append(meta.get('algo_scores', ''))
            game_result['entropy_at_turn'].append(meta.get('entropy_at_turn', ''))
            game_result['llm_followed_algo'].append(meta.get('llm_followed_algo', ''))
            game_result['displayed_top1'].append(meta.get('displayed_top1', ''))
            game_result['llm_picked_displayed_top1'].append(meta.get('llm_picked_displayed_top1', ''))
            game_result['attempts'] = attempt

            if feedback_str != "INVALID":
                print(f"  Attempt {attempt} [{strategy_label}]: {guess} -> {feedback_str} "
                      f"({len(agent.candidates)} remaining)", end="")
                if meta.get('algo_top1'):
                    print(f" [algo_top1={meta['algo_top1']}, followed={meta.get('llm_followed_algo', '')}]", end="")
                print()

            if guess == target:
                game_result['won'] = True
                wins += 1
                total_attempts += attempt
                print(f"  Won in {attempt} attempts!")
                break

        if not game_result['won']:
            print("  Failed to find code")

        results.append(game_result)

        if game_num % 20 == 0:
            print(f"  Progress: {game_num}/{num_games} games ({wins} wins so far)")

    # Statistics
    win_rate = wins / num_games if num_games > 0 else 0
    avg_attempts = total_attempts / wins if wins > 0 else 0

    # Follow rate
    follow_count = sum(1 for r in results for v in r['llm_followed_algo'] if v is True)
    llm_turn_count = sum(1 for r in results for v in r['llm_followed_algo'] if v in (True, False))
    follow_rate = follow_count / llm_turn_count if llm_turn_count > 0 else 0

    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    print(f"Games played: {num_games}")
    print(f"Wins: {wins}")
    print(f"Win rate: {win_rate * 100:.1f}%")
    print(f"Average attempts (when won): {avg_attempts:.2f}")
    if condition in ("voi_informed", "shuffled_ranking"):
        print(f"LLM follow rate (chose algo true top-1): {follow_rate * 100:.1f}% ({follow_count}/{llm_turn_count})")
    if condition == "shuffled_ranking":
        disp_follow = sum(1 for r in results for v in r['llm_picked_displayed_top1'] if v is True)
        disp_total = sum(1 for r in results for v in r['llm_picked_displayed_top1'] if v in (True, False))
        disp_rate = disp_follow / disp_total if disp_total > 0 else 0
        print(f"LLM displayed-top1 pick rate (rank imitation): {disp_rate * 100:.1f}% ({disp_follow}/{disp_total})")
    print("=" * 80)

    # Save results
    output_dir_env = os.getenv("OUTPUT_DIR")
    if output_dir_env:
        output_dir = Path(output_dir_env)
    else:
        output_dir = PROJECT_ROOT / 'voi_integration' / 'results' / 'mastermind'
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prompt_suffix = "_cot" if prompt_type == "cot" else ""
    safe_config = config_name.replace(" ", "_").replace("/", "_")
    csv_file = output_dir / f"{safe_config}_{model_name}{prompt_suffix}_{timestamp}.csv"

    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)

        header = ['game_number', 'target_code', 'won', 'attempts']
        for i in range(1, MAX_ROUNDS + 1):
            header.extend([
                f'guess_{i}', f'feedback_{i}', f'strategy_{i}', f'candidates_{i}',
                f'algo_top1_{i}', f'algo_scores_{i}',
                f'entropy_{i}', f'llm_followed_algo_{i}',
                f'displayed_top1_{i}', f'llm_picked_displayed_top1_{i}'
            ])
        writer.writerow(header)

        for result in results:
            row = [result['game_number'], result['target_code'], result['won'], result['attempts']]
            for i in range(MAX_ROUNDS):
                if i < len(result['guesses']):
                    row.extend([
                        result['guesses'][i],
                        result['feedbacks'][i],
                        result['strategy_used'][i] if i < len(result['strategy_used']) else '',
                        result['candidates_remaining'][i] if i < len(result['candidates_remaining']) else '',
                        result['algo_top1'][i] if i < len(result['algo_top1']) else '',
                        result['algo_scores'][i] if i < len(result['algo_scores']) else '',
                        result['entropy_at_turn'][i] if i < len(result['entropy_at_turn']) else '',
                        result['llm_followed_algo'][i] if i < len(result['llm_followed_algo']) else '',
                        result['displayed_top1'][i] if i < len(result['displayed_top1']) else '',
                        result['llm_picked_displayed_top1'][i] if i < len(result['llm_picked_displayed_top1']) else ''
                    ])
                else:
                    row.extend([''] * 10)
            writer.writerow(row)

    # Save summary JSON
    summary = {
        'strategy': 'voi_informed_mastermind_hybrid',
        'config_name': config_name,
        'variant': variant,
        'model_name': model_name,
        'algorithm': algorithm,
        'condition': condition,
        'prompt_type': prompt_type,
        'top_k': top_k,
        'schedule': {str(k): v for k, v in schedule.items()},
        'total_games': num_games,
        'wins': wins,
        'win_rate': win_rate,
        'avg_attempts_when_won': avg_attempts,
        'follow_rate': follow_rate,
        'follow_count': follow_count,
        'llm_turn_count': llm_turn_count,
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
    config_name = os.getenv("CONFIG_NAME", "voi_informed")
    algorithm = os.getenv("ALGORITHM", "css")
    condition = os.getenv("CONDITION", "voi_informed")
    top_k = int(os.getenv("TOP_K", "5"))
    variant = os.getenv("VARIANT", "classic")

    # Parse schedule
    schedule_str = os.getenv("SCHEDULE")
    if schedule_str:
        raw = json.loads(schedule_str)
        schedule = {int(k): v for k, v in raw.items()}
    else:
        # Default: LLM round 1, algorithm rounds 2-10
        algo = algorithm if algorithm in VALID_STRATEGIES else "css"
        schedule = {1: "llm"}
        for i in range(2, MAX_ROUNDS + 1):
            schedule[i] = algo

    # Check API key
    if "llm" in schedule.values():
        try:
            _get_api_key_for_model(model_name)
        except RuntimeError as e:
            print(f"ERROR: {e}")
            sys.exit(1)

    run_evaluation(
        num_games=num_games,
        variant=variant,
        model_name=model_name,
        schedule=schedule,
        config_name=config_name,
        prompt_type=prompt_type,
        algorithm=algorithm,
        condition=condition,
        top_k=top_k
    )
