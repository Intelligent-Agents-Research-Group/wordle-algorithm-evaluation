#!/usr/bin/env python3
"""
Held-Out Model Comparison (§5.1 of Formal Framework)

Tests whether an alignment-modulated integration weight α_t = σ(b + β·A)
outperforms a constant-weight model P(follow) = σ(b) for predicting
LLM signal-following behavior.

Uses only Python stdlib (no numpy/scipy/pandas).
"""

import csv
import glob
import json
import math
import os
import sys
from collections import defaultdict

# ── Configuration ──────────────────────────────────────────────────────────

RESULTS_BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'results')
OUTPUT_DIR = os.path.join(RESULTS_BASE, 'alignment_model_comparison')

DOMAINS = {
    'wordle': {
        'dir': 'wordle',
        'max_turns': 6,
    },
    'mastermind': {
        'dir': 'mastermind_extended',
        'max_turns': 10,
    },
    'mastermind_hard': {
        'dir': 'mastermind_extended_hard',
        'max_turns': 10,
    },
}

ALGOS = ['css', 'voi']
EXCLUDE_MODELS = {'llama-3.1-nemotron-nano-8b-v1'}
TOP_K = 5
EPS = 1e-12


# ── Math Utilities ─────────────────────────────────────────────────────────

def sigmoid(x):
    """Numerically stable sigmoid."""
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    else:
        ex = math.exp(x)
        return ex / (1.0 + ex)


def log_likelihood_constant(b, ys):
    """Log-likelihood for constant model: logit(p) = b."""
    ll = 0.0
    p = sigmoid(b)
    p = max(EPS, min(1 - EPS, p))
    lp = math.log(p)
    lq = math.log(1 - p)
    for y in ys:
        ll += y * lp + (1 - y) * lq
    return ll


def log_likelihood_alignment(b, beta, ys, As):
    """Log-likelihood for alignment model: logit(p) = b + β·A."""
    ll = 0.0
    for y, a in zip(ys, As):
        p = sigmoid(b + beta * a)
        p = max(EPS, min(1 - EPS, p))
        ll += y * math.log(p) + (1 - y) * math.log(1 - p)
    return ll


def fit_constant_model(ys):
    """Fit constant model via grid + Newton's method. Returns (b, ll)."""
    # Closed form: b = log(p/(1-p)) where p = mean(y)
    p = sum(ys) / len(ys)
    p = max(EPS, min(1 - EPS, p))
    b = math.log(p / (1 - p))
    ll = log_likelihood_constant(b, ys)
    return b, ll


def fit_alignment_model(ys, As):
    """Fit alignment model via coordinate descent. Returns (b, beta, ll)."""
    # Initialize from constant model
    p = sum(ys) / len(ys)
    p = max(EPS, min(1 - EPS, p))
    b = math.log(p / (1 - p))
    beta = 0.0

    lr = 0.01
    for iteration in range(5000):
        # Compute gradients
        grad_b = 0.0
        grad_beta = 0.0
        for y, a in zip(ys, As):
            pred = sigmoid(b + beta * a)
            residual = y - pred
            grad_b += residual
            grad_beta += residual * a

        # Update with gradient ascent (maximizing LL)
        b += lr * grad_b / len(ys)
        beta += lr * grad_beta / len(ys)

        # Adaptive learning rate
        if iteration % 500 == 499:
            lr *= 0.8

    ll = log_likelihood_alignment(b, beta, ys, As)
    return b, beta, ll


def compute_se_constant(b, ys):
    """Standard error of b for constant model via Fisher information."""
    p = sigmoid(b)
    p = max(EPS, min(1 - EPS, p))
    # Fisher info for logistic: n * p * (1-p)
    fisher = len(ys) * p * (1 - p)
    if fisher < EPS:
        return float('nan')
    return 1.0 / math.sqrt(fisher)


def compute_se_alignment(b, beta, ys, As):
    """Standard errors for alignment model via observed Fisher information."""
    # Hessian of log-likelihood
    h_bb = 0.0
    h_bB = 0.0
    h_BB = 0.0
    for y, a in zip(ys, As):
        p = sigmoid(b + beta * a)
        p = max(EPS, min(1 - EPS, p))
        w = p * (1 - p)
        h_bb -= w
        h_bB -= w * a
        h_BB -= w * a * a

    # Invert 2x2 Hessian (-H) to get covariance
    det = h_bb * h_BB - h_bB * h_bB
    if abs(det) < EPS:
        return float('nan'), float('nan')

    # Cov = (-H)^{-1}, but H is already negative
    # -H = [[|h_bb|, |h_bB|], [|h_bB|, |h_BB|]]
    neg_h_bb = -h_bb
    neg_h_bB = -h_bB
    neg_h_BB = -h_BB
    det = neg_h_bb * neg_h_BB - neg_h_bB * neg_h_bB

    if det < EPS:
        return float('nan'), float('nan')

    var_b = neg_h_BB / det
    var_beta = neg_h_bb / det

    se_b = math.sqrt(max(0, var_b))
    se_beta = math.sqrt(max(0, var_beta))
    return se_b, se_beta


