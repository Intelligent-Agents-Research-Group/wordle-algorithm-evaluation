#!/usr/bin/env python3
"""
Calculate candidates remaining after each guess for algorithm and hybrid data.
This post-processes existing CSV files to add candidate count information.
"""

import pandas as pd
import os
from typing import List, Tuple
from tqdm import tqdm


def load_word_list(filepath: str = "wordlist/wordlist.txt") -> List[str]:
    """Load the Wordle word list."""
    with open(filepath, 'r') as f:
        words = [line.strip().upper() for line in f if line.strip()]
    return words


def generate_feedback(target: str, guess: str) -> List[str]:
    """
    Generate feedback for a guess against a target word.
    Same logic as in wordle_env.py and css_strategy.py
    """
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
    """
    Check if a word is consistent with the feedback from a guess.
    feedback is a string like 'GYGGG' or '---Y-'
    """
    if len(feedback) != 5:
        return False

    feedback_list = list(feedback)
    expected_feedback = generate_feedback(word, guess)
    return expected_feedback == feedback_list


def filter_candidates(candidates: List[str], guess: str, feedback: str) -> List[str]:
    """Filter candidates based on guess and feedback."""
    return [word for word in candidates if is_consistent(word, guess, feedback)]


def process_algorithm_data(input_file: str, output_file: str, word_list: List[str]):
    """
    Process algorithm CSV file and add candidate count columns.

    Algorithm CSV format:
    strategy,game_number,target_word,tier,won,attempts,total_reward,
    guess_1,feedback_1,hamming_1,levenshtein_1,...
    """
    print(f"\nProcessing: {input_file}")
    df = pd.read_csv(input_file)

    # Add new columns for each round (1-6)
    for round_num in range(1, 7):
        df[f'candidates_before_{round_num}'] = None
        df[f'candidates_after_{round_num}'] = None
        df[f'reduction_rate_{round_num}'] = None

    # Process each game
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Games"):
        candidates = word_list.copy()

        # Process each round
        for round_num in range(1, 7):
            guess_col = f'guess_{round_num}'
            feedback_col = f'feedback_{round_num}'

            # Check if this round exists for this game
            if guess_col not in row or pd.isna(row[guess_col]):
                break

            guess = row[guess_col]
            feedback = row[feedback_col]

            # Record candidates before
            candidates_before = len(candidates)
            df.at[idx, f'candidates_before_{round_num}'] = candidates_before

            # Filter candidates based on feedback
            candidates = filter_candidates(candidates, guess, feedback)

            # Record candidates after
            candidates_after = len(candidates)
            df.at[idx, f'candidates_after_{round_num}'] = candidates_after

            # Calculate reduction rate
            if candidates_before > 0:
                reduction_rate = ((candidates_before - candidates_after) / candidates_before) * 100
                df.at[idx, f'reduction_rate_{round_num}'] = reduction_rate
            else:
                df.at[idx, f'reduction_rate_{round_num}'] = 0.0

    # Save processed data
    df.to_csv(output_file, index=False)
    print(f"Saved to: {output_file}")
    return df


def process_hybrid_data(input_file: str, output_file: str, word_list: List[str]):
    """
    Process hybrid CSV file and add candidate count columns.

    Hybrid CSV format:
    game_number,target_word,won,attempts,
    guess_1,feedback_1,hamming_1,levenshtein_1,strategy_1,...
    """
    print(f"\nProcessing: {input_file}")
    df = pd.read_csv(input_file)

    # Add new columns for each round (1-6)
    for round_num in range(1, 7):
        df[f'candidates_before_{round_num}'] = None
        df[f'candidates_after_{round_num}'] = None
        df[f'reduction_rate_{round_num}'] = None

    # Process each game
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Games"):
        candidates = word_list.copy()

        # Process each round
        for round_num in range(1, 7):
            guess_col = f'guess_{round_num}'
            feedback_col = f'feedback_{round_num}'

            # Check if this round exists for this game
            if guess_col not in row or pd.isna(row[guess_col]):
                break

            guess = row[guess_col]
            feedback = row[feedback_col]

            # Record candidates before
            candidates_before = len(candidates)
            df.at[idx, f'candidates_before_{round_num}'] = candidates_before

            # Filter candidates based on feedback
            candidates = filter_candidates(candidates, guess, feedback)

            # Record candidates after
            candidates_after = len(candidates)
            df.at[idx, f'candidates_after_{round_num}'] = candidates_after

            # Calculate reduction rate
            if candidates_before > 0:
                reduction_rate = ((candidates_before - candidates_after) / candidates_before) * 100
                df.at[idx, f'reduction_rate_{round_num}'] = reduction_rate
            else:
                df.at[idx, f'reduction_rate_{round_num}'] = 0.0

    # Save processed data
    df.to_csv(output_file, index=False)
    print(f"Saved to: {output_file}")
    return df


def main():
    """Main function to process all algorithm and hybrid data files."""

    print("Loading word list...")
    word_list = load_word_list()
    print(f"Loaded {len(word_list)} words")

    # Process algorithm data
    algorithm_input = "results/algorithms/raw data/algorithm_results_20251211_175156.csv"
    algorithm_output = "results/algorithms/raw data/algorithm_results_with_candidates.csv"

    if os.path.exists(algorithm_input):
        process_algorithm_data(algorithm_input, algorithm_output, word_list)
    else:
        print(f"Warning: {algorithm_input} not found")

    # Process hybrid data - Stage 3 (zero-shot)
    hybrid_dir_zs = "results/hybrids/stage3/raw data"
    if os.path.exists(hybrid_dir_zs):
        hybrid_files_zs = [f for f in os.listdir(hybrid_dir_zs) if f.endswith('.csv')]
        print(f"\nFound {len(hybrid_files_zs)} hybrid zero-shot files to process")

        for filename in hybrid_files_zs:
            input_path = os.path.join(hybrid_dir_zs, filename)
            output_filename = filename.replace('.csv', '_with_candidates.csv')
            output_path = os.path.join(hybrid_dir_zs, output_filename)

            process_hybrid_data(input_path, output_path, word_list)
    else:
        print(f"Warning: {hybrid_dir_zs} not found")

    # Process hybrid data - Stage 3 CoT
    hybrid_dir_cot = "results/hybrids/stage3-cot/raw data"
    if os.path.exists(hybrid_dir_cot):
        hybrid_files_cot = [f for f in os.listdir(hybrid_dir_cot) if f.endswith('.csv')]
        print(f"\nFound {len(hybrid_files_cot)} hybrid CoT files to process")

        for filename in hybrid_files_cot:
            input_path = os.path.join(hybrid_dir_cot, filename)
            output_filename = filename.replace('.csv', '_with_candidates.csv')
            output_path = os.path.join(hybrid_dir_cot, output_filename)

            process_hybrid_data(input_path, output_path, word_list)
    else:
        print(f"Warning: {hybrid_dir_cot} not found")

    print("\n✓ All processing complete!")


if __name__ == "__main__":
    main()
