#!/usr/bin/env python3
"""
Workshop Extension — Statistical Analysis (Paper 2)

1. Two-way ANOVA: handoff direction x domain on win rate / attempts
2. Dose-response analysis: k algo rounds before LLM handoff
3. Per-model breakdown with effect sizes
4. Search space regression analysis

Usage:
    python scripts/workshop_extension_anova.py
"""

import csv
import sys
import os
import math
from pathlib import Path
from collections import defaultdict
from itertools import product

import numpy as np
from scipy import stats as sp_stats

PROJECT_ROOT = Path(__file__).parent.parent
ANALYSIS_DIR = PROJECT_ROOT / "results" / "analysis"


def load_handoff_csv(filepath: Path) -> list:
    """Load a handoff analysis CSV."""
    rows = []
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["won"] = row["won"] == "True"
            row["attempts"] = int(row["attempts"])
            row["candidates_at_handoff"] = int(row["candidates_at_handoff"])
            row["log_candidates"] = float(row["log_candidates"])
            row["handoff_turn"] = int(row["handoff_turn"])
            row["invalid_after_handoff"] = int(row["invalid_after_handoff"])
            rows.append(row)
    return rows


def cohens_d(group1, group2):
    """Compute Cohen's d effect size."""
    n1, n2 = len(group1), len(group2)
    if n1 < 2 or n2 < 2:
        return float("nan")
    var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
    pooled_std = math.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
    if pooled_std == 0:
        return 0.0
    return (np.mean(group1) - np.mean(group2)) / pooled_std


def print_header(title):
    print(f"\n{'=' * 90}")
    print(title)
    print(f"{'=' * 90}")


# ============================================================
# 1. ANOVA: Direction x Domain
# ============================================================

def direction_anova(all_data):
    """Two-way analysis: handoff direction x domain on win rate and attempts."""
    print_header("1. HANDOFF DIRECTION EFFECT (LLM-first vs Algo-first)")

    for domain in ["wordle", "mastermind", "mastermind_extended"]:
        a2l = [r for r in all_data if r["domain"] == domain and r["direction"] == "algo_to_llm"]
        l2a = [r for r in all_data if r["domain"] == domain and r["direction"] == "llm_to_algo"]

        if not a2l or not l2a:
            continue

        a2l_wins = [1 if r["won"] else 0 for r in a2l]
        l2a_wins = [1 if r["won"] else 0 for r in l2a]
        a2l_att = [r["attempts"] for r in a2l]
        l2a_att = [r["attempts"] for r in l2a]

        print(f"\n  {domain.upper()}")
        print(f"  {'':>25} {'Algo→LLM':>12} {'LLM→Algo':>12} {'Diff':>10} {'p-value':>10} {'Cohen d':>10}")
        print(f"  {'-' * 80}")

        # Win rate comparison (chi-square)
        a2l_win_n = sum(a2l_wins)
        l2a_win_n = sum(l2a_wins)
        a2l_total = len(a2l_wins)
        l2a_total = len(l2a_wins)

        # Use chi-square test for win rates
        contingency = np.array([[a2l_win_n, a2l_total - a2l_win_n],
                                 [l2a_win_n, l2a_total - l2a_win_n]])
        if contingency.min() > 0:
            chi2, p_win, _, _ = sp_stats.chi2_contingency(contingency)
        else:
            chi2, p_win = 0, 1.0

        a2l_wr = np.mean(a2l_wins) * 100
        l2a_wr = np.mean(l2a_wins) * 100
        d_win = cohens_d(a2l_wins, l2a_wins)
        print(f"  {'Win rate (%)':>25} {a2l_wr:>11.1f}% {l2a_wr:>11.1f}% {l2a_wr - a2l_wr:>+9.1f}pp {p_win:>10.4f} {d_win:>10.3f}")

        # Attempts comparison (t-test)
        t_att, p_att = sp_stats.ttest_ind(a2l_att, l2a_att, equal_var=False)
        d_att = cohens_d(a2l_att, l2a_att)
        print(f"  {'Avg attempts':>25} {np.mean(a2l_att):>12.2f} {np.mean(l2a_att):>12.2f} {np.mean(l2a_att) - np.mean(a2l_att):>+10.2f} {p_att:>10.4f} {d_att:>10.3f}")

        # Invalid guesses
        a2l_inv = [r["invalid_after_handoff"] for r in a2l]
        l2a_inv = [r["invalid_after_handoff"] for r in l2a]
        t_inv, p_inv = sp_stats.ttest_ind(a2l_inv, l2a_inv, equal_var=False)
        d_inv = cohens_d(a2l_inv, l2a_inv)
        print(f"  {'Avg invalid guesses':>25} {np.mean(a2l_inv):>12.2f} {np.mean(l2a_inv):>12.2f} {np.mean(l2a_inv) - np.mean(a2l_inv):>+10.2f} {p_inv:>10.4f} {d_inv:>10.3f}")

        print(f"  {'N games':>25} {len(a2l):>12} {len(l2a):>12}")

    # Cross-domain comparison: is the direction effect larger in Mastermind?
    print(f"\n  CROSS-DOMAIN COMPARISON")
    for domain in ["wordle", "mastermind", "mastermind_extended"]:
        a2l = [r for r in all_data if r["domain"] == domain and r["direction"] == "algo_to_llm"]
        l2a = [r for r in all_data if r["domain"] == domain and r["direction"] == "llm_to_algo"]
        if a2l and l2a:
            diff = np.mean([1 if r["won"] else 0 for r in l2a]) * 100 - np.mean([1 if r["won"] else 0 for r in a2l]) * 100
            print(f"  {domain:>15}: LLM-first advantage = {diff:+.1f} pp")


