"""
Counterfactual Analysis for Mastermind: What would the algorithm have done on LLM turns?

Adapted from the Wordle counterfactual analysis. For each LLM turn in the
Mastermind workshop data, this script:
1. Reconstructs the candidate set at that point in the game
2. Asks MastermindCSS and MastermindVOI what they WOULD have guessed
3. Computes the information gain of both the actual LLM guess and the counterfactual
4. Checks if the LLM guess was in the candidate set (belief alignment)
5. Handles INVALID guesses from LLMs

Usage:
    python scripts/mastermind_counterfactual_analysis.py
    python scripts/mastermind_counterfactual_analysis.py --max-files 4
"""

import csv
import math
import os
import sys
import glob
import random
import argparse
import statistics
from itertools import product
from collections import defaultdict

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from algorithms.mastermind_css_strategy import MastermindCSSStrategy
from algorithms.mastermind_voi_strategy import MastermindVOIStrategy


# Mastermind Classic: 6 colors, 4 pegs
COLORS_CLASSIC = "RGBYOW"
NUM_PEGS = 4


def generate_all_codes():
    """Generate all 1,296 possible Mastermind Classic codes."""
    return [''.join(p) for p in product(COLORS_CLASSIC, repeat=NUM_PEGS)]


def generate_feedback(target, guess):
    """Generate (black_pegs, white_pegs) feedback."""
    black_pegs = 0
    white_pegs = 0
    target_chars = list(target)
    guess_chars = list(guess)

    for i in range(NUM_PEGS):
        if guess_chars[i] == target_chars[i]:
            black_pegs += 1
            target_chars[i] = None
            guess_chars[i] = None

    for i in range(NUM_PEGS):
        if guess_chars[i] is not None and guess_chars[i] in target_chars:
            white_pegs += 1
            target_chars[target_chars.index(guess_chars[i])] = None

    return (black_pegs, white_pegs)


def feedback_str_to_tuple(fb_str):
    """Parse feedback string like '2B1W' to (2, 1) tuple."""
    if fb_str == "INVALID" or not fb_str:
        return None
    try:
        black = int(fb_str[0])
        white = int(fb_str[2])
        return (black, white)
    except (ValueError, IndexError):
        return None


def filter_candidates(candidates, guess, feedback_tuple):
    """Filter candidates consistent with observed feedback."""
    return [c for c in candidates if generate_feedback(c, guess) == feedback_tuple]


def compute_info_gain(candidates, guess):
    """Compute information gain (Shannon entropy of feedback partition)."""
    if len(candidates) <= 1:
        return 0.0

    feedback_groups = defaultdict(int)
    for code in candidates:
        fb = generate_feedback(code, guess)
        feedback_groups[fb] += 1

    total = len(candidates)
    entropy = 0.0
    for count in feedback_groups.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)

    return entropy


def is_valid_code(guess):
    """Check if a guess is a valid Mastermind Classic code."""
    if len(guess) != NUM_PEGS:
        return False
    return all(c in COLORS_CLASSIC for c in guess)


def get_css_counterfactual(candidates, history_tuples):
    """Get what Mastermind CSS would have guessed."""
    css = MastermindCSSStrategy(num_pegs=NUM_PEGS)
    for guess, feedback in history_tuples:
        css.knowledge_base[guess] = feedback
    return css.select_guess(candidates, history_tuples)


def get_voi_counterfactual(all_codes, history_tuples):
    """Get what Mastermind VOI would have guessed."""
    voi = MastermindVOIStrategy(num_pegs=NUM_PEGS)

    # Replay from scratch to build belief state
    candidates = list(all_codes)
    voi.initialize_beliefs(candidates)

    for guess, feedback in history_tuples:
        candidates = voi.update_belief(candidates, guess, feedback)

    return voi.select_guess(candidates, history_tuples)


def extract_metadata(filepath):
    """Extract group, config, model from filepath."""
    parts = filepath.replace("\\", "/").split("/")

    group = ""
    config = ""
    for i, p in enumerate(parts):
        if p.startswith("group_"):
            group = p
            if i + 1 < len(parts) and parts[i + 1] != "raw_data":
                config = parts[i + 1]

    filename = os.path.basename(filepath).replace(".csv", "")
    model = filename
    for prefix in ["L_to_C_", "L_to_V_", "C_to_L_", "V_to_L_",
                   "L_to_C_alt_", "L_to_C_then_V_", "L_to_V_then_C_",
                   "flexible_hybrid_", "alt_css_start_", "alt_voi_start_"]:
        if model.startswith(prefix):
            model = model[len(prefix):]
            break
    parts_model = model.rsplit("_", 2)
    if len(parts_model) >= 3 and parts_model[-1].isdigit() and parts_model[-2].isdigit():
        model = "_".join(parts_model[:-2])

    return group, config, model


