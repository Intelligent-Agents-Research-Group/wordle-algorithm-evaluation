#!/usr/bin/env python3
"""Calculate constraint violations for workshop hybrid data."""

import pandas as pd
from pathlib import Path
from tqdm import tqdm


class ConstraintTracker:
    """Tracks and validates Wordle constraints."""

    def __init__(self):
        self.green_constraints = {}
        self.yellow_constraints = {}
        self.gray_letters = set()

    def add_feedback(self, guess: str, feedback: str):
        if len(guess) != 5 or len(feedback) != 5:
            return

        for i, (letter, fb) in enumerate(zip(guess, feedback)):
            if fb == 'G':
                self.green_constraints[i] = letter
            elif fb == 'Y':
                if letter not in self.yellow_constraints:
                    self.yellow_constraints[letter] = set()
                self.yellow_constraints[letter].add(i)
            elif fb == '-':
                is_green_or_yellow = any(
                    (feedback[j] in ['G', 'Y'] and guess[j] == letter)
                    for j in range(5)
                )
                if not is_green_or_yellow:
                    self.gray_letters.add(letter)

    def check_violations(self, guess: str) -> int:
        if len(guess) != 5:
            return 0

        violations = 0

        for pos, required_letter in self.green_constraints.items():
            if guess[pos] != required_letter:
                violations += 1

        for letter, forbidden_positions in self.yellow_constraints.items():
            if letter not in guess:
                violations += 1
            for pos in forbidden_positions:
                if guess[pos] == letter:
                    violations += 1

        for letter in self.gray_letters:
            if letter in guess:
                violations += 1

        return violations


def process_csv(csv_path: Path) -> pd.DataFrame:
    """Process a single CSV and add total_violations column."""
    df = pd.read_csv(csv_path)

    total_violations = []

    for idx, row in df.iterrows():
        tracker = ConstraintTracker()
        game_violations = 0

        for round_num in range(1, 7):
            guess_col = f'guess_{round_num}'
            feedback_col = f'feedback_{round_num}'

            if guess_col not in row or pd.isna(row[guess_col]):
                break

            guess = str(row[guess_col])
            feedback = str(row[feedback_col])

            if round_num > 1:
                game_violations += tracker.check_violations(guess)

            tracker.add_feedback(guess, feedback)

        total_violations.append(game_violations)

    df['total_violations'] = total_violations
    return df


def main():
    workshop_dir = Path(__file__).parent.parent
    results_dir = workshop_dir / "results_css"

    csv_files = list(results_dir.rglob("*.csv"))
    print(f"Found {len(csv_files)} CSV files to process")

    for csv_path in tqdm(csv_files, desc="Processing"):
        try:
            df = process_csv(csv_path)
            df.to_csv(csv_path, index=False)
        except Exception as e:
            print(f"Error processing {csv_path}: {e}")

    print("Done!")


if __name__ == "__main__":
    main()
