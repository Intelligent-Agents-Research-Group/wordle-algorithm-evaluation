#!/usr/bin/env python3
"""
Figure: Performance vs Inherited Search Space Size

Two-panel figure (Wordle | Mastermind) showing:
  - Line 1 (Algo→LLM): LLM performance degrades with larger inherited search space
  - Line 2 (LLM→Algo): Algorithm performance stays flat regardless of inherited space

Demonstrates the core asymmetry that motivates the coordination strategy.
"""

import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent
ANALYSIS_DIR = PROJECT_ROOT / 'results' / 'analysis'


def load_csv(filepath):
    rows = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def bucket_data(rows, bucket_edges, bucket_labels):
    """Bucket rows by candidates_at_handoff and compute metrics."""
    buckets = defaultdict(list)
    for row in rows:
        c = int(row['candidates_at_handoff'])
        for j in range(len(bucket_edges) - 1):
            if bucket_edges[j] < c <= bucket_edges[j + 1]:
                buckets[bucket_labels[j]].append(row)
                break

    results = []
    for label in bucket_labels:
        entries = buckets.get(label, [])
        if not entries:
            results.append(None)
            continue
        n = len(entries)
        win_rate = sum(1 for e in entries if e['won'] == 'True') / n * 100
        avg_att = np.mean([int(e['attempts']) for e in entries])
        results.append({
            'label': label,
            'n': n,
            'win_rate': win_rate,
            'avg_attempts': avg_att,
        })
    return results


