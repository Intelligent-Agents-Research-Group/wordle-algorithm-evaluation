"""
Counterfactual Analysis: What would the algorithm have done on LLM turns?

For each LLM turn in the workshop data, this script:
1. Reconstructs the candidate set at that point in the game
2. Asks CSS and VOI what they WOULD have guessed
3. Computes the information gain of both the actual LLM guess and the counterfactual algorithm guess
4. Checks if the LLM guess was in the candidate set (belief alignment)

This directly addresses the reviewer critique about "not true integration" by measuring
whether LLM and algorithm choices are complementary or redundant.

Usage:
    python scripts/counterfactual_analysis.py
"""

import csv
import math
import os
import sys
import glob
import random
import argparse
from collections import defaultdict

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from algorithms.css_strategy import CSSStrategy
from algorithms.voi_strategy import VOIStrategy


def load_wordlist(path="wordlist/wordlist.txt"):
    """Load the full wordlist."""
    words = []
    with open(path, "r") as f:
        for line in f:
            word = line.strip().upper()
            if word and len(word) == 5:
                words.append(word)
    return words


def generate_feedback_str(target, guess):
    """Generate Wordle feedback as a string (e.g., 'GY--G')."""
    feedback = ["-"] * 5
    target_chars = list(target)
    guess_chars = list(guess)

    for i in range(5):
        if guess_chars[i] == target_chars[i]:
            feedback[i] = "G"
            target_chars[i] = None
            guess_chars[i] = None

    for i in range(5):
        if guess_chars[i] and guess_chars[i] in target_chars:
            feedback[i] = "Y"
            target_chars[target_chars.index(guess_chars[i])] = None

    return "".join(feedback)


def filter_candidates(candidates, guess, feedback_str):
    """Filter candidates consistent with observed feedback."""
    return [w for w in candidates if generate_feedback_str(w, guess) == feedback_str]


def compute_info_gain(candidates, guess):
    """Compute information gain of a guess against a candidate set."""
    if len(candidates) <= 1:
        return 0.0

    # Group candidates by the feedback they would produce
    feedback_groups = defaultdict(int)
    for word in candidates:
        fb = generate_feedback_str(word, guess)
        feedback_groups[fb] += 1

    # Shannon entropy of the partition
    total = len(candidates)
    entropy = 0.0
    for count in feedback_groups.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)

    return entropy


def get_css_counterfactual(candidates, history):
    """Get what CSS would have guessed given the current candidates and history."""
    css = CSSStrategy()
    # Rebuild knowledge base from history
    for guess, feedback_list in history:
        css.knowledge_base[guess] = feedback_list
    return css.select_guess(candidates, history)


def get_voi_counterfactual(candidates, history):
    """Get what VOI would have guessed given the current candidates and history."""
    voi = VOIStrategy()
    voi.initialize_beliefs(candidates)

    # Replay history to update beliefs
    current_candidates = candidates
    for guess, feedback_list in history:
        voi.update_belief(current_candidates, guess, feedback_list)
        current_candidates = [w for w in current_candidates
                              if generate_feedback_str(w, guess) == "".join(feedback_list)]

    return voi.select_guess(current_candidates, history)


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

    # Extract model from filename
    filename = os.path.basename(filepath).replace(".csv", "")
    # Remove known prefixes and trailing timestamps
    model = filename
    for prefix in ["L_to_C_", "L_to_V_", "C_to_L_", "V_to_L_",
                   "L_to_C_alt_", "L_to_C_then_V_", "L_to_V_then_C_",
                   "flexible_hybrid_", "alternating_algorithm_first_",
                   "alternating_llm_first_"]:
        if model.startswith(prefix):
            model = model[len(prefix):]
            break
    parts_model = model.rsplit("_", 2)
    if len(parts_model) >= 3 and parts_model[-1].isdigit() and parts_model[-2].isdigit():
        model = "_".join(parts_model[:-2])

    return group, config, model


