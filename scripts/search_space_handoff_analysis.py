#!/usr/bin/env python3
"""
Search Space Handoff Analysis

Measures the performance gap as a function of remaining search space at handoff.

Key questions:
  1. When the LLM inherits a pruned search space, how does the remaining size
     correlate with LLM performance (win rate, attempts, constraint violations)?
  2. Does this explain why LLM-first outperforms algo-first?
  3. Is the pattern consistent across Wordle and Mastermind?

Approach:
  - For algo-first configs (C_to_L, V_to_L, cssk_to_L, voik_to_L):
    identify the handoff turn and remaining candidates at that point.
  - For LLM-first configs (L_to_C, L_to_V, Lk_to_css, Lk_to_voi):
    identify when algo takes over and remaining candidates.
  - Bucket games by search space at handoff and compute per-bucket metrics.

Data sources:
  - Mastermind: candidates_N column in raw CSVs
  - Wordle: reconstruct candidates from game engine (feedback + word list)

Usage:
  python scripts/search_space_handoff_analysis.py
"""

import csv
import json
import sys
import math
import os
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Tuple, Optional

import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent

# ============================================================
# Mastermind Analysis (has candidates_N directly)
# ============================================================

def load_mastermind_hybrid_data(results_dir: Path) -> List[dict]:
    """Load all Mastermind hybrid CSV data with candidates tracking."""
    all_games = []

    for group_dir in sorted(results_dir.glob("group_*")):
        for config_dir in sorted(group_dir.iterdir()):
            if not config_dir.is_dir():
                continue
            config_name = config_dir.name
            raw_dir = config_dir / "raw_data"
            if not raw_dir.exists():
                continue

            for csv_file in sorted(raw_dir.glob("*.csv")):
                # Extract model name from filename
                parts = csv_file.stem.split("_")
                # Find the model name (after config prefix, before timestamp)
                # Format: CONFIG_MODEL_TIMESTAMP
                model_name = "_".join(parts[len(config_name.split("_")):-2])
                if not model_name:
                    model_name = "unknown"

                # Skip nemotron (known broken)
                if "nemotron" in model_name:
                    continue

                with open(csv_file, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        game = {
                            'config': config_name,
                            'model': model_name,
                            'group': group_dir.name,
                            'domain': 'mastermind',
                            'won': row.get('won', '').lower() == 'true',
                            'attempts': int(row.get('attempts', 0)),
                            'strategies': [],
                            'candidates': [],
                            'guesses': [],
                            'feedbacks': [],
                        }

                        for i in range(1, 11):
                            strat = row.get(f'strategy_{i}', '').strip()
                            cand = row.get(f'candidates_{i}', '').strip()
                            guess = row.get(f'guess_{i}', '').strip()
                            fb = row.get(f'feedback_{i}', '').strip()

                            if strat:
                                game['strategies'].append(strat)
                                game['candidates'].append(int(cand) if cand else None)
                                game['guesses'].append(guess)
                                game['feedbacks'].append(fb)

                        all_games.append(game)

    return all_games


# ============================================================
# Wordle Analysis (reconstruct candidates from feedback)
# ============================================================

def load_wordle_word_list() -> List[str]:
    """Load the Wordle word list."""
    wl_path = PROJECT_ROOT / 'wordlist' / 'wordlist.txt'
    with open(wl_path, 'r') as f:
        return [line.strip().upper() for line in f if line.strip()]


def compute_wordle_feedback(guess: str, target: str) -> str:
    """Compute Wordle feedback string (G/Y/-)."""
    feedback = ['-'] * 5
    target_chars = list(target)

    # First pass: greens
    for i in range(5):
        if guess[i] == target[i]:
            feedback[i] = 'G'
            target_chars[i] = None

    # Second pass: yellows
    for i in range(5):
        if feedback[i] == '-' and guess[i] in target_chars:
            feedback[i] = 'Y'
            target_chars[target_chars.index(guess[i])] = None

    return ''.join(feedback)


def filter_wordle_candidates(candidates: List[str], guess: str, feedback: str) -> List[str]:
    """Filter candidates based on guess and feedback."""
    result = []
    for word in candidates:
        if compute_wordle_feedback(guess, word) == feedback:
            result.append(word)
    return result


def load_wordle_hybrid_data(results_dir: Path, word_list: List[str]) -> List[dict]:
    """Load all Wordle hybrid CSV data, reconstructing candidates."""
    all_games = []

    for group_dir in sorted(results_dir.glob("group_*")):
        for config_dir in sorted(group_dir.iterdir()):
            if not config_dir.is_dir():
                continue
            config_name = config_dir.name
            raw_dir = config_dir / "raw_data"
            if not raw_dir.exists():
                continue

            for csv_file in sorted(raw_dir.glob("*.csv")):
                parts = csv_file.stem.split("_")
                model_name = "_".join(parts[len(config_name.split("_")):-2])
                if not model_name:
                    model_name = "unknown"

                if "nemotron" in model_name:
                    continue

                with open(csv_file, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        game = {
                            'config': config_name,
                            'model': model_name,
                            'group': group_dir.name,
                            'domain': 'wordle',
                            'won': row.get('won', '').lower() == 'true',
                            'attempts': int(row.get('attempts', 0)),
                            'target': row.get('target_word', '').upper(),
                            'strategies': [],
                            'candidates': [],
                            'guesses': [],
                            'feedbacks': [],
                        }

                        # Reconstruct candidates turn by turn
                        current_candidates = list(word_list)

                        for i in range(1, 7):
                            strat = row.get(f'strategy_{i}', '').strip()
                            guess = row.get(f'guess_{i}', '').strip().upper()
                            fb = row.get(f'feedback_{i}', '').strip()

                            if not strat or not guess:
                                break

                            game['strategies'].append(strat)
                            game['guesses'].append(guess)
                            game['feedbacks'].append(fb)

                            # Candidates BEFORE this guess
                            game['candidates'].append(len(current_candidates))

                            # Filter candidates based on feedback
                            if fb and fb != 'INVALID' and len(fb) == 5:
                                current_candidates = filter_wordle_candidates(
                                    current_candidates, guess, fb)

                        all_games.append(game)

    return all_games


# ============================================================
# Handoff Analysis
# ============================================================

def find_handoff_turn(strategies: List[str]) -> Optional[Tuple[str, int, str]]:
    """Find the handoff point in a strategy sequence.

    Returns: (direction, handoff_turn_index, from_strategy)
      - direction: 'algo_to_llm' or 'llm_to_algo'
      - handoff_turn_index: 0-indexed turn where the NEW strategy starts
      - from_strategy: what was running before handoff
    """
    if len(strategies) < 2:
        return None

    for i in range(1, len(strategies)):
        prev = strategies[i-1].upper()
        curr = strategies[i].upper()

        prev_is_llm = 'LLM' in prev
        curr_is_llm = 'LLM' in curr
        prev_is_algo = prev in ('CSS', 'VOI')
        curr_is_algo = curr in ('CSS', 'VOI')

        if prev_is_algo and curr_is_llm:
            return ('algo_to_llm', i, prev)
        elif prev_is_llm and curr_is_algo:
            return ('llm_to_algo', i, 'LLM')

    return None


def analyze_handoff_performance(games: List[dict], domain: str):
    """Analyze performance as a function of search space at handoff."""

    # For algo→LLM handoffs: search space at the point LLM takes over
    algo_to_llm_data = []
    # For LLM→algo handoffs: search space at the point algo takes over
    llm_to_algo_data = []

    for game in games:
        handoff = find_handoff_turn(game['strategies'])
        if not handoff:
            continue

        direction, turn_idx, from_strat = handoff

        # Get candidates at handoff turn
        if domain == 'mastermind':
            # candidates_N is AFTER turn N, so candidates at handoff = candidates[turn_idx-1]
            if turn_idx - 1 < len(game['candidates']) and game['candidates'][turn_idx - 1] is not None:
                candidates_at_handoff = game['candidates'][turn_idx - 1]
            else:
                continue
        else:
            # For Wordle: candidates[i] is BEFORE turn i
            if turn_idx < len(game['candidates']):
                candidates_at_handoff = game['candidates'][turn_idx]
            else:
                continue

        # Count invalid guesses after handoff
        invalid_count = sum(1 for fb in game['feedbacks'][turn_idx:]
                           if fb == 'INVALID')

        entry = {
            'config': game['config'],
            'model': game['model'],
            'won': game['won'],
            'attempts': game['attempts'],
            'candidates_at_handoff': candidates_at_handoff,
            'handoff_turn': turn_idx + 1,  # 1-indexed
            'from_strategy': from_strat,
            'invalid_after_handoff': invalid_count,
            'log_candidates': math.log2(candidates_at_handoff) if candidates_at_handoff > 0 else 0,
        }

        if direction == 'algo_to_llm':
            algo_to_llm_data.append(entry)
        else:
            llm_to_algo_data.append(entry)

    return algo_to_llm_data, llm_to_algo_data


def bucket_analysis(data: List[dict], domain: str, direction: str):
    """Bucket games by search space at handoff and compute metrics."""

    if not data:
        return

    # Define buckets based on domain
    if domain == 'mastermind_extended':
        bucket_edges = [0, 10, 50, 100, 300, 500, 1000, 4096]
        bucket_labels = ['1-10', '11-50', '51-100', '101-300', '301-500', '501-1000', '1001-4096']
    elif domain == 'mastermind':
        # Mastermind Classic: 1296 total codes
        bucket_edges = [0, 10, 50, 100, 300, 500, 1296]
        bucket_labels = ['1-10', '11-50', '51-100', '101-300', '301-500', '501-1296']
    else:
        # Wordle: ~5629 total words
        bucket_edges = [0, 10, 50, 200, 500, 1000, 5629]
        bucket_labels = ['1-10', '11-50', '51-200', '201-500', '501-1000', '1001-5629']

    buckets = defaultdict(list)
    for entry in data:
        c = entry['candidates_at_handoff']
        for j in range(len(bucket_edges) - 1):
            if bucket_edges[j] < c <= bucket_edges[j + 1]:
                buckets[bucket_labels[j]].append(entry)
                break

    title = f"{domain.upper()} — {direction.replace('_', ' ').title()}"
    print(f"\n{'='*90}")
    print(title)
    print(f"{'='*90}")
    print(f"{'Search Space':<15} {'N Games':>8} {'Win%':>7} {'Avg Att':>8} {'Avg Invalid':>12} {'Entropy':>8}")
    print("-" * 90)

    for label in bucket_labels:
        entries = buckets.get(label, [])
        if not entries:
            continue
        n = len(entries)
        win_rate = sum(1 for e in entries if e['won']) / n * 100
        avg_att = np.mean([e['attempts'] for e in entries])
        avg_invalid = np.mean([e['invalid_after_handoff'] for e in entries])
        avg_entropy = np.mean([e['log_candidates'] for e in entries])
        print(f"{label:<15} {n:>8} {win_rate:>6.1f}% {avg_att:>8.2f} {avg_invalid:>12.2f} {avg_entropy:>7.1f}b")

    # Overall
    n = len(data)
    win_rate = sum(1 for e in data if e['won']) / n * 100
    avg_att = np.mean([e['attempts'] for e in data])
    print("-" * 90)
    print(f"{'TOTAL':<15} {n:>8} {win_rate:>6.1f}% {avg_att:>8.2f}")


def config_level_analysis(data: List[dict], domain: str, direction: str):
    """Show per-config summary with average search space at handoff."""
    if not data:
        return

    title = f"{domain.upper()} — Per-Config Summary ({direction.replace('_', ' ').title()})"
    print(f"\n{'='*100}")
    print(title)
    print(f"{'='*100}")
    print(f"{'Config':<20} {'N':>6} {'Win%':>7} {'Avg Att':>8} {'Avg Candidates':>15} {'Avg Entropy':>12} {'Handoff Turn':>13}")
    print("-" * 100)

    by_config = defaultdict(list)
    for e in data:
        by_config[e['config']].append(e)

    for config in sorted(by_config.keys()):
        entries = by_config[config]
        n = len(entries)
        win_rate = sum(1 for e in entries if e['won']) / n * 100
        avg_att = np.mean([e['attempts'] for e in entries])
        avg_cand = np.mean([e['candidates_at_handoff'] for e in entries])
        avg_entropy = np.mean([e['log_candidates'] for e in entries])
        avg_handoff = np.mean([e['handoff_turn'] for e in entries])
        print(f"{config:<20} {n:>6} {win_rate:>6.1f}% {avg_att:>8.2f} {avg_cand:>15.1f} {avg_entropy:>11.1f}b {avg_handoff:>13.1f}")


def model_level_analysis(data: List[dict], domain: str, direction: str):
    """Show per-model summary for algo-to-LLM handoffs."""
    if not data:
        return

    title = f"{domain.upper()} — Per-Model LLM Performance After Handoff ({direction.replace('_', ' ')})"
    print(f"\n{'='*100}")
    print(title)
    print(f"{'='*100}")
    print(f"{'Model':<35} {'N':>6} {'Win%':>7} {'Avg Att':>8} {'Avg Candidates':>15} {'Avg Invalid':>12}")
    print("-" * 100)

    by_model = defaultdict(list)
    for e in data:
        by_model[e['model']].append(e)

    for model in sorted(by_model.keys()):
        entries = by_model[model]
        n = len(entries)
        win_rate = sum(1 for e in entries if e['won']) / n * 100
        avg_att = np.mean([e['attempts'] for e in entries])
        avg_cand = np.mean([e['candidates_at_handoff'] for e in entries])
        avg_invalid = np.mean([e['invalid_after_handoff'] for e in entries])
        print(f"{model:<35} {n:>6} {win_rate:>6.1f}% {avg_att:>8.2f} {avg_cand:>15.1f} {avg_invalid:>12.2f}")


def correlation_analysis(data: List[dict], domain: str, direction: str):
    """Compute correlation between search space size and performance."""
    if len(data) < 10:
        return

    from scipy import stats as sp_stats

    log_cands = np.array([e['log_candidates'] for e in data])
    win_arr = np.array([1 if e['won'] else 0 for e in data])
    att_arr = np.array([e['attempts'] for e in data])

    title = f"{domain.upper()} — Correlation: Search Space vs Performance ({direction.replace('_', ' ')})"
    print(f"\n{'='*90}")
    print(title)
    print(f"{'='*90}")

    # Point-biserial correlation: log(candidates) vs win
    if len(set(win_arr)) > 1:
        r_win, p_win = sp_stats.pointbiserialr(win_arr, log_cands)
        print(f"  log2(candidates) vs win:      r={r_win:.4f}, p={p_win:.4f}")
    else:
        print(f"  log2(candidates) vs win:      all same outcome, skipping")

    # Pearson correlation: log(candidates) vs attempts
    r_att, p_att = sp_stats.pearsonr(log_cands, att_arr)
    print(f"  log2(candidates) vs attempts: r={r_att:.4f}, p={p_att:.4f}")

    if domain == 'mastermind':
        invalid_arr = np.array([e['invalid_after_handoff'] for e in data])
        r_inv, p_inv = sp_stats.pearsonr(log_cands, invalid_arr)
        print(f"  log2(candidates) vs invalid:  r={r_inv:.4f}, p={p_inv:.4f}")


def save_csv(data: List[dict], filepath: Path, direction: str):
    """Save handoff analysis data to CSV for further analysis."""
    if not data:
        return

    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'domain', 'config', 'model', 'direction', 'won', 'attempts',
            'candidates_at_handoff', 'log_candidates', 'handoff_turn',
            'from_strategy', 'invalid_after_handoff'
        ])
        writer.writeheader()
        for e in data:
            writer.writerow({
                'domain': e.get('domain', ''),
                'config': e['config'],
                'model': e['model'],
                'direction': direction,
                'won': e['won'],
                'attempts': e['attempts'],
                'candidates_at_handoff': e['candidates_at_handoff'],
                'log_candidates': round(e['log_candidates'], 4),
                'handoff_turn': e['handoff_turn'],
                'from_strategy': e['from_strategy'],
                'invalid_after_handoff': e['invalid_after_handoff'],
            })
    print(f"\nSaved {len(data)} rows to {filepath}")