def plot_figure():
    # --- Load data ---
    mm_a2l = load_csv(ANALYSIS_DIR / 'handoff_mastermind_algo_to_llm.csv')
    mm_l2a = load_csv(ANALYSIS_DIR / 'handoff_mastermind_llm_to_algo.csv')
    w_a2l = load_csv(ANALYSIS_DIR / 'handoff_wordle_algo_to_llm.csv')
    w_l2a = load_csv(ANALYSIS_DIR / 'handoff_wordle_llm_to_algo.csv')

    # Extended Mastermind
    mm_ext_a2l_path = ANALYSIS_DIR / 'handoff_mastermind_extended_algo_to_llm.csv'
    mm_ext_l2a_path = ANALYSIS_DIR / 'handoff_mastermind_extended_llm_to_algo.csv'
    mm_ext_a2l = load_csv(mm_ext_a2l_path) if mm_ext_a2l_path.exists() else []
    mm_ext_l2a = load_csv(mm_ext_l2a_path) if mm_ext_l2a_path.exists() else []

    # --- Define buckets per domain ---
    w_edges = [0, 10, 50, 200, 500, 1000]
    w_labels = ['1–10', '11–50', '51–200', '201–500', '501–1000']

    mm_edges = [0, 10, 50, 100, 300, 500]
    mm_labels = ['1–10', '11–50', '51–100', '101–300', '301–500']

    mm_ext_edges = [0, 10, 50, 100, 300, 500, 1000]
    mm_ext_labels = ['1–10', '11–50', '51–100', '101–300', '301–500', '501–1000']

    # --- Bucket the data ---
    w_a2l_buckets = bucket_data(w_a2l, w_edges, w_labels)
    w_l2a_buckets = bucket_data(w_l2a, w_edges, w_labels)
    mm_a2l_buckets = bucket_data(mm_a2l, mm_edges, mm_labels)
    mm_l2a_buckets = bucket_data(mm_l2a, mm_edges, mm_labels)
    mm_ext_a2l_buckets = bucket_data(mm_ext_a2l, mm_ext_edges, mm_ext_labels)
    mm_ext_l2a_buckets = bucket_data(mm_ext_l2a, mm_ext_edges, mm_ext_labels)

    # --- Create figure ---
    n_panels = 3 if mm_ext_a2l else 2
    fig, axes = plt.subplots(1, n_panels, figsize=(7 * n_panels, 5.5), sharey=False)
    if n_panels == 2:
        axes = list(axes)
    fig.suptitle('Reasoning Performance vs. Inherited Search Space Size',
                 fontsize=15, fontweight='bold', y=0.98)

    # Colors
    color_a2l = '#d62728'   # red - LLM inherits (degraded)
    color_l2a = '#2ca02c'   # green - algo inherits (robust)

    marker_a2l = 's'
    marker_l2a = 'o'

    panel_configs = [
        (axes[0], w_a2l_buckets, w_l2a_buckets, w_labels, 'Wordle'),
        (axes[1], mm_a2l_buckets, mm_l2a_buckets, mm_labels, 'Mastermind Classic'),
    ]
    if n_panels == 3:
        panel_configs.append(
            (axes[2], mm_ext_a2l_buckets, mm_ext_l2a_buckets, mm_ext_labels, 'Mastermind Extended')
        )

    for ax_idx, (ax, a2l_buckets, l2a_buckets, labels, domain_name) in enumerate(panel_configs):
        x = np.arange(len(labels))

        # Extract values (skip None buckets)
        a2l_att = []
        a2l_x = []
        a2l_n = []
        for i, b in enumerate(a2l_buckets):
            if b is not None and b['n'] >= 10:
                a2l_att.append(b['avg_attempts'])
                a2l_x.append(i)
                a2l_n.append(b['n'])

        l2a_att = []
        l2a_x = []
        l2a_n = []
        for i, b in enumerate(l2a_buckets):
            if b is not None and b['n'] >= 10:
                l2a_att.append(b['avg_attempts'])
                l2a_x.append(i)
                l2a_n.append(b['n'])

        # Plot lines
        ax.plot(a2l_x, a2l_att, color=color_a2l, marker=marker_a2l,
                markersize=8, linewidth=2.5, label='Algo → LLM  (LLM inherits)',
                zorder=3)
        ax.plot(l2a_x, l2a_att, color=color_l2a, marker=marker_l2a,
                markersize=8, linewidth=2.5, label='LLM → Algo  (Algo inherits)',
                zorder=3)

        # Add sample sizes as subtle annotations
        for xi, yi, ni in zip(a2l_x, a2l_att, a2l_n):
            ax.annotate(f'n={ni}', (xi, yi), textcoords="offset points",
                        xytext=(0, 10), fontsize=7, color=color_a2l,
                        ha='center', alpha=0.7)
        for xi, yi, ni in zip(l2a_x, l2a_att, l2a_n):
            ax.annotate(f'n={ni}', (xi, yi), textcoords="offset points",
                        xytext=(0, -15), fontsize=7, color=color_l2a,
                        ha='center', alpha=0.7)

        # Formatting
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=10)
        ax.set_xlabel('Remaining Candidates at Handoff', fontsize=12)
        ax.set_ylabel('Average Attempts', fontsize=12)
        ax.set_title(domain_name, fontsize=13, fontweight='bold')
        ax.legend(fontsize=10, loc='upper left')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        # Shade the gap region
        if a2l_x and l2a_x:
            # Find overlapping x range
            common_x = sorted(set(a2l_x) & set(l2a_x))
            if common_x:
                a2l_dict = dict(zip(a2l_x, a2l_att))
                l2a_dict = dict(zip(l2a_x, l2a_att))
                fill_x = common_x
                fill_a2l = [a2l_dict[xi] for xi in fill_x]
                fill_l2a = [l2a_dict[xi] for xi in fill_x]
                ax.fill_between(fill_x, fill_l2a, fill_a2l,
                                alpha=0.1, color='gray',
                                label='_nolegend_')

    fig.tight_layout(rect=[0, 0.02, 1, 0.94])

    # Add caption below
    fig.text(0.5, -0.02,
             'LLM performance degrades when inheriting algorithm-generated reasoning states,\n'
             'while classical solvers remain robust regardless of inherited state. '
             'Shaded region indicates the performance gap.',
             ha='center', fontsize=10, style='italic', color='#555555')

    # Save
    out_dir = PROJECT_ROOT / 'figures'
    out_dir.mkdir(parents=True, exist_ok=True)

    fig.savefig(out_dir / 'search_space_performance.pdf',
                bbox_inches='tight', dpi=300)
    fig.savefig(out_dir / 'search_space_performance.png',
                bbox_inches='tight', dpi=300)

    print(f"Saved to:")
    print(f"  {out_dir / 'search_space_performance.pdf'}")
    print(f"  {out_dir / 'search_space_performance.png'}")

    plt.close(fig)


if __name__ == "__main__":
    plot_figure()
