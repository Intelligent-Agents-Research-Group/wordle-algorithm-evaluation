#!/usr/bin/env python3
"""
Workshop Extension Figures (Paper 2)

Generates:
  1. Dose-response: win rate by k algo rounds before LLM handoff
  2. Per-model handoff direction effect (Wordle + Mastermind)

Usage:
    python scripts/plot_workshop_extension_figures.py
"""

import csv
import sys
import math
from pathlib import Path
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent
ANALYSIS_DIR = PROJECT_ROOT / "results" / "analysis"
FIGURES_DIR = PROJECT_ROOT / "figures"
FIGURES_DIR.mkdir(exist_ok=True)


def load_handoff_csv(filepath: Path) -> list:
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


def load_all_data():
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
            all_data.extend(load_handoff_csv(filepath))
    return all_data


# ============================================================
# Figure 1: Dose-Response
# ============================================================

def plot_dose_response(all_data):
    """6-panel figure: CSS/VOI x Wordle/Mastermind Classic/Mastermind Extended dose-response."""
    fig, axes = plt.subplots(3, 2, figsize=(12, 13))

    configs = [
        ("wordle", "CSS", axes[0, 0]),
        ("wordle", "VOI", axes[0, 1]),
        ("mastermind", "CSS", axes[1, 0]),
        ("mastermind", "VOI", axes[1, 1]),
        ("mastermind_extended", "CSS", axes[2, 0]),
        ("mastermind_extended", "VOI", axes[2, 1]),
    ]

    for domain, algo, ax in configs:
        a2l = [r for r in all_data if r["domain"] == domain and r["direction"] == "algo_to_llm"]

        by_config = defaultdict(list)
        for r in a2l:
            by_config[r["config"]].append(r)

        doses = {}
        prefix = algo.lower()
        for config, games in by_config.items():
            if config.startswith(prefix) and "_to_L" in config:
                k_str = config.replace(prefix, "").replace("_to_L", "")
                if k_str.isdigit():
                    doses[int(k_str)] = games

        if not doses:
            ax.set_visible(False)
            continue

        sorted_k = sorted(doses.keys())
        win_rates = []
        avg_attempts = []
        ns = []
        ci_low = []
        ci_high = []

        for k in sorted_k:
            games = doses[k]
            wins = [1 if g["won"] else 0 for g in games]
            wr = np.mean(wins)
            win_rates.append(wr * 100)
            avg_attempts.append(np.mean([g["attempts"] for g in games]))
            ns.append(len(games))
            # 95% CI for proportion
            se = math.sqrt(wr * (1 - wr) / len(games))
            ci_low.append((wr - 1.96 * se) * 100)
            ci_high.append((wr + 1.96 * se) * 100)

        x = np.arange(len(sorted_k))
        bars = ax.bar(x, win_rates, width=0.6, color=["#e74c3c", "#f39c12", "#2ecc71"],
                       edgecolor="black", linewidth=0.5, alpha=0.85)

        # Error bars
        for i, (lo, hi, wr) in enumerate(zip(ci_low, ci_high, win_rates)):
            ax.plot([i, i], [lo, hi], color="black", linewidth=1.5)

        # Value labels
        for i, (wr, n) in enumerate(zip(win_rates, ns)):
            ax.text(i, wr + 1.5, f"{wr:.1f}%", ha="center", fontsize=10, fontweight="bold")
            ax.text(i, wr - 3, f"n={n}", ha="center", fontsize=8, color="white", fontweight="bold")

        ax.set_xticks(x)
        ax.set_xticklabels([f"k={k}" for k in sorted_k])
        ax.set_xlabel("Algorithm Rounds Before LLM Handoff", fontsize=10)
        ax.set_ylabel("Win Rate (%)", fontsize=10)
        domain_label = {"wordle": "Wordle", "mastermind": "Mastermind Classic", "mastermind_extended": "Mastermind Extended"}
        ax.set_title(f"{domain_label.get(domain, domain)} — {algo}", fontsize=12, fontweight="bold")

        # Set y-axis to highlight differences
        min_wr = min(win_rates)
        ax.set_ylim(max(0, min_wr - 8), 102)
        ax.axhline(y=100, color="gray", linestyle="--", alpha=0.3)

    fig.suptitle("Dose-Response: LLM Performance After k Algorithm Rounds", fontsize=14, fontweight="bold", y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.95])

    for ext in ["pdf", "png"]:
        fig.savefig(FIGURES_DIR / f"dose_response_k_handoff.{ext}", dpi=300, bbox_inches="tight")
    print(f"  Saved dose_response_k_handoff.pdf/png")
    plt.close(fig)