# ============================================================
# Main
# ============================================================

def main():
    print("=" * 90)
    print("SEARCH SPACE HANDOFF ANALYSIS")
    print("Performance Gap as a Function of Remaining Search Space")
    print("=" * 90)

    # --- Mastermind Classic ---
    mm_results_dir = PROJECT_ROOT / 'results' / 'mastermind' / 'hybrids' / 'classic'
    if mm_results_dir.exists():
        print(f"\nLoading Mastermind Classic data from {mm_results_dir}...")
        mm_games = load_mastermind_hybrid_data(mm_results_dir)
        print(f"  Loaded {len(mm_games)} Mastermind Classic games")

        mm_a2l, mm_l2a = analyze_handoff_performance(mm_games, 'mastermind')
        print(f"  Algo→LLM handoffs: {len(mm_a2l)}")
        print(f"  LLM→Algo handoffs: {len(mm_l2a)}")

        if mm_a2l:
            bucket_analysis(mm_a2l, 'mastermind', 'algo_to_llm')
            config_level_analysis(mm_a2l, 'mastermind', 'algo_to_llm')
            model_level_analysis(mm_a2l, 'mastermind', 'algo_to_llm')
            correlation_analysis(mm_a2l, 'mastermind', 'algo_to_llm')

        if mm_l2a:
            bucket_analysis(mm_l2a, 'mastermind', 'llm_to_algo')
            config_level_analysis(mm_l2a, 'mastermind', 'llm_to_algo')
            correlation_analysis(mm_l2a, 'mastermind', 'llm_to_algo')

        # Save CSVs
        out_dir = PROJECT_ROOT / 'results' / 'analysis'
        for tag, d, data_list in [('algo_to_llm', 'mastermind', mm_a2l),
                                   ('llm_to_algo', 'mastermind', mm_l2a)]:
            if data_list:
                for e in data_list:
                    e['domain'] = d
                save_csv(data_list, out_dir / f'handoff_{d}_{tag}.csv', tag)
    else:
        print(f"\nMastermind Classic results not found at {mm_results_dir}")

    # --- Mastermind Extended ---
    mm_ext_dir = PROJECT_ROOT / 'results' / 'mastermind' / 'hybrids' / 'extended'
    if mm_ext_dir.exists():
        print(f"\n{'='*90}")
        print(f"Loading Mastermind Extended data from {mm_ext_dir}...")
        mm_ext_games = load_mastermind_hybrid_data(mm_ext_dir)
        print(f"  Loaded {len(mm_ext_games)} Mastermind Extended games")

        mm_ext_a2l, mm_ext_l2a = analyze_handoff_performance(mm_ext_games, 'mastermind_extended')
        print(f"  Algo→LLM handoffs: {len(mm_ext_a2l)}")
        print(f"  LLM→Algo handoffs: {len(mm_ext_l2a)}")

        if mm_ext_a2l:
            bucket_analysis(mm_ext_a2l, 'mastermind_extended', 'algo_to_llm')
            config_level_analysis(mm_ext_a2l, 'mastermind_extended', 'algo_to_llm')
            model_level_analysis(mm_ext_a2l, 'mastermind_extended', 'algo_to_llm')
            correlation_analysis(mm_ext_a2l, 'mastermind_extended', 'algo_to_llm')

        if mm_ext_l2a:
            bucket_analysis(mm_ext_l2a, 'mastermind_extended', 'llm_to_algo')
            config_level_analysis(mm_ext_l2a, 'mastermind_extended', 'llm_to_algo')
            correlation_analysis(mm_ext_l2a, 'mastermind_extended', 'llm_to_algo')

        # Save CSVs
        out_dir = PROJECT_ROOT / 'results' / 'analysis'
        for tag, d, data_list in [('algo_to_llm', 'mastermind_extended', mm_ext_a2l),
                                   ('llm_to_algo', 'mastermind_extended', mm_ext_l2a)]:
            if data_list:
                for e in data_list:
                    e['domain'] = d
                save_csv(data_list, out_dir / f'handoff_{d}_{tag}.csv', tag)
    else:
        print(f"\nMastermind Extended results not found at {mm_ext_dir}")

    # --- Wordle ---
    wordle_results_dir = PROJECT_ROOT / 'results' / 'workshop'
    if wordle_results_dir.exists():
        print(f"\n{'='*90}")
        print(f"Loading Wordle data from {wordle_results_dir}...")
        print("  (Reconstructing candidate counts from feedback — this may take a minute)")
        word_list = load_wordle_word_list()
        print(f"  Word list: {len(word_list)} words")

        wordle_games = load_wordle_hybrid_data(wordle_results_dir, word_list)
        print(f"  Loaded {len(wordle_games)} Wordle games")

        w_a2l, w_l2a = analyze_handoff_performance(wordle_games, 'wordle')
        print(f"  Algo→LLM handoffs: {len(w_a2l)}")
        print(f"  LLM→Algo handoffs: {len(w_l2a)}")

        if w_a2l:
            bucket_analysis(w_a2l, 'wordle', 'algo_to_llm')
            config_level_analysis(w_a2l, 'wordle', 'algo_to_llm')
            model_level_analysis(w_a2l, 'wordle', 'algo_to_llm')
            correlation_analysis(w_a2l, 'wordle', 'algo_to_llm')

        if w_l2a:
            bucket_analysis(w_l2a, 'wordle', 'llm_to_algo')
            config_level_analysis(w_l2a, 'wordle', 'llm_to_algo')
            correlation_analysis(w_l2a, 'wordle', 'llm_to_algo')

        # Save CSVs
        out_dir = PROJECT_ROOT / 'results' / 'analysis'
        for tag, d, data_list in [('algo_to_llm', 'wordle', w_a2l),
                                   ('llm_to_algo', 'wordle', w_l2a)]:
            if data_list:
                for e in data_list:
                    e['domain'] = d
                save_csv(data_list, out_dir / f'handoff_{d}_{tag}.csv', tag)

    else:
        print(f"\nWordle results not found at {wordle_results_dir}")

    print(f"\n{'='*90}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*90}")


if __name__ == "__main__":
    main()