def chi2_sf(x, df=1):
    """Survival function for chi-squared distribution (p-value).
    Uses Wilson-Hilferty approximation for df=1."""
    if x <= 0:
        return 1.0
    if df == 1:
        # For chi2 with df=1, p = 2 * (1 - Phi(sqrt(x)))
        z = math.sqrt(x)
        return 2.0 * normal_sf(z)
    return None


def normal_sf(z):
    """Survival function for standard normal (1 - Phi(z)).
    Uses Abramowitz & Stegun approximation 26.2.17."""
    if z < 0:
        return 1.0 - normal_sf(-z)
    # Constants
    b0 = 0.2316419
    b1 = 0.319381530
    b2 = -0.356563782
    b3 = 1.781477937
    b4 = -1.821255978
    b5 = 1.330274429
    t = 1.0 / (1.0 + b0 * z)
    phi = math.exp(-0.5 * z * z) / math.sqrt(2 * math.pi)
    return phi * t * (b1 + t * (b2 + t * (b3 + t * (b4 + t * b5))))


# ── Data Loading ───────────────────────────────────────────────────────────

def find_csv(directory, condition, algo, model):
    """Find the CSV file for a given condition/algo/model combo."""
    pattern = os.path.join(directory, f'{condition}_{algo}_{model}_*.csv')
    matches = glob.glob(pattern)
    if not matches:
        return None
    return sorted(matches)[-1]


def parse_algo_scores(scores_str):
    """Parse algo_scores JSON string into list of (word, score) tuples."""
    if not scores_str or scores_str.strip() == '':
        return []
    try:
        parsed = json.loads(scores_str)
        return [(str(w), float(s)) for w, s in parsed]
    except (json.JSONDecodeError, ValueError, TypeError):
        try:
            fixed = scores_str.replace('""', '"')
            parsed = json.loads(fixed)
            return [(str(w), float(s)) for w, s in parsed]
        except Exception:
            return []


def load_per_turn_data(csv_path, max_turns):
    """Load a CSV and return per-turn records."""
    records = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            game_num = int(row['game_number'])
            for t in range(1, max_turns + 1):
                guess = row.get(f'guess_{t}', '').strip()
                if not guess:
                    break

                followed_str = row.get(f'llm_followed_algo_{t}', '').strip()
                if followed_str.lower() not in ('true', 'false'):
                    continue

                followed = followed_str.lower() == 'true'
                algo_scores = parse_algo_scores(row.get(f'algo_scores_{t}', ''))
                algo_top1 = row.get(f'algo_top1_{t}', '').strip()

                records.append({
                    'game_number': game_num,
                    'turn': t,
                    'guess': guess,
                    'followed': followed,
                    'algo_top1': algo_top1,
                    'algo_scores': algo_scores,
                })
    return records


# ── Alignment Score ────────────────────────────────────────────────────────

def compute_alignment_score(baseline_records, top_k=TOP_K):
    """
    A = 2 * (fraction of baseline turns where LLM guess ∈ algo top-k) - 1
    """
    if not baseline_records:
        return None

    in_topk = 0
    total = 0
    for rec in baseline_records:
        if not rec['algo_scores']:
            continue
        topk_words = {w.upper() for w, _ in rec['algo_scores'][:top_k]}
        if rec['guess'].upper() in topk_words:
            in_topk += 1
        total += 1

    if total == 0:
        return None

    return 2.0 * (in_topk / total) - 1.0


# ── Main ───────────────────────────────────────────────────────────────────