def process_game(all_codes, row, num_counterfactual_samples=3):
    """Process a single Mastermind game with counterfactual analysis."""
    candidates = list(all_codes)
    target = row["target_code"].upper()
    history_tuples = []  # list of (guess, (black, white)) tuples
    results = []

    for r in range(1, 11):  # Mastermind allows up to 10 rounds
        guess = row.get(f"guess_{r}", "").strip().upper()
        feedback_raw = row.get(f"feedback_{r}", "").strip()
        strategy = row.get(f"strategy_{r}", "").strip()
        candidates_recorded = row.get(f"candidates_{r}", "").strip()

        if not guess or not feedback_raw:
            break

        is_invalid = (feedback_raw == "INVALID")
        feedback_tuple = feedback_str_to_tuple(feedback_raw)
        valid_code = is_valid_code(guess)

        candidates_before = len(candidates)
        entropy_before = math.log2(candidates_before) if candidates_before > 1 else 0.0

        # Compute info gain of actual guess (only if valid)
        actual_info_gain = 0.0
        guess_in_candidates = False
        if valid_code and not is_invalid:
            actual_info_gain = compute_info_gain(candidates, guess)
            guess_in_candidates = guess in candidates

        # Compute counterfactuals for LLM turns
        css_guess = None
        voi_guess = None
        css_info_gain = None
        voi_info_gain = None
        css_agrees = None
        voi_agrees = None

        if strategy == "LLM" and candidates_before > 1:
            # CSS counterfactual
            css_guesses = []
            for _ in range(num_counterfactual_samples):
                try:
                    g = get_css_counterfactual(list(candidates), list(history_tuples))
                    if g:
                        css_guesses.append(g)
                except Exception:
                    pass

            if css_guesses:
                css_guess = max(set(css_guesses), key=css_guesses.count)
                css_info_gain = compute_info_gain(candidates, css_guess)
                css_agrees = (css_guess == guess) if valid_code else False

            # VOI counterfactual
            voi_guesses = []
            for _ in range(num_counterfactual_samples):
                try:
                    g = get_voi_counterfactual(list(all_codes), list(history_tuples))
                    if g:
                        voi_guesses.append(g)
                except Exception:
                    pass

            if voi_guesses:
                voi_guess = max(set(voi_guesses), key=voi_guesses.count)
                voi_info_gain = compute_info_gain(candidates, voi_guess)
                voi_agrees = (voi_guess == guess) if valid_code else False

        # Update candidates for next round (skip if INVALID)
        if feedback_tuple is not None and valid_code:
            candidates = filter_candidates(candidates, guess, feedback_tuple)
            history_tuples.append((guess, feedback_tuple))

        candidates_after = len(candidates)
        is_solved = (feedback_raw == f"{NUM_PEGS}B0W")

        results.append({
            "round": r,
            "strategy": strategy,
            "guess": guess,
            "feedback": feedback_raw,
            "is_invalid": is_invalid,
            "is_valid_code": valid_code,
            "candidates_before": candidates_before,
            "candidates_after": candidates_after,
            "candidates_recorded": candidates_recorded,
            "entropy_before": round(entropy_before, 4),
            "actual_info_gain": round(actual_info_gain, 4),
            "guess_in_candidates": guess_in_candidates,
            "css_counterfactual": css_guess or "",
            "css_info_gain": round(css_info_gain, 4) if css_info_gain is not None else "",
            "css_agrees": css_agrees if css_agrees is not None else "",
            "voi_counterfactual": voi_guess or "",
            "voi_info_gain": round(voi_info_gain, 4) if voi_info_gain is not None else "",
            "voi_agrees": voi_agrees if voi_agrees is not None else "",
            "is_correct": is_solved,
        })

        if is_solved:
            break

    return results


def find_mastermind_csvs(base_dir="results/mastermind/hybrids/classic"):
    """Find all raw data CSV files."""
    pattern = os.path.join(base_dir, "**", "raw_data", "*.csv")
    return sorted(glob.glob(pattern, recursive=True))


