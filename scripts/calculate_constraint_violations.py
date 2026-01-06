#!/usr/bin/env python3
"""
Calculate constraint violations for algorithm and hybrid data.
Tracks whether guesses respect the feedback from previous rounds.
"""

import pandas as pd
import os
from typing import List, Dict, Set, Tuple
from tqdm import tqdm


class ConstraintTracker:
    """Tracks and validates Wordle constraints."""

    def __init__(self):
        self.green_constraints = {}  # position -> letter
        self.yellow_constraints = {}  # letter -> set of positions where it can't be
        self.gray_letters = set()  # letters that must not appear

    def add_feedback(self, guess: str, feedback: str):
        """
        Add constraints from a guess and its feedback.

        Feedback format: 'GYGGG' where:
        - G = green (correct letter, correct position)
        - Y = yellow (correct letter, wrong position)
        - - = gray (letter not in word)
        """
        if len(guess) != 5 or len(feedback) != 5:
            return

        for i, (letter, fb) in enumerate(zip(guess, feedback)):
            if fb == 'G':
                # This letter must be at this position
                self.green_constraints[i] = letter
            elif fb == 'Y':
                # This letter is in word but not at this position
                if letter not in self.yellow_constraints:
                    self.yellow_constraints[letter] = set()
                self.yellow_constraints[letter].add(i)
            elif fb == '-':
                # This letter is not in word (unless it appeared as G or Y elsewhere)
                # Only add to gray if it's not green/yellow anywhere in this guess
                is_green_or_yellow = any(
                    (feedback[j] in ['G', 'Y'] and guess[j] == letter)
                    for j in range(5)
                )
                if not is_green_or_yellow:
                    self.gray_letters.add(letter)

    def check_violations(self, guess: str) -> Dict[str, int]:
        """
        Check if a guess violates any constraints.

        Returns dict with counts of each violation type:
        - violated_green_constraint
        - violated_yellow_constraint
        - violated_gray_constraint
        - total_constraint_violations
        """
        violations = {
            'violated_green_constraint': 0,
            'violated_yellow_constraint': 0,
            'violated_gray_constraint': 0,
            'total_constraint_violations': 0
        }

        if len(guess) != 5:
            return violations

        # Check green constraints
        for pos, required_letter in self.green_constraints.items():
            if guess[pos] != required_letter:
                violations['violated_green_constraint'] += 1

        # Check yellow constraints
        for letter, forbidden_positions in self.yellow_constraints.items():
            # Letter must appear in word
            if letter not in guess:
                violations['violated_yellow_constraint'] += 1
            # Letter must not be at forbidden positions
            for pos in forbidden_positions:
                if guess[pos] == letter:
                    violations['violated_yellow_constraint'] += 1

        # Check gray constraints
        for letter in self.gray_letters:
            if letter in guess:
                violations['violated_gray_constraint'] += 1

        violations['total_constraint_violations'] = (
            violations['violated_green_constraint'] +
            violations['violated_yellow_constraint'] +
            violations['violated_gray_constraint']
        )

        return violations


def process_algorithm_data(input_file: str, output_file: str):
    """
    Process algorithm CSV and add constraint violation columns.

    Algorithm CSV format:
    strategy,game_number,target_word,tier,won,attempts,total_reward,
    guess_1,feedback_1,hamming_1,levenshtein_1,...
    """
    print(f"\nProcessing: {input_file}")
    df = pd.read_csv(input_file)

    # Add violation columns for each round
    for round_num in range(1, 7):
        df[f'violated_green_{round_num}'] = 0
        df[f'violated_yellow_{round_num}'] = 0
        df[f'violated_gray_{round_num}'] = 0
        df[f'total_violations_{round_num}'] = 0

    # Process each game
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Games"):
        tracker = ConstraintTracker()

        # Process each round
        for round_num in range(1, 7):
            guess_col = f'guess_{round_num}'
            feedback_col = f'feedback_{round_num}'

            # Check if this round exists
            if guess_col not in row or pd.isna(row[guess_col]):
                break

            guess = row[guess_col]
            feedback = row[feedback_col]

            # Check violations BEFORE adding this round's feedback
            if round_num > 1:  # First guess can't violate anything
                violations = tracker.check_violations(guess)
                df.at[idx, f'violated_green_{round_num}'] = violations['violated_green_constraint']
                df.at[idx, f'violated_yellow_{round_num}'] = violations['violated_yellow_constraint']
                df.at[idx, f'violated_gray_{round_num}'] = violations['violated_gray_constraint']
                df.at[idx, f'total_violations_{round_num}'] = violations['total_constraint_violations']

            # Add this round's feedback to constraints
            tracker.add_feedback(guess, feedback)

    # Save processed data
    df.to_csv(output_file, index=False)
    print(f"Saved to: {output_file}")
    return df


