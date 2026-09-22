#!/usr/bin/env python3
"""
Analyze VOI-Informed Integration Experiment Results for Mastermind

Compares baseline vs voi_informed conditions across models and algorithms.

Metrics:
  - Win rate, average attempts
  - Follow rate: how often LLM chose algo's top-1 recommendation
  - Agreement by entropy level
  - Surface imitation diagnostic (shuffled_ranking condition)

Statistical tests: paired t-test (same target codes), Cohen's d effect size.

Usage:
  python voi_integration/scripts/analyze_mastermind_results.py [results_dir]
"""

import csv
import json
import sys
import math
from pathlib import Path
from collections import defaultdict
from typing import List, Dict

import numpy as np
from scipy import stats


MAX_ROUNDS = 10


def load_results(results_dir: Path) -> Dict[str, dict]:
    """Load all CSV results, grouped by config name.

    When duplicates exist for the same model/algo/condition, keeps the newest file.
    Skips results with 0 wins and 0% win rate (broken runs).
    """
    grouped = {}

    # Sort by modification time so newest overwrites oldest
    csv_files = sorted(results_dir.glob("*.csv"), key=lambda p: p.stat().st_mtime)

    for csv_file in csv_files:
        stem = csv_file.stem
        meta = {}
        for json_file in results_dir.glob(f"summary_*{csv_file.stem.split('_', 1)[-1] if '_' in stem else stem}*.json"):
            try:
                with open(json_file) as f:
                    meta = json.load(f)
                break
            except Exception:
                continue

        model = meta.get('model_name', 'unknown')
        algorithm = meta.get('algorithm', 'unknown')
        condition = meta.get('condition', 'unknown')

        # Skip broken runs
        if meta.get('wins', -1) == 0 and meta.get('total_games', 0) > 0:
            continue

        rows = []
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)

        config = meta.get('config_name', stem)
        key = f"{model}__{algorithm}__{condition}"
        grouped[key] = {
            'rows': rows,
            'meta': meta,
            'model': model,
            'algorithm': algorithm,
            'condition': condition,
            'config': config
        }

    return grouped


def compute_game_stats(rows: List[dict]) -> dict:
    """Compute aggregate stats from CSV rows."""
    wins = sum(1 for r in rows if r.get('won', '').lower() == 'true')
    n = len(rows)
    attempts_when_won = [int(r['attempts']) for r in rows
                         if r.get('won', '').lower() == 'true']

    # Per-game attempt scores (11 = loss, since Mastermind has 10 turns)
    attempt_scores = []
    for r in rows:
        if r.get('won', '').lower() == 'true':
            attempt_scores.append(int(r['attempts']))
        else:
            attempt_scores.append(11)

    # Follow rate
    follow_true = 0
    follow_total = 0
    for r in rows:
        for i in range(1, MAX_ROUNDS + 1):
            val = r.get(f'llm_followed_algo_{i}', '').strip()
            if val in ('True', 'true'):
                follow_true += 1
                follow_total += 1
            elif val in ('False', 'false'):
                follow_total += 1

    # Entropy buckets
    entropy_buckets = defaultdict(lambda: {'follow': 0, 'total': 0})
    for r in rows:
        for i in range(1, MAX_ROUNDS + 1):
            ent_str = r.get(f'entropy_{i}', '').strip()
            followed_str = r.get(f'llm_followed_algo_{i}', '').strip()
            if not ent_str or not followed_str or followed_str not in ('True', 'False', 'true', 'false'):
                continue
            try:
                ent = float(ent_str)
            except ValueError:
                continue
            if ent < 3:
                bucket = 'low (<3 bits)'
            elif ent < 7:
                bucket = 'mid (3-7 bits)'
            else:
                bucket = 'high (7+ bits)'
            entropy_buckets[bucket]['total'] += 1
            if followed_str in ('True', 'true'):
                entropy_buckets[bucket]['follow'] += 1

    return {
        'n': n,
        'wins': wins,
        'win_rate': wins / n if n > 0 else 0,
        'avg_attempts': np.mean(attempts_when_won) if attempts_when_won else 0,
        'attempt_scores': attempt_scores,
        'follow_rate': follow_true / follow_total if follow_total > 0 else None,
        'follow_count': follow_true,
        'follow_total': follow_total,
        'entropy_buckets': dict(entropy_buckets)
    }