# ============================================================
# Figure 2: Per-Model Direction Effect
# ============================================================

def plot_per_model_direction(all_data):
    """3-panel figure: per-model win rate by direction (Wordle | Classic | Extended)."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    skip_models = {"unknown", "model", "cot", "voi", "voi_cot"}
    domain_labels = {"wordle": "Wordle", "mastermind": "Mastermind Classic", "mastermind_extended": "Mastermind Extended"}

    for idx, (domain, ax) in enumerate(zip(["wordle", "mastermind", "mastermind_extended"], axes)):
        data = [r for r in all_data if r["domain"] == domain]
        models = sorted(set(r["model"] for r in data if r["model"] not in skip_models))

        model_labels = []
        a2l_rates = []
        l2a_rates = []

        for model in models:
            a2l = [r for r in data if r["model"] == model and r["direction"] == "algo_to_llm"]
            l2a = [r for r in data if r["model"] == model and r["direction"] == "llm_to_algo"]
            if not a2l or not l2a:
                continue

            a2l_wr = np.mean([1 if r["won"] else 0 for r in a2l]) * 100
            l2a_wr = np.mean([1 if r["won"] else 0 for r in l2a]) * 100

            # Shorten model names
            short = model.replace("-instruct", "").replace("granite-3.3-", "granite-").replace("llama-3.1-", "llama3.1-").replace("llama-3.3-", "llama3.3-").replace("gemma-3-", "gemma-").replace("mistral-7b", "mistral-7b").replace("codestral-", "codestral-")
            model_labels.append(short)
            a2l_rates.append(a2l_wr)
            l2a_rates.append(l2a_wr)

        y = np.arange(len(model_labels))
        height = 0.35

        bars_a2l = ax.barh(y - height/2, a2l_rates, height, label="Algo→LLM", color="#e74c3c", alpha=0.85, edgecolor="black", linewidth=0.5)
        bars_l2a = ax.barh(y + height/2, l2a_rates, height, label="LLM→Algo", color="#2ecc71", alpha=0.85, edgecolor="black", linewidth=0.5)

        # Value labels
        for bar in bars_a2l:
            w = bar.get_width()
            ax.text(w + 0.3, bar.get_y() + bar.get_height()/2, f"{w:.1f}%", va="center", fontsize=8)
        for bar in bars_l2a:
            w = bar.get_width()
            ax.text(w + 0.3, bar.get_y() + bar.get_height()/2, f"{w:.1f}%", va="center", fontsize=8)

        ax.set_yticks(y)
        ax.set_yticklabels(model_labels, fontsize=9)
        ax.set_xlabel("Win Rate (%)", fontsize=10)
        ax.set_title(f"{domain_labels.get(domain, domain)}", fontsize=12, fontweight="bold")
        ax.legend(fontsize=9, loc="lower right" if domain == "mastermind" else "lower left")

        # Set x-axis to show differences
        min_rate = min(min(a2l_rates), min(l2a_rates))
        ax.set_xlim(max(0, min_rate - 5), 103)
        ax.axvline(x=100, color="gray", linestyle="--", alpha=0.3)

    fig.suptitle("Per-Model Performance by Handoff Direction", fontsize=14, fontweight="bold", y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.95])

    for ext in ["pdf", "png"]:
        fig.savefig(FIGURES_DIR / f"per_model_direction_effect.{ext}", dpi=300, bbox_inches="tight")
    print(f"  Saved per_model_direction_effect.pdf/png")
    plt.close(fig)


# ============================================================
# Main
# ============================================================

def main():
    print("Generating Paper 2 figures...")
    all_data = load_all_data()
    print(f"  Loaded {len(all_data)} observations")

    plot_dose_response(all_data)
    plot_per_model_direction(all_data)

    print("\nAll figures saved to figures/")


if __name__ == "__main__":
    main()
