#!/usr/bin/env python3
"""
Performance-Conditioned Analysis

Tests whether following algorithmic signals helps more when prior-signal
alignment is high vs low. Key question: does following VOI signals lead
to better outcomes than following CSS signals?

Analyses:
1. Win rate comparison: followed vs not-followed games, by algorithm
2. Attempt efficiency: avg attempts when LLM followed vs didn't, by algorithm
3. Per-turn impact: does following on turn t reduce remaining attempts?
4. Alignment × follow interaction: is following beneficial only when alignment is high?
"""

import csv
import glob
import json
import math
import os
import sys
from collections import defaultdict

RESULTS_BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'results')
OUTPUT_DIR = os.path.join(RESULTS_BASE, 'performance_conditioned')

DOMAINS = {
    'wordle': {'dir': 'wordle', 'max_turns': 6},
    'mastermind': {'dir': 'mastermind_extended', 'max_turns': 10},
    'mastermind_hard': {'dir': 'mastermind_extended_hard', 'max_turns': 10},
}

ALGOS = ['css', 'voi']
EXCLUDE_MODELS = {'llama-3.1-nemotron-nano-8b-v1'}
TOP_K = 5


def find_csv(directory, condition, algo, model):
    pattern = os.path.join(directory, f'{condition}_{algo}_{model}_*.csv')
    matches = glob.glob(pattern)
    return sorted(matches)[-1] if matches else None


def parse_algo_scores(scores_str):
    if not scores_str or scores_str.strip() == '':
        return []
    try:
        parsed = json.loads(scores_str)
        return [(str(w), float(s)) for w, s in parsed]
    except (json.JSONDecodeError, ValueError, TypeError):
        return []


def load_game_data(csv_path, max_turns):
    """Load per-game data with per-turn follow information."""
    games = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            game = {
                'game_number': int(row['game_number']),
                'won': row.get('won', '').strip().lower() == 'true',
                'attempts': int(row.get('attempts', 0)),
                'turns': [],
            }

            total_follows = 0
            total_turns_with_signal = 0

            for t in range(1, max_turns + 1):
                guess = row.get(f'guess_{t}', '').strip()
                if not guess:
                    break

                followed_str = row.get(f'llm_followed_algo_{t}', '').strip()
                if followed_str.lower() in ('true', 'false'):
                    followed = followed_str.lower() == 'true'
                    total_turns_with_signal += 1
                    if followed:
                        total_follows += 1
                else:
                    followed = None

                algo_scores = parse_algo_scores(row.get(f'algo_scores_{t}', ''))

                game['turns'].append({
                    'turn': t,
                    'guess': guess,
                    'followed': followed,
                    'algo_scores': algo_scores,
                })

            game['follow_rate'] = (total_follows / total_turns_with_signal
                                   if total_turns_with_signal > 0 else None)
            game['total_follows'] = total_follows
            game['total_signal_turns'] = total_turns_with_signal
            games.append(game)
    return games


def compute_alignment_score(baseline_games, top_k=TOP_K):
    in_topk = 0
    total = 0
    for game in baseline_games:
        for turn in game['turns']:
            if not turn['algo_scores']:
                continue
            topk_words = {w.upper() for w, _ in turn['algo_scores'][:top_k]}
            if turn['guess'].upper() in topk_words:
                in_topk += 1
            total += 1
    if total == 0:
        return None
    return 2.0 * (in_topk / total) - 1.0


def wilson_ci(successes, total, z=1.96):
    """Wilson score confidence interval."""
    if total == 0:
        return 0, (0, 0)
    p = successes / total
    denom = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    spread = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denom
    return p, (max(0, center - spread), min(1, center + spread))