def analyze_results(all_results):
    """Print counterfactual analysis."""

    llm_turns = [r for r in all_results if r["strategy"] == "LLM" and r["css_info_gain"] != ""]

    if not llm_turns:
        print("No LLM turns with counterfactual data found.")
        return

    print(f"\n{'=' * 80}")
    print(f"MASTERMIND COUNTERFACTUAL ANALYSIS: LLM vs Algorithm on LLM Turns")
    print(f"{'=' * 80}")
    print(f"\nTotal LLM turns analyzed: {len(llm_turns)}")

    # Count invalid guesses
    invalid_turns = [r for r in all_results if r["strategy"] == "LLM" and r["is_invalid"]]
    valid_llm_turns = [r for r in all_results if r["strategy"] == "LLM" and not r["is_invalid"]]
    print(f"Invalid LLM guesses: {len(invalid_turns)}/{len(invalid_turns) + len(valid_llm_turns)} "
          f"({100 * len(invalid_turns) / (len(invalid_turns) + len(valid_llm_turns)):.1f}%)")

    # 1. Overall info gain comparison
    llm_gains = [r["actual_info_gain"] for r in llm_turns]
    css_gains = [float(r["css_info_gain"]) for r in llm_turns if r["css_info_gain"] != ""]
    voi_gains = [float(r["voi_info_gain"]) for r in llm_turns if r["voi_info_gain"] != ""]

    print(f"\n--- Overall Information Gain (bits) ---")
    print(f"{'Agent':<15} {'Mean':<10} {'Median':<10} {'Std':<10} {'N':<8}")
    print("-" * 53)

    for name, gains in [("LLM (actual)", llm_gains), ("CSS (counter.)", css_gains), ("VOI (counter.)", voi_gains)]:
        if gains:
            mean = statistics.mean(gains)
            median = statistics.median(gains)
            std = statistics.stdev(gains) if len(gains) > 1 else 0
            print(f"{name:<15} {mean:<10.3f} {median:<10.3f} {std:<10.3f} {len(gains):<8}")

    # 2. How often does LLM beat algorithm?
    llm_beats_css = sum(1 for r in llm_turns if r["css_info_gain"] != "" and r["actual_info_gain"] > float(r["css_info_gain"]))
    llm_beats_voi = sum(1 for r in llm_turns if r["voi_info_gain"] != "" and r["actual_info_gain"] > float(r["voi_info_gain"]))
    css_total = sum(1 for r in llm_turns if r["css_info_gain"] != "")
    voi_total = sum(1 for r in llm_turns if r["voi_info_gain"] != "")

    print(f"\n--- How Often Does LLM Provide MORE Information? ---")
    if css_total:
        print(f"LLM > CSS: {llm_beats_css}/{css_total} ({100 * llm_beats_css / css_total:.1f}%)")
    if voi_total:
        print(f"LLM > VOI: {llm_beats_voi}/{voi_total} ({100 * llm_beats_voi / voi_total:.1f}%)")

    # 3. Agreement rate
    css_agree = sum(1 for r in llm_turns if r["css_agrees"] is True)
    voi_agree = sum(1 for r in llm_turns if r["voi_agrees"] is True)

    print(f"\n--- Agreement Rate (Same Guess) ---")
    if css_total:
        print(f"LLM == CSS: {css_agree}/{css_total} ({100 * css_agree / css_total:.1f}%)")
    if voi_total:
        print(f"LLM == VOI: {voi_agree}/{voi_total} ({100 * voi_agree / voi_total:.1f}%)")

    # 4. Belief alignment
    valid_llm_with_cf = [r for r in llm_turns if r["is_valid_code"]]
    in_candidates = sum(1 for r in valid_llm_with_cf if r["guess_in_candidates"])
    print(f"\n--- Belief Alignment ---")
    if valid_llm_with_cf:
        print(f"LLM guess in candidate set: {in_candidates}/{len(valid_llm_with_cf)} "
              f"({100 * in_candidates / len(valid_llm_with_cf):.1f}%)")
        out_of_set = [r for r in valid_llm_with_cf if not r["guess_in_candidates"]]
        in_set = [r for r in valid_llm_with_cf if r["guess_in_candidates"]]
        if in_set:
            print(f"  In-set avg info gain:  {statistics.mean([r['actual_info_gain'] for r in in_set]):.3f} bits")
        if out_of_set:
            print(f"  Out-of-set avg info gain: {statistics.mean([r['actual_info_gain'] for r in out_of_set]):.3f} bits")

    # Invalid guess analysis
    all_llm = [r for r in all_results if r["strategy"] == "LLM"]
    invalid_by_model = defaultdict(lambda: {"invalid": 0, "total": 0})
    for r in all_results:
        if r["strategy"] == "LLM":
            invalid_by_model[r.get("model", "unknown")]["total"] += 1
            if r["is_invalid"]:
                invalid_by_model[r.get("model", "unknown")]["invalid"] += 1

    if any(v["invalid"] > 0 for v in invalid_by_model.values()):
        print(f"\n--- Invalid Guess Rate by Model ---")
        print(f"{'Model':<35} {'Invalid':<10} {'Total':<10} {'Rate':<10}")
        print("-" * 65)
        for model in sorted(invalid_by_model.keys()):
            v = invalid_by_model[model]
            rate = 100 * v["invalid"] / v["total"] if v["total"] > 0 else 0
            print(f"{model:<35} {v['invalid']:<10} {v['total']:<10} {rate:<10.1f}%")

    # 5. Breakdown by entropy level
    print(f"\n--- Info Gain Comparison by Entropy Level ---")
    print(f"{'Entropy':<12} {'LLM gain':<12} {'CSS gain':<12} {'VOI gain':<12} {'LLM>CSS':<10} {'LLM>VOI':<10} {'N':<6}")
    print("-" * 74)

    for lo, hi, label in [(0, 2, "0-2"), (2, 4, "2-4"), (4, 6, "4-6"),
                           (6, 8, "6-8"), (8, 10, "8-10"), (10, 20, "10+")]:
        bucket = [r for r in llm_turns if lo <= r["entropy_before"] < hi]
        if not bucket:
            continue

        llm_avg = statistics.mean([r["actual_info_gain"] for r in bucket])
        css_bucket = [r for r in bucket if r["css_info_gain"] != ""]
        voi_bucket = [r for r in bucket if r["voi_info_gain"] != ""]
        css_avg = statistics.mean([float(r["css_info_gain"]) for r in css_bucket]) if css_bucket else 0
        voi_avg = statistics.mean([float(r["voi_info_gain"]) for r in voi_bucket]) if voi_bucket else 0

        llm_gt_css = sum(1 for r in css_bucket if r["actual_info_gain"] > float(r["css_info_gain"]))
        llm_gt_voi = sum(1 for r in voi_bucket if r["actual_info_gain"] > float(r["voi_info_gain"]))
        css_pct = f"{100 * llm_gt_css / len(css_bucket):.0f}%" if css_bucket else "N/A"
        voi_pct = f"{100 * llm_gt_voi / len(voi_bucket):.0f}%" if voi_bucket else "N/A"

        print(f"{label:<12} {llm_avg:<12.3f} {css_avg:<12.3f} {voi_avg:<12.3f} {css_pct:<10} {voi_pct:<10} {len(bucket):<6}")

    # 6. Per-config breakdown
    print(f"\n--- Info Gain by Config (Handoff Direction) ---")
    print(f"{'Config':<25} {'LLM gain':<12} {'CSS gain':<12} {'VOI gain':<12} {'LLM>Algo':<10} {'N':<6}")
    print("-" * 77)

    by_config = defaultdict(list)
    for r in all_results:
        by_config[r.get("config", "unknown")].append(r)

    for config in sorted(by_config.keys()):
        config_llm = [r for r in by_config[config]
                      if r["strategy"] == "LLM" and (r["css_info_gain"] != "" or r["voi_info_gain"] != "")]
        if not config_llm:
            continue

        llm_avg = statistics.mean([r["actual_info_gain"] for r in config_llm])
        css_vals = [float(r["css_info_gain"]) for r in config_llm if r["css_info_gain"] != ""]
        voi_vals = [float(r["voi_info_gain"]) for r in config_llm if r["voi_info_gain"] != ""]
        css_avg = statistics.mean(css_vals) if css_vals else 0
        voi_avg = statistics.mean(voi_vals) if voi_vals else 0

        llm_better = sum(1 for r in config_llm
                         if (r["css_info_gain"] != "" and r["actual_info_gain"] > float(r["css_info_gain"])) or
                            (r["voi_info_gain"] != "" and r["actual_info_gain"] > float(r["voi_info_gain"])))
        pct = f"{100 * llm_better / len(config_llm):.0f}%"
        print(f"{config:<25} {llm_avg:<12.3f} {css_avg:<12.3f} {voi_avg:<12.3f} {pct:<10} {len(config_llm):<6}")

    # 7. Comparison with Wordle results
    print(f"\n{'=' * 80}")
    print(f"SUMMARY: Key Metrics for Cross-Domain Comparison")
    print(f"{'=' * 80}")

    total_agree = css_agree + voi_agree
    total_compared = css_total + voi_total
    agree_rate = total_agree / total_compared if total_compared > 0 else 0

    avg_llm = statistics.mean(llm_gains)
    avg_css = statistics.mean(css_gains) if css_gains else 0
    avg_voi = statistics.mean(voi_gains) if voi_gains else 0
    avg_algo = max(avg_css, avg_voi)
    gap = avg_algo - avg_llm

    print(f"\n{'Metric':<35} {'Mastermind':<15} {'Wordle*':<15}")
    print("-" * 65)
    print(f"{'Agreement rate':<35} {agree_rate:.1%}{'':<10} {'12.8%':<15}")
    print(f"{'Belief alignment':<35} {100 * in_candidates / len(valid_llm_with_cf):.1f}%{'':<10} {'95.4%':<15}" if valid_llm_with_cf else "")
    print(f"{'LLM avg info gain':<35} {avg_llm:.3f}{'':<10} {'3.157':<15}")
    print(f"{'Best algo avg info gain':<35} {avg_algo:.3f}{'':<10} {'3.810':<15}")
    print(f"{'Algo advantage':<35} {gap:.3f} bits{'':<6} {'0.653 bits':<15}")
    print(f"{'LLM beats algo':<35} {100 * llm_beats_css / css_total:.1f}%{'':<10} {'1.5%':<15}" if css_total else "")
    print(f"\n* Wordle values from prior analysis for comparison")