# ============================================================
# 2. DOSE-RESPONSE: k algo rounds before LLM handoff
# ============================================================

def dose_response_analysis(all_data):
    """Analyze dose-response: more algo rounds before LLM = worse performance."""
    print_header("2. DOSE-RESPONSE: k ALGORITHM ROUNDS BEFORE LLM HANDOFF")

    for domain in ["wordle", "mastermind", "mastermind_extended"]:
        # Only algo→LLM configs with numbered rounds: css1_to_L, css2_to_L, css3_to_L, etc.
        a2l = [r for r in all_data if r["domain"] == domain and r["direction"] == "algo_to_llm"]

        # Group by config to get dose levels
        by_config = defaultdict(list)
        for r in a2l:
            by_config[r["config"]].append(r)

        # Extract dose level from config name
        css_doses = {}
        voi_doses = {}
        for config, games in by_config.items():
            if config.startswith("css") and "_to_L" in config:
                k = int(config.replace("css", "").replace("_to_L", ""))
                css_doses[k] = games
            elif config.startswith("voi") and "_to_L" in config:
                k = int(config.replace("voi", "").replace("_to_L", ""))
                voi_doses[k] = games
            elif config == "C_to_L":
                css_doses[99] = games  # full algo-first
            elif config == "V_to_L":
                voi_doses[99] = games

        for algo_name, doses in [("CSS", css_doses), ("VOI", voi_doses)]:
            if len(doses) < 2:
                continue

            print(f"\n  {domain.upper()} — {algo_name} Dose-Response")
            print(f"  {'k rounds':>10} {'N':>6} {'Win%':>8} {'Avg Att':>10} {'Avg SearchSpace':>16} {'Avg Invalid':>12}")
            print(f"  {'-' * 65}")

            sorted_k = sorted(k for k in doses.keys() if k != 99)
            if 99 in doses:
                sorted_k.append(99)

            win_rates_by_k = []
            att_by_k = []

            for k in sorted_k:
                games = doses[k]
                n = len(games)
                wr = np.mean([1 if g["won"] else 0 for g in games]) * 100
                att = np.mean([g["attempts"] for g in games])
                cand = np.mean([g["candidates_at_handoff"] for g in games])
                inv = np.mean([g["invalid_after_handoff"] for g in games])
                label = f"k={k}" if k != 99 else "full"
                print(f"  {label:>10} {n:>6} {wr:>7.1f}% {att:>10.2f} {cand:>16.1f} {inv:>12.2f}")

                win_rates_by_k.append([1 if g["won"] else 0 for g in games])
                att_by_k.append([g["attempts"] for g in games])

            # One-way ANOVA across dose levels
            if len(win_rates_by_k) >= 2:
                # Kruskal-Wallis for win rates (binary outcome)
                H, p_kw = sp_stats.kruskal(*win_rates_by_k)
                print(f"\n  Kruskal-Wallis (win rate): H={H:.3f}, p={p_kw:.4f}")

                # One-way ANOVA for attempts
                F, p_anova = sp_stats.f_oneway(*att_by_k)
                print(f"  One-way ANOVA (attempts):  F={F:.3f}, p={p_anova:.4f}")

                # Trend test: Jonckheere-Terpstra (via Spearman on dose level)
                all_doses_flat = []
                all_wins_flat = []
                for i, k in enumerate(sorted_k):
                    for g in doses[k]:
                        all_doses_flat.append(i)
                        all_wins_flat.append(1 if g["won"] else 0)
                rho, p_trend = sp_stats.spearmanr(all_doses_flat, all_wins_flat)
                print(f"  Spearman trend (dose→win): rho={rho:.4f}, p={p_trend:.4f}")


