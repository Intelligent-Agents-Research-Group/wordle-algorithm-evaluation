#!/usr/bin/env python3
"""
Single model evaluation script for array job.
Runs one model with one prompting type on the standardized word set.
Logs full chain-of-thought (CoT) traces and final guesses per attempt.
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
import numpy as np

from wordle_env import WordleEnv
from guessing_agent import GuessingAgent
from llm_strategy import LLMStrategy
from test_set_loader import get_test_words_only


# ----------------- Helpers -----------------

def call_with_retry(fn, tries=5, base_delay=1.0):
    """Retry wrapper for transient API errors (429/5xx/etc.)."""
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            print(f"API call attempt {i+1}/{tries} failed: {e}")
            if i == tries - 1:
                raise
            # Exponential backoff with jitter
            delay = base_delay * (2 ** i) + random.uniform(0, 1)
            time.sleep(delay)


def extract_valid_guess(text: str, used: set, word_list: List[str]) -> str | None:
    """
    Extract a single valid 5-letter word from LLM output.
    Must be in word_list and not already guessed.
    """
    if not text:
        return None
    cands = re.findall(r'\b[A-Za-z]{5}\b', text.upper())
    for w in cands:
        if w in word_list and w not in used:
            return w
    return None


def filter_candidates_by_feedback(candidates: List[str], guess: str, feedback: List[int]) -> List[str]:
    """Basic Wordle filtering (greens, yellows, grays)."""
    guess = guess.upper()
    keep = []
    for w in candidates:
        wu = w.upper()
        ok = True
        # greens
        for i, f in enumerate(feedback):
            if f == 2 and wu[i] != guess[i]:
                ok = False; break
        if not ok: 
            continue
        # yellows: letter present but in different position
        for i, f in enumerate(feedback):
            if f == 1:
                if guess[i] not in wu or wu[i] == guess[i]:
                    ok = False; break
        if not ok: 
            continue
        # grays: letter not present anywhere (simplified; duplicates not handled)
        for i, f in enumerate(feedback):
            if f == 0 and guess[i] in wu:
                ok = False; break
        if ok:
            keep.append(w)
    return keep


def shorten(s: str, limit: int = 2000) -> str:
    """Trim long blobs so CSVs don't explode. Keep head & tail."""
    if s is None:
        return ""
    if len(s) <= limit:
        return s
    head = s[: limit // 2]
    tail = s[-(limit // 2):]
    return head + "\n...[truncated]...\n" + tail


# ----------------- Metrics Calculations -----------------

def calculate_constraint_violations(guess: str, feedback_history: List[Tuple[str, str]], target_word: str = None) -> dict:
    """
    Check if a guess violates known constraints from previous feedback.
    Returns dict with violation flags and counts.
    """
    violations = {
        'violated_green': False,      # Used letter known to be in wrong position (green constraint)
        'violated_yellow': False,     # Missed letter known to be in word (yellow constraint)
        'violated_gray': False,       # Reused letter known not to be in word (gray constraint)
        'violation_count': 0
    }

    if not feedback_history:
        return violations

    guess = guess.upper()

    # Build constraint sets from history
    green_positions = {}  # pos -> letter that must be there
    yellow_letters = set()  # letters that must be in word
    yellow_exclusions = {}  # letter -> set of positions it can't be
    gray_letters = set()  # letters not in word

    for prev_guess, prev_feedback in feedback_history:
        prev_guess = prev_guess.upper()
        for i, (letter, fb) in enumerate(zip(prev_guess, prev_feedback)):
            if fb == 'G':
                green_positions[i] = letter
                if letter in yellow_letters:
                    yellow_letters.remove(letter)  # green overrides yellow
            elif fb == 'Y':
                if i not in green_positions:  # only track if not already green
                    yellow_letters.add(letter)
                    if letter not in yellow_exclusions:
                        yellow_exclusions[letter] = set()
                    yellow_exclusions[letter].add(i)
            elif fb == '-':
                # Only gray if letter isn't green/yellow elsewhere
                if letter not in green_positions.values() and letter not in yellow_letters:
                    gray_letters.add(letter)

    # Check violations
    # Green violations: wrong letter in known position
    for pos, required_letter in green_positions.items():
        if guess[pos] != required_letter:
            violations['violated_green'] = True
            violations['violation_count'] += 1

    # Yellow violations: missing known letter or letter in known-bad position
    for letter in yellow_letters:
        if letter not in guess:
            violations['violated_yellow'] = True
            violations['violation_count'] += 1
        elif letter in yellow_exclusions:
            for i, g_letter in enumerate(guess):
                if g_letter == letter and i in yellow_exclusions[letter]:
                    violations['violated_yellow'] = True
                    violations['violation_count'] += 1

    # Gray violations: reusing excluded letter
    for letter in gray_letters:
        if letter in guess:
            violations['violated_gray'] = True
            violations['violation_count'] += 1

    return violations


def calculate_information_gain(candidates_before: int, candidates_after: int) -> float:
    """
    Calculate information gain from a guess using entropy reduction.
    Returns bits of information gained.
    """
    if candidates_before <= 0:
        return 0.0
    if candidates_after <= 0:
        candidates_after = 1  # Perfect elimination

    # Entropy = log2(possibilities)
    # Information gain = reduction in entropy
    from math import log2
    entropy_before = log2(candidates_before)
    entropy_after = log2(candidates_after)
    return max(0.0, entropy_before - entropy_after)


def calculate_candidate_reduction_rate(candidates_before: int, candidates_after: int) -> float:
    """
    Calculate percentage reduction in candidate pool.
    Returns value between 0.0 and 1.0.
    """
    if candidates_before <= 0:
        return 0.0
    reduction = candidates_before - candidates_after
    return reduction / candidates_before


def is_valid_guess(guess: str, word_list: List[str]) -> bool:
    """Check if guess is a valid word from the word list."""
    return guess.upper() in [w.upper() for w in word_list]


# ----------------- Strategies -----------------

class NavigatorUFStrategy(LLMStrategy):
    """Base strategy for Navigator UF models (zero-shot)."""
    def __init__(self, model_name, temperature=0.7):
        super().__init__(model_name, temperature)
        self.api_base = os.getenv("NAVIGATOR_API_ENDPOINT", "https://api.navigator.uf.edu/v1")
        self.used = set()

    def _build_prompt(self, word_list, feedback_history):
        prior = ""
        if feedback_history:
            last = feedback_history[-3:]   # keep context compact
            lines = []
            for g, fb in last:
                # feedback is a list of strings like ['G','Y','-','-','G']; convert to string
                if isinstance(fb, list) and len(fb) > 0:
                    if isinstance(fb[0], str):
                        # Already string format
                        fb_str = ''.join(fb)
                    else:
                        # Integer format, convert to string
                        fb_str = ''.join('GY-'[x] for x in fb)  # 2->G,1->Y,0->-
                else:
                    fb_str = str(fb)

                # Create letter-by-letter breakdown for clarity
                g_upper = g.upper()
                letter_breakdown = "  ".join([f"{g_upper[i]}:{fb_str[i]}" for i in range(min(len(g_upper), len(fb_str)))])

                lines.append(f"Guess: {g}, Feedback: {fb_str}")
                lines.append(f"  Per letter: {letter_breakdown}")
            prior = "Previous attempts:\n" + "\n".join(lines) + "\n"

        # Include candidate word list (sample if too large, full list if reasonable)
        if len(word_list) <= 50:
            candidates_str = ", ".join(word_list)
        else:
            # Show first 30 + last 20 for context
            sample = word_list[:30] + ["..."] + word_list[-20:]
            candidates_str = ", ".join(sample)

        prompt = (
            "You are playing Wordle. Return ONLY the next guess as a single "
            "5-letter English word from the allowed list. Do NOT repeat previous guesses.\n\n"
            "Feedback codes: G=green (correct letter, correct position), "
            "Y=yellow (correct letter, wrong position), -=letter not in word.\n"
            "Each feedback position corresponds to the letter at that position in your guess.\n\n"
            f"{prior}"
            f"Allowed words remaining: {len(word_list)}\n"
            f"Candidate words: {candidates_str}\n\n"
            "Answer with just the word."
        )
        self.last_prompt = prompt  # Store for CSV logging
        return prompt

    def get_guess(self, word_list, feedback_history=None):
        try:
            import openai
            client = openai.OpenAI(
                api_key=os.getenv("NAVIGATOR_UF_API_KEY"),
                base_url=self.api_base
            )
            feedback_history = feedback_history or []
            prompt = self._build_prompt(word_list, feedback_history)

            def api_call():
                return client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.temperature,
                    max_tokens=16,
                    timeout=30.0  # Add explicit timeout
                )

            response = call_with_retry(api_call, tries=3, base_delay=0.75)

            # Check if response has choices and content
            if not response.choices or len(response.choices) == 0:
                raise ValueError("API returned empty choices array")

            raw = (response.choices[0].message.content or "").strip()
            # zero-shot has no explicit CoT; we still log raw response as "cot_trace" for parity
            cot_trace = raw
            guess = extract_valid_guess(raw, self.used, word_list)

            # Debug logging
            if not guess:
                print(f"[WARNING] Could not extract valid guess from response: {raw[:100]}")
                print(f"[WARNING] Used words: {self.used}")
                print(f"[WARNING] Candidates available: {len(word_list)}")

            if not guess:
                pool = [w for w in word_list if w not in self.used]
                guess = random.choice(pool) if pool else random.choice(word_list)

            self.used.add(guess)
            # Store latest trace/raw for the agent to log (agent can read from strategy if needed)
            self.last_trace = shorten(cot_trace, 2000)
            self.last_raw = shorten(raw, 2000)
            return guess

        except Exception as e:
            print(f"Error with {self.model_name}: {e}")
            print(f"Error type: {type(e).__name__}")
            pool = [w for w in word_list if w not in self.used]
            guess = random.choice(pool) if pool else random.choice(word_list)
            self.used.add(guess)
            self.last_trace = f"[ERROR] {type(e).__name__}: {e}"
            self.last_raw = self.last_trace
            return guess

    def update_belief(self, candidates, guess, feedback):
        """Filter candidates based on feedback (handles duplicate letters correctly)."""
        # Ensure feedback is in string format ('G', 'Y', '-')
        if feedback and isinstance(feedback[0], int):
            str_feedback = ['G' if f == 2 else 'Y' if f == 1 else '-' for f in feedback]
        else:
            str_feedback = feedback

        # Filter using consistency check (handles duplicates correctly)
        return [word for word in candidates if self._is_consistent(word, guess, str_feedback)]

    def _is_consistent(self, word, guess, feedback):
        """Check if a word is consistent with the feedback from a guess."""
        return self._generate_feedback(word, guess) == feedback

    def _generate_feedback(self, target, guess):
        """Generate feedback for a guess against a target word (handles duplicates)."""
        feedback = ["-"] * 5
        target_chars = list(target)
        guess_chars = list(guess)

        # Mark greens first
        for i in range(5):
            if guess_chars[i] == target_chars[i]:
                feedback[i] = "G"
                target_chars[i] = None
                guess_chars[i] = None

        # Mark yellows
        for i in range(5):
            if guess_chars[i] and guess_chars[i] in target_chars:
                feedback[i] = "Y"
                target_chars[target_chars.index(guess_chars[i])] = None

        return feedback


class NavigatorUFCoTStrategy(NavigatorUFStrategy):
    """Chain-of-thought version for Navigator UF models with trace capture."""

    def _construct_prompt(self, word_list, feedback_history):
        # Ask for visible reasoning that we can capture, then a single final guess.
        prompt = (
            "You are an expert Wordle player. Use brief, structured reasoning.\n"
            "Return output in this exact format:\n"
            "THINKING: <your concise step-by-step reasoning>\n"
            "FINAL: <ONE 5-letter guess only>\n\n"
            "Feedback codes: G=green (correct letter, correct position), "
            "Y=yellow (correct letter, wrong position), -=letter not in word.\n"
            "Each feedback position corresponds to the letter at that position in your guess.\n"
            "Example: Guess HOUSE → Feedback ----G means H:-, O:-, U:-, S:-, E:G\n"
            "  (H not in word, O not in word, U not in word, S not in word, E correct at position 5)\n\n"
        )
        if feedback_history:
            prompt += "Previous attempts:\n"
            for guess, feedback in feedback_history:
                # feedback is a list of strings like ['G','Y','-','-','G']; convert to string
                if isinstance(feedback, list) and len(feedback) > 0:
                    if isinstance(feedback[0], str):
                        # Already string format
                        fb_str = ''.join(feedback)
                    else:
                        # Integer format, convert to string
                        fb_str = ''.join({2:'G', 1:'Y', 0:'-'}.get(x, str(x)) for x in feedback)
                else:
                    fb_str = str(feedback)

                # Create letter-by-letter breakdown for clarity
                guess_upper = guess.upper()
                letter_breakdown = "  ".join([f"{guess_upper[i]}:{fb_str[i]}" for i in range(min(len(guess_upper), len(fb_str)))])

                prompt += f"- Guess: {guess}  Feedback: {fb_str}\n"
                prompt += f"  Per letter: {letter_breakdown}\n"

        # Include candidate word list (sample if too large, full list if reasonable)
        if len(word_list) <= 50:
            candidates_str = ", ".join(word_list)
        else:
            # Show first 30 + last 20 for context
            sample = word_list[:30] + ["..."] + word_list[-20:]
            candidates_str = ", ".join(sample)

        prompt += (
            f"\nAllowed words remaining: {len(word_list)}\n"
            f"Candidate words: {candidates_str}\n\n"
            "Constraints:\n"
            "• Do NOT repeat previous guesses.\n"
            "• The FINAL line must be exactly ONE valid 5-letter word from the allowed list.\n"
            "• Keep THINKING concise (1–5 short lines)."
        )
        self.last_prompt = prompt  # Store for CSV logging
        return prompt

    def pop_trace(self) -> str:
        """Return and clear the last captured trace text."""
        t, self._last_trace = getattr(self, "_last_trace", ""), ""
        return t

    def _parse_thinking_and_final(self, text: str) -> tuple[str, str]:
        """
        Extract THINKING block and FINAL guess. Robust to variations.
        Returns (thinking, guess) where guess is UPPERCASE 5 letters or ''.
        """
        import re
        s = text or ""
        # Try to split on FINAL:
        m_final = re.search(r'FINAL\s*:\s*([A-Za-z]{5})\b', s)
        guess = m_final.group(1).upper() if m_final else ""

        # THINKING section: lines after 'THINKING:' up to 'FINAL:' (or end)
        thinking = ""
        m_think = re.search(r'THINKING\s*:\s*(.*)', s, flags=re.IGNORECASE | re.DOTALL)
        if m_think:
            block = m_think.group(1)
            if m_final:
                block = block[:m_final.start() - m_think.start(1)]
            thinking = block.strip()

        return thinking, guess

    def get_guess(self, word_list, feedback_history=None):
        """
        Call Navigator UF (OpenAI-compatible) endpoint, capture THINKING trace and FINAL guess.
        """
        try:
            import openai
            client = openai.OpenAI(
                api_key=os.getenv("NAVIGATOR_UF_API_KEY"),
                base_url=self.api_base
            )

            prompt = self._construct_prompt(word_list, feedback_history or [])

            # Call API
            resp = client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=300,
                timeout=30.0  # Add explicit timeout
            )
            
            # Check if response has choices and content
            if not resp.choices or len(resp.choices) == 0:
                raise ValueError("API returned empty choices array")
            
            raw = (resp.choices[0].message.content or "").strip()

            thinking, guess = self._parse_thinking_and_final(raw)
            
            # Store traces in the format expected by the evaluation code
            self.last_trace = shorten(thinking, 2000)
            self.last_raw = shorten(raw, 2000)

            # Validate guess; fall back if invalid
            guess = guess.upper()
            if guess not in word_list:
                print(f"[WARNING] Extracted guess '{guess}' not in candidates (size={len(word_list)})")
                print(f"[WARNING] THINKING: {thinking[:200]}")
                # Prefer a new word if we can (avoid repeats)
                pool = list(word_list)
                import random
                guess = random.choice(pool) if pool else "CRANE"
                print(f"[WARNING] Falling back to random guess: {guess}")

            return guess

        except Exception as e:
            # On error, record trace as the error message for debugging
            print(f"Error with {self.model_name}: {e}")
            print(f"Error type: {type(e).__name__}")
            error_msg = f"[ERROR] {type(e).__name__}: {e}"
            self.last_trace = error_msg
            self.last_raw = error_msg
            import random
            return random.choice(word_list)

# ----------------- Word List + Test Set -----------------

def load_word_list(filename='words'):
    """Load word list from file."""
    with open(filename, 'r') as f:
        return [word.strip().upper() for word in f.readlines() if len(word.strip()) == 5]


def create_standardized_test_set(word_list, num_words=100, seed=42):
    """Create a standardized test set."""
    random.seed(seed)
    np.random.seed(seed)
    test_words = [
        "CRANE", "SLATE", "CRATE", "SLANT", "TRACE", "LEAST", "LEARN", "RATES", "STARE", "TEARS",
        "AROSE", "STORE", "STONE", "ATONE", "ALONE", "PHONE", "SHONE", "THONE", "BONE", "CONE",
        "DONE", "GONE", "HONE", "LONE", "NONE", "PONE", "TONE", "ZONE", "ABOUT", "ABOVE",
        "ABUSE", "ACTOR", "ACUTE", "ADMIT", "ADOPT", "ADULT", "AFTER", "AGAIN", "AGENT", "AGREE",
        "AHEAD", "ALARM", "ALBUM", "ALERT", "ALIEN", "ALIGN", "ALIKE", "ALIVE", "ALLOW", "ALONE",
        "ALONG", "ALTER", "AMONG", "ANGER", "ANGLE", "ANGRY", "APART", "APPLE", "APPLY", "ARENA",
        "ARGUE", "ARISE", "ARRAY", "ASIDE", "ASSET", "AVOID", "AWAKE", "AWARD", "AWARE", "BADLY",
        "BAKER", "BASES", "BASIC", "BEACH", "BEGAN", "BEGIN", "BEING", "BELOW", "BENCH", "BILLY",
        "BIRTH", "BLACK", "BLAME", "BLANK", "BLIND", "BLOCK", "BLOOD", "BOARD", "BOOST", "BOOTH",
        "BOUND", "BRAIN", "BRAND", "BRASS", "BRAVE", "BREAD", "BREAK", "BREED", "BRIEF", "BRING"
    ]
    return test_words[:num_words]


# ----------------- Evaluation -----------------

def test_api_connection(model_name=None):
    """Test if the Navigator UF API is accessible."""
    try:
        import openai

        # Test API with actual authenticated call
        api_endpoint = os.getenv("NAVIGATOR_API_ENDPOINT", "https://api.navigator.uf.edu/v1")
        print(f"Testing API connection to {api_endpoint}...")

        client = openai.OpenAI(
            api_key=os.getenv("NAVIGATOR_UF_API_KEY"),
            base_url=api_endpoint
        )

        # Use the actual model if provided, otherwise use a test model
        test_model = model_name if model_name else "mistral-7b-instruct"
        print(f"Testing API call with model: {test_model}...")

        response = client.chat.completions.create(
            model=test_model,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5,
            timeout=30
        )

        if not response.choices or len(response.choices) == 0:
            return False, "API returned empty response"

        print(f"✓ API call successful with {test_model}")
        return True, "API connection successful"

    except Exception as e:
        error_type = type(e).__name__
        return False, f"API connection failed ({error_type}): {str(e)}"

def evaluate_single_model(model_name, prompt_type, word_list, test_words, num_games=100):
    """Evaluate a single model on the test words and log CoT traces."""
    print(f"Evaluating {model_name} with {prompt_type} prompting...")

    # Test API connection first - warn if it fails but continue
    api_ok, api_msg = test_api_connection(model_name)
    if not api_ok:
        print(f"\n⚠️  API CONNECTION WARNING: {api_msg}")
        print("Continuing anyway - will attempt to use API during evaluation...")
        print("(Set STRICT_API_CHECK=1 to abort on API test failure)\n")

        if os.getenv('STRICT_API_CHECK') == '1':
            print("\nTroubleshooting steps:")
            print("1. Verify NAVIGATOR_UF_API_KEY is set correctly")
            print("2. Check that NAVIGATOR_API_ENDPOINT is correct (or unset to use default)")
            print("3. Ensure you have network access to the API endpoint")
            print("4. Run diagnose_api_issues.py for detailed diagnostics")
            raise RuntimeError(f"API connection test failed: {api_msg}")
    else:
        print(f"✓ API connection test passed\n")

    # Set up debug mode for saving raw responses
    debug_mode = os.getenv('DEBUG_RESPONSES', '0') == '1'
    debug_dir = None
    if debug_mode:
        out_dir = os.getenv('OUT_DIR', '.')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        debug_dir = f"{out_dir}/debug_responses/{model_name.replace('-', '_')}_{prompt_type}_{timestamp}"
        os.makedirs(debug_dir, exist_ok=True)
        print(f"🔍 DEBUG MODE: Saving raw responses to {debug_dir}\n")

    # choose strategy (Navigator API)
    strategy = NavigatorUFCoTStrategy(model_name) if prompt_type == "chain-of-thought" else NavigatorUFStrategy(model_name)

    out_dir = os.getenv('OUT_DIR', '.')
    os.makedirs(out_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    individual_csv = f"{out_dir}/model_{model_name.replace('-', '_')}_{prompt_type}_{timestamp}.csv"

    headers = [
        'game_id', 'target_word', 'model_name', 'prompt_type', 'attempt_number',
        'guess', 'feedback', 'win', 'attempts_to_win', 'timestamp',
        'prompt', 'cot_trace', 'raw_response',
        # New metrics columns
        'is_valid_word', 'is_error', 'candidates_before', 'candidates_after',
        'candidate_reduction_rate', 'information_gain_bits',
        'violated_green_constraint', 'violated_yellow_constraint',
        'violated_gray_constraint', 'total_constraint_violations'
    ]
    with open(individual_csv, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()

    results = []
    wins = 0
    total_attempts = 0

    # fixed number of games equals number of test_words provided
    for game_id, target_word in enumerate(test_words):
        env = WordleEnv(word_list)
        agent = GuessingAgent(word_list, strategy)
        env.target_word = target_word
        env.attempts = 0
        env.done = False
        agent.reset()
        strategy.used.clear()

        # per-game working candidate list
        remaining = list(word_list)
        # Track feedback history for constraint violation checking
        game_feedback_history = []

        win = False
        attempts_to_win = 0
        for attempt in range(6):
            try:
                # Capture candidates BEFORE the guess
                candidates_before = len(remaining)

                guess = agent.select_guess()
                feedback, reward = env.guess(guess)
                agent.update(guess, feedback, reward)

                # shrink candidates for next attempt
                # Convert string feedback to integer feedback for filtering
                int_feedback = [2 if f == "G" else 1 if f == "Y" else 0 for f in feedback]
                remaining = filter_candidates_by_feedback(remaining, guess, int_feedback)
                candidates_after = len(remaining)

                # Calculate metrics
                is_valid = is_valid_guess(guess, word_list)
                is_error = False
                reduction_rate = calculate_candidate_reduction_rate(candidates_before, candidates_after)
                info_gain = calculate_information_gain(candidates_before, candidates_after)

                # Check constraint violations (using history from BEFORE this guess)
                violations = calculate_constraint_violations(guess, game_feedback_history, target_word)

                # Update history for next iteration
                game_feedback_history.append((guess, ''.join(feedback)))

                # collect traces saved by the strategy
                cot_trace = getattr(strategy, "last_trace", "")
                raw_resp  = getattr(strategy, "last_raw", "")

                # Add additional context to traces for better analysis
                context_info = f"Game {game_id+1}/{len(test_words)} | Target: {target_word} | Attempt {attempt+1}/6 | Candidates: {candidates_before}"
                if cot_trace and not cot_trace.startswith("ERROR"):
                    cot_trace = f"{context_info}\n\n{cot_trace}"
                if raw_resp and not raw_resp.startswith("ERROR"):
                    raw_resp = f"{context_info}\n\n{raw_resp}"

                # Save raw response to debug folder if debug mode is enabled
                if debug_mode and debug_dir and raw_resp:
                    debug_filename = f"{debug_dir}/game{game_id+1:03d}_attempt{attempt+1}_raw.txt"
                    with open(debug_filename, 'w') as f:
                        f.write(f"=== RAW RESPONSE DEBUG ===\n")
                        f.write(f"Game: {game_id+1}/{len(test_words)}\n")
                        f.write(f"Target: {target_word}\n")
                        f.write(f"Attempt: {attempt+1}/6\n")
                        f.write(f"Guess: {guess}\n")
                        f.write(f"Feedback: {''.join(feedback)}\n")
                        f.write(f"Candidates before: {candidates_before}\n")
                        f.write(f"Candidates after: {candidates_after}\n")
                        f.write(f"Prompt type: {prompt_type}\n")
                        f.write(f"\n=== PROMPT SENT ===\n")
                        f.write(getattr(strategy, 'last_prompt', '[Prompt not available]'))
                        f.write(f"\n\n=== RAW RESPONSE ===\n")
                        f.write(raw_resp)
                        f.write(f"\n\n=== EXTRACTED COT TRACE ===\n")
                        f.write(cot_trace if cot_trace else "(none)")
                        f.write(f"\n\n=== CONSTRAINT VIOLATIONS ===\n")
                        f.write(f"Green violations: {violations['violated_green']}\n")
                        f.write(f"Yellow violations: {violations['violated_yellow']}\n")
                        f.write(f"Gray violations: {violations['violated_gray']}\n")
                        f.write(f"Total violations: {violations['violation_count']}\n")

                # Get the prompt from the strategy if available
                prompt_sent = getattr(strategy, 'last_prompt', '')

                row_data = {
                    'game_id': game_id,
                    'target_word': target_word,
                    'model_name': model_name,
                    'prompt_type': prompt_type,
                    'attempt_number': attempt + 1,
                    'guess': guess,
                    'feedback': ''.join(feedback),  # feedback is already in G/Y/- format
                    'win': (guess == target_word),
                    'attempts_to_win': attempt + 1,
                    'timestamp': datetime.now().isoformat(),
                    'prompt': prompt_sent,
                    'cot_trace': cot_trace,
                    'raw_response': raw_resp,
                    # New metrics
                    'is_valid_word': is_valid,
                    'is_error': is_error,
                    'candidates_before': candidates_before,
                    'candidates_after': candidates_after,
                    'candidate_reduction_rate': f"{reduction_rate:.4f}",
                    'information_gain_bits': f"{info_gain:.4f}",
                    'violated_green_constraint': violations['violated_green'],
                    'violated_yellow_constraint': violations['violated_yellow'],
                    'violated_gray_constraint': violations['violated_gray'],
                    'total_constraint_violations': violations['violation_count']
                }
                with open(individual_csv, 'a', newline='') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=headers)
                    writer.writerow(row_data)

                if guess == target_word:
                    win = True
                    attempts_to_win = attempt + 1
                    wins += 1
                    total_attempts += attempts_to_win
                    break

            except Exception as e:
                # log an error row so diagnostics are preserved
                row_data = {
                    'game_id': game_id,
                    'target_word': target_word,
                    'model_name': model_name,
                    'prompt_type': prompt_type,
                    'attempt_number': attempt + 1,
                    'guess': 'ERROR',
                    'feedback': 'ERROR',
                    'win': False,
                    'attempts_to_win': attempt + 1,
                    'timestamp': datetime.now().isoformat(),
                    'cot_trace': f"ERROR: {e}",
                    'raw_response': f"ERROR: {e}",
                    # Error metrics
                    'is_valid_word': False,
                    'is_error': True,
                    'candidates_before': len(remaining) if 'remaining' in locals() else 0,
                    'candidates_after': len(remaining) if 'remaining' in locals() else 0,
                    'candidate_reduction_rate': 0.0,
                    'information_gain_bits': 0.0,
                    'violated_green_constraint': False,
                    'violated_yellow_constraint': False,
                    'violated_gray_constraint': False,
                    'total_constraint_violations': 0
                }
                with open(individual_csv, 'a', newline='') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=headers)
                    writer.writerow(row_data)
                # continue to next attempt (don't kill whole game on one hiccup)
                continue

        if not win:
            attempts_to_win = 7

        results.append({
            'game_id': game_id,
            'target_word': target_word,
            'win': win,
            'attempts_to_win': attempts_to_win
        })

    # Calculate aggregate metrics from results
    total_valid_guesses = 0
    total_errors = 0
    total_violations = 0
    total_info_gain = 0.0
    total_reduction_rate = 0.0
    guess_count = 0

    # Read the CSV to calculate aggregate metrics
    with open(individual_csv, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['is_error'] == 'True':
                total_errors += 1
            elif row['is_valid_word'] == 'True':
                total_valid_guesses += 1

            total_violations += int(row['total_constraint_violations'])
            total_info_gain += float(row['information_gain_bits'])
            total_reduction_rate += float(row['candidate_reduction_rate'])
            guess_count += 1

    # summary
    win_rate = wins / len(test_words)
    avg_attempts = total_attempts / wins if wins > 0 else 7
    completion_rate = (len(test_words) - (total_errors / 6 if total_errors > 0 else 0)) / len(test_words)  # rough estimate
    valid_guess_rate = total_valid_guesses / guess_count if guess_count > 0 else 0
    avg_info_gain = total_info_gain / guess_count if guess_count > 0 else 0
    avg_reduction_rate = total_reduction_rate / guess_count if guess_count > 0 else 0
    avg_violations_per_guess = total_violations / guess_count if guess_count > 0 else 0

    summary = {
        'model_name': model_name,
        'prompt_type': prompt_type,
        'total_games': len(test_words),
        'wins': wins,
        'win_rate': win_rate,
        'avg_attempts_when_won': avg_attempts,
        'csv_file': individual_csv,
        # New aggregate metrics
        'completion_rate': completion_rate,
        'valid_guess_rate': valid_guess_rate,
        'total_errors': total_errors,
        'total_constraint_violations': total_violations,
        'avg_constraint_violations_per_guess': avg_violations_per_guess,
        'avg_information_gain_bits': avg_info_gain,
        'avg_candidate_reduction_rate': avg_reduction_rate
    }
    summary_filename = f"{out_dir}/summary_{model_name.replace('-', '_')}_{prompt_type}_{timestamp}.json"
    with open(summary_filename, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"Win rate: {win_rate:.2%} | Avg attempts (wins): {avg_attempts:.2f}")
    print(f"Valid guess rate: {valid_guess_rate:.2%} | Avg info gain: {avg_info_gain:.3f} bits")
    print(f"Avg constraint violations: {avg_violations_per_guess:.3f} | Errors: {total_errors}")
    print(f"Results: {individual_csv}")
    print(f"Summary: {summary_filename}")

    return summary


# ----------------- Main -----------------

def main():
    # Validate environment variables
    model_name = os.getenv('MODEL')
    prompt_type = os.getenv('PROMPT_TYPE')

    print("=" * 60)
    print("Wordle Model Evaluation")
    print("=" * 60)

    # Check required environment variables
    missing_vars = []
    if not model_name:
        missing_vars.append("MODEL")
    if not prompt_type:
        missing_vars.append("PROMPT_TYPE")
    if not os.getenv("NAVIGATOR_UF_API_KEY"):
        missing_vars.append("NAVIGATOR_UF_API_KEY")

    if missing_vars:
        print(f"\n❌ ERROR: Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these variables before running:")
        print("   export MODEL='model-name'")
        print("   export PROMPT_TYPE='zero-shot' or 'chain-of-thought'")
        print("   export NAVIGATOR_UF_API_KEY='your-api-key'")
        print("   export NAVIGATOR_API_ENDPOINT='https://api.navigator.uf.edu/v1'  # (optional)")
        return 1

    # Display configuration
    print(f"\nConfiguration:")
    print(f"  Model: {model_name}")
    print(f"  Prompt Type: {prompt_type}")
    print(f"  API Endpoint: {os.getenv('NAVIGATOR_API_ENDPOINT', 'https://api.navigator.uf.edu/v1')}")
    print(f"  API Key: {os.getenv('NAVIGATOR_UF_API_KEY')[:6]}...{os.getenv('NAVIGATOR_UF_API_KEY')[-4:]}")
    print()

    # word list & test set
    try:
        word_list = load_word_list()
        print(f"✓ Loaded {len(word_list)} words from word list")
    except Exception as e:
        print(f"❌ ERROR: Failed to load word list: {e}")
        return 1

    # Load canonical test set (ensures all evaluations use same words)
    try:
        canonical_words = get_test_words_only()
        print(f"✓ Loaded canonical test set ({len(canonical_words)} words)")
    except FileNotFoundError as e:
        print(f"❌ ERROR: {e}")
        return 1

    # Allow testing with subset of canonical set
    num_test_games = int(os.getenv('NUM_TEST_GAMES', str(len(canonical_words))))
    test_words = canonical_words[:num_test_games]
    print(f"✓ Using {len(test_words)} words from canonical set")
    print()

    start = time.time()
    try:
        evaluate_single_model(model_name, prompt_type, word_list, test_words)
        elapsed = time.time() - start
        print(f"\n✅ Evaluation completed successfully in {elapsed:.2f} seconds")
        return 0
    except Exception as e:
        elapsed = time.time() - start
        print(f"\n❌ Evaluation failed after {elapsed:.2f} seconds")
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