def process_game(wordlist, row, num_counterfactual_samples=5):
    """Process a single game, computing counterfactuals for LLM turns.

    Runs CSS/VOI multiple times (they sample internally) and takes the
    most common choice for stability.
    """
    candidates = list(wordlist)
    target = row["target_word"].upper()
    history = []  # list of (guess, feedback_list) tuples
    results = []

    for r in range(1, 7):
        guess = row.get(f"guess_{r}", "").strip().upper()
        feedback_str = row.get(f"feedback_{r}", "").strip()
        strategy = row.get(f"strategy_{r}", "").strip()

        if not guess or not feedback_str:
            break

        candidates_before = len(candidates)
        entropy_before = math.log2(candidates_before) if candidates_before > 1 else 0.0

        # Compute info gain of the actual guess
        actual_info_gain = compute_info_gain(candidates, guess)

        # Check belief alignment: is the LLM guess in the candidate set?
        guess_in_candidates = guess in candidates

        # Compute counterfactuals for LLM turns
        css_guess = None
        voi_guess = None
        css_info_gain = None
        voi_info_gain = None
        css_agrees = None
        voi_agrees = None

        if strategy == "LLM" and candidates_before > 1:
            # Run CSS multiple times for stability
            css_guesses = []
            for _ in range(num_counterfactual_samples):
                try:
                    g = get_css_counterfactual(list(candidates), list(history))
                    if g:
                        css_guesses.append(g)
                except Exception:
                    pass

            if css_guesses:
                # Take most common
                css_guess = max(set(css_guesses), key=css_guesses.count)
                css_info_gain = compute_info_gain(candidates, css_guess)
                css_agrees = (css_guess == guess)

            # Run VOI multiple times for stability
            voi_guesses = []
            for _ in range(num_counterfactual_samples):
                try:
                    g = get_voi_counterfactual(list(wordlist), list(history))
                    if g:
                        voi_guesses.append(g)
                except Exception:
                    pass

            if voi_guesses:
                voi_guess = max(set(voi_guesses), key=voi_guesses.count)
                voi_info_gain = compute_info_gain(candidates, voi_guess)
                voi_agrees = (voi_guess == guess)

        # Update candidates for next round
        feedback_list = list(feedback_str)
        candidates = filter_candidates(candidates, guess, feedback_str)
        candidates_after = len(candidates)

        history.append((guess, feedback_list))

        results.append({
            "round": r,
            "strategy": strategy,
            "guess": guess,
            "feedback": feedback_str,
            "candidates_before": candidates_before,
            "candidates_after": candidates_after,
            "entropy_before": round(entropy_before, 4),
            "actual_info_gain": round(actual_info_gain, 4),
            "guess_in_candidates": guess_in_candidates,
            "css_counterfactual": css_guess or "",
            "css_info_gain": round(css_info_gain, 4) if css_info_gain is not None else "",
            "css_agrees": css_agrees if css_agrees is not None else "",
            "voi_counterfactual": voi_guess or "",
            "voi_info_gain": round(voi_info_gain, 4) if voi_info_gain is not None else "",
            "voi_agrees": voi_agrees if voi_agrees is not None else "",
            "is_correct": feedback_str == "GGGGG",
        })

        if feedback_str == "GGGGG":
            break

    return results


def find_workshop_csvs(base_dir="results/workshop"):
    """Find all raw data CSV files."""
    pattern = os.path.join(base_dir, "**", "raw_data", "*.csv")
    return sorted(glob.glob(pattern, recursive=True))


