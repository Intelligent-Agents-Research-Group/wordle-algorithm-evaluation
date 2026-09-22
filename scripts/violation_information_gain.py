#!/usr/bin/env python3
"""
Analyze information gain of constraint-violating vs compliant LLM guesses.

Replays each LLM-only game from raw data, computing per-round:
- candidates_before / candidates_after
- information_gain_bits = log2(before / after)
- uses the pre-computed violation flags from the original data

Outputs summary comparing violated vs compliant guesses.
"""

import csv
import glob
import math
import os
import statistics
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
WORDLIST_PATH = PROJECT_ROOT / "wordlist" / "wordlist.txt"
RAW_DATA_DIR = PROJECT_ROOT / "results" / "llms" / "raw data"
OUTPUT_DIR = PROJECT_ROOT / "feedback_compliance_analysis"


def load_wordlist():
    with open(WORDLIST_PATH) as f:
        return [w.strip().upper() for w in f if w.strip()]


def generate_feedback(guess, target):
    """Standard Wordle feedback: G=green, Y=yellow, -=gray."""
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


def filter_candidates(candidates, guess, feedback):
    """Keep candidates consistent with observed feedback."""
    return [w for w in candidates if generate_feedback(guess, w) == feedback]


def count_redundant_signals(guess, feedback, known_greens, known_grays):
    """Count feedback signals that are redundant (already known info)."""
    redundant = 0
    for i, (ch, fb) in enumerate(zip(guess, feedback)):
        if fb == "G" and known_greens.get(i) == ch:
            redundant += 1
        elif fb == "-" and ch in known_grays:
            redundant += 1
    return redundant


def update_known(known_greens, known_grays, guess, feedback):
    """Track known greens and grays for redundancy counting."""
    for i, (ch, fb) in enumerate(zip(guess, feedback)):
        if fb == "G":
            known_greens[i] = ch
        elif fb == "-":
            is_elsewhere = any(
                feedback[j] in ("G", "Y") and guess[j] == ch
                for j in range(5) if j != i
            )
            if not is_elsewhere:
                known_grays.add(ch)