def run_analysis():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Discover models
    all_models = set()
    for domain_key, domain_cfg in DOMAINS.items():
        data_dir = os.path.join(RESULTS_BASE, domain_cfg['dir'])
        for algo in ALGOS:
            pattern = os.path.join(data_dir, f'baseline_{algo}_*_*.csv')
            for fpath in glob.glob(pattern):
                fname = os.path.basename(fpath)
                parts = fname.replace(f'baseline_{algo}_', '', 1)
                model = '_'.join(parts.split('_')[:-2])
                if model not in EXCLUDE_MODELS:
                    all_models.add(model)

    all_models = sorted(all_models)
    print(f"Models: {all_models}\n")

    # Load data and compute alignment scores
    alignment_scores = {}
    informed_data = {}

    for model in all_models:
        for domain_key, domain_cfg in DOMAINS.items():
            data_dir = os.path.join(RESULTS_BASE, domain_cfg['dir'])
            max_turns = domain_cfg['max_turns']

            for algo in ALGOS:
                key = (model, domain_key, algo)

                baseline_csv = find_csv(data_dir, 'baseline', algo, model)
                if baseline_csv is None:
                    continue
                baseline_records = load_per_turn_data(baseline_csv, max_turns)
                A = compute_alignment_score(baseline_records)
                if A is None:
                    continue
                alignment_scores[key] = A

                informed_csv = find_csv(data_dir, 'voi_informed', algo, model)
                if informed_csv is None:
                    continue
                informed_records = load_per_turn_data(informed_csv, max_turns)
                informed_data[key] = informed_records

    # Print alignment scores
    print("=" * 70)
    print("ALIGNMENT SCORES (from baseline condition)")
    print("=" * 70)
    print(f"{'Model':<30} {'Domain':<18} {'Algo':<6} {'A':>8}")
    print("-" * 70)
    for key in sorted(alignment_scores.keys()):
        model, domain, algo = key
        print(f"{model:<30} {domain:<18} {algo:<6} {alignment_scores[key]:>8.4f}")
    print()

    # Per-model fitting
    results = []
    train_games = set(range(1, 51))
    test_games = set(range(51, 101))

    for model in all_models:
        conditions = []
        for domain_key in DOMAINS:
            for algo in ALGOS:
                key = (model, domain_key, algo)
                if key in alignment_scores and key in informed_data:
                    conditions.append(key)

        if not conditions:
            print(f"Skipping {model}: no data")
            continue

        train_y = []
        train_A = []
        test_y = []
        test_A = []

        for key in conditions:
            A = alignment_scores[key]
            for rec in informed_data[key]:
                if rec['game_number'] in train_games:
                    train_y.append(float(rec['followed']))
                    train_A.append(A)
                elif rec['game_number'] in test_games:
                    test_y.append(float(rec['followed']))
                    test_A.append(A)

        if len(train_y) < 10 or len(test_y) < 10:
            print(f"Skipping {model}: insufficient data (train={len(train_y)}, test={len(test_y)})")
            continue

        # Fit on training data
        b_const, ll_const_train = fit_constant_model(train_y)
        b_align, beta, ll_align_train = fit_alignment_model(train_y, train_A)

        # Evaluate on held-out test data
        ll_const_test = log_likelihood_constant(b_const, test_y)
        ll_align_test = log_likelihood_alignment(b_align, beta, test_y, test_A)

        # Likelihood ratio test (training data)
        delta_ll_train = ll_align_train - ll_const_train
        lr_stat = 2 * delta_ll_train
        p_value = chi2_sf(lr_stat, df=1) if lr_stat > 0 else 1.0

        # Held-out improvement
        delta_ll_test = ll_align_test - ll_const_test

        # Standard errors
        se_b_const = compute_se_constant(b_const, train_y)
        se_b_align, se_beta = compute_se_alignment(b_align, beta, train_y, train_A)

        # Follow rates
        train_follow = sum(train_y) / len(train_y)
        test_follow = sum(test_y) / len(test_y)

        unique_A = sorted(set(round(a, 4) for a in train_A))

        results.append({
            'model': model,
            'n_conditions': len(conditions),
            'n_train': len(train_y),
            'n_test': len(test_y),
            'train_follow': train_follow,
            'test_follow': test_follow,
            'b_const': b_const,
            'se_b_const': se_b_const,
            'b_align': b_align,
            'se_b_align': se_b_align,
            'beta': beta,
            'se_beta': se_beta,
            'delta_ll_train': delta_ll_train,
            'delta_ll_test': delta_ll_test,
            'lr_stat': lr_stat,
            'p_value': p_value,
            'unique_A': unique_A,
        })

    # Results table
    print("=" * 120)
    print("HELD-OUT MODEL COMPARISON RESULTS")
    print("=" * 120)
    print(f"{'Model':<30} {'b_c':>7} {'b_a':>7} {'β':>8} {'β SE':>7} "
          f"{'β p':>12} {'ΔLL_train':>10} {'ΔLL_test':>10} {'N_train':>8} {'N_test':>8}")
    print("-" * 120)

    for r in results:
        sig = '***' if r['p_value'] < 0.001 else '**' if r['p_value'] < 0.01 else '*' if r['p_value'] < 0.05 else ''
        print(f"{r['model']:<30} {r['b_const']:>7.3f} {r['b_align']:>7.3f} {r['beta']:>8.3f} "
              f"{r['se_beta']:>7.3f} {r['p_value']:>11.2e} {r['delta_ll_train']:>10.2f} "
              f"{r['delta_ll_test']:>10.2f} {r['n_train']:>8d} {r['n_test']:>8d}  {sig}")

    # Detailed output
    print()
    print("=" * 120)
    print("DETAILED PER-MODEL RESULTS")
    print("=" * 120)

    for r in results:
        b_ci = (r['b_align'] - 1.96 * r['se_b_align'], r['b_align'] + 1.96 * r['se_b_align'])
        beta_ci = (r['beta'] - 1.96 * r['se_beta'], r['beta'] + 1.96 * r['se_beta'])

        print(f"\n--- {r['model']} ---")
        print(f"  Conditions: {r['n_conditions']} (domain × algo)")
        print(f"  Turns: train={r['n_train']}, test={r['n_test']}")
        print(f"  Follow rates: train={r['train_follow']:.3f}, test={r['test_follow']:.3f}")
        print(f"  Alignment scores: {[f'{a:.3f}' for a in r['unique_A']]}")
        print(f"  Constant model: b = {r['b_const']:.4f} (SE={r['se_b_const']:.4f})")
        print(f"  Alignment model: b = {r['b_align']:.4f} (SE={r['se_b_align']:.4f})")
        print(f"                   β = {r['beta']:.4f} (SE={r['se_beta']:.4f})"
              f"  95% CI [{beta_ci[0]:.4f}, {beta_ci[1]:.4f}]")
        print(f"  LR test: χ²={r['lr_stat']:.4f}, p={r['p_value']:.2e}")
        print(f"  ΔLL train: {r['delta_ll_train']:.2f},  ΔLL test: {r['delta_ll_test']:.2f}")

        if r['p_value'] < 0.05 and r['beta'] > 0:
            print(f"  → Significant positive β: alignment-modulated integration")
        elif r['p_value'] < 0.05 and r['beta'] < 0:
            print(f"  → Significant negative β: counter-alignment effect")
        else:
            print(f"  → β not significant: constant-weight model adequate")

    # Regime classification
    print("\n" + "=" * 120)
    print("REGIME CLASSIFICATION")
    print("=" * 120)
    for r in results:
        fr = r['test_follow']
        sig = r['p_value'] < 0.05
        pos = r['beta'] > 0

        if fr > 0.6 and not sig:
            regime = "Integration (high follow, constant)"
        elif sig and pos:
            regime = "Selective Integration (alignment-modulated)"
        elif fr < 0.2:
            regime = "Rejection (low follow)"
        else:
            regime = "Opaque Processing (moderate follow, no alignment effect)"

        print(f"  {r['model']:<30} → {regime}")
        print(f"    follow={fr:.3f}, β={r['beta']:.3f}, p={r['p_value']:.2e}")

    # Save CSV
    csv_path = os.path.join(OUTPUT_DIR, 'alignment_model_comparison.csv')
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'model', 'n_conditions', 'n_train', 'n_test',
            'train_follow_rate', 'test_follow_rate',
            'b_constant', 'b_constant_se',
            'b_alignment', 'b_alignment_se',
            'beta', 'beta_se', 'beta_ci_low', 'beta_ci_high',
            'delta_ll_train', 'delta_ll_test',
            'lr_chi2', 'p_value'
        ])
        for r in results:
            beta_ci = (r['beta'] - 1.96 * r['se_beta'], r['beta'] + 1.96 * r['se_beta'])
            writer.writerow([
                r['model'], r['n_conditions'], r['n_train'], r['n_test'],
                f"{r['train_follow']:.6f}", f"{r['test_follow']:.6f}",
                f"{r['b_const']:.6f}", f"{r['se_b_const']:.6f}",
                f"{r['b_align']:.6f}", f"{r['se_b_align']:.6f}",
                f"{r['beta']:.6f}", f"{r['se_beta']:.6f}",
                f"{beta_ci[0]:.6f}", f"{beta_ci[1]:.6f}",
                f"{r['delta_ll_train']:.6f}", f"{r['delta_ll_test']:.6f}",
                f"{r['lr_stat']:.6f}", f"{r['p_value']:.10f}",
            ])
    print(f"\nResults saved to {csv_path}")

    # Save alignment scores
    align_path = os.path.join(OUTPUT_DIR, 'alignment_scores.csv')
    with open(align_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['model', 'domain', 'algorithm', 'alignment_score'])
        for key in sorted(alignment_scores.keys()):
            model, domain, algo = key
            writer.writerow([model, domain, algo, f"{alignment_scores[key]:.6f}"])
    print(f"Alignment scores saved to {align_path}")


if __name__ == '__main__':
    run_analysis()