def analyze_results(all_results):
    """Print analysis of counterfactual results."""

    # Filter to LLM turns with counterfactual data
    llm_turns = [r for r in all_results if r["strategy"] == "LLM" and r["css_info_gain"] != ""]

    if not llm_turns:
        print("No LLM turns with counterfactual data found.")
        return

    print(f"\n{'=' * 80}")
    print(f"COUNTERFACTUAL ANALYSIS: LLM vs Algorithm on LLM Turns")
    print(f"{'=' * 80}")
    print(f"\nTotal LLM turns analyzed: {len(llm_turns)}")

    # 1. Overall info gain comparison
    llm_gains = [r["actual_info_gain"] for r in llm_turns]
    css_gains = [float(r["css_info_gain"]) for r in llm_turns if r["css_info_gain"] != ""]
    voi_gains = [float(r["voi_info_gain"]) for r in llm_turns if r["voi_info_gain"] != ""]

    print(f"\n--- Overall Information Gain (bits) ---")
    print(f"{'Agent':<15} {'Mean':<10} {'Median':<10} {'Std':<10} {'N':<8}")
    print("-" * 53)

    import statistics
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
    print(f"LLM > CSS: {llm_beats_css}/{css_total} ({100*llm_beats_css/css_total:.1f}%)" if css_total else "")
    print(f"LLM > VOI: {llm_beats_voi}/{voi_total} ({100*llm_beats_voi/voi_total:.1f}%)" if voi_total else "")

    # 3. Agreement rate
    css_agree = sum(1 for r in llm_turns if r["css_agrees"] == True)
    voi_agree = sum(1 for r in llm_turns if r["voi_agrees"] == True)

    print(f"\n--- Agreement Rate (Same Guess) ---")
    print(f"LLM == CSS: {css_agree}/{css_total} ({100*css_agree/css_total:.1f}%)" if css_total else "")
    print(f"LLM == VOI: {voi_agree}/{voi_total} ({100*voi_agree/voi_total:.1f}%)" if voi_total else "")

    # 4. Belief alignment: is LLM guess in candidate set?
    in_candidates = sum(1 for r in llm_turns if r["guess_in_candidates"])
    print(f"\n--- Belief Alignment ---")
    print(f"LLM guess in candidate set: {in_candidates}/{len(llm_turns)} ({100*in_candidates/len(llm_turns):.1f}%)")
    out_of_set = [r for r in llm_turns if not r["guess_in_candidates"]]
    if out_of_set:
        out_gains = [r["actual_info_gain"] for r in out_of_set]
        in_gains = [r["actual_info_gain"] for r in llm_turns if r["guess_in_candidates"]]
        print(f"  In-set avg info gain:  {statistics.mean(in_gains):.3f} bits")
        print(f"  Out-of-set avg info gain: {statistics.mean(out_gains):.3f} bits")

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
        css_pct = f"{100*llm_gt_css/len(css_bucket):.0f}%" if css_bucket else "N/A"
        voi_pct = f"{100*llm_gt_voi/len(voi_bucket):.0f}%" if voi_bucket else "N/A"

        print(f"{label:<12} {llm_avg:<12.3f} {css_avg:<12.3f} {voi_avg:<12.3f} {css_pct:<10} {voi_pct:<10} {len(bucket):<6}")

    # 6. Breakdown by config (handoff direction)
    print(f"\n--- Info Gain by Config (Handoff Direction) ---")
    print(f"{'Config':<25} {'LLM gain':<12} {'CSS gain':<12} {'VOI gain':<12} {'LLM>Algo':<10} {'N':<6}")
    print("-" * 77)

    by_config = defaultdict(list)
    for r in all_results:
        by_config[r["config"]].append(r)

    for config in sorted(by_config.keys()):
        config_llm = [r for r in by_config[config] if r["strategy"] == "LLM" and r["css_info_gain"] != ""]
        if not config_llm:
            # Try VOI counterfactual
            config_llm = [r for r in by_config[config] if r["strategy"] == "LLM" and r["voi_info_gain"] != ""]
        if not config_llm:
            continue

        llm_avg = statistics.mean([r["actual_info_gain"] for r in config_llm])

        css_vals = [float(r["css_info_gain"]) for r in config_llm if r["css_info_gain"] != ""]
        voi_vals = [float(r["voi_info_gain"]) for r in config_llm if r["voi_info_gain"] != ""]
        css_avg = statistics.mean(css_vals) if css_vals else 0
        voi_avg = statistics.mean(voi_vals) if voi_vals else 0

        best_algo = max(css_avg, voi_avg)
        llm_better = sum(1 for r in config_llm
                         if (r["css_info_gain"] != "" and r["actual_info_gain"] > float(r["css_info_gain"])) or
                            (r["voi_info_gain"] != "" and r["actual_info_gain"] > float(r["voi_info_gain"])))
        pct = f"{100*llm_better/len(config_llm):.0f}%"

        print(f"{config:<25} {llm_avg:<12.3f} {css_avg:<12.3f} {voi_avg:<12.3f} {pct:<10} {len(config_llm):<6}")

    # 7. Key finding: complementary vs redundant
    print(f"\n{'=' * 80}")
    print(f"KEY FINDING: Are LLM and Algorithm choices complementary or redundant?")
    print(f"{'=' * 80}")

    total_agree = css_agree + voi_agree
    total_compared = css_total + voi_total
    agree_rate = total_agree / total_compared if total_compared > 0 else 0

    if agree_rate < 0.05:
        print(f"\nAgreement rate: {agree_rate:.1%} — HIGHLY COMPLEMENTARY")
        print("LLM and algorithms almost never choose the same guess.")
        print("This suggests the alternation produces genuinely different search behavior,")
        print("not just a worse version of the algorithm.")
    elif agree_rate < 0.20:
        print(f"\nAgreement rate: {agree_rate:.1%} — MOSTLY COMPLEMENTARY")
        print("LLM and algorithms occasionally agree but mostly explore differently.")
    else:
        print(f"\nAgreement rate: {agree_rate:.1%} — PARTIALLY REDUNDANT")
        print("LLM often chooses the same word the algorithm would have.")

    avg_llm = statistics.mean(llm_gains)
    avg_css = statistics.mean(css_gains) if css_gains else 0
    avg_voi = statistics.mean(voi_gains) if voi_gains else 0
    avg_algo = max(avg_css, avg_voi)
    gap = avg_algo - avg_llm

    print(f"\nInfo gain gap: Algorithm gets {gap:.3f} more bits/turn on average")
    if gap > 0.5:
        print("→ LLM is measurably less efficient, but if choices differ, it may")
        print("  still contribute unique information the algorithm would miss.")
    elif gap > 0:
        print("→ Small gap — LLM is nearly as efficient as the algorithm.")


