"""
Compute per-turn entropy and information gain for workshop Wordle experiments.

Replays each game from the CSV data, filtering candidates at each step,
and computing:
  - candidates_before: number of valid candidates before each guess
  - candidates_after: number of valid candidates after feedback
  - information_gain: log2(before / after) in bits
  - entropy_before: Shannon entropy = log2(candidates_before)
  - strategy: which agent (LLM or algorithm) made the guess

Goal: Determine the optimal entropy/candidate threshold for LLM-to-algorithm handoff.

Usage:
    python scripts/compute_workshop_entropy.py
    python scripts/compute_workshop_entropy.py --output results/workshop/entropy_analysis.csv
"""

import csv
import math
import os
import glob
import argparse
from collections import defaultdict


def load_wordlist(path="wordlist/wordlist.txt"):
    """Load the full wordlist."""
    words = []
    with open(path, "r") as f:
        for line in f:
            word = line.strip().upper()
            if word and len(word) == 5:
                words.append(word)
    return words


def generate_feedback(target, guess):
    """Generate Wordle feedback for a guess against a target word."""
    feedback = ["-"] * 5
    target_chars = list(target)
    guess_chars = list(guess)

    # Mark greens first
    for i in range(5):
        if guess_chars[i] == target_chars[i]:
            feedback[i] = "G"
            target_chars[i] = None
            guess_chars[i] = None

    # Mark yellows
    for i in range(5):
        if guess_chars[i] and guess_chars[i] in target_chars:
            feedback[i] = "Y"
            target_chars[target_chars.index(guess_chars[i])] = None

    return "".join(feedback)


def filter_candidates(candidates, guess, feedback):
    """Filter candidate list to those consistent with the observed feedback."""
    consistent = []
    for word in candidates:
        if generate_feedback(word, guess) == feedback:
            consistent.append(word)
    return consistent


def replay_game(wordlist, row):
    """Replay a single game and compute entropy metrics per turn.

    Returns a list of dicts, one per guess round.
    """
    candidates = list(wordlist)
    target = row["target_word"].upper()
    rounds = []

    for r in range(1, 7):
        guess_key = f"guess_{r}"
        feedback_key = f"feedback_{r}"
        strategy_key = f"strategy_{r}"

        guess = row.get(guess_key, "").strip().upper()
        feedback = row.get(feedback_key, "").strip()
        strategy = row.get(strategy_key, "").strip()

        if not guess or not feedback:
            break

        candidates_before = len(candidates)
        entropy_before = math.log2(candidates_before) if candidates_before > 1 else 0.0

        # Filter candidates based on this guess + feedback
        candidates = filter_candidates(candidates, guess, feedback)
        candidates_after = len(candidates)

        info_gain = math.log2(candidates_before / candidates_after) if candidates_after > 0 else 0.0
        entropy_after = math.log2(candidates_after) if candidates_after > 1 else 0.0

        rounds.append({
            "round": r,
            "guess": guess,
            "feedback": feedback,
            "strategy": strategy,
            "candidates_before": candidates_before,
            "candidates_after": candidates_after,
            "entropy_before": round(entropy_before, 4),
            "entropy_after": round(entropy_after, 4),
            "information_gain": round(info_gain, 4),
            "is_correct": feedback == "GGGGG",
        })

        if feedback == "GGGGG":
            break

    return rounds