def main():
    wordlist = load_wordlist()
    print(f"Loaded {len(wordlist)} words")

    csv_files = sorted(glob.glob(str(RAW_DATA_DIR / "model_*.csv")))
    print(f"Found {len(csv_files)} LLM result files")

    per_round_rows = []

    for csv_file in csv_files:
        fname = os.path.basename(csv_file)
        with open(csv_file) as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Group rows by game
        games = defaultdict(list)
        for row in rows:
            games[int(row["game_id"])].append(row)

        for game_id, turns in sorted(games.items()):
            turns.sort(key=lambda r: int(r["attempt_number"]))
            target = turns[0]["target_word"].upper()
            model = turns[0]["model_name"]
            prompt_type = turns[0]["prompt_type"]

            candidates = list(wordlist)
            known_greens = {}
            known_grays = set()

            for turn in turns:
                attempt = int(turn["attempt_number"])
                guess = turn["guess"].strip().upper() if turn["guess"] else ""
                feedback = turn["feedback"].strip() if turn["feedback"] else ""

                if not guess or not feedback or len(guess) != 5 or len(feedback) != 5:
                    continue

                # Use pre-computed violation count from original data
                try:
                    orig_violations = int(turn.get("total_constraint_violations", 0))
                except (ValueError, TypeError):
                    orig_violations = 0
                violated = orig_violations > 0 and attempt > 1

                # Compute info gain by replaying candidate filtering
                candidates_before = len(candidates)
                entropy_before = math.log2(candidates_before) if candidates_before > 1 else 0

                candidates_after_list = filter_candidates(candidates, guess, feedback)
                candidates_after = len(candidates_after_list)
                if candidates_after == 0:
                    # Guess might not be in wordlist — still filters by feedback
                    candidates_after = 1

                info_gain = math.log2(candidates_before / candidates_after) if candidates_before > candidates_after else 0
                entropy_after = math.log2(candidates_after) if candidates_after > 1 else 0

                # Count redundant signals
                redundant = count_redundant_signals(guess, feedback, known_greens, known_grays)

                per_round_rows.append({
                    "file": fname,
                    "model": model,
                    "prompt_type": prompt_type,
                    "game_id": game_id,
                    "target": target,
                    "round": attempt,
                    "guess": guess,
                    "feedback": feedback,
                    "violated": violated,
                    "violation_count": orig_violations if attempt > 1 else 0,
                    "redundant_signals": redundant,
                    "candidates_before": candidates_before,
                    "candidates_after": candidates_after,
                    "info_gain_bits": round(info_gain, 4),
                    "entropy_before": round(entropy_before, 4),
                    "entropy_after": round(entropy_after, 4),
                    "candidates_eliminated": candidates_before - candidates_after,
                    "reduction_rate": round(1 - candidates_after / candidates_before, 4) if candidates_before > 0 else 0,
                })

                # Update state for next round
                update_known(known_greens, known_grays, guess, feedback)
                candidates = candidates_after_list if candidates_after_list else candidates

        print(f"  Processed {fname}: {len(games)} games")

    # Save per-round CSV
    per_round_path = OUTPUT_DIR / "violation_info_gain_per_round.csv"
    with open(per_round_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=per_round_rows[0].keys())
        writer.writeheader()
        writer.writerows(per_round_rows)
    print(f"\nSaved {len(per_round_rows)} rows to {per_round_path}")

    # === Summary Statistics ===
    r2plus = [r for r in per_round_rows if r["round"] > 1]
    violated_rows = [r for r in r2plus if r["violated"]]
    compliant_rows = [r for r in r2plus if not r["violated"]]

    print(f"\n{'='*60}")
    print(f"VIOLATION vs COMPLIANT INFORMATION GAIN ANALYSIS")
    print(f"{'='*60}")
    print(f"Total guesses (round 2+): {len(r2plus)}")
    print(f"Violated: {len(violated_rows)} ({len(violated_rows)/len(r2plus)*100:.1f}%)")
    print(f"Compliant: {len(compliant_rows)} ({len(compliant_rows)/len(r2plus)*100:.1f}%)")

    v_ig = [r["info_gain_bits"] for r in violated_rows]
    c_ig = [r["info_gain_bits"] for r in compliant_rows]

    if v_ig and c_ig:
        v_mean = statistics.mean(v_ig)
        c_mean = statistics.mean(c_ig)
        diff_pct = (c_mean - v_mean) / c_mean * 100 if c_mean > 0 else 0

        print(f"\n--- Information Gain (bits) ---")
        print(f"Violated:  mean={v_mean:.3f}, median={statistics.median(v_ig):.3f}")
        print(f"Compliant: mean={c_mean:.3f}, median={statistics.median(c_ig):.3f}")
        print(f"Difference: violated guesses get {diff_pct:.1f}% less information")

        v_elim = [r["candidates_eliminated"] for r in violated_rows]
        c_elim = [r["candidates_eliminated"] for r in compliant_rows]
        print(f"\n--- Candidates Eliminated ---")
        print(f"Violated:  mean={statistics.mean(v_elim):.1f}")
        print(f"Compliant: mean={statistics.mean(c_elim):.1f}")

        v_red = [r["redundant_signals"] for r in violated_rows]
        c_red = [r["redundant_signals"] for r in compliant_rows]
        print(f"\n--- Redundant Signals per Guess ---")
        print(f"Violated:  mean={statistics.mean(v_red):.2f}")
        print(f"Compliant: mean={statistics.mean(c_red):.2f}")

        v_rr = [r["reduction_rate"] for r in violated_rows]
        c_rr = [r["reduction_rate"] for r in compliant_rows]
        print(f"\n--- Candidate Reduction Rate ---")
        print(f"Violated:  mean={statistics.mean(v_rr):.3f}")
        print(f"Compliant: mean={statistics.mean(c_rr):.3f}")

    # Per-model breakdown
    models = sorted(set(r["model"] for r in r2plus))
    print(f"\n--- Per-Model Breakdown ---")
    print(f"{'Model':<35} {'V':>4} {'V_info':>8} {'C_info':>8} {'Diff':>8} {'V_redund':>9}")
    print("-" * 75)
    for model in models:
        mv = [r for r in violated_rows if r["model"] == model]
        mc = [r for r in compliant_rows if r["model"] == model]
        if mv:
            v_m = statistics.mean([r["info_gain_bits"] for r in mv])
            c_m = statistics.mean([r["info_gain_bits"] for r in mc])
            d = (c_m - v_m) / c_m * 100 if c_m > 0 else 0
            vr = statistics.mean([r["redundant_signals"] for r in mv])
            print(f"{model:<35} {len(mv):>4} {v_m:>7.2f}b {c_m:>7.2f}b {d:>+7.1f}% {vr:>9.2f}")
        else:
            c_m = statistics.mean([r["info_gain_bits"] for r in mc]) if mc else 0
            print(f"{model:<35} {'0':>4} {'n/a':>8} {c_m:>7.2f}b {'n/a':>8} {'n/a':>9}")

    # Save summary
    summary_rows = []
    for label, group in [("violated", violated_rows), ("compliant", compliant_rows)]:
        if group:
            summary_rows.append({
                "group": label,
                "count": len(group),
                "mean_info_gain": round(statistics.mean([r["info_gain_bits"] for r in group]), 4),
                "median_info_gain": round(statistics.median([r["info_gain_bits"] for r in group]), 4),
                "mean_candidates_eliminated": round(statistics.mean([r["candidates_eliminated"] for r in group]), 2),
                "mean_reduction_rate": round(statistics.mean([r["reduction_rate"] for r in group]), 4),
                "mean_redundant_signals": round(statistics.mean([r["redundant_signals"] for r in group]), 4),
                "mean_entropy_before": round(statistics.mean([r["entropy_before"] for r in group]), 4),
                "mean_entropy_after": round(statistics.mean([r["entropy_after"] for r in group]), 4),
            })

    summary_path = OUTPUT_DIR / "violation_info_gain_summary.csv"
    with open(summary_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=summary_rows[0].keys())
        writer.writeheader()
        writer.writerows(summary_rows)
    print(f"\nSaved summary to {summary_path}")


if __name__ == "__main__":
    main()