def main():
    parser = argparse.ArgumentParser(description="Counterfactual analysis of LLM vs algorithm choices")
    parser.add_argument("--output", default="results/workshop/counterfactual_analysis.csv",
                        help="Output CSV path")
    parser.add_argument("--workshop-dir", default="results/workshop",
                        help="Workshop results directory")
    parser.add_argument("--wordlist", default="wordlist/wordlist.txt",
                        help="Path to wordlist")
    parser.add_argument("--samples", type=int, default=5,
                        help="Number of counterfactual samples per turn (for stability)")
    parser.add_argument("--max-files", type=int, default=0,
                        help="Max CSV files to process (0 = all)")
    args = parser.parse_args()

    random.seed(42)

    print("Loading wordlist...")
    wordlist = load_wordlist(args.wordlist)
    print(f"  Loaded {len(wordlist)} words")

    print(f"\nFinding workshop CSV files...")
    csv_files = find_workshop_csvs(args.workshop_dir)
    if args.max_files > 0:
        csv_files = csv_files[:args.max_files]
    print(f"  Processing {len(csv_files)} CSV files")

    all_results = []
    for i, filepath in enumerate(csv_files):
        group, config, model = extract_metadata(filepath)
        rel_path = os.path.relpath(filepath)
        print(f"  [{i+1}/{len(csv_files)}] {config}/{model}...")

        try:
            with open(filepath, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    game_results = process_game(wordlist, row, args.samples)
                    for rd in game_results:
                        rd["group"] = group
                        rd["config"] = config
                        rd["model"] = model
                        rd["game_number"] = row.get("game_number", "")
                        rd["target_word"] = row.get("target_word", "").upper()
                        rd["won"] = row.get("won", "")
                        rd["attempts"] = row.get("attempts", "")
                    all_results.extend(game_results)
        except Exception as e:
            print(f"    ERROR: {e}")

    print(f"\nTotal rows: {len(all_results)}")

    # Write output
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    fieldnames = [
        "group", "config", "model", "game_number", "target_word", "won", "attempts",
        "round", "strategy", "guess", "feedback",
        "candidates_before", "candidates_after", "entropy_before",
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
