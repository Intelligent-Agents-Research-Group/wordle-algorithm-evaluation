#!/usr/bin/env python3
"""
Cross-Domain Regime Transfer Analysis

Tests whether a model's integration regime in one domain predicts its
regime in another domain. If regimes transfer, it suggests the behavior
is a stable model property rather than task-dependent.

Analyses:
1. Follow rate correlation across domains (Wordle vs MM vs MM Hard)
2. Regime classification consistency
3. Algorithm sensitivity transfer (CSS-VOI gap)
"""

import csv
import glob
import json
import math
import os
import sys
from collections import defaultdict

RESULTS_BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'results')
OUTPUT_DIR = os.path.join(RESULTS_BASE, 'cross_domain_transfer')

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
        return [(str(w), float(s)) for w, s in json.loads(scores_str)]
    except (json.JSONDecodeError, ValueError, TypeError):
        return []


def compute_follow_rate(csv_path, max_turns):
    """Compute overall follow rate from a CSV."""
    follows = 0
    total = 0
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            for t in range(1, max_turns + 1):
                val = row.get(f'llm_followed_algo_{t}', '').strip().lower()
                if val in ('true', 'false'):
                    total += 1
                    if val == 'true':
                        follows += 1
    if total == 0:
        return None, 0
    return follows / total, total


def compute_win_rate(csv_path):
    """Compute win rate from a CSV."""
    wins = 0
    total = 0
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            if row.get('won', '').strip().lower() == 'true':
                wins += 1
    return wins / total if total > 0 else None, total


def compute_alignment(csv_path, max_turns, top_k=TOP_K):
    """Compute alignment score from baseline CSV."""
    in_topk = 0
    total = 0
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            for t in range(1, max_turns + 1):
                guess = row.get(f'guess_{t}', '').strip()
                if not guess:
                    break
                scores = parse_algo_scores(row.get(f'algo_scores_{t}', ''))
                if not scores:
                    continue
                topk = {w.upper() for w, _ in scores[:top_k]}
                if guess.upper() in topk:
                    in_topk += 1
                total += 1
    if total == 0:
        return None
    return 2.0 * (in_topk / total) - 1.0


def classify_regime(follow_rate, css_voi_gap=None):
    """Classify into regime based on follow rate."""
    if follow_rate is None:
        return "Unknown"
    if follow_rate > 0.6:
        return "Integration"
    elif follow_rate < 0.2:
        return "Rejection"
    elif 0.2 <= follow_rate <= 0.6:
        return "Moderate"
    return "Unknown"


def pearson_r(xs, ys):
    """Compute Pearson correlation coefficient."""
    n = len(xs)
    if n < 3:
        return None, None
    mx = sum(xs) / n
    my = sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs) / (n - 1))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys) / (n - 1))
    if sx < 1e-12 or sy < 1e-12:
        return None, None
    r = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / ((n - 1) * sx * sy)
    # t-test for significance
    if abs(r) >= 1.0:
        return r, 0.0
    t_stat = r * math.sqrt((n - 2) / (1 - r * r))
    # Approximate p-value using normal for large n
    p = 2 * normal_sf(abs(t_stat))
    return r, p


def normal_sf(z):
    if z < 0:
        return 1.0 - normal_sf(-z)
    b0 = 0.2316419
    b1, b2, b3, b4, b5 = 0.319381530, -0.356563782, 1.781477937, -1.821255978, 1.330274429
    t = 1.0 / (1.0 + b0 * z)
    phi = math.exp(-0.5 * z * z) / math.sqrt(2 * math.pi)
    return phi * t * (b1 + t * (b2 + t * (b3 + t * (b4 + t * b5))))