def process_csv(filepath, wordlist):
    """Process a single CSV file and return enriched rows."""
    results = []

    # Extract metadata from path
    parts = filepath.replace("\\", "/").split("/")
    # Find group and config from path
    group = ""
    config = ""
    for i, p in enumerate(parts):
        if p.startswith("group_"):
            group = p
            if i + 1 < len(parts) and parts[i + 1] != "raw_data":
                config = parts[i + 1]
            elif i + 2 < len(parts) and parts[i + 1] == "raw_data":
                # config is one level up
                pass

    # Better config extraction: look for the directory between group_X and raw_data
    try:
        group_idx = parts.index(next(p for p in parts if p.startswith("group_")))
        config = parts[group_idx + 1]
        if config == "raw_data":
            config = "unknown"
    except (StopIteration, IndexError):
        config = "unknown"

    # Extract model from filename
    filename = os.path.basename(filepath)
    model = filename.replace(".csv", "")
    # Remove common prefixes
    for prefix in ["L_to_C_", "L_to_V_", "C_to_L_", "V_to_L_",
                   "L_to_C_alt_", "L_to_C_then_V_", "L_to_V_then_C_",
                   "flexible_hybrid_", "alternating_algorithm_first_",
                   "alternating_llm_first_"]:
        if model.startswith(prefix):
            model = model[len(prefix):]
            break
    # Remove trailing timestamp (e.g., _20260216_125442)
    parts_model = model.rsplit("_", 2)
    if len(parts_model) >= 3 and parts_model[-1].isdigit() and parts_model[-2].isdigit():
        model = "_".join(parts_model[:-2])

    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            game_num = row.get("game_number", "")
            target = row.get("target_word", "").upper()
            won = row.get("won", "").strip()
            attempts = row.get("attempts", "")

            rounds = replay_game(wordlist, row)

            for rd in rounds:
                results.append({
                    "group": group,
                    "config": config,
                    "model": model,
                    "game_number": game_num,
                    "target_word": target,
                    "won": won,
                    "attempts": attempts,
                    **rd,
                })

    return results


def find_workshop_csvs(base_dir="results/workshop"):
    """Find all raw data CSV files in the workshop results."""
    pattern = os.path.join(base_dir, "**", "raw_data", "*.csv")
    return sorted(glob.glob(pattern, recursive=True))


def analyze_handoff_entropy(results):
    """Analyze information gain by strategy and entropy level to find optimal handoff."""

    # Group by strategy and entropy bucket
    buckets = defaultdict(lambda: {"total_gain": 0, "count": 0, "correct": 0})

    for row in results:
        strategy = row["strategy"]
        entropy = row["entropy_before"]
        # Bucket entropy into ranges
        if entropy <= 2:
            bucket = "0-2"
        elif entropy <= 4:
            bucket = "2-4"
        elif entropy <= 6:
            bucket = "4-6"
        elif entropy <= 8:
            bucket = "6-8"
        elif entropy <= 10:
            bucket = "8-10"
        else:
            bucket = "10+"

        key = (strategy, bucket)
        buckets[key]["total_gain"] += row["information_gain"]
        buckets[key]["count"] += 1
        buckets[key]["correct"] += 1 if row["is_correct"] else 0

    # Also compute by round number
    by_round = defaultdict(lambda: {"total_gain": 0, "count": 0, "avg_entropy": 0, "avg_candidates": 0})
    for row in results:
        key = (row["strategy"], row["round"])
        by_round[key]["total_gain"] += row["information_gain"]
        by_round[key]["count"] += 1
        by_round[key]["avg_entropy"] += row["entropy_before"]
        by_round[key]["avg_candidates"] += row["candidates_before"]

    print("\n" + "=" * 80)
    print("ENTROPY ANALYSIS: Information Gain by Strategy and Entropy Level")
    print("=" * 80)

    print(f"\n{'Strategy':<10} {'Entropy Bucket':<15} {'Avg Info Gain':<15} {'Solve Rate':<12} {'Count':<8}")
    print("-" * 60)

    for (strategy, bucket) in sorted(buckets.keys()):
        b = buckets[(strategy, bucket)]
        avg_gain = b["total_gain"] / b["count"] if b["count"] > 0 else 0
        solve_rate = b["correct"] / b["count"] if b["count"] > 0 else 0
        print(f"{strategy:<10} {bucket:<15} {avg_gain:<15.3f} {solve_rate:<12.3f} {b['count']:<8}")

    print(f"\n{'Strategy':<10} {'Round':<8} {'Avg Info Gain':<15} {'Avg Entropy':<14} {'Avg Candidates':<16} {'Count':<8}")
    print("-" * 72)

    for (strategy, rnd) in sorted(by_round.keys()):
        b = by_round[(strategy, rnd)]
        avg_gain = b["total_gain"] / b["count"] if b["count"] > 0 else 0
        avg_ent = b["avg_entropy"] / b["count"] if b["count"] > 0 else 0
        avg_cand = b["avg_candidates"] / b["count"] if b["count"] > 0 else 0
        print(f"{strategy:<10} {rnd:<8} {avg_gain:<15.3f} {avg_ent:<14.3f} {avg_cand:<16.1f} {b['count']:<8}")

    # Handoff analysis: compare LLM vs algorithm at each entropy level
    print("\n" + "=" * 80)
    print("HANDOFF ANALYSIS: LLM vs Algorithm Information Gain by Entropy Level")
    print("=" * 80)

    entropy_buckets = sorted(set(b for (_, b) in buckets.keys()))
    strategies = sorted(set(s for (s, _) in buckets.keys()))

    print(f"\n{'Entropy':<15}", end="")
    for s in strategies:
        print(f"{s + ' gain':<14} {s + ' n':<10}", end="")
    print(f"  {'Better':<10}")
    print("-" * (15 + len(strategies) * 24 + 10))

    for bucket in entropy_buckets:
        print(f"{bucket:<15}", end="")
        gains = {}
        for s in strategies:
            b = buckets.get((s, bucket))
            if b and b["count"] > 0:
                avg = b["total_gain"] / b["count"]
                gains[s] = avg
                print(f"{avg:<14.3f} {b['count']:<10}", end="")
            else:
                print(f"{'N/A':<14} {0:<10}", end="")
        # Determine which is better
        llm_gain = gains.get("LLM", 0)
        css_gain = gains.get("CSS", 0)
        voi_gain = gains.get("VOI", 0)
        algo_gain = max(css_gain, voi_gain)
        if llm_gain > algo_gain and llm_gain > 0:
            print(f"  {'LLM':<10}")
        elif algo_gain > llm_gain and algo_gain > 0:
            best_algo = "CSS" if css_gain >= voi_gain else "VOI"
            print(f"  {best_algo:<10}")
        else:
            print(f"  {'Tie':<10}")

    # Summary by config type
    print("\n" + "=" * 80)
    print("PER-CONFIG ANALYSIS: Average Info Gain by Config and Strategy")
    print("=" * 80)

    by_config = defaultdict(lambda: {"total_gain": 0, "count": 0})
    for row in results:
        key = (row["config"], row["strategy"])
        by_config[key]["total_gain"] += row["information_gain"]
        by_config[key]["count"] += 1

    configs = sorted(set(c for (c, _) in by_config.keys()))
    print(f"\n{'Config':<25}", end="")
    for s in strategies:
        print(f"{s:<14}", end="")
    print()
    print("-" * (25 + len(strategies) * 14))

    for config in configs:
        print(f"{config:<25}", end="")
        for s in strategies:
            b = by_config.get((config, s))
            if b and b["count"] > 0:
                avg = b["total_gain"] / b["count"]
                print(f"{avg:<14.3f}", end="")
            else:
                print(f"{'N/A':<14}", end="")
        print()


