#!/usr/bin/env python3
"""
CoT Reasoning Trace Experiment

Captures full chain-of-thought reasoning traces from LLMs when presented
with algorithmic signals. Tests whether models explicitly reference,
reason over, or ignore the Algorithm Analysis section.

Runs a small subset of models (one per behavioral regime) with CoT
prompting in the voi_informed condition, saving the full THINKING text
for qualitative analysis.

Models:
  - granite-3.3-8b-instruct (Signal Integration regime)
  - codestral-22b (Surface Imitation regime)
  - llama-3.3-70b-instruct (Signal Rejection regime)

Configured via env vars:
  DOMAIN         - "wordle" or "mastermind" (default: wordle)
  MODEL          - Override model (default: runs all 3)
  NUM_GAMES      - Games per run (default: 30)
  ALGORITHM      - "css" or "voi" (default: css)
  VARIANT        - Mastermind variant (default: classic)
  OUTPUT_DIR     - Output directory
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

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'engines'))
sys.path.insert(0, str(PROJECT_ROOT / 'algorithms'))
# Wordle scripts path must come before mastermind to resolve test_set_loader correctly
sys.path.insert(0, str(PROJECT_ROOT / 'scripts'))
# Mastermind path added at end so it doesn't shadow Wordle's test_set_loader
sys.path.append(str(PROJECT_ROOT / 'scripts' / 'mastermind'))

# Models that require the GPT API key
GPT_API_MODELS = {
    "gpt-5-mini", "gpt-4.1", "gpt-4.1-mini", "gpt-4o", "gpt-4o-mini",
    "claude-3-opus", "claude-3.7-sonnet", "claude-4-sonnet", "claude-4.5-sonnet",
    "gemini-2.5-flash", "gemini-2.0-flash"
}

# Models that use NAVIGATOR_UF_API_KEY3
KEY3_MODELS = {"gpt-5", "gemini-2.5-pro"}

# One model per behavioral regime
REGIME_MODELS = {
    'integration': 'granite-3.3-8b-instruct',
    'imitation': 'codestral-22b',
    'rejection': 'llama-3.3-70b-instruct',
}


def _get_api_key_for_model(model_name: str) -> str:
    if model_name in KEY3_MODELS:
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


# ============================================================
# Wordle helpers
# ============================================================

def setup_wordle():
    from wordle_env import WordleEnv
    from css_strategy import CSSStrategy
    from voi_strategy import VOIStrategy
    from test_set_loader import get_test_words_only

    with open(PROJECT_ROOT / 'wordlist' / 'wordlist.txt', 'r') as f:
        word_list = [line.strip().upper() for line in f if line.strip()]

    test_words = get_test_words_only()
    return word_list, test_words, WordleEnv, CSSStrategy, VOIStrategy


def build_wordle_cot_prompt(candidates, history, algo_scores, entropy):
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
            fb_str = ''.join(feedback) if isinstance(feedback, list) else feedback
            prompt += f"- Guess: {guess}  Feedback: {fb_str}\n"

    if len(candidates) <= 50:
        candidates_str = ", ".join(candidates)
    else:
        sample = candidates[:30] + ["..."] + candidates[-20:]
        candidates_str = ", ".join(sample)

    prompt += (
        f"\nAllowed words remaining: {len(candidates)}\n"
        f"Candidate words: {candidates_str}\n"
    )

    # Algorithm Analysis section
    if algo_scores is not None and entropy is not None:
        prompt += "\nAlgorithm Analysis:\n"
        prompt += f"- Current entropy: {entropy:.1f} bits ({len(candidates)} candidates remaining)\n"
        prompt += "- Top candidates ranked by information value:\n"
        for i, (word, score) in enumerate(algo_scores, 1):
            prompt += f"    {i}. {word} (score: {score:.2f})\n"
        if algo_scores:
            prompt += f"- Algorithm's recommended guess: {algo_scores[0][0]}\n"
        prompt += (
            "\nUse this analysis as one input to your reasoning, but make your own decision. "
            "Do NOT simply copy the algorithm's top pick — consider the candidates critically "
            "and choose the word you believe will maximize information gain based on your own analysis.\n"
        )

    prompt += (
        "\nConstraints:\n"
        "- Do NOT repeat previous guesses.\n"
        "- The FINAL line must be exactly ONE valid 5-letter word from the allowed list.\n"
        "- Keep THINKING concise (1-5 short lines)."
    )
    return prompt


# ============================================================
# Mastermind helpers
# ============================================================

def setup_mastermind(variant='classic'):
    from mastermind_env import MastermindEnv
    from mastermind_css_strategy import MastermindCSSStrategy
    from mastermind_voi_strategy import MastermindVOIStrategy
    from test_set_loader import get_test_codes

    env = MastermindEnv(variant=variant)
    info = env.get_info()
    test_codes = get_test_codes(variant)
    return env, info, test_codes, MastermindCSSStrategy, MastermindVOIStrategy


def build_mastermind_cot_prompt(candidates, history, algo_scores, entropy, num_pegs, colors):
    color_names = {
        'R': 'Red', 'G': 'Green', 'B': 'Blue', 'Y': 'Yellow',
        'O': 'Orange', 'W': 'White', 'P': 'Purple', 'K': 'blacK'
    }
    colors_desc = ", ".join(f"{c}={color_names[c]}" for c in colors)

    prompt = (
        f"You are an expert Mastermind player. The secret code is {num_pegs} colors.\n"
        f"Colors: {colors_desc}\n\n"
        "Use brief, structured reasoning.\n"
        "Return output in this exact format:\n"
        "THINKING: <your concise step-by-step reasoning>\n"
        f"FINAL: <ONE {num_pegs}-character code only>\n\n"
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

    # Algorithm Analysis section
    if algo_scores is not None and entropy is not None:
        prompt += "\nAlgorithm Analysis:\n"
        prompt += f"- Current entropy: {entropy:.1f} bits ({len(candidates)} codes remaining)\n"
        prompt += "- Top candidates ranked by information value:\n"
        for i, (code, score) in enumerate(algo_scores, 1):
            prompt += f"    {i}. {code} (score: {score:.2f})\n"
        if algo_scores:
            prompt += f"- Algorithm's recommended guess: {algo_scores[0][0]}\n"
        prompt += (
            "\nUse this analysis as one input to your reasoning, but make your own decision. "
            "Do NOT simply copy the algorithm's top pick — consider the candidates critically "
            "and choose the code you believe will maximize information gain based on your own analysis.\n"
        )

    prompt += (
        "\nConstraints:\n"
        "- Do NOT repeat previous guesses.\n"
        f"- ONLY use these {len(colors)} colors: {colors}\n"
        f"- The FINAL line must be exactly ONE valid {num_pegs}-character code.\n"
        "- Keep THINKING concise (1-5 short lines)."
    )
    return prompt


# ============================================================
# LLM call with trace capture
# ============================================================

REASONING_MODELS = {"gpt-oss-120b", "gpt-5"}


def call_llm_with_trace(model_name: str, prompt: str, api_base: str) -> Tuple[Optional[str], Optional[str]]:
    """Call LLM and return (full_response_text, extracted_guess).

    Returns the complete reasoning trace for qualitative analysis.
    """
    import openai

    client = openai.OpenAI(
        api_key=_get_api_key_for_model(model_name),
        base_url=api_base
    )

    is_reasoning = model_name in REASONING_MODELS
    max_tok = 16384 if is_reasoning else 400

    call_kwargs = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tok,
    }
    if not is_reasoning:
        call_kwargs["temperature"] = 0.7

    for attempt in range(5):
        try:
            response = client.chat.completions.create(**call_kwargs)
            content = response.choices[0].message.content
            if content is None:
                content = getattr(response.choices[0].message, 'reasoning_content', None) or ""
            text = content.strip()
            return text, text
        except Exception as e:
            print(f"  LLM attempt {attempt+1}/5 failed: {e}")
            if attempt < 4:
                time.sleep(2 ** attempt + random.uniform(0, 1))

    return None, None


def extract_guess_from_trace(text: str, history_guesses: set, num_chars: int = 5) -> Optional[str]:
    """Extract guess from CoT response."""
    if not text:
        return None

    # Try FINAL: pattern first
    pattern = rf'FINAL\s*:\s*([A-Za-z]{{{num_chars}}})\b'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        guess = match.group(1).upper()
        if guess not in history_guesses:
            return guess

    # Fallback: any N-letter word
    pattern = rf'\b[A-Za-z]{{{num_chars}}}\b'
    words = re.findall(pattern, text.upper())
    for word in words:
        if word not in history_guesses:
            return word

    return None


# ============================================================
# Trace analysis helpers
# ============================================================

def analyze_trace(trace: str, algo_top1: str, algo_scores: List[Tuple[str, float]]) -> dict:
    """Analyze a reasoning trace for signal references."""
    if not trace:
        return {'references_signal': False, 'references_scores': False,
                'references_entropy': False, 'references_top1': False,
                'explicitly_rejects': False, 'mentions_algo_candidates': 0,
                'trace_length': 0}

    trace_lower = trace.lower()
    algo_words = [w.lower() for w, _ in algo_scores] if algo_scores else []

    return {
        'references_signal': any(kw in trace_lower for kw in
            ['algorithm', 'analysis', 'information value', 'ranked', 'recommended']),
        'references_scores': any(kw in trace_lower for kw in
            ['score', 'value', 'information gain', 'entropy']),
        'references_entropy': 'entropy' in trace_lower or 'bits' in trace_lower,
        'references_top1': algo_top1.lower() in trace_lower if algo_top1 else False,
        'explicitly_rejects': any(kw in trace_lower for kw in
            ['disagree', 'instead', 'rather', 'better choice', 'i think', 'however',
             'but i', 'my own', 'i prefer', 'i\'ll go with', 'i choose']),
        'mentions_algo_candidates': sum(1 for w in algo_words if w in trace_lower),
        'trace_length': len(trace),
    }


# ============================================================
# Main experiment
# ============================================================

def run_wordle_cot(model_name: str, algorithm: str, num_games: int, output_dir: Path):
    """Run Wordle CoT trace experiment for one model."""
    from wordle_env import WordleEnv
    from css_strategy import CSSStrategy
    from voi_strategy import VOIStrategy
    from test_set_loader import get_test_words_only

    with open(PROJECT_ROOT / 'wordlist' / 'wordlist.txt', 'r') as f:
        word_list = [line.strip().upper() for line in f if line.strip()]

    test_words = get_test_words_only()[:num_games]
    api_base = os.getenv("NAVIGATOR_API_ENDPOINT", "https://api.ai.it.ufl.edu/v1")

    scoring_algo = CSSStrategy() if algorithm == 'css' else VOIStrategy()
    belief_algo = CSSStrategy()

    print(f"\n{'='*80}")
    print(f"WORDLE CoT TRACE: {model_name} / {algorithm}")
    print(f"{'='*80}")

    traces = []

    for game_num, target in enumerate(test_words, 1):
        print(f"\nGame {game_num}/{num_games}: Target = {target}")

        env = WordleEnv([target])
        env.reset()
        candidates = list(word_list)
        history = []
        history_guesses = set()

        if isinstance(scoring_algo, VOIStrategy):
            scoring_algo.beliefs = {}
            scoring_algo.feedback_cache = {}

        # Only capture trace for round 1 (LLM turn)
        # Compute algo scores
        if isinstance(scoring_algo, VOIStrategy) and not scoring_algo.beliefs:
            scoring_algo.initialize_beliefs(candidates)
        algo_scores = scoring_algo.score_candidates(candidates, history, 5)
        entropy = math.log2(len(candidates)) if len(candidates) > 1 else 0.0
        algo_top1 = algo_scores[0][0] if algo_scores else ''

        # Build CoT prompt with signals
        prompt = build_wordle_cot_prompt(candidates, history, algo_scores, entropy)

        # Call LLM
        full_text, _ = call_llm_with_trace(model_name, prompt, api_base)
        guess = extract_guess_from_trace(full_text, history_guesses, 5) if full_text else None

        if not guess:
            print(f"  Round 1: No valid guess extracted")
            traces.append({
                'game': game_num, 'target': target, 'round': 1,
                'guess': '', 'algo_top1': algo_top1, 'followed': '',
                'full_trace': full_text or '', 'prompt': prompt,
                'trace_analysis': analyze_trace(full_text, algo_top1, algo_scores),
                'won': False, 'total_attempts': 0,
            })
            continue

        followed = (guess == algo_top1)
        trace_analysis = analyze_trace(full_text, algo_top1, algo_scores)

        print(f"  Round 1 [LLM_COT]: {guess} (algo_top1={algo_top1}, followed={followed})")
        print(f"    Trace refs: signal={trace_analysis['references_signal']}, "
              f"scores={trace_analysis['references_scores']}, "
              f"rejects={trace_analysis['explicitly_rejects']}")

        # Play out remaining rounds with algorithm
        feedback, reward = env.guess(guess)
        str_feedback = list(feedback)  # already strings from WordleEnv
        history.append((guess, str_feedback))
        history_guesses.add(guess)
        candidates = belief_algo.update_belief(candidates, guess, str_feedback)

        won = all(f == 'G' for f in str_feedback)
        total_attempts = 1

        if not won:
            for attempt in range(2, 7):
                if env.done:
                    total_attempts = attempt - 1
                    break
                algo_guess = belief_algo.select_guess(candidates, history)
                if not algo_guess:
                    total_attempts = attempt
                    break
                fb, rw = env.guess(algo_guess)
                str_fb = list(fb)  # already strings from WordleEnv
                history.append((algo_guess, str_fb))
                history_guesses.add(algo_guess)
                candidates = belief_algo.update_belief(candidates, algo_guess, str_fb)
                total_attempts = attempt
                if all(f == 'G' for f in str_fb):
                    won = True
                    break

        traces.append({
            'game': game_num, 'target': target, 'round': 1,
            'guess': guess, 'algo_top1': algo_top1, 'followed': followed,
            'full_trace': full_text, 'prompt': prompt,
            'trace_analysis': trace_analysis,
            'won': won, 'total_attempts': total_attempts,
        })

        if won:
            print(f"  Won in {total_attempts} attempts")

    return traces


def run_mastermind_cot(model_name: str, algorithm: str, num_games: int,
                       variant: str, output_dir: Path):
    """Run Mastermind CoT trace experiment for one model."""
    from mastermind_env import MastermindEnv
    from mastermind_css_strategy import MastermindCSSStrategy
    from mastermind_voi_strategy import MastermindVOIStrategy
    # Import Mastermind test_set_loader explicitly
    import importlib.util
    mm_loader_path = PROJECT_ROOT / 'scripts' / 'mastermind' / 'test_set_loader.py'
    spec = importlib.util.spec_from_file_location("mm_test_set_loader", mm_loader_path)
    mm_loader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mm_loader)
    get_test_codes = mm_loader.get_test_codes

    env = MastermindEnv(variant=variant)
    info = env.get_info()
    test_codes = get_test_codes(variant, num_games)
    api_base = os.getenv("NAVIGATOR_API_ENDPOINT", "https://api.ai.it.ufl.edu/v1")

    scoring_algo = MastermindCSSStrategy(num_pegs=env.num_pegs) if algorithm == 'css' \
        else MastermindVOIStrategy(num_pegs=env.num_pegs)
    belief_algo = MastermindCSSStrategy(num_pegs=env.num_pegs)
    all_candidates = env.get_all_candidates()

    print(f"\n{'='*80}")
    print(f"MASTERMIND CoT TRACE: {model_name} / {algorithm}")
    print(f"{'='*80}")

    traces = []

    for game_num, target in enumerate(test_codes, 1):
        print(f"\nGame {game_num}/{num_games}: Target = {target}")

        env.reset(target=target)
        candidates = list(all_candidates)
        history = []
        history_guesses = set()

        if isinstance(scoring_algo, MastermindVOIStrategy):
            if hasattr(scoring_algo, 'beliefs'):
                scoring_algo.beliefs = {}

        # Round 1: LLM with CoT
        if isinstance(scoring_algo, MastermindVOIStrategy):
            if not scoring_algo.beliefs:
                scoring_algo.initialize_beliefs(candidates)
        algo_scores = scoring_algo.score_candidates(candidates, history, 5)
        entropy = math.log2(len(candidates)) if len(candidates) > 1 else 0.0
        algo_top1 = algo_scores[0][0] if algo_scores else ''

        prompt = build_mastermind_cot_prompt(
            candidates, history, algo_scores, entropy,
            env.num_pegs, info['colors'])

        full_text, _ = call_llm_with_trace(model_name, prompt, api_base)
        guess = extract_guess_from_trace(full_text, history_guesses, env.num_pegs) if full_text else None

        if not guess:
            print(f"  Round 1: No valid guess extracted")
            traces.append({
                'game': game_num, 'target': target, 'round': 1,
                'guess': '', 'algo_top1': algo_top1, 'followed': '',
                'full_trace': full_text or '', 'prompt': prompt,
                'trace_analysis': analyze_trace(full_text, algo_top1, algo_scores),
                'won': False, 'total_attempts': 0,
            })
            continue

        followed = (guess == algo_top1)
        trace_analysis = analyze_trace(full_text, algo_top1, algo_scores)

        print(f"  Round 1 [LLM_COT]: {guess} (algo_top1={algo_top1}, followed={followed})")
        print(f"    Trace refs: signal={trace_analysis['references_signal']}, "
              f"scores={trace_analysis['references_scores']}, "
              f"rejects={trace_analysis['explicitly_rejects']}")

        # Play out remaining rounds with algorithm
        try:
            feedback, reward = env.guess(guess)
            history.append((guess, feedback))
            history_guesses.add(guess)
            candidates = belief_algo.update_belief(candidates, guess, feedback)
            won = (guess == target)
            total_attempts = 1
        except ValueError:
            won = False
            total_attempts = 1

        if not won:
            for attempt in range(2, env.max_attempts + 1):
                algo_guess = belief_algo.select_guess(candidates, history)
                try:
                    fb, rw = env.guess(algo_guess)
                    history.append((algo_guess, fb))
                    history_guesses.add(algo_guess)
                    candidates = belief_algo.update_belief(candidates, algo_guess, fb)
                    total_attempts = attempt
                    if algo_guess == target:
                        won = True
                        break
                except ValueError:
                    total_attempts = attempt
                    break

        traces.append({
            'game': game_num, 'target': target, 'round': 1,
            'guess': guess, 'algo_top1': algo_top1, 'followed': followed,
            'full_trace': full_text, 'prompt': prompt,
            'trace_analysis': trace_analysis,
            'won': won, 'total_attempts': total_attempts,
        })

        if won:
            print(f"  Won in {total_attempts} attempts")

    return traces


def save_traces(traces: List[dict], model_name: str, domain: str,
                algorithm: str, output_dir: Path):
    """Save traces to JSON (full detail) and CSV (summary)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Full traces as JSON (for qualitative analysis)
    json_file = output_dir / f"cot_traces_{domain}_{algorithm}_{model_name}_{timestamp}.json"
    with open(json_file, 'w') as f:
        json.dump({
            'model': model_name,
            'domain': domain,
            'algorithm': algorithm,
            'num_games': len(traces),
            'timestamp': timestamp,
            'traces': [{
                'game': t['game'],
                'target': t['target'],
                'guess': t['guess'],
                'algo_top1': t['algo_top1'],
                'followed': t['followed'],
                'won': t['won'],
                'total_attempts': t['total_attempts'],
                'full_trace': t['full_trace'],
                'trace_analysis': t['trace_analysis'],
            } for t in traces]
        }, f, indent=2)

    # Summary CSV
    csv_file = output_dir / f"cot_summary_{domain}_{algorithm}_{model_name}_{timestamp}.csv"
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'game', 'target', 'guess', 'algo_top1', 'followed', 'won',
            'attempts', 'refs_signal', 'refs_scores', 'refs_entropy',
            'refs_top1', 'explicitly_rejects', 'mentions_algo_candidates',
            'trace_length'
        ])
        for t in traces:
            ta = t['trace_analysis']
            writer.writerow([
                t['game'], t['target'], t['guess'], t['algo_top1'],
                t['followed'], t['won'], t['total_attempts'],
                ta['references_signal'], ta['references_scores'],
                ta['references_entropy'], ta['references_top1'],
                ta['explicitly_rejects'], ta['mentions_algo_candidates'],
                ta['trace_length']
            ])

    # Print summary
    n = len(traces)
    valid = [t for t in traces if t['guess']]
    wins = sum(1 for t in traces if t['won'])
    followed = sum(1 for t in valid if t['followed'] is True)
    refs_signal = sum(1 for t in valid if t['trace_analysis']['references_signal'])
    refs_scores = sum(1 for t in valid if t['trace_analysis']['references_scores'])
    refs_top1 = sum(1 for t in valid if t['trace_analysis']['references_top1'])
    rejects = sum(1 for t in valid if t['trace_analysis']['explicitly_rejects'])
    nv = len(valid)

    print(f"\n{'='*60}")
    print(f"TRACE SUMMARY: {model_name} / {domain} / {algorithm}")
    print(f"{'='*60}")
    print(f"  Games: {n}, Valid guesses: {nv}, Wins: {wins}")
    print(f"  Follow rate: {followed}/{nv} ({followed/nv*100:.0f}%)" if nv else "  No valid guesses")
    print(f"  References signal:    {refs_signal}/{nv} ({refs_signal/nv*100:.0f}%)" if nv else "")
    print(f"  References scores:    {refs_scores}/{nv} ({refs_scores/nv*100:.0f}%)" if nv else "")
    print(f"  References algo top1: {refs_top1}/{nv} ({refs_top1/nv*100:.0f}%)" if nv else "")
    print(f"  Explicitly rejects:   {rejects}/{nv} ({rejects/nv*100:.0f}%)" if nv else "")
    print(f"\nSaved to:")
    print(f"  {json_file}")
    print(f"  {csv_file}")

    return json_file, csv_file