def run_analysis():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Discover models
    all_models = set()
    for domain_key, domain_cfg in DOMAINS.items():
        data_dir = os.path.join(RESULTS_BASE, domain_cfg['dir'])
        for algo in ALGOS:
            for fpath in glob.glob(os.path.join(data_dir, f'voi_informed_{algo}_*_*.csv')):
                fname = os.path.basename(fpath)
                parts = fname.replace(f'voi_informed_{algo}_', '', 1)
                model = '_'.join(parts.split('_')[:-2])
                if model not in EXCLUDE_MODELS:
                    all_models.add(model)
    all_models = sorted(all_models)

    # Collect per-(model, domain, algo) metrics
    metrics = {}  # key: (model, domain, algo) -> {follow_rate, win_rate, alignment, ...}

    for model in all_models:
        for domain_key, domain_cfg in DOMAINS.items():
            data_dir = os.path.join(RESULTS_BASE, domain_cfg['dir'])
            max_turns = domain_cfg['max_turns']

            for algo in ALGOS:
                key = (model, domain_key, algo)

                informed_csv = find_csv(data_dir, 'voi_informed', algo, model)
                baseline_csv = find_csv(data_dir, 'baseline', algo, model)

                if not informed_csv:
                    continue

                fr, n_turns = compute_follow_rate(informed_csv, max_turns)
                wr, n_games = compute_win_rate(informed_csv)

                A = None
                if baseline_csv:
                    A = compute_alignment(baseline_csv, max_turns)

                wr_base = None
                if baseline_csv:
                    wr_base, _ = compute_win_rate(baseline_csv)

                metrics[key] = {
                    'follow_rate': fr,
                    'win_rate': wr,
                    'win_rate_baseline': wr_base,
                    'alignment': A,
                    'n_turns': n_turns,
                    'n_games': n_games,
                }

    # ── Analysis 1: Follow rate table ──────────────────────────────────────
    print("=" * 110)
    print("ANALYSIS 1: FOLLOW RATES ACROSS DOMAINS AND ALGORITHMS")
    print("=" * 110)
    print(f"\n{'Model':<30}", end='')
    for domain_key in DOMAINS:
        for algo in ALGOS:
            print(f" {domain_key[:6]}_{algo:>3}", end='')
    print()
    print("-" * 110)

    for model in all_models:
        print(f"{model:<30}", end='')
        for domain_key in DOMAINS:
            for algo in ALGOS:
                key = (model, domain_key, algo)
                if key in metrics and metrics[key]['follow_rate'] is not None:
                    print(f" {metrics[key]['follow_rate']:>10.1%}", end='')
                else:
                    print(f" {'--':>10}", end='')
        print()

    # ── Analysis 2: Cross-domain correlations ──────────────────────────────
    print("\n" + "=" * 110)
    print("ANALYSIS 2: CROSS-DOMAIN FOLLOW RATE CORRELATIONS")
    print("Do models that follow more in one domain also follow more in others?")
    print("=" * 110)

    domain_keys = list(DOMAINS.keys())
    for i in range(len(domain_keys)):
        for j in range(i + 1, len(domain_keys)):
            d1, d2 = domain_keys[i], domain_keys[j]
            xs, ys, labels = [], [], []
            for model in all_models:
                for algo in ALGOS:
                    k1 = (model, d1, algo)
                    k2 = (model, d2, algo)
                    if k1 in metrics and k2 in metrics:
                        fr1 = metrics[k1]['follow_rate']
                        fr2 = metrics[k2]['follow_rate']
                        if fr1 is not None and fr2 is not None:
                            xs.append(fr1)
                            ys.append(fr2)
                            labels.append(f"{model[:15]}_{algo}")

            r, p = pearson_r(xs, ys)
            sig = '***' if p and p < 0.001 else '**' if p and p < 0.01 else '*' if p and p < 0.05 else ''
            print(f"\n  {d1} vs {d2}: r = {r:.4f}, p = {p:.2e} {sig}  (n={len(xs)} points)")

    # Also correlate per-model averages (collapsing across algos)
    print("\n  Per-model average follow rates (collapsing across algos):")
    for i in range(len(domain_keys)):
        for j in range(i + 1, len(domain_keys)):
            d1, d2 = domain_keys[i], domain_keys[j]
            xs, ys = [], []
            for model in all_models:
                frs1 = [metrics[(model, d1, a)]['follow_rate']
                        for a in ALGOS if (model, d1, a) in metrics
                        and metrics[(model, d1, a)]['follow_rate'] is not None]
                frs2 = [metrics[(model, d2, a)]['follow_rate']
                        for a in ALGOS if (model, d2, a) in metrics
                        and metrics[(model, d2, a)]['follow_rate'] is not None]
                if frs1 and frs2:
                    xs.append(sum(frs1) / len(frs1))
                    ys.append(sum(frs2) / len(frs2))

            r, p = pearson_r(xs, ys)
            if r is not None:
                sig = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else ''
                print(f"    {d1} vs {d2}: r = {r:.4f}, p = {p:.2e} {sig}  (n={len(xs)} models)")

    # ── Analysis 3: Regime classification consistency ──────────────────────
    print("\n" + "=" * 110)
    print("ANALYSIS 3: REGIME CLASSIFICATION CONSISTENCY")
    print("Does a model's regime transfer across domains?")
    print("=" * 110)

    print(f"\n{'Model':<30}", end='')
    for domain_key in DOMAINS:
        print(f" {domain_key:<20}", end='')
    print("  Consistent?")
    print("-" * 110)

    consistent_count = 0
    total_count = 0

    for model in all_models:
        regimes = {}
        print(f"{model:<30}", end='')
        for domain_key in DOMAINS:
            # Average follow rate across algos
            frs = [metrics[(model, domain_key, a)]['follow_rate']
                   for a in ALGOS if (model, domain_key, a) in metrics
                   and metrics[(model, domain_key, a)]['follow_rate'] is not None]
            if frs:
                avg_fr = sum(frs) / len(frs)
                regime = classify_regime(avg_fr)
                regimes[domain_key] = regime
                print(f" {regime:<12} ({avg_fr:.0%})", end='')
            else:
                print(f" {'N/A':<20}", end='')

        if len(regimes) >= 2:
            unique_regimes = set(regimes.values())
            is_consistent = len(unique_regimes) == 1
            total_count += 1
            if is_consistent:
                consistent_count += 1
            print(f"  {'Yes' if is_consistent else 'No'}")
        else:
            print()

    if total_count > 0:
        print(f"\n  Consistency rate: {consistent_count}/{total_count} "
              f"({consistent_count/total_count:.0%}) models have same regime across all domains")

    # ── Analysis 4: CSS-VOI gap transfer ───────────────────────────────────
    print("\n" + "=" * 110)
    print("ANALYSIS 4: CSS-VOI FOLLOW RATE GAP TRANSFER")
    print("Does the algorithm sensitivity (CSS vs VOI gap) transfer across domains?")
    print("=" * 110)

    print(f"\n{'Model':<30}", end='')
    for domain_key in DOMAINS:
        print(f" gap_{domain_key[:8]:>10}", end='')
    print()
    print("-" * 90)

    gaps = defaultdict(dict)  # model -> domain -> gap

    for model in all_models:
        print(f"{model:<30}", end='')
        for domain_key in DOMAINS:
            k_css = (model, domain_key, 'css')
            k_voi = (model, domain_key, 'voi')
            if k_css in metrics and k_voi in metrics:
                fr_css = metrics[k_css]['follow_rate']
                fr_voi = metrics[k_voi]['follow_rate']
                if fr_css is not None and fr_voi is not None:
                    gap = fr_voi - fr_css
                    gaps[model][domain_key] = gap
                    print(f" {gap:>+10.1%}", end='')
                else:
                    print(f" {'--':>10}", end='')
            else:
                print(f" {'--':>10}", end='')
        print()

    # Correlate gaps across domains
    print("\n  Gap correlations:")
    for i in range(len(domain_keys)):
        for j in range(i + 1, len(domain_keys)):
            d1, d2 = domain_keys[i], domain_keys[j]
            xs, ys = [], []
            for model in all_models:
                if d1 in gaps[model] and d2 in gaps[model]:
                    xs.append(gaps[model][d1])
                    ys.append(gaps[model][d2])
            r, p = pearson_r(xs, ys)
            if r is not None:
                sig = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else ''
                print(f"    {d1} vs {d2}: r = {r:.4f}, p = {p:.2e} {sig}  (n={len(xs)})")

    # ── Analysis 5: Alignment score transfer ───────────────────────────────
    print("\n" + "=" * 110)
    print("ANALYSIS 5: ALIGNMENT SCORE TRANSFER")
    print("Do models with high alignment in one domain also have high alignment in others?")
    print("=" * 110)

    print(f"\n{'Model':<30}", end='')
    for domain_key in DOMAINS:
        for algo in ALGOS:
            print(f" A_{domain_key[:4]}_{algo}", end='')
    print()
    print("-" * 110)

    for model in all_models:
        print(f"{model:<30}", end='')
        for domain_key in DOMAINS:
            for algo in ALGOS:
                key = (model, domain_key, algo)
                if key in metrics and metrics[key]['alignment'] is not None:
                    print(f" {metrics[key]['alignment']:>10.3f}", end='')
                else:
                    print(f" {'--':>10}", end='')
        print()

    # Alignment correlations
    print("\n  Alignment score correlations:")
    for i in range(len(domain_keys)):
        for j in range(i + 1, len(domain_keys)):
            d1, d2 = domain_keys[i], domain_keys[j]
            xs, ys = [], []
            for model in all_models:
                for algo in ALGOS:
                    k1 = (model, d1, algo)
                    k2 = (model, d2, algo)
                    if (k1 in metrics and k2 in metrics and
                            metrics[k1]['alignment'] is not None and
                            metrics[k2]['alignment'] is not None):
                        xs.append(metrics[k1]['alignment'])
                        ys.append(metrics[k2]['alignment'])
            r, p = pearson_r(xs, ys)
            if r is not None:
                sig = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else ''
                print(f"    {d1} vs {d2}: r = {r:.4f}, p = {p:.2e} {sig}  (n={len(xs)})")

    # Save summary CSV
    csv_path = os.path.join(OUTPUT_DIR, 'cross_domain_metrics.csv')
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['model', 'domain', 'algorithm', 'follow_rate', 'win_rate',
                         'win_rate_baseline', 'alignment', 'regime'])
        for key in sorted(metrics.keys()):
            model, domain, algo = key
            m = metrics[key]
            regime = classify_regime(m['follow_rate'])
            writer.writerow([
                model, domain, algo,
                f"{m['follow_rate']:.6f}" if m['follow_rate'] is not None else '',
                f"{m['win_rate']:.6f}" if m['win_rate'] is not None else '',
                f"{m['win_rate_baseline']:.6f}" if m['win_rate_baseline'] is not None else '',
                f"{m['alignment']:.6f}" if m['alignment'] is not None else '',
                regime,
            ])
    print(f"\nResults saved to {csv_path}")


if __name__ == '__main__':
    run_analysis()
