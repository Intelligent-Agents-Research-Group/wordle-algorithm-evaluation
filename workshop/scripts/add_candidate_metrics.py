#!/usr/bin/env python3
"""
Add candidate count and space reduction metrics to workshop CSV files.
Post-processes existing CSVs to add:
- candidates_before_N: candidates remaining before round N
- candidates_after_N: candidates remaining after round N
- reduction_rate_N: percentage of candidates eliminated in round N

These metrics enable calculation of:
- Space reduction (reduction_rate_1 for first-round reduction)
- Convergence rate: (hamming_1 - hamming_final) / avg_rounds
  where hamming_final = 0 for winners, last hamming for losers
"""

import pandas as pd
import numpy as np
import os
from typing import List
from tqdm import tqdm
from pathlib import Path


def load_word_list(filepath: str = None) -> List[str]:
    """Load the Wordle word list."""
    if filepath is None:
        # Try to find wordlist relative to script
        script_dir = Path(__file__).parent
        project_dir = script_dir.parent.parent
        filepath = project_dir / "wordlist" / "wordlist.txt"

    with open(filepath, 'r') as f:
        words = [line.strip().upper() for line in f if line.strip()]
    return words


def generate_feedback(target: str, guess: str) -> List[str]:
    """Generate feedback for a guess against a target word."""
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

    return feedback


def is_consistent(word: str, guess: str, feedback: str) -> bool:
    """Check if a word is consistent with the feedback from a guess."""
    if len(feedback) != 5:
        return False

    feedback_list = list(feedback)
    expected_feedback = generate_feedback(word, guess)
    return expected_feedback == feedback_list


def filter_candidates(candidates: List[str], guess: str, feedback: str) -> List[str]:
    """Filter candidates based on guess and feedback."""
    return [word for word in candidates if is_consistent(word, guess, feedback)]


def process_csv(input_file: str, output_file: str, word_list: List[str]):
    """
    Process a CSV file and add candidate count columns.

    Expected CSV format:
    game_number,target_word,won,attempts,
    guess_1,feedback_1,hamming_1,levenshtein_1,strategy_1,...
    """
    print(f"\nProcessing: {input_file}")
    df = pd.read_csv(input_file)

    # Check if already processed
    if 'candidates_before_1' in df.columns:
        print(f"  Already processed, skipping")
        return df

    # Add new columns for each round (1-6)
    for round_num in range(1, 7):
        df[f'candidates_before_{round_num}'] = None
        df[f'candidates_after_{round_num}'] = None
        df[f'reduction_rate_{round_num}'] = None

    # Process each game
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Games", leave=False):
        candidates = word_list.copy()

        # Process each round
        for round_num in range(1, 7):
            guess_col = f'guess_{round_num}'
            feedback_col = f'feedback_{round_num}'

            # Check if this round exists for this game
            if guess_col not in row or pd.isna(row[guess_col]):
                break

            guess = str(row[guess_col]).upper()
            feedback = str(row[feedback_col])

            if not guess or guess == 'NAN' or not feedback:
                break

            # Record candidates before
            candidates_before = len(candidates)
            df.at[idx, f'candidates_before_{round_num}'] = candidates_before

            # Filter candidates based on feedback
            candidates = filter_candidates(candidates, guess, feedback)

            # Record candidates after
            candidates_after = len(candidates)
            df.at[idx, f'candidates_after_{round_num}'] = candidates_after

            # Calculate reduction rate (as percentage)
            if candidates_before > 0:
                reduction_rate = ((candidates_before - candidates_after) / candidates_before) * 100
                df.at[idx, f'reduction_rate_{round_num}'] = reduction_rate
            else:
                df.at[idx, f'reduction_rate_{round_num}'] = 0.0

    # Save processed data (overwrite original)
    df.to_csv(output_file, index=False)
    print(f"  Saved: {output_file}")
    return df


def calculate_convergence_rate(df: pd.DataFrame) -> float:
    """
    Calculate convergence rate for a DataFrame using the formula:
    convergence_rate = (hamming_1 - hamming_final) / avg_rounds

    Where:
    - hamming_final = 0 for winners, last non-NaN hamming for losers
    - avg_rounds = approach's average rounds played
    """
    if 'hamming_1' not in df.columns:
        return np.nan

    h1 = df['hamming_1'].values.astype(float)
    won = df['won'].values.astype(float)
    attempts = df['attempts'].values.astype(float)

    n = len(df)
    h_final = np.zeros(n, dtype=float)

    for i in range(n):
        if won[i] > 0.5:  # winner - final hamming is 0
            h_final[i] = 0
        else:  # loser - use last non-NaN hamming
            for r in range(6, 0, -1):
                col = f'hamming_{r}'
                if col in df.columns and not np.isnan(df[col].values[i]):
                    h_final[i] = df[col].values[i]
                    break

    # Use approach's average rounds as divisor
    # For losers, count as 6 rounds
    rounds_played = np.where(won > 0.5, attempts, 6.0)
    avg_rounds = max(np.mean(rounds_played), 1.0)

    conv = (h1 - h_final) / avg_rounds
    return np.nanmean(conv)


def main():
    """Process all workshop CSV files."""

    print("Loading word list...")
    word_list = load_word_list()
    print(f"Loaded {len(word_list)} words")

    # Find all workshop CSV files
    workshop_dir = Path(__file__).parent.parent / "results_css"

    csv_files = list(workshop_dir.rglob("*.csv"))
    # Filter to only raw data files (not summaries)
    csv_files = [f for f in csv_files if not f.name.startswith('summary_')]

    print(f"\nFound {len(csv_files)} CSV files to process")

    processed = 0
    skipped = 0
    errors = []

    for csv_file in csv_files:
        try:
            # Check if already has candidate columns
            df_check = pd.read_csv(csv_file, nrows=1)
            if 'candidates_before_1' in df_check.columns:
                skipped += 1
                continue

            process_csv(str(csv_file), str(csv_file), word_list)
            processed += 1
        except Exception as e:
            print(f"Error processing {csv_file}: {e}")
            errors.append((csv_file, str(e)))

    print(f"\n{'='*60}")
    print(f"PROCESSING COMPLETE")
    print(f"{'='*60}")
    print(f"Processed: {processed}")
    print(f"Skipped (already done): {skipped}")
    print(f"Errors: {len(errors)}")
    print(f"Total files: {len(csv_files)}")

    if errors:
        print(f"\nErrors encountered:")
        for f, e in errors[:10]:  # Show first 10 errors
            print(f"  {f.name}: {e}")


if __name__ == "__main__":
    main()