def main():
    domain = os.getenv("DOMAIN", "wordle")
    algorithm = os.getenv("ALGORITHM", "css")
    num_games = int(os.getenv("NUM_GAMES", "30"))
    variant = os.getenv("VARIANT", "classic")
    single_model = os.getenv("MODEL", "")

    output_dir_env = os.getenv("OUTPUT_DIR")
    if output_dir_env:
        output_dir = Path(output_dir_env)
    else:
        output_dir = PROJECT_ROOT / 'voi_integration' / 'results' / 'cot_traces'

    if single_model:
        models = [single_model]
    else:
        models = list(REGIME_MODELS.values())

    print("=" * 80)
    print("CoT REASONING TRACE EXPERIMENT")
    print("=" * 80)
    print(f"Domain: {domain}")
    print(f"Algorithm: {algorithm}")
    print(f"Models: {models}")
    print(f"Games per model: {num_games}")
    print(f"Output: {output_dir}")
    print("=" * 80)

    for model_name in models:
        try:
            _get_api_key_for_model(model_name)
        except RuntimeError as e:
            print(f"Skipping {model_name}: {e}")
            continue

        if domain == "wordle":
            traces = run_wordle_cot(model_name, algorithm, num_games, output_dir)
        elif domain == "mastermind":
            traces = run_mastermind_cot(model_name, algorithm, num_games, variant, output_dir)
        else:
            print(f"Unknown domain: {domain}")
            sys.exit(1)

        save_traces(traces, model_name, domain, algorithm, output_dir)

        # Pause between models to avoid rate limits
        print("\nPausing 30s before next model...")
        time.sleep(30)

    print(f"\n{'='*80}")
    print("ALL CoT TRACE EXPERIMENTS COMPLETE")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