def cohens_d(x: np.ndarray, y: np.ndarray) -> float:
    nx, ny = len(x), len(y)
    pooled_std = math.sqrt(((nx - 1) * np.var(x, ddof=1) + (ny - 1) * np.var(y, ddof=1)) / (nx + ny - 2))
    if pooled_std == 0:
        return 0.0
    return (np.mean(x) - np.mean(y)) / pooled_std


def analyze(results_dir: Path):
    """Run full analysis and print report."""
    grouped = load_results(results_dir)

    if not grouped:
        print(f"No results found in {results_dir}")
        return

    print("=" * 90)
    print("MASTERMIND VOI-INFORMED INTEGRATION EXPERIMENT ANALYSIS")
    print("=" * 90)

    # Group by model+algorithm
    pairs = defaultdict(dict)
    for key, data in grouped.items():
        model = data['model']
        algo = data['algorithm']
        cond = data['condition']
        pair_key = f"{model}__{algo}"
        pairs[pair_key][cond] = data

    # Summary table
    print(f"\n{'Model':<35} {'Algo':<6} {'Cond':<18} {'Win%':>6} {'AvgAtt':>7} {'Follow%':>8}")
    print("-" * 94)

    for pair_key in sorted(pairs.keys()):
        conds = pairs[pair_key]
        for cond_name in ['baseline', 'voi_informed', 'shuffled_ranking']:
            if cond_name not in conds:
                continue
            data = conds[cond_name]
            s = compute_game_stats(data['rows'])
            follow_str = f"{s['follow_rate']*100:.1f}" if s['follow_rate'] is not None else "N/A"
            print(f"{data['model']:<35} {data['algorithm']:<6} {cond_name:<18} "
                  f"{s['win_rate']*100:>5.1f}% {s['avg_attempts']:>6.2f} {follow_str:>7}%")

    # Paired statistical tests
    print("\n" + "=" * 90)
    print("PAIRED COMPARISONS (baseline vs voi_informed)")
    print("=" * 90)

    for pair_key in sorted(pairs.keys()):
        conds = pairs[pair_key]
        if 'baseline' not in conds or 'voi_informed' not in conds:
            print(f"\n{pair_key}: Missing one condition, skipping paired test")
            continue

        base_stats = compute_game_stats(conds['baseline']['rows'])
        voi_stats = compute_game_stats(conds['voi_informed']['rows'])

        base_scores = np.array(base_stats['attempt_scores'])
        voi_scores = np.array(voi_stats['attempt_scores'])

        if len(base_scores) == len(voi_scores) and len(base_scores) > 1:
            t_stat, p_val = stats.ttest_rel(base_scores, voi_scores)
            d = cohens_d(base_scores, voi_scores)

            print(f"\n{pair_key.replace('__', ' / ')}")
            print(f"  Baseline:     win={base_stats['win_rate']*100:.1f}%  avg_att={base_stats['avg_attempts']:.2f}")
            print(f"  VOI-Informed: win={voi_stats['win_rate']*100:.1f}%  avg_att={voi_stats['avg_attempts']:.2f}")
            print(f"  Paired t-test: t={t_stat:.3f}, p={p_val:.4f}")
            print(f"  Cohen's d: {d:.3f} ({'small' if abs(d) < 0.5 else 'medium' if abs(d) < 0.8 else 'large'})")
            if p_val < 0.05:
                winner = "VOI-Informed" if np.mean(voi_scores) < np.mean(base_scores) else "Baseline"
                print(f"  * Significant (p<0.05): {winner} is better")
            else:
                print("  * Not significant (p>=0.05)")
        else:
            print(f"\n{pair_key}: Cannot pair (different game counts)")

    # Entropy-bucket breakdown
    print("\n" + "=" * 90)
    print("FOLLOW RATE BY ENTROPY LEVEL (voi_informed only)")
    print("=" * 90)
    print(f"{'Model':<35} {'Algo':<6} {'Bucket':<18} {'Follow%':>8} {'N':>5}")
    print("-" * 90)

    for pair_key in sorted(pairs.keys()):
        conds = pairs[pair_key]
        if 'voi_informed' not in conds:
            continue
        data = conds['voi_informed']
        s = compute_game_stats(data['rows'])
        for bucket in ['low (<3 bits)', 'mid (3-7 bits)', 'high (7+ bits)']:
            info = s['entropy_buckets'].get(bucket, {'follow': 0, 'total': 0})
            if info['total'] > 0:
                rate = info['follow'] / info['total'] * 100
                print(f"{data['model']:<35} {data['algorithm']:<6} {bucket:<18} {rate:>7.1f}% {info['total']:>5}")

    # Surface Imitation Diagnostic
    has_shuffled = any('shuffled_ranking' in conds for conds in pairs.values())
    if has_shuffled:
        print("\n" + "=" * 94)
        print("SURFACE IMITATION DIAGNOSTIC (shuffled_ranking condition)")
        print("=" * 94)
        print()
        print("If the LLM truly reasons over scores, it should pick the highest-scored code")
        print("regardless of display position. If it imitates rank order, it picks whatever")
        print("is listed first.")
        print()
        print(f"{'Model':<35} {'Algo':<6} {'TrueTop1%':>10} {'DispTop1%':>10} {'Verdict':<20}")
        print("-" * 94)

        for pair_key in sorted(pairs.keys()):
            conds = pairs[pair_key]
            if 'shuffled_ranking' not in conds:
                continue
            data = conds['shuffled_ranking']
            rows = data['rows']

            true_follow = 0
            true_total = 0
            disp_follow = 0
            disp_total = 0

            for r in rows:
                for i in range(1, MAX_ROUNDS + 1):
                    followed_str = r.get(f'llm_followed_algo_{i}', '').strip()
                    disp_str = r.get(f'llm_picked_displayed_top1_{i}', '').strip()

                    if followed_str in ('True', 'true', 'False', 'false'):
                        true_total += 1
                        if followed_str in ('True', 'true'):
                            true_follow += 1

                    if disp_str in ('True', 'true', 'False', 'false'):
                        disp_total += 1
                        if disp_str in ('True', 'true'):
                            disp_follow += 1

            true_rate = true_follow / true_total * 100 if true_total > 0 else 0
            disp_rate = disp_follow / disp_total * 100 if disp_total > 0 else 0

            if disp_total > 0 and true_total > 0:
                if disp_rate > true_rate + 10:
                    verdict = "RANK IMITATION"
                elif true_rate > disp_rate + 10:
                    verdict = "SCORE REASONING"
                else:
                    verdict = "INCONCLUSIVE"
            else:
                verdict = "INSUFFICIENT DATA"

            print(f"{data['model']:<35} {data['algorithm']:<6} {true_rate:>9.1f}% {disp_rate:>9.1f}% {verdict:<20}")

        print()
        print("Interpretation:")
        print("  TrueTop1%  = LLM picked the highest-scored code (true best)")
        print("  DispTop1%  = LLM picked the code listed first (displayed rank 1)")
        print("  If DispTop1% >> TrueTop1%: LLM imitates rank order (surface imitation)")
        print("  If TrueTop1% >> DispTop1%: LLM reasons over scores (belief integration)")
        print("  If similar: inconclusive (may need more data)")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        results_dir = Path(sys.argv[1])
    else:
        results_dir = Path(__file__).parent.parent / 'results' / 'mastermind'

    analyze(results_dir)
