#!/usr/bin/env python3
"""
Repair Hybrid Strategies

Two repair mechanisms:
  D18 - Constraint Filter: LLM proposes a guess; if it violates known constraints,
        the algorithm picks instead.
  D19 - Rerank: Algorithm generates top-k candidates; LLM picks from them.

Configured via REPAIR_MODE env var: "constraint_filter" or "rerank".
ALGORITHM env var selects the algorithm: "css" or "voi".
"""

import os
import csv
import time
import json
import random
import re
import sys
from datetime import datetime
from typing import List, Tuple
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


class RepairHybridStrategy:
    """
    Repair hybrid: combines LLM guessing with algorithmic safety nets.

    Modes:
      - constraint_filter: LLM guesses first. If invalid (not in remaining
        candidates), the algorithm picks instead.
      - rerank: Algorithm scores top-k candidates. LLM picks from that shortlist.
    """

    def __init__(self, repair_mode: str = "constraint_filter",
                 algorithm: str = "css", model_name: str = "llama-3.3-70b-instruct",
                 temperature: float = 0.7, prompt_type: str = "zero-shot",
                 top_k: int = 5):
        self.repair_mode = repair_mode.lower()
        self.algorithm = algorithm.lower()
        self.model_name = model_name
        self.temperature = temperature
        self.prompt_type = prompt_type.lower()
        self.top_k = top_k
        self.turn_number = 0
        self.api_base = os.getenv("NAVIGATOR_API_ENDPOINT", "https://api.navigator.uf.edu/v1")

        # Counters for tracking repairs
        self.llm_accepted = 0
        self.llm_repaired = 0

        if self.algorithm == "css":
            self.algo_strategy = CSSStrategy()
        elif self.algorithm == "css_true":
            self.algo_strategy = CSSTrueStrategy()
        elif self.algorithm == "voi":
            self.algo_strategy = VOIStrategy()
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")

    def update_belief(self, candidates: List[str], guess: str, feedback: List[str]) -> List[str]:
        """Update candidates based on feedback."""
        return self.algo_strategy.update_belief(candidates, guess, feedback)

    def get_guess(self, candidates: List[str], history: List[Tuple[str, List[str]]]) -> Tuple[str, str]:
        """
        Get next guess using the repair mechanism.

        Returns: (guess, strategy_label) where strategy_label indicates
                 what actually happened: 'LLM', 'LLM_REPAIRED', 'ALGO', etc.
        """
        self.turn_number = len(history) + 1

        if self.repair_mode == "constraint_filter":
            return self._constraint_filter_guess(candidates, history)
        elif self.repair_mode == "rerank":
            return self._rerank_guess(candidates, history)
        elif self.repair_mode == "rerank_llm_first":
            return self._rerank_llm_first_guess(candidates, history)
        else:
            raise ValueError(f"Unknown repair mode: {self.repair_mode}")

    def _constraint_filter_guess(self, candidates: List[str],
                                  history: List[Tuple[str, List[str]]]) -> Tuple[str, str]:
        """
        D18: LLM proposes; if invalid (not in candidates), algorithm picks instead.
        """
        llm_guess = self._get_llm_guess_raw(candidates, history)

        if llm_guess and llm_guess in candidates:
            self.llm_accepted += 1
            return llm_guess, "LLM"
        else:
            self.llm_repaired += 1
            algo_label = self.algorithm.upper()
            if llm_guess:
                print(f"    Constraint filter: '{llm_guess}' not in candidates, using {algo_label}")
            else:
                print(f"    Constraint filter: LLM failed, using {algo_label}")
            algo_guess = self.algo_strategy.select_guess(candidates, history)
            return algo_guess, f"{algo_label}_REPAIR"

    def _rerank_guess(self, candidates: List[str],
                       history: List[Tuple[str, List[str]]]) -> Tuple[str, str]:
        """
        D19: Algorithm generates top-k, LLM picks from them.
        """
        # Get top-k from algorithm
        if hasattr(self.algo_strategy, 'score_candidates'):
            top_k_candidates = self.algo_strategy.score_candidates(candidates, history, self.top_k)
            shortlist = [w for w, _ in top_k_candidates]
        else:
            # Fallback: just sample from candidates
            shortlist = random.sample(candidates, min(self.top_k, len(candidates)))

        if len(shortlist) == 1:
            return shortlist[0], self.algorithm.upper()

        # Ask LLM to pick from the shortlist
        llm_pick = self._get_llm_rerank_guess(shortlist, candidates, history)

        if llm_pick and llm_pick in shortlist:
            self.llm_accepted += 1
            return llm_pick, "LLM_RERANK"
        else:
            # LLM didn't pick from shortlist, use algorithm's top pick
            self.llm_repaired += 1
            return shortlist[0], self.algorithm.upper()

    def _rerank_llm_first_guess(self, candidates: List[str],
                                  history: List[Tuple[str, List[str]]]) -> Tuple[str, str]:
        """
        D19a: LLM proposes top-k preferences from candidates, algorithm selects best among them.

        LLM acts as heuristic prior, algorithm is the final safety gate.
        """
        # Ask LLM to suggest its top picks from valid candidates
        llm_picks = self._get_llm_topk_suggestions(candidates, history)

        if llm_picks and len(llm_picks) > 0:
            # Filter to only valid candidates
            valid_picks = [w for w in llm_picks if w in candidates]

            if valid_picks:
                # Algorithm selects the best from LLM's valid suggestions
                if hasattr(self.algo_strategy, 'score_candidates'):
                    scored = self.algo_strategy.score_candidates(
                        valid_picks, history, min(self.top_k, len(valid_picks)))
                    best = scored[0][0] if scored else valid_picks[0]
                else:
                    best = self.algo_strategy.select_guess(valid_picks, history)
                    if best not in valid_picks:
                        best = valid_picks[0]

                self.llm_accepted += 1
                return best, f"{self.algorithm.upper()}_FROM_LLM"

        # LLM failed to provide valid suggestions, fall back to pure algorithm
        self.llm_repaired += 1
        algo_guess = self.algo_strategy.select_guess(candidates, history)
        return algo_guess, self.algorithm.upper()

    def _get_llm_topk_suggestions(self, candidates: List[str],
                                    history: List[Tuple[str, List[str]]]) -> List[str]:
        """Ask LLM to suggest its top-k preferred guesses from candidates."""
        try:
            import openai
            client = openai.OpenAI(
                api_key=os.getenv("NAVIGATOR_UF_API_KEY"),
                base_url=self.api_base
            )

            prompt = self._build_llm_topk_prompt(candidates, history)

            for attempt in range(5):
                try:
                    response = client.chat.completions.create(
                        model=self.model_name,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=self.temperature,
                        max_tokens=200
                    )
                    text = response.choices[0].message.content.strip()
                    picks = self._extract_multiple_guesses(text, history, candidates)
                    return picks
                except Exception as e:
                    print(f"    LLM topk attempt {attempt+1}/5 failed: {e}")
                    if attempt < 4:
                        time.sleep(2 ** attempt + random.uniform(0, 1))

        except Exception as e:
            print(f"    LLM initialization failed: {e}")

        return []

    def _build_llm_topk_prompt(self, candidates: List[str],
                                 history: List[Tuple[str, List[str]]]) -> str:
        """Build prompt asking LLM to suggest top-k guesses."""
        if self.prompt_type == "cot":
            prompt = (
                "You are an expert Wordle player. Suggest your TOP 5 best guesses.\n"
                "Return output in this exact format:\n"
                "THINKING: <your concise reasoning>\n"
                "PICKS: <word1>, <word2>, <word3>, <word4>, <word5>\n\n"
                "Feedback codes: G=green (correct position), Y=yellow (wrong position), -=not in word.\n\n"
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
                "List your TOP 5 choices from the candidates (best first).\n"
                "Keep THINKING concise."
            )
        else:
            prompt = "You are playing Wordle. Suggest your TOP 5 best guesses.\n\n"

            if history:
                prompt += "Previous guesses:\n"
                for guess, feedback in history:
                    feedback_str = ''.join(
                        ['🟩' if f == 'G' else '🟨' if f == 'Y' else '⬜' for f in feedback])
                    prompt += f"{guess}: {feedback_str}\n"
                prompt += "\n"

            if len(candidates) <= 30:
                prompt += f"Remaining possible words ({len(candidates)}): {', '.join(candidates)}\n\n"
            elif len(candidates) <= 100:
                sample = random.sample(candidates, 20)
                prompt += f"Remaining possible words ({len(candidates)}, showing sample): {', '.join(sample)}\n\n"
            else:
                prompt += f"Number of remaining possible words: {len(candidates)}\n\n"

            prompt += "List your TOP 5 best guesses, separated by commas.\n"
            prompt += "Return ONLY five 5-letter words in uppercase, comma-separated.\n"
            prompt += "Your picks: "

        return prompt

    def _extract_multiple_guesses(self, text: str, history: List[Tuple[str, List[str]]],
                                    candidates: List[str]) -> List[str]:
        """Extract multiple 5-letter words from LLM response."""
        if not text:
            return []

        used = {g for g, _ in history}

        # Try PICKS: line first for CoT
        if self.prompt_type == "cot":
            picks_match = re.search(r'PICKS\s*:\s*(.+)', text, re.IGNORECASE)
            if picks_match:
                text = picks_match.group(1)

        words = re.findall(r'\b[A-Za-z]{5}\b', text.upper())
        # Deduplicate while preserving order
        seen = set()
        result = []
        for word in words:
            if word not in seen and word not in used:
                seen.add(word)
                result.append(word)
                if len(result) >= self.top_k:
                    break

        return result

    def _get_llm_guess_raw(self, candidates: List[str],
                            history: List[Tuple[str, List[str]]]) -> str:
        """Get raw LLM guess (may or may not be valid)."""
        try:
            import openai
            client = openai.OpenAI(
                api_key=os.getenv("NAVIGATOR_UF_API_KEY"),
                base_url=self.api_base
            )

            prompt = self._build_prompt(candidates, history)

            for attempt in range(5):
                try:
                    response = client.chat.completions.create(
                        model=self.model_name,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=self.temperature,
                        max_tokens=150
                    )
                    text = response.choices[0].message.content.strip()
                    guess = self._extract_guess(text, history, candidates)
                    return guess  # May be None
                except Exception as e:
                    print(f"    LLM API attempt {attempt+1}/5 failed: {e}")
                    if attempt < 4:
                        time.sleep(2 ** attempt + random.uniform(0, 1))

        except Exception as e:
            print(f"    LLM initialization failed: {e}")

        return None

    def _get_llm_rerank_guess(self, shortlist: List[str], candidates: List[str],
                               history: List[Tuple[str, List[str]]]) -> str:
        """Get LLM to pick from a shortlist of algorithm-ranked candidates."""
        try:
            import openai
            client = openai.OpenAI(
                api_key=os.getenv("NAVIGATOR_UF_API_KEY"),
                base_url=self.api_base
            )

            prompt = self._build_rerank_prompt(shortlist, candidates, history)

            for attempt in range(5):
                try:
                    response = client.chat.completions.create(
                        model=self.model_name,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=self.temperature,
                        max_tokens=150
                    )
                    text = response.choices[0].message.content.strip()
                    guess = self._extract_rerank_guess(text, history, shortlist)
                    return guess
                except Exception as e:
                    print(f"    LLM rerank attempt {attempt+1}/5 failed: {e}")
                    if attempt < 4:
                        time.sleep(2 ** attempt + random.uniform(0, 1))

        except Exception as e:
            print(f"    LLM initialization failed: {e}")

        return None

    def _build_prompt(self, candidates: List[str], history: List[Tuple[str, List[str]]]) -> str:
        """Build standard prompt for constraint filter mode."""
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
                "- Do NOT repeat previous guesses.\n"
                "- The FINAL line must be exactly ONE valid 5-letter word from the allowed list.\n"
                "- Keep THINKING concise (1-5 short lines)."
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
            elif len(candidates) <= 100:
                sample = random.sample(candidates, 20)
                prompt += f"Remaining possible words ({len(candidates)}, showing sample): {', '.join(sample)}\n\n"
            else:
                prompt += f"Number of remaining possible words: {len(candidates)}\n\n"

            prompt += "Based on the feedback, what should the next guess be?\n"
            prompt += "Return ONLY a single 5-letter word in uppercase, nothing else.\n"
            prompt += "Your guess: "

        return prompt

    def _build_rerank_prompt(self, shortlist: List[str], candidates: List[str],
                              history: List[Tuple[str, List[str]]]) -> str:
        """Build prompt for rerank mode - LLM picks from shortlist."""
        if self.prompt_type == "cot":
            prompt = (
                "You are an expert Wordle player. An algorithm has narrowed down the best guesses.\n"
                "Choose the BEST guess from the shortlist below.\n"
                "Return output in this exact format:\n"
                "THINKING: <your concise reasoning for choosing>\n"
                "FINAL: <ONE 5-letter word from the shortlist>\n\n"
                "Feedback codes: G=green (correct position), Y=yellow (wrong position), -=not in word.\n\n"
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

            prompt += f"\nRemaining candidates: {len(candidates)}\n"
            prompt += f"Algorithm's top picks: {', '.join(shortlist)}\n\n"
            prompt += "Choose ONE word from the shortlist above. Keep THINKING concise."
        else:
            prompt = "You are playing Wordle. An algorithm has pre-selected the best candidate guesses.\n\n"

            if history:
                prompt += "Previous guesses:\n"
                for guess, feedback in history:
                    feedback_str = ''.join(
                        ['🟩' if f == 'G' else '🟨' if f == 'Y' else '⬜' for f in feedback])
                    prompt += f"{guess}: {feedback_str}\n"
                prompt += "\n"

            prompt += f"Remaining possible words: {len(candidates)}\n"
            prompt += f"Top candidates to choose from: {', '.join(shortlist)}\n\n"
            prompt += "Pick the BEST word from the candidates above.\n"
            prompt += "Return ONLY a single 5-letter word in uppercase, nothing else.\n"
            prompt += "Your choice: "

        return prompt

    def _extract_guess(self, text: str, history: List[Tuple[str, List[str]]],
                       candidates: List[str]) -> str:
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

    def _extract_rerank_guess(self, text: str, history: List[Tuple[str, List[str]]],
                               shortlist: List[str]) -> str:
        """Extract a word from the shortlist out of LLM response."""
        if not text:
            return None

        used = {g for g, _ in history}
        shortlist_set = set(shortlist)

        if self.prompt_type == "cot":
            final_match = re.search(r'FINAL\s*:\s*([A-Za-z]{5})\b', text, re.IGNORECASE)
            if final_match:
                word = final_match.group(1).upper()
                if word in shortlist_set and word not in used:
                    return word

        words = re.findall(r'\b[A-Za-z]{5}\b', text.upper())

        for word in words:
            if word in shortlist_set and word not in used:
                return word

        return None


# ----------------- Guessing Agent -----------------

class RepairGuessingAgent:
    """Agent that uses the repair hybrid strategy to play Wordle."""

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

    def select_guess(self):
        """Select next guess using strategy. Returns (guess, strategy_label)."""
        return self.strategy.get_guess(self.candidates, self.history)

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
                   repair_mode="constraint_filter", algorithm="css",
                   prompt_type="zero-shot", config_name=None, top_k=5):
    """Run repair hybrid evaluation on canonical test set."""

    if config_name is None:
        config_name = f"{repair_mode}_{algorithm}"

    print("=" * 80)
    print(f"REPAIR HYBRID EVALUATION: {config_name}")
    print("=" * 80)
    print(f"Model: {model_name}")
    print(f"Repair Mode: {repair_mode}")
    print(f"Algorithm: {algorithm.upper()}")
    print(f"Prompt Type: {prompt_type}")
    if repair_mode == "rerank":
        print(f"Top-K: {top_k}")
    print(f"Games: {num_games}")
    print("=" * 80)

    # Load word list and test set
    script_dir = Path(__file__).parent.parent.parent
    with open(script_dir / 'wordlist' / 'wordlist.txt', 'r') as f:
        word_list = [line.strip().upper() for line in f if line.strip()]

    test_words = get_test_words_only()[:num_games]

    # Initialize strategy and agent
    strategy = RepairHybridStrategy(
        repair_mode=repair_mode, algorithm=algorithm,
        model_name=model_name, temperature=0.7,
        prompt_type=prompt_type, top_k=top_k
    )
    agent = RepairGuessingAgent(word_list, strategy)

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
            guess, strategy_label = agent.select_guess()
            if not guess:
                print(f"  Attempt {attempt}: No valid guess available")
                break

            feedback, reward = env.guess(guess)
            agent.update(guess, feedback, reward)

            ham_dist = hamming_distance(guess, target_word)
            lev_dist = levenshtein_distance(guess, target_word)
            feedback_str = ''.join(feedback)

            game_result['strategy_used'].append(strategy_label)

            print(f"  Attempt {attempt} [{strategy_label}]: {guess} -> {feedback_str} (H:{ham_dist}, L:{lev_dist})")

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

    # Statistics
    win_rate = wins / num_games if num_games > 0 else 0
    avg_attempts = total_attempts / wins if wins > 0 else 0
    total_guesses = strategy.llm_accepted + strategy.llm_repaired
    repair_rate = strategy.llm_repaired / total_guesses if total_guesses > 0 else 0

    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    print(f"Games played: {num_games}")
    print(f"Wins: {wins}")
    print(f"Win rate: {win_rate * 100:.1f}%")
    print(f"Average attempts (when won): {avg_attempts:.2f}")
    print(f"LLM accepted: {strategy.llm_accepted}")
    print(f"LLM repaired/overridden: {strategy.llm_repaired}")
    print(f"Repair rate: {repair_rate * 100:.1f}%")
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
        'strategy': 'repair_hybrid',
        'config_name': config_name,
        'repair_mode': repair_mode,
        'algorithm': algorithm,
        'model_name': model_name,
        'prompt_type': prompt_type,
        'top_k': top_k if repair_mode == "rerank" else None,
        'total_games': num_games,
        'wins': wins,
        'win_rate': win_rate,
        'avg_attempts_when_won': avg_attempts,
        'llm_accepted': strategy.llm_accepted,
        'llm_repaired': strategy.llm_repaired,
        'repair_rate': repair_rate,
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
    repair_mode = os.getenv("REPAIR_MODE", "constraint_filter")
    algorithm = os.getenv("ALGORITHM", "css")
    config_name = os.getenv("CONFIG_NAME")
    top_k = int(os.getenv("TOP_K", "5"))

    if not os.getenv("NAVIGATOR_UF_API_KEY"):
        print("ERROR: NAVIGATOR_UF_API_KEY environment variable not set")
        sys.exit(1)

    run_evaluation(
        num_games=num_games,
        model_name=model_name,
        repair_mode=repair_mode,
        algorithm=algorithm,
        prompt_type=prompt_type,
        config_name=config_name,
        top_k=top_k
    )
