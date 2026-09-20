#!/usr/bin/env python3
"""
VOI-Informed Integration Hybrid Strategy

Implements Option 4: the LLM receives the algorithm's top-k candidates ranked
by VOI/CSS score + entropy context in its prompt, enabling shared reasoning
rather than blind switching.

Two conditions:
  - baseline: Standard schedule (no VOI signals) -- reuses flexible_hybrid logic
  - voi_informed: Same schedule but with VOI signals injected into LLM prompts

Configured via env vars:
  MODEL          - LLM model name (default: llama-3.3-70b-instruct)
  NUM_GAMES      - Number of games to play (default: 100)
  PROMPT_TYPE    - "zero-shot" or "cot" (default: zero-shot)
  SCHEDULE       - JSON round-to-strategy mapping
  CONFIG_NAME    - Label for output files
  ALGORITHM      - Algorithm for scoring: "css" or "voi" (default: css)
  CONDITION      - "baseline", "voi_informed", or "shuffled_ranking" (default: voi_informed)
  TOP_K          - Number of top candidates to show LLM (default: 5)
  OUTPUT_DIR     - Output directory (default: voi_integration/results/wordle)
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
sys.path.insert(0, str(PROJECT_ROOT / 'scripts'))

from wordle_env import WordleEnv
from test_set_loader import get_test_words_only
from css_strategy import CSSStrategy
from voi_strategy import VOIStrategy

# Models that require the GPT API key (frontier models)
GPT_API_MODELS = {
    "gpt-5-mini", "gpt-4.1", "gpt-4.1-mini", "gpt-4o", "gpt-4o-mini",
    "claude-3-opus", "claude-3.7-sonnet", "claude-4.5-sonnet",
    "gemini-2.5-flash", "gemini-2.0-flash"
}

# Models that use NAVIGATOR_UF_API_KEY1
KEY1_MODELS = {"claude-4-sonnet"}

# Models that use NAVIGATOR_UF_API_KEY3
KEY3_MODELS = {"gpt-5", "gemini-2.5-pro"}

# Reasoning models: need max_completion_tokens instead of max_tokens, no temperature
REASONING_MODELS = {"gpt-5", "gpt-oss-120b"}

VALID_STRATEGIES = {"llm", "css", "voi"}


def _get_api_key_for_model(model_name: str) -> str:
    if model_name in KEY1_MODELS:
        key = os.getenv("NAVIGATOR_UF_API_KEY1")
        if not key:
            raise RuntimeError(f"NAVIGATOR_UF_API_KEY1 not set (required for {model_name})")
        return key
    elif model_name in KEY3_MODELS:
        key = os.getenv("NAVIGATOR_UF_API_KEY3")
        if not key:
            raise RuntimeError(f"NAVIGATOR_UF_API_KEY3 not set (required for {model_name})")
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


def _create_algo_strategy(name: str):
    if name == "css":
        return CSSStrategy()
    elif name == "voi":
        return VOIStrategy()
    else:
        raise ValueError(f"Unknown algorithm: {name}")


class VOIInformedHybridStrategy:
    """
    Hybrid strategy with VOI-informed integration.

    On LLM turns, the algorithm's top-k candidates (ranked by score) and
    current entropy are injected into the prompt, giving the LLM shared
    reasoning context rather than operating blindly.

    In baseline condition, this section is omitted (standard prompt only).
    """

    def __init__(self, schedule: Dict[int, str], model_name: str = "llama-3.3-70b-instruct",
                 temperature: float = 0.7, prompt_type: str = "zero-shot",
                 algorithm: str = "css", condition: str = "voi_informed", top_k: int = 5):
        self.schedule = schedule
        self.model_name = model_name
        self.temperature = temperature
        self.prompt_type = prompt_type.lower()
        self.algorithm = algorithm.lower()
        self.condition = condition.lower()
        self.top_k = top_k
        self.turn_number = 0
        self.api_base = os.getenv("NAVIGATOR_API_ENDPOINT", "https://api.navigator.uf.edu/v1")

        for rnd, strat in schedule.items():
            if strat not in VALID_STRATEGIES:
                raise ValueError(f"Invalid strategy '{strat}' for round {rnd}. Must be one of {VALID_STRATEGIES}")

        # Initialize algorithm strategies
        algo_names = {s for s in schedule.values() if s != "llm"}
        self.algo_strategies = {name: _create_algo_strategy(name) for name in algo_names}

        # Scoring algorithm (for VOI signals)
        self.scoring_algo = _create_algo_strategy(self.algorithm)

        # Primary algorithm for belief updates
        priority = ["css", "voi"]
        self._primary_algo = None
        for p in priority:
            if p in self.algo_strategies:
                self._primary_algo = self.algo_strategies[p]
                break
        if self._primary_algo is None:
            self._primary_algo = self.scoring_algo

        # Per-turn VOI metadata (populated during get_guess)
        self.last_turn_metadata = {}

    def update_belief(self, candidates: List[str], guess: str, feedback: List[str]) -> List[str]:
        return self._primary_algo.update_belief(candidates, guess, feedback)

    def get_guess(self, candidates: List[str], history: List[Tuple[str, List[str]]], attempt: int = None) -> str:
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
            # Compute VOI signals (always, for metadata tracking)
            algo_scores = self._get_algo_scores(candidates, history)
            entropy = math.log2(len(candidates)) if len(candidates) > 1 else 0.0

            self.last_turn_metadata['algo_top1'] = algo_scores[0][0] if algo_scores else ''
            self.last_turn_metadata['algo_scores'] = json.dumps(
                [(w, round(s, 4)) for w, s in algo_scores])
            self.last_turn_metadata['entropy_at_turn'] = round(entropy, 4)

            # Get LLM guess (with or without VOI signals in prompt)
            inject_signals = self.condition in ("voi_informed", "shuffled_ranking")
            if inject_signals and self.condition == "shuffled_ranking":
                # Shuffle display order but preserve actual scores
                # This tests whether LLM reasons over scores or imitates rank position
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

            # For shuffled condition: track displayed top-1 vs actual top-1
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

    def _get_algo_scores(self, candidates: List[str], history: List[Tuple[str, List[str]]]) -> List[Tuple[str, float]]:
        """Get top-k scored candidates from the scoring algorithm."""
        if len(candidates) <= 1:
            return [(candidates[0], 1.0)] if candidates else []

        # Ensure VOI strategy has beliefs initialized
        if isinstance(self.scoring_algo, VOIStrategy) and not self.scoring_algo.beliefs:
            self.scoring_algo.initialize_beliefs(candidates)

        return self.scoring_algo.score_candidates(candidates, history, self.top_k)

    def _get_llm_guess(self, candidates: List[str], history: List[Tuple[str, List[str]]],
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

            is_reasoning = self.model_name in REASONING_MODELS
            call_kwargs = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
            }
            if is_reasoning:
                call_kwargs["max_completion_tokens"] = 16384
            else:
                call_kwargs["temperature"] = self.temperature
                call_kwargs["max_tokens"] = 150

            def api_call():
                return client.chat.completions.create(**call_kwargs)

            for attempt in range(5):
                try:
                    response = api_call()
                    content = response.choices[0].message.content
                    if content is None:
                        content = getattr(response.choices[0].message, 'reasoning_content', None) or ""
                    text = content.strip()
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

    def _build_prompt(self, candidates: List[str], history: List[Tuple[str, List[str]]],
                      algo_scores: Optional[List[Tuple[str, float]]] = None,
                      entropy: Optional[float] = None) -> str:
        """Build prompt with optional VOI signal injection."""
        if self.prompt_type == "cot":
            prompt = self._build_cot_prompt(candidates, history, algo_scores, entropy)
        else:
            prompt = self._build_zero_shot_prompt(candidates, history, algo_scores, entropy)
        return prompt

    def _build_algo_analysis_section(self, algo_scores: List[Tuple[str, float]],
                                     entropy: float, num_candidates: int) -> str:
        """Build the Algorithm Analysis section for prompt injection."""
        section = "\nAlgorithm Analysis:\n"
        section += f"- Current entropy: {entropy:.1f} bits ({num_candidates} candidates remaining)\n"
        section += "- Top candidates ranked by information value:\n"
        for i, (word, score) in enumerate(algo_scores, 1):
            section += f"    {i}. {word} (score: {score:.2f})\n"
        if algo_scores:
            section += f"- Algorithm's recommended guess: {algo_scores[0][0]}\n"
        section += (
            "\nUse this analysis as one input to your reasoning, but make your own decision. "
            "Do NOT simply copy the algorithm's top pick — consider the candidates critically "
            "and choose the word you believe will maximize information gain based on your own analysis.\n"
        )
        return section

    def _build_zero_shot_prompt(self, candidates: List[str], history: List[Tuple[str, List[str]]],
                                algo_scores: Optional[List[Tuple[str, float]]] = None,
                                entropy: Optional[float] = None) -> str:
        prompt = "You are playing Wordle. Your goal is to guess a 5-letter word.\n\n"

        if history:
            prompt += "Previous guesses:\n"
            for guess, feedback in history:
                feedback_str = ''.join(
                    ['\U0001f7e9' if f == 'G' else '\U0001f7e8' if f == 'Y' else '\u2b1c' for f in feedback])
                prompt += f"{guess}: {feedback_str}\n"
            prompt += "\n"

        if len(candidates) <= 30:
            prompt += f"Remaining possible words ({len(candidates)}): {', '.join(candidates)}\n\n"
        else:
            sample = random.sample(candidates, min(30, len(candidates)))
            prompt += f"Remaining possible words ({len(candidates)}, showing sample): {', '.join(sample)}\n\n"

        # Inject VOI signals if provided (voi_informed condition)
        if algo_scores is not None and entropy is not None:
            prompt += self._build_algo_analysis_section(algo_scores, entropy, len(candidates))
            prompt += "\n"

        prompt += "Based on the feedback, what should the next guess be?\n"
        prompt += "IMPORTANT: Your guess MUST be from the remaining possible words shown above.\n"
        prompt += "Return ONLY a single 5-letter word in uppercase, nothing else.\n"
        prompt += "Your guess: "
        return prompt

    def _build_cot_prompt(self, candidates: List[str], history: List[Tuple[str, List[str]]],
                          algo_scores: Optional[List[Tuple[str, float]]] = None,
                          entropy: Optional[float] = None) -> str:
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
            f"Candidate words: {candidates_str}\n"
        )

        # Inject VOI signals if provided (voi_informed condition)
        if algo_scores is not None and entropy is not None:
            prompt += self._build_algo_analysis_section(algo_scores, entropy, len(candidates))

        prompt += (
            "\nConstraints:\n"
            "- Do NOT repeat previous guesses.\n"
            "- The FINAL line must be exactly ONE valid 5-letter word from the allowed list.\n"
            "- Keep THINKING concise (1-5 short lines)."
        )
        return prompt

    def _extract_guess(self, text: str, history: List[Tuple[str, List[str]]], candidates: List[str]) -> Optional[str]:
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

class VOIInformedGuessingAgent:
    """Agent that uses the VOI-informed hybrid strategy to play Wordle."""

    def __init__(self, word_list, strategy):
        self.word_list = word_list
        self.strategy = strategy
        self.candidates = list(word_list)
        self.history = []

    def reset(self):
        self.candidates = list(self.word_list)
        self.history = []
        self.strategy.turn_number = 0
        # Reset scoring algo beliefs for VOI
        if isinstance(self.strategy.scoring_algo, VOIStrategy):
            self.strategy.scoring_algo.beliefs = {}
            self.strategy.scoring_algo.feedback_cache = {}

    def select_guess(self, attempt: int = None):
        return self.strategy.get_guess(self.candidates, self.history, attempt)

    def update(self, guess, feedback, reward):
        if feedback and isinstance(feedback[0], int):
            str_feedback = ['G' if f == 2 else 'Y' if f == 1 else '-' for f in feedback]
        else:
            str_feedback = feedback

        self.history.append((guess, str_feedback))
        self.candidates = self.strategy.update_belief(self.candidates, guess, str_feedback)

        # Keep scoring algo's beliefs in sync
        if isinstance(self.strategy.scoring_algo, VOIStrategy):
            if not self.strategy.scoring_algo.beliefs:
                self.strategy.scoring_algo.initialize_beliefs(self.candidates)
            self.strategy.scoring_algo.update_belief(
                list(self.strategy.scoring_algo.beliefs.keys()), guess, str_feedback)


# ----------------- Distance Metrics -----------------

def hamming_distance(word1: str, word2: str) -> int:
    return sum(c1 != c2 for c1, c2 in zip(word1.upper(), word2.upper()))


def levenshtein_distance(word1: str, word2: str) -> int:
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
                   schedule=None, config_name="voi_informed", prompt_type="zero-shot",
                   algorithm="css", condition="voi_informed", top_k=5):
    """Run VOI-informed hybrid evaluation on canonical test set."""

    if schedule is None:
        schedule = {1: "llm", 2: "css", 3: "css", 4: "css", 5: "css", 6: "css"}

    print("=" * 80)
    print(f"VOI-INFORMED HYBRID EVALUATION: {config_name}")
    print("=" * 80)
    print(f"Model: {model_name}")
    print(f"Algorithm: {algorithm.upper()}")
    print(f"Condition: {condition}")
    print(f"Prompt Type: {prompt_type}")
    print(f"Top-K: {top_k}")
    print(f"Schedule: {json.dumps({str(k): v for k, v in schedule.items()})}")
    print(f"Games: {num_games}")
    print("=" * 80)

    # Load word list and test set
    with open(PROJECT_ROOT / 'wordlist' / 'wordlist.txt', 'r') as f:
        word_list = [line.strip().upper() for line in f if line.strip()]

    test_words = get_test_words_only()[:num_games]

    # Initialize strategy and agent
    strategy = VOIInformedHybridStrategy(
        schedule=schedule, model_name=model_name,
        temperature=0.7, prompt_type=prompt_type,
        algorithm=algorithm, condition=condition, top_k=top_k
    )
    agent = VOIInformedGuessingAgent(word_list, strategy)

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
            'strategy_used': [],
            'algo_top1': [],
            'algo_scores': [],
            'entropy_at_turn': [],
            'llm_followed_algo': [],
            'displayed_top1': [],
            'llm_picked_displayed_top1': []
        }

        for attempt in range(1, 7):
            guess = agent.select_guess(attempt)
            if not guess:
                print(f"  Attempt {attempt}: No valid guess available")
                break

            # Capture VOI metadata before updating state
            meta = dict(strategy.last_turn_metadata)

            feedback, reward = env.guess(guess)
            agent.update(guess, feedback, reward)

            ham_dist = hamming_distance(guess, target_word)
            lev_dist = levenshtein_distance(guess, target_word)
            feedback_str = ''.join(feedback)
            strategy_label = strategy.get_strategy_label(attempt)

            print(f"  Attempt {attempt} [{strategy_label}]: {guess} -> {feedback_str} "
                  f"(H:{ham_dist}, L:{lev_dist})", end="")
            if meta.get('algo_top1'):
                print(f" [algo_top1={meta['algo_top1']}, followed={meta.get('llm_followed_algo', '')}]", end="")
            print()

            game_result['guesses'].append(guess)
            game_result['feedbacks'].append(feedback_str)
            game_result['hamming_distances'].append(ham_dist)
            game_result['levenshtein_distances'].append(lev_dist)
            game_result['strategy_used'].append(strategy_label)
            game_result['algo_top1'].append(meta.get('algo_top1', ''))
            game_result['algo_scores'].append(meta.get('algo_scores', ''))
            game_result['entropy_at_turn'].append(meta.get('entropy_at_turn', ''))
            game_result['llm_followed_algo'].append(meta.get('llm_followed_algo', ''))
            game_result['displayed_top1'].append(meta.get('displayed_top1', ''))
            game_result['llm_picked_displayed_top1'].append(meta.get('llm_picked_displayed_top1', ''))
            game_result['attempts'] = attempt

            if all(f == "G" for f in feedback):
                game_result['won'] = True
                wins += 1
                total_attempts += attempt
                print(f"  Won in {attempt} attempts!")
                break

        if not game_result['won']:
            print("  Failed to find word")

        results.append(game_result)

    # Statistics
    win_rate = wins / num_games if num_games > 0 else 0
    avg_attempts = total_attempts / wins if wins > 0 else 0

    # Calculate follow rate
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
        # How often did LLM pick the displayed-first word (rank position imitation)
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
        output_dir = PROJECT_ROOT / 'voi_integration' / 'results' / 'wordle'
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prompt_suffix = "_cot" if prompt_type == "cot" else ""
    safe_config = config_name.replace(" ", "_").replace("/", "_")
    csv_file = output_dir / f"{safe_config}_{model_name}{prompt_suffix}_{timestamp}.csv"

    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)

        header = ['game_number', 'target_word', 'won', 'attempts']
        for i in range(1, 7):
            header.extend([
                f'guess_{i}', f'feedback_{i}', f'hamming_{i}', f'levenshtein_{i}',
                f'strategy_{i}', f'algo_top1_{i}', f'algo_scores_{i}',
                f'entropy_{i}', f'llm_followed_algo_{i}',
                f'displayed_top1_{i}', f'llm_picked_displayed_top1_{i}'
            ])
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
                        result['strategy_used'][i] if i < len(result['strategy_used']) else '',
                        result['algo_top1'][i] if i < len(result['algo_top1']) else '',
                        result['algo_scores'][i] if i < len(result['algo_scores']) else '',
                        result['entropy_at_turn'][i] if i < len(result['entropy_at_turn']) else '',
                        result['llm_followed_algo'][i] if i < len(result['llm_followed_algo']) else '',
                        result['displayed_top1'][i] if i < len(result['displayed_top1']) else '',
                        result['llm_picked_displayed_top1'][i] if i < len(result['llm_picked_displayed_top1']) else ''
                    ])
                else:
                    row.extend([''] * 11)
            writer.writerow(row)

    # Save summary JSON
    summary = {
        'strategy': 'voi_informed_hybrid',
        'config_name': config_name,
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

    # Parse schedule
    schedule_str = os.getenv("SCHEDULE")
    if schedule_str:
        raw = json.loads(schedule_str)
        schedule = {int(k): v for k, v in raw.items()}
    else:
        # Default: LLM round 1, algorithm rounds 2-6
        algo = algorithm if algorithm in VALID_STRATEGIES else "css"
        schedule = {1: "llm", 2: algo, 3: algo, 4: algo, 5: algo, 6: algo}

    # Check API key
    if "llm" in schedule.values():
        try:
            _get_api_key_for_model(model_name)
        except RuntimeError as e:
            print(f"ERROR: {e}")
            sys.exit(1)

    run_evaluation(
        num_games=num_games,
        model_name=model_name,
        schedule=schedule,
        config_name=config_name,
        prompt_type=prompt_type,
        algorithm=algorithm,
        condition=condition,
        top_k=top_k
    )