# ============================================================
# 3. PER-MODEL BREAKDOWN
# ============================================================

def per_model_analysis(all_data):
    """Per-model performance comparison across handoff directions."""
    print_header("3. PER-MODEL ANALYSIS: HANDOFF DIRECTION EFFECT")

    for domain in ["wordle", "mastermind", "mastermind_extended"]:
        data = [r for r in all_data if r["domain"] == domain]
        if not data:
            continue

        # Get unique models (exclude noise)
        models = sorted(set(r["model"] for r in data if r["model"] not in ("unknown", "model", "cot", "voi", "voi_cot")))

        print(f"\n  {domain.upper()}")
        print(f"  {'Model':<35} {'A→L Win%':>10} {'L→A Win%':>10} {'Diff':>8} {'A→L Att':>8} {'L→A Att':>8} {'p(win)':>8}")
        print(f"  {'-' * 95}")

        for model in models:
            a2l = [r for r in data if r["model"] == model and r["direction"] == "algo_to_llm"]
            l2a = [r for r in data if r["model"] == model and r["direction"] == "llm_to_algo"]

            if not a2l or not l2a:
                continue

            a2l_wr = np.mean([1 if r["won"] else 0 for r in a2l]) * 100
            l2a_wr = np.mean([1 if r["won"] else 0 for r in l2a]) * 100

            a2l_att = np.mean([r["attempts"] for r in a2l])
            l2a_att = np.mean([r["attempts"] for r in l2a])

            # Fisher's exact or chi-square for win rate difference
            a2l_w = sum(1 for r in a2l if r["won"])
            l2a_w = sum(1 for r in l2a if r["won"])
            contingency = np.array([[a2l_w, len(a2l) - a2l_w],
                                     [l2a_w, len(l2a) - l2a_w]])
            try:
                if contingency.min() == 0 or contingency.max() < 5:
                    _, p = sp_stats.fisher_exact(contingency)
                else:
                    _, p, _, _ = sp_stats.chi2_contingency(contingency)
            except Exception:
                p = 1.0

            sig = "*" if p < 0.05 else " "
            sig = "**" if p < 0.01 else sig
            sig = "***" if p < 0.001 else sig

            print(f"  {model:<35} {a2l_wr:>9.1f}% {l2a_wr:>9.1f}% {l2a_wr - a2l_wr:>+7.1f}pp {a2l_att:>8.2f} {l2a_att:>8.2f} {p:>7.4f} {sig}")


# ============================================================
# 4. SEARCH SPACE REGRESSION
# ============================================================

def search_space_regression(all_data):
    """Logistic and linear regression of search space on performance."""
    print_header("4. SEARCH SPACE SIZE → PERFORMANCE REGRESSION")

    for domain in ["wordle", "mastermind", "mastermind_extended"]:
        a2l = [r for r in all_data if r["domain"] == domain and r["direction"] == "algo_to_llm"]
        l2a = [r for r in all_data if r["domain"] == domain and r["direction"] == "llm_to_algo"]

        for direction, data in [("Algo→LLM", a2l), ("LLM→Algo", l2a)]:
            if len(data) < 10:
                continue

            log_cand = np.array([r["log_candidates"] for r in data])
            wins = np.array([1 if r["won"] else 0 for r in data])
            attempts = np.array([r["attempts"] for r in data])

            print(f"\n  {domain.upper()} — {direction} (N={len(data)})")

            # Pearson: log_candidates vs attempts
            r_att, p_att = sp_stats.pearsonr(log_cand, attempts)
            print(f"    log2(candidates) vs attempts:  r={r_att:.4f}, p={p_att:.6f}")

            # Point-biserial: log_candidates vs win
            if len(set(wins)) > 1:
                r_win, p_win = sp_stats.pointbiserialr(wins, log_cand)
                print(f"    log2(candidates) vs win:       r={r_win:.4f}, p={p_win:.6f}")
            else:
                print(f"    log2(candidates) vs win:       all {'wins' if wins[0] == 1 else 'losses'}")

            # Linear regression: attempts = a + b * log2(candidates)
            slope, intercept, r_value, p_value, std_err = sp_stats.linregress(log_cand, attempts)
            print(f"    Linear: attempts = {intercept:.2f} + {slope:.3f} * log2(cand)  (R²={r_value**2:.4f}, p={p_value:.6f})")


# ============================================================
# 5. ALGORITHM INVARIANCE TEST
# ============================================================

