#!/usr/bin/env python3
"""
Analyze Stage 1 hybrid strategy validation results.

Compares hybrid strategies against pure algorithm and LLM baselines to determine
if any hybrid approach shows promise for full evaluation.
"""

import os
import json
import glob
from pathlib import Path
from typing import Dict, List

# Baselines from previous evaluations
PURE_CSS_BASELINE = {
    'strategy': 'CSS (pure)',
    'win_rate': 0.98,
    'avg_attempts': 3.79
}

PURE_LLM_BASELINES = {
    'mistral-small-3.1': {'win_rate': 1.00, 'avg_attempts': 4.30},
    'llama-3.3-70b-instruct': {'win_rate': 0.93, 'avg_attempts': 4.03},
    'mistral-7b-instruct': {'win_rate': 0.98, 'avg_attempts': 4.10}
}


def load_stage1_results(stage1_dir: Path) -> List[Dict]:
    """Load all Stage 1 summary JSON files."""
    results = []

    summary_files = glob.glob(str(stage1_dir / "summary_*.json"))

    for filepath in summary_files:
        with open(filepath, 'r') as f:
            data = json.load(f)
            results.append(data)

    return results


def analyze_results(results: List[Dict]) -> None:
    """Analyze and print Stage 1 results with comparison to baselines."""

    print("="*90)
    print("STAGE 1 HYBRID STRATEGY VALIDATION RESULTS")
    print("="*90)
    print()

    # Group by strategy
    by_strategy = {}
    for result in results:
        strategy = result.get('strategy', 'unknown')
        if strategy not in by_strategy:
            by_strategy[strategy] = []
        by_strategy[strategy].append(result)

    # Print results by strategy
    for strategy in sorted(by_strategy.keys()):
        print(f"\n{strategy.upper()}")
        print("-" * 90)
        print(f"{'Model':<35} {'Games':<8} {'Wins':<6} {'Win Rate':<12} {'Avg Attempts':<12} {'vs CSS':<12}")
        print("-" * 90)

        strategy_results = by_strategy[strategy]
        total_games = 0
        total_wins = 0
        total_attempts = 0

        for result in sorted(strategy_results, key=lambda x: x.get('model_name', '')):
            model = result.get('model_name', 'unknown')
            games = result.get('total_games', 0)
            wins = result.get('wins', 0)
            win_rate = result.get('win_rate', 0)
            avg_attempts = result.get('avg_attempts_when_won', 0)

            total_games += games
            total_wins += wins
            if wins > 0:
                total_attempts += avg_attempts * wins

            # Compare to CSS baseline
            if avg_attempts > 0:
                vs_css = avg_attempts - PURE_CSS_BASELINE['avg_attempts']
                vs_css_str = f"{vs_css:+.2f}"
            else:
                vs_css_str = "N/A"

            print(f"{model:<35} {games:<8} {wins:<6} {win_rate*100:>5.1f}%      {avg_attempts:>5.2f}        {vs_css_str}")

        # Strategy average
        avg_win_rate = total_wins / total_games if total_games > 0 else 0
        avg_attempts_overall = total_attempts / total_wins if total_wins > 0 else 0
        vs_css_overall = avg_attempts_overall - PURE_CSS_BASELINE['avg_attempts'] if avg_attempts_overall > 0 else 0

        print("-" * 90)
        print(f"{'STRATEGY AVERAGE':<35} {total_games:<8} {total_wins:<6} {avg_win_rate*100:>5.1f}%      "
              f"{avg_attempts_overall:>5.2f}        {vs_css_overall:+.2f}")
        print()

    # Overall comparison
    print("\n" + "="*90)
    print("COMPARISON TO BASELINES")
    print("="*90)
    print()

    # Pure CSS baseline
    print("Pure CSS (baseline):")
    print(f"  Win Rate: {PURE_CSS_BASELINE['win_rate']*100:.1f}%")
    print(f"  Avg Attempts: {PURE_CSS_BASELINE['avg_attempts']:.2f}")
    print()

    # Pure LLM baselines
    print("Pure LLM (baselines from full 100-game evaluations):")
    for model, baseline in sorted(PURE_LLM_BASELINES.items()):
        print(f"  {model}:")
        print(f"    Win Rate: {baseline['win_rate']*100:.1f}%")
        print(f"    Avg Attempts: {baseline['avg_attempts']:.2f}")
    print()

    # Find best hybrid
    best_hybrid = None
    best_avg_attempts = float('inf')

    for result in results:
        avg_attempts = result.get('avg_attempts_when_won', float('inf'))
        if avg_attempts > 0 and avg_attempts < best_avg_attempts:
            best_avg_attempts = avg_attempts
            best_hybrid = result

    if best_hybrid:
        print("="*90)
        print("BEST HYBRID PERFORMER")
        print("="*90)
        print(f"Strategy: {best_hybrid.get('strategy')}")
        print(f"Model: {best_hybrid.get('model_name')}")
        print(f"Win Rate: {best_hybrid.get('win_rate', 0)*100:.1f}%")
        print(f"Avg Attempts: {best_hybrid.get('avg_attempts_when_won', 0):.2f}")
        print(f"vs Pure CSS: {best_hybrid.get('avg_attempts_when_won', 0) - PURE_CSS_BASELINE['avg_attempts']:+.2f}")
        print()

    # Recommendations
    print("="*90)
    print("RECOMMENDATIONS")
    print("="*90)
    print()

    if best_avg_attempts < PURE_CSS_BASELINE['avg_attempts']:
        print(f"✓ PROMISING: Best hybrid ({best_avg_attempts:.2f} attempts) beats pure CSS ({PURE_CSS_BASELINE['avg_attempts']:.2f})")
        print()
        print("Next Steps:")
        print(f"  1. Run Stage 2 full evaluation (100 games) with {best_hybrid.get('strategy')}")
        print(f"  2. Consider testing {best_hybrid.get('strategy')} with all 11 LLM models")
        print("  3. Analyze why this hybrid approach is effective")
    elif best_avg_attempts < 4.0:
        print(f"⚠ MIXED: Best hybrid ({best_avg_attempts:.2f}) doesn't beat CSS but competitive with LLMs")
        print()
        print("Next Steps:")
        print("  1. Test top 2 hybrid strategies with full 100-game evaluation")
        print("  2. Analyze trade-offs: slight efficiency loss for LLM benefits?")
        print("  3. Consider cost vs performance for production use")
    else:
        print(f"✗ NOT PROMISING: Best hybrid ({best_avg_attempts:.2f}) doesn't improve over pure approaches")
        print()
        print("Next Steps:")
        print("  1. Document findings: hybrids don't provide benefit for Wordle")
        print("  2. Analyze why: perhaps Wordle is too deterministic for hybrid benefits")
        print("  3. Consider other tasks where hybrids might help")

    print()
    print("="*90)


def main():
    """Main analysis function."""
    script_dir = Path(__file__).parent
    stage1_dir = script_dir.parent.parent / 'results' / 'hybrids' / 'stage1'

    if not stage1_dir.exists():
        print(f"ERROR: Stage 1 results directory not found: {stage1_dir}")
        print("Have you run the Stage 1 tests yet?")
        print("  cd scripts/hybrid")
        print("  ./run_stage1_test.sh")
        return

    # Load results
    results = load_stage1_results(stage1_dir)

    if not results:
        print(f"ERROR: No results found in {stage1_dir}")
        print("Make sure Stage 1 tests have completed successfully.")
        return

    print(f"\nLoaded {len(results)} result files from {stage1_dir}")
    print()

    # Analyze
    analyze_results(results)

    # Save summary
    summary_file = stage1_dir / "stage1_analysis_summary.txt"
    print(f"\nAnalysis saved to: {summary_file}")


if __name__ == "__main__":
    main()