def run_analysis():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Discover models
    all_models = set()
    for domain_key, domain_cfg in DOMAINS.items():
        data_dir = os.path.join(RESULTS_BASE, domain_cfg['dir'])
        for algo in ALGOS:
            for fpath in glob.glob(os.path.join(data_dir, f'baseline_{algo}_*_*.csv')):
                fname = os.path.basename(fpath)
                parts = fname.replace(f'baseline_{algo}_', '', 1)
                model = '_'.join(parts.split('_')[:-2])
                if model not in EXCLUDE_MODELS:
                    all_models.add(model)
    all_models = sorted(all_models)

    # ── Analysis 1: Win rate by follow behavior ────────────────────────────
    print("=" * 100)
    print("ANALYSIS 1: WIN RATE BY FOLLOW BEHAVIOR (informed condition)")
    print("Does following the algorithm's recommendation improve win rate?")
    print("=" * 100)

    # Collect per-game data
    all_game_records = []  # (model, domain, algo, game_follow_rate, won, attempts, alignment)

    alignment_scores = {}

    for model in all_models:
        for domain_key, domain_cfg in DOMAINS.items():
            data_dir = os.path.join(RESULTS_BASE, domain_cfg['dir'])
            max_turns = domain_cfg['max_turns']

            for algo in ALGOS:
                # Alignment from baseline
                baseline_csv = find_csv(data_dir, 'baseline', algo, model)
                if not baseline_csv:
                    continue
                baseline_games = load_game_data(baseline_csv, max_turns)
                A = compute_alignment_score(baseline_games)
                alignment_scores[(model, domain_key, algo)] = A

                # Informed condition
                informed_csv = find_csv(data_dir, 'voi_informed', algo, model)
                if not informed_csv:
                    continue
                informed_games = load_game_data(informed_csv, max_turns)

                for game in informed_games:
                    if game['follow_rate'] is not None:
                        all_game_records.append({
                            'model': model,
                            'domain': domain_key,
                            'algo': algo,
                            'follow_rate': game['follow_rate'],
                            'won': game['won'],
                            'attempts': game['attempts'],
                            'alignment': A,
                        })

    # Split games into high-follow vs low-follow
    print(f"\n{'Model':<30} {'Domain':<15} {'Algo':<5} {'A':>6} "
          f"{'WR_hi':>7} {'WR_lo':>7} {'Δ':>7} {'Att_hi':>7} {'Att_lo':>7}")
    print("-" * 100)

    csv_rows = []

    for model in all_models:
        for domain_key in DOMAINS:
            for algo in ALGOS:
                games = [r for r in all_game_records
                         if r['model'] == model and r['domain'] == domain_key and r['algo'] == algo]
                if not games:
                    continue

                A = alignment_scores.get((model, domain_key, algo))

                # High follow: games where LLM followed on >50% of turns
                high_follow = [g for g in games if g['follow_rate'] > 0.5]
                low_follow = [g for g in games if g['follow_rate'] <= 0.5]

                if not high_follow or not low_follow:
                    continue

                wr_hi = sum(g['won'] for g in high_follow) / len(high_follow)
                wr_lo = sum(g['won'] for g in low_follow) / len(low_follow)
                att_hi_won = [g['attempts'] for g in high_follow if g['won']]
                att_lo_won = [g['attempts'] for g in low_follow if g['won']]
                att_hi = sum(att_hi_won) / len(att_hi_won) if att_hi_won else float('nan')
                att_lo = sum(att_lo_won) / len(att_lo_won) if att_lo_won else float('nan')

                delta = wr_hi - wr_lo
                a_str = f"{A:.3f}" if A is not None else "N/A"

                print(f"{model:<30} {domain_key:<15} {algo:<5} {a_str:>6} "
                      f"{wr_hi:>7.1%} {wr_lo:>7.1%} {delta:>+7.1%} "
                      f"{att_hi:>7.2f} {att_lo:>7.2f}")

                csv_rows.append({
                    'model': model, 'domain': domain_key, 'algo': algo,
                    'alignment': A,
                    'n_high_follow': len(high_follow), 'n_low_follow': len(low_follow),
                    'win_rate_high_follow': wr_hi, 'win_rate_low_follow': wr_lo,
                    'delta_win_rate': delta,
                    'avg_attempts_high_follow': att_hi, 'avg_attempts_low_follow': att_lo,
                })

    # ── Analysis 2: Aggregate by algorithm ─────────────────────────────────
    print("\n" + "=" * 100)
    print("ANALYSIS 2: AGGREGATE FOLLOW BENEFIT BY ALGORITHM")
    print("Is following CSS signals more/less beneficial than following VOI signals?")
    print("=" * 100)

    for algo in ALGOS:
        algo_games = [r for r in all_game_records if r['algo'] == algo]
        high = [g for g in algo_games if g['follow_rate'] > 0.5]
        low = [g for g in algo_games if g['follow_rate'] <= 0.5]

        if high and low:
            wr_hi, ci_hi = wilson_ci(sum(g['won'] for g in high), len(high))
            wr_lo, ci_lo = wilson_ci(sum(g['won'] for g in low), len(low))
            print(f"\n  {algo.upper()}:")
            print(f"    High-follow games: {len(high)}, win rate = {wr_hi:.1%} "
                  f"[{ci_hi[0]:.1%}, {ci_hi[1]:.1%}]")
            print(f"    Low-follow games:  {len(low)}, win rate = {wr_lo:.1%} "
                  f"[{ci_lo[0]:.1%}, {ci_lo[1]:.1%}]")
            print(f"    Δ win rate: {wr_hi - wr_lo:+.1%}")

    # ── Analysis 3: Aggregate by model ─────────────────────────────────────
    print("\n" + "=" * 100)
    print("ANALYSIS 3: FOLLOW BENEFIT BY MODEL (across all domains/algos)")
    print("=" * 100)
    print(f"\n{'Model':<30} {'N_hi':>6} {'WR_hi':>7} {'N_lo':>6} {'WR_lo':>7} {'Δ':>7}")
    print("-" * 70)

    for model in all_models:
        model_games = [r for r in all_game_records if r['model'] == model]
        high = [g for g in model_games if g['follow_rate'] > 0.5]
        low = [g for g in model_games if g['follow_rate'] <= 0.5]

        if high and low:
            wr_hi = sum(g['won'] for g in high) / len(high)
            wr_lo = sum(g['won'] for g in low) / len(low)
            print(f"{model:<30} {len(high):>6} {wr_hi:>7.1%} {len(low):>6} {wr_lo:>7.1%} "
                  f"{wr_hi - wr_lo:>+7.1%}")
        elif high:
            wr_hi = sum(g['won'] for g in high) / len(high)
            print(f"{model:<30} {len(high):>6} {wr_hi:>7.1%} {'--':>6} {'--':>7} {'--':>7}")
        elif low:
            wr_lo = sum(g['won'] for g in low) / len(low)
            print(f"{model:<30} {'--':>6} {'--':>7} {len(low):>6} {wr_lo:>7.1%} {'--':>7}")

    # ── Analysis 4: Alignment × Follow interaction ─────────────────────────
    print("\n" + "=" * 100)
    print("ANALYSIS 4: ALIGNMENT × FOLLOW INTERACTION")
    print("Is following more beneficial when alignment is high?")
    print("=" * 100)

    # Split by alignment: high alignment (A > median) vs low alignment
    all_As = [r['alignment'] for r in all_game_records if r['alignment'] is not None]
    if all_As:
        median_A = sorted(all_As)[len(all_As) // 2]
        print(f"\n  Median alignment score: {median_A:.4f}")

        for label, filter_fn in [
            ("High alignment (A > median)", lambda r: r['alignment'] is not None and r['alignment'] > median_A),
            ("Low alignment (A ≤ median)", lambda r: r['alignment'] is not None and r['alignment'] <= median_A),
        ]:
            subset = [r for r in all_game_records if filter_fn(r)]
            high = [g for g in subset if g['follow_rate'] > 0.5]
            low = [g for g in subset if g['follow_rate'] <= 0.5]

            print(f"\n  {label}:")
            if high and low:
                wr_hi, ci_hi = wilson_ci(sum(g['won'] for g in high), len(high))
                wr_lo, ci_lo = wilson_ci(sum(g['won'] for g in low), len(low))
                print(f"    High-follow: n={len(high)}, win rate = {wr_hi:.1%} [{ci_hi[0]:.1%}, {ci_hi[1]:.1%}]")
                print(f"    Low-follow:  n={len(low)}, win rate = {wr_lo:.1%} [{ci_lo[0]:.1%}, {ci_lo[1]:.1%}]")
                print(f"    Δ win rate: {wr_hi - wr_lo:+.1%}")
            else:
                print(f"    Insufficient data for comparison (hi={len(high)}, lo={len(low)})")

    # ── Analysis 5: Baseline vs Informed win rates ─────────────────────────
    print("\n" + "=" * 100)
    print("ANALYSIS 5: BASELINE vs INFORMED WIN RATES")
    print("Does providing signals improve performance overall?")
    print("=" * 100)
    print(f"\n{'Model':<30} {'Domain':<15} {'Algo':<5} {'WR_base':>8} {'WR_inf':>8} {'Δ':>7}")
    print("-" * 85)

    for model in all_models:
        for domain_key, domain_cfg in DOMAINS.items():
            data_dir = os.path.join(RESULTS_BASE, domain_cfg['dir'])
            max_turns = domain_cfg['max_turns']

            for algo in ALGOS:
                baseline_csv = find_csv(data_dir, 'baseline', algo, model)
                informed_csv = find_csv(data_dir, 'voi_informed', algo, model)
                if not baseline_csv or not informed_csv:
                    continue

                baseline_games = load_game_data(baseline_csv, max_turns)
                informed_games = load_game_data(informed_csv, max_turns)

                wr_base = sum(g['won'] for g in baseline_games) / len(baseline_games)
                wr_inf = sum(g['won'] for g in informed_games) / len(informed_games)
                delta = wr_inf - wr_base

                print(f"{model:<30} {domain_key:<15} {algo:<5} {wr_base:>8.1%} {wr_inf:>8.1%} {delta:>+7.1%}")

    # Save CSV
    csv_path = os.path.join(OUTPUT_DIR, 'performance_conditioned.csv')
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'model', 'domain', 'algo', 'alignment',
            'n_high_follow', 'n_low_follow',
            'win_rate_high_follow', 'win_rate_low_follow', 'delta_win_rate',
            'avg_attempts_high_follow', 'avg_attempts_low_follow',
        ])
        writer.writeheader()
        for row in csv_rows:
            writer.writerow({k: (f"{v:.6f}" if isinstance(v, float) else v)
                             for k, v in row.items()})
    print(f"\nResults saved to {csv_path}")


if __name__ == '__main__':
    run_analysis()