def algorithm_invariance_test(all_data):
    """Test the claim that algorithms are invariant to inherited search space size."""
    print_header("5. ALGORITHM INVARIANCE TO INHERITED STATE")

    for domain in ["wordle", "mastermind", "mastermind_extended"]:
        l2a = [r for r in all_data if r["domain"] == domain and r["direction"] == "llm_to_algo"]
        if not l2a:
            continue

        log_cand = np.array([r["log_candidates"] for r in l2a])
        wins = np.array([1 if r["won"] else 0 for r in l2a])
        attempts = np.array([r["attempts"] for r in l2a])

        print(f"\n  {domain.upper()} — LLM→Algo (N={len(l2a)})")
        print(f"    Win rate: {np.mean(wins)*100:.1f}%")
        print(f"    Avg attempts: {np.mean(attempts):.2f}")

        # Test: does search space size affect algo performance?
        r_att, p_att = sp_stats.pearsonr(log_cand, attempts)
        print(f"    log2(candidates) vs attempts: r={r_att:.4f}, p={p_att:.6f}")

        if len(set(wins)) > 1:
            r_win, p_win = sp_stats.pointbiserialr(wins, log_cand)
            print(f"    log2(candidates) vs win:      r={r_win:.4f}, p={p_win:.6f}")
        else:
            print(f"    log2(candidates) vs win:      ALL {'won' if wins[0] == 1 else 'lost'} — algorithm perfectly invariant")

        # Bucket comparison for algo
        small = [r for r in l2a if r["log_candidates"] <= 5]
        large = [r for r in l2a if r["log_candidates"] > 8]
        if small and large:
            small_wr = np.mean([1 if r["won"] else 0 for r in small]) * 100
            large_wr = np.mean([1 if r["won"] else 0 for r in large]) * 100
            small_att = np.mean([r["attempts"] for r in small])
            large_att = np.mean([r["attempts"] for r in large])
            print(f"    Small search space (≤32 cand):  win={small_wr:.1f}%, att={small_att:.2f} (N={len(small)})")
            print(f"    Large search space (>256 cand): win={large_wr:.1f}%, att={large_att:.2f} (N={len(large)})")


# ============================================================
# SUMMARY TABLE (LaTeX-ready)
# ============================================================

def summary_table(all_data):
    """Print a LaTeX-ready summary table."""
    print_header("6. SUMMARY TABLE (for paper)")

    print(f"\n  {'Domain':<12} {'Direction':<12} {'N':>6} {'Win%':>8} {'Att':>6} {'Invalid':>8} {'Entropy':>8}")
    print(f"  {'-' * 65}")

    for domain in ["wordle", "mastermind", "mastermind_extended"]:
        for direction in ["algo_to_llm", "llm_to_algo"]:
            data = [r for r in all_data if r["domain"] == domain and r["direction"] == direction]
            if not data:
                continue
            n = len(data)
            wr = np.mean([1 if r["won"] else 0 for r in data]) * 100
            att = np.mean([r["attempts"] for r in data])
            inv = np.mean([r["invalid_after_handoff"] for r in data])
            ent = np.mean([r["log_candidates"] for r in data])
            dir_label = "Algo→LLM" if direction == "algo_to_llm" else "LLM→Algo"
            print(f"  {domain:<12} {dir_label:<12} {n:>6} {wr:>7.1f}% {att:>6.2f} {inv:>8.2f} {ent:>7.1f}b")


# ============================================================
# Main
# ============================================================

def main():
    print("=" * 90)
    print("PAPER 2: WORKSHOP EXTENSION — STATISTICAL ANALYSIS")
    print("Cross-Domain Validation of State Ownership Effect")
    print("=" * 90)

    # Load all data
    all_data = []
    for filename in [
        "handoff_wordle_algo_to_llm.csv",
        "handoff_wordle_llm_to_algo.csv",
        "handoff_mastermind_algo_to_llm.csv",
        "handoff_mastermind_llm_to_algo.csv",
        "handoff_mastermind_extended_algo_to_llm.csv",
        "handoff_mastermind_extended_llm_to_algo.csv",
    ]:
        filepath = ANALYSIS_DIR / filename
        if filepath.exists():
            rows = load_handoff_csv(filepath)
            print(f"  Loaded {len(rows):>6} rows from {filename}")
            all_data.extend(rows)

    print(f"\n  Total: {len(all_data)} handoff observations")

    # Run all analyses
    summary_table(all_data)
    direction_anova(all_data)
    dose_response_analysis(all_data)
    per_model_analysis(all_data)
    search_space_regression(all_data)
    algorithm_invariance_test(all_data)

    print(f"\n{'=' * 90}")
    print("ANALYSIS COMPLETE")
    print(f"{'=' * 90}")


if __name__ == "__main__":
    main()