def main():
    parser = argparse.ArgumentParser(description="Mastermind counterfactual analysis")
    parser.add_argument("--output", default="results/mastermind/counterfactual_analysis.csv",
                        help="Output CSV path")
    parser.add_argument("--mastermind-dir", default="results/mastermind/hybrids/classic",
                        help="Mastermind results directory")
    parser.add_argument("--samples", type=int, default=3,
                        help="Number of counterfactual samples per turn")
    parser.add_argument("--max-files", type=int, default=0,
                        help="Max CSV files to process (0 = all)")
    args = parser.parse_args()

    random.seed(42)

    print("Generating all Mastermind Classic codes...")
    all_codes = generate_all_codes()
    print(f"  Generated {len(all_codes)} codes")

    print(f"\nFinding Mastermind CSV files...")
    csv_files = find_mastermind_csvs(args.mastermind_dir)
    if args.max_files > 0:
        csv_files = csv_files[:args.max_files]
    print(f"  Processing {len(csv_files)} CSV files")

    all_results = []
    for i, filepath in enumerate(csv_files):
        group, config, model = extract_metadata(filepath)
        print(f"  [{i + 1}/{len(csv_files)}] {config}/{model}...")

        try:
            with open(filepath, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    game_results = process_game(all_codes, row, args.samples)
                    for rd in game_results:
                        rd["group"] = group
                        rd["config"] = config
                        rd["model"] = model
                        rd["game_number"] = row.get("game_number", "")
                        rd["target_code"] = row.get("target_code", "").upper()
                        rd["won"] = row.get("won", "")
                        rd["attempts"] = row.get("attempts", "")
                    all_results.extend(game_results)
        except Exception as e:
            print(f"    ERROR: {e}")

    print(f"\nTotal rows: {len(all_results)}")

    # Write output
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    fieldnames = [
        "group", "config", "model", "game_number", "target_code", "won", "attempts",
        "round", "strategy", "guess", "feedback", "is_invalid", "is_valid_code",
        "candidates_before", "candidates_after", "candidates_recorded", "entropy_before",
        "actual_info_gain", "guess_in_candidates",
        "css_counterfactual", "css_info_gain", "css_agrees",
        "voi_counterfactual", "voi_info_gain", "voi_agrees",
        "is_correct",
    ]

    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_results)

    print(f"Wrote data to {args.output}")

    analyze_results(all_results)


if __name__ == "__main__":
    main()