def process_hybrid_data(input_file: str, output_file: str):
    """
    Process hybrid CSV and add constraint violation columns.

    Hybrid CSV format:
    game_number,target_word,won,attempts,
    guess_1,feedback_1,hamming_1,levenshtein_1,strategy_1,...
    """
    print(f"\nProcessing: {input_file}")
    df = pd.read_csv(input_file)

    # Add violation columns for each round
    for round_num in range(1, 7):
        df[f'violated_green_{round_num}'] = 0
        df[f'violated_yellow_{round_num}'] = 0
        df[f'violated_gray_{round_num}'] = 0
        df[f'total_violations_{round_num}'] = 0

    # Process each game
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Games"):
        tracker = ConstraintTracker()

        # Process each round
        for round_num in range(1, 7):
            guess_col = f'guess_{round_num}'
            feedback_col = f'feedback_{round_num}'

            # Check if this round exists
            if guess_col not in row or pd.isna(row[guess_col]):
                break

            guess = row[guess_col]
            feedback = row[feedback_col]

            # Check violations BEFORE adding this round's feedback
            if round_num > 1:  # First guess can't violate anything
                violations = tracker.check_violations(guess)
                df.at[idx, f'violated_green_{round_num}'] = violations['violated_green_constraint']
                df.at[idx, f'violated_yellow_{round_num}'] = violations['violated_yellow_constraint']
                df.at[idx, f'violated_gray_{round_num}'] = violations['violated_gray_constraint']
                df.at[idx, f'total_violations_{round_num}'] = violations['total_constraint_violations']

            # Add this round's feedback to constraints
            tracker.add_feedback(guess, feedback)

    # Save processed data
    df.to_csv(output_file, index=False)
    print(f"Saved to: {output_file}")
    return df


def main():
    """Main function to process all data files."""

    print("="*80)
    print("CONSTRAINT VIOLATION ANALYSIS")
    print("="*80)
    print("\nThis analyzes whether guesses violate feedback from previous rounds.")
    print("\nViolation types:")
    print("  - Green: Wrong letter at a position that was marked correct")
    print("  - Yellow: Missing a letter or placing it at a forbidden position")
    print("  - Gray: Using a letter that was marked as not in word")
    print("="*80)

    # Process algorithm data
    algorithm_input = "results/algorithms/raw data/algorithm_results_20251211_175156.csv"
    algorithm_output = "results/algorithms/raw data/algorithm_results_with_violations.csv"

    if os.path.exists(algorithm_input):
        process_algorithm_data(algorithm_input, algorithm_output)
    else:
        print(f"Warning: {algorithm_input} not found")

    # Process hybrid data - Stage 3 (zero-shot)
    hybrid_dir_zs = "results/hybrids/stage3/raw data"
    if os.path.exists(hybrid_dir_zs):
        hybrid_files_zs = [f for f in os.listdir(hybrid_dir_zs)
                          if f.endswith('.csv') and not f.endswith('_with_violations.csv')
                          and not f.endswith('_with_candidates.csv')]
        print(f"\nFound {len(hybrid_files_zs)} hybrid zero-shot files to process")

        for filename in hybrid_files_zs:
            input_path = os.path.join(hybrid_dir_zs, filename)
            output_filename = filename.replace('.csv', '_with_violations.csv')
            output_path = os.path.join(hybrid_dir_zs, output_filename)

            process_hybrid_data(input_path, output_path)
    else:
        print(f"Warning: {hybrid_dir_zs} not found")

    # Process hybrid data - Stage 3 CoT
    hybrid_dir_cot = "results/hybrids/stage3-cot/raw data"
    if os.path.exists(hybrid_dir_cot):
        hybrid_files_cot = [f for f in os.listdir(hybrid_dir_cot)
                           if f.endswith('.csv') and not f.endswith('_with_violations.csv')
                           and not f.endswith('_with_candidates.csv')]
        print(f"\nFound {len(hybrid_files_cot)} hybrid CoT files to process")

        for filename in hybrid_files_cot:
            input_path = os.path.join(hybrid_dir_cot, filename)
            output_filename = filename.replace('.csv', '_with_violations.csv')
            output_path = os.path.join(hybrid_dir_cot, output_filename)

            process_hybrid_data(input_path, output_path)
    else:
        print(f"Warning: {hybrid_dir_cot} not found")

    print("\n" + "="*80)
    print("✓ All processing complete!")
    print("="*80)


if __name__ == "__main__":
    main()