def main():
    parser = argparse.ArgumentParser(description="Compute per-turn entropy for workshop Wordle experiments")
    parser.add_argument("--output", default="results/workshop/entropy_analysis.csv",
                        help="Output CSV path")
    parser.add_argument("--workshop-dir", default="results/workshop",
                        help="Workshop results directory")
    parser.add_argument("--wordlist", default="wordlist/wordlist.txt",
                        help="Path to wordlist file")
    args = parser.parse_args()

    print("Loading wordlist...")
    wordlist = load_wordlist(args.wordlist)
    print(f"  Loaded {len(wordlist)} words")

    print(f"\nFinding workshop CSV files in {args.workshop_dir}...")
    csv_files = find_workshop_csvs(args.workshop_dir)
    print(f"  Found {len(csv_files)} CSV files")

    all_results = []
    for i, filepath in enumerate(csv_files):
        rel_path = os.path.relpath(filepath)
        print(f"  [{i+1}/{len(csv_files)}] Processing {rel_path}...")
        try:
            results = process_csv(filepath, wordlist)
            all_results.extend(results)
        except Exception as e:
            print(f"    ERROR: {e}")

    print(f"\nTotal rows: {len(all_results)}")

    # Write output CSV
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    fieldnames = [
        "group", "config", "model", "game_number", "target_word", "won", "attempts",
        "round", "guess", "feedback", "strategy",
        "candidates_before", "candidates_after",
        "entropy_before", "entropy_after", "information_gain", "is_correct",
    ]

    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_results)

    print(f"\nWrote enriched data to {args.output}")

    # Run analysis
    analyze_handoff_entropy(all_results)


if __name__ == "__main__":
    main()
