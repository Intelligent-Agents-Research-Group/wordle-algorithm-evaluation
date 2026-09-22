#!/usr/bin/env python3
"""
Comprehensive metrics across all testbeds for Paper 2.
Computes: win rate, avg attempts, hamming distance, levenshtein distance,
convergence rate, and constraint violations — broken down by agent, direction,
round, and model.

Testbeds: Wordle, Mastermind Classic, Mastermind Extended
"""

import glob
import csv
import os
from collections import defaultdict
from itertools import product

# ─── Helpers ───────────────────────────────────────────────────────────────────

def hamming(a, b):
    """Hamming distance between two equal-length strings."""
    return sum(c1 != c2 for c1, c2 in zip(a, b))

def levenshtein(a, b):
    """Levenshtein distance between two strings."""
    n, m = len(a), len(b)
    dp = list(range(m + 1))
    for i in range(1, n + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, m + 1):
            temp = dp[j]
            dp[j] = min(dp[j] + 1, dp[j-1] + 1,
                        prev + (0 if a[i-1] == b[j-1] else 1))
            prev = temp
    return dp[m]


def parse_mastermind_feedback(fb_str):
    """Parse '2B1W' -> (2, 1) i.e. (black_pegs, white_pegs)."""
    try:
        parts = fb_str.upper().replace(' ', '')
        b_idx = parts.index('B')
        w_idx = parts.index('W')
        blacks = int(parts[:b_idx])
        whites = int(parts[b_idx+1:w_idx])
        return blacks, whites
    except (ValueError, IndexError):
        return None, None


# ─── Constraint Tracking ──────────────────────────────────────────────────────

class WordleConstraintTracker:
    """Tracks Wordle constraints from G/Y/- feedback."""
    def __init__(self):
        self.green = {}              # pos -> letter
        self.yellow_letters = set()  # letters known in word
        self.yellow_not_at = defaultdict(set)  # letter -> forbidden positions
        self.gray = set()            # letters not in word

    def add_feedback(self, guess, feedback):
        if len(guess) != 5 or len(feedback) != 5:
            return
        round_greens, round_yellows = set(), set()
        for i, (ch, sig) in enumerate(zip(guess, feedback)):
            if sig == 'G':
                round_greens.add(ch)
                self.green[i] = ch
            elif sig == 'Y':
                round_yellows.add(ch)
                self.yellow_letters.add(ch)
                self.yellow_not_at[ch].add(i)
        for i, (ch, sig) in enumerate(zip(guess, feedback)):
            if sig == '-' and ch not in round_greens and ch not in round_yellows:
                self.gray.add(ch)

    def check(self, guess):
        """Returns dict of violation counts."""
        v = {'gray': 0, 'green': 0, 'yellow_pos': 0, 'yellow_missing': 0}
        if len(guess) != 5:
            return v
        for ch in guess:
            if ch in self.gray:
                v['gray'] += 1
                break
        for pos, letter in self.green.items():
            if pos < len(guess) and guess[pos] != letter:
                v['green'] += 1
                break
        for i, ch in enumerate(guess):
            if i in self.yellow_not_at.get(ch, set()):
                v['yellow_pos'] += 1
                break
        for letter in self.yellow_letters:
            if letter not in guess and letter not in self.green.values():
                v['yellow_missing'] += 1
                break
        return v


class MastermindConstraintTracker:
    """
    Tracks Mastermind constraints.

    In Mastermind, feedback is aggregate (XB, YW) not per-position, so we
    can't track position-level constraints directly. Instead we track:
    1. Guesses that are inconsistent with ALL prior feedback (would be eliminated
       by a proper constraint solver).

    We do this by checking: given all prior (guess, feedback) pairs, is the
    new guess consistent? i.e., if the new guess were the secret code, would
    each prior guess have produced the feedback it actually got?
    """
    def __init__(self):
        self.history = []  # list of (guess, blacks, whites)

    def add_feedback(self, guess, feedback_str):
        blacks, whites = parse_mastermind_feedback(feedback_str)
        if blacks is not None:
            self.history.append((guess, blacks, whites))

    def _compute_feedback(self, guess, secret):
        """Compute what feedback guess would get if secret were the code."""
        blacks = sum(g == s for g, s in zip(guess, secret))
        # Count color matches (whites)
        guess_counts = defaultdict(int)
        secret_counts = defaultdict(int)
        for g, s in zip(guess, secret):
            if g != s:
                guess_counts[g] += 1
                secret_counts[s] += 1
        whites = sum(min(guess_counts[c], secret_counts[c]) for c in guess_counts)
        return blacks, whites

    def check(self, new_guess):
        """
        Check if new_guess is consistent with all prior feedback.
        Returns {'inconsistent': 0 or 1}
        """
        # If new_guess were the secret, would prior guesses match their feedback?
        for prior_guess, exp_blacks, exp_whites in self.history:
            blacks, whites = self._compute_feedback(prior_guess, new_guess)
            if blacks != exp_blacks or whites != exp_whites:
                return {'inconsistent': 1}
        return {'inconsistent': 0}


# ─── Data Loading ─────────────────────────────────────────────────────────────

def classify_direction(config_name):
    """Classify a config as LLM-first, Algo-first, or alternation (excluded from direction comparison)."""
    alternation = ['alt_css_start_zs', 'alt_css_start_cot',
                   'alt_voi_start_zs', 'alt_voi_start_cot']
    if config_name in alternation:
        return 'alternation'
    algo_first = ['C_to_L', 'V_to_L', 'css1_to_L', 'css2_to_L', 'css3_to_L',
                  'voi1_to_L', 'voi2_to_L', 'voi3_to_L']
    return 'algo_first' if config_name in algo_first else 'llm_first'


def get_model_short(model):
    """Shorten model names for display."""
    mapping = {
        'llama-3.3-70b-instruct': 'llama3.3-70b',
        'llama-3.1-70b-instruct': 'llama3.1-70b',
        'llama-3.1-8b-instruct': 'llama3.1-8b',
        'mistral-7b-instruct': 'mistral-7b',
        'codestral-22b': 'codestral-22b',
        'granite-3.3-8b-instruct': 'granite-8b',
        'gemma-3-27b-it': 'gemma-27b',
    }
    return mapping.get(model, model)


def load_wordle_data():
    """Load all Wordle workshop data."""
    files = glob.glob('results/workshop/group_*/*/raw_data/*.csv')
    return files, 'wordle'


def load_mastermind_data(variant):
    """Load Mastermind classic or extended data."""
    files = glob.glob(f'results/mastermind/hybrids/{variant}/group_*/*/raw_data/*.csv')
    return files, f'mastermind_{variant}'


def extract_config_model(filepath, domain):
    """Extract config name and model from filepath."""
    parts = filepath.split('/')
    # Find the config name (directory above raw_data)
    for i, p in enumerate(parts):
        if p == 'raw_data':
            config = parts[i-1]
            break
    else:
        config = 'unknown'

    filename = os.path.basename(filepath)
    # Model name is between config_ and _YYYYMMDD
    # e.g. L_to_C_llama-3.1-70b-instruct_20260318_170339.csv
    name_part = filename.replace('.csv', '')
    # Remove config prefix
    if name_part.startswith(config + '_'):
        name_part = name_part[len(config)+1:]
    # Remove timestamp suffix (last two _NNNN parts)
    parts_list = name_part.split('_')
    # Find timestamp: last parts that are all digits
    while parts_list and parts_list[-1].isdigit():
        parts_list.pop()
    # Remove _cot suffix if present
    if parts_list and parts_list[-1] == 'cot':
        parts_list.pop()
    model = '_'.join(parts_list) if parts_list else 'unknown'
    # Fix common model names
    model = model.replace('_', '-') if 'llama' not in model and 'granite' not in model and 'gemma' not in model else model
    return config, model


# ─── Main Analysis ────────────────────────────────────────────────────────────

def analyze_testbed(files, domain, max_rounds):
    """Analyze a complete testbed. Returns structured metrics dict."""

    is_wordle = domain == 'wordle'
    code_len = 5 if is_wordle else 4

    # Accumulators
    metrics = {
        'domain': domain,
        'total_games': 0,
        'total_wins': 0,
        # Per-agent
        'by_agent': defaultdict(lambda: {
            'guesses': 0, 'ham_sum': 0, 'lev_sum': 0,
            'violations': 0, 'all_gray_or_inconsistent': 0,
            'new_greens': 0, 'new_yellows': 0,
        }),
        # Per-agent per-round
        'by_agent_round': defaultdict(lambda: defaultdict(lambda: {
            'guesses': 0, 'ham_sum': 0, 'lev_sum': 0,
            'violations': 0, 'won_this_round': 0,
        })),
        # Per-direction
        'by_direction': defaultdict(lambda: {
            'games': 0, 'wins': 0, 'attempts_sum': 0,
        }),
        # Per-model per-direction
        'by_model_direction': defaultdict(lambda: defaultdict(lambda: {
            'games': 0, 'wins': 0, 'attempts_sum': 0,
        })),
        # Per-config
        'by_config': defaultdict(lambda: {
            'games': 0, 'wins': 0, 'attempts_sum': 0,
        }),
        # Convergence: distance delta per round
        'convergence_by_agent': defaultdict(lambda: {
            'closer': 0, 'same': 0, 'farther': 0, 'total': 0,
            'delta_sum': 0,
        }),
    }

    skipped_nemotron = 0

    for filepath in files:
        if 'nemotron' in filepath:
            skipped_nemotron += 1
            continue

        config, model = extract_config_model(filepath, domain)
        direction = classify_direction(config)

        with open(filepath) as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                metrics['total_games'] += 1
                won = row.get('won', '').lower() == 'true'
                attempts = int(row['attempts']) if row.get('attempts') else max_rounds

                if won:
                    metrics['total_wins'] += 1

                metrics['by_direction'][direction]['games'] += 1
                metrics['by_direction'][direction]['attempts_sum'] += attempts
                if won:
                    metrics['by_direction'][direction]['wins'] += 1

                metrics['by_model_direction'][model][direction]['games'] += 1
                metrics['by_model_direction'][model][direction]['attempts_sum'] += attempts
                if won:
                    metrics['by_model_direction'][model][direction]['wins'] += 1

                metrics['by_config'][config]['games'] += 1
                metrics['by_config'][config]['attempts_sum'] += attempts
                if won:
                    metrics['by_config'][config]['wins'] += 1

                target = row.get('target_word', row.get('target_code', '')).upper()

                # Set up constraint tracker
                if is_wordle:
                    tracker = WordleConstraintTracker()
                else:
                    tracker = MastermindConstraintTracker()

                prev_ham = None
                for r in range(1, max_rounds + 1):
                    guess = row.get(f'guess_{r}', '')
                    fb = row.get(f'feedback_{r}', '')
                    strat = row.get(f'strategy_{r}', '')
                    if not guess or not fb:
                        break

                    guess = guess.upper()

                    # Is this the winning guess?
                    is_win = (fb == 'GGGGG') if is_wordle else (fb.startswith('4B') or guess == target)

                    # Compute distances
                    if len(guess) == code_len and len(target) == code_len:
                        ham = hamming(guess, target)
                        lev = levenshtein(guess, target) if is_wordle else ham  # use hamming for Mastermind
                    else:
                        ham = code_len
                        lev = code_len

                    ag = metrics['by_agent'][strat]
                    ag['guesses'] += 1
                    ag['ham_sum'] += ham
                    ag['lev_sum'] += lev

                    ar = metrics['by_agent_round'][strat][r]
                    ar['guesses'] += 1
                    ar['ham_sum'] += ham
                    ar['lev_sum'] += lev
                    if is_win:
                        ar['won_this_round'] += 1

                    # Convergence (round-over-round distance change)
                    if prev_ham is not None:
                        delta = ham - prev_ham
                        conv = metrics['convergence_by_agent'][strat]
                        conv['total'] += 1
                        conv['delta_sum'] += delta
                        if delta < 0:
                            conv['closer'] += 1
                        elif delta == 0:
                            conv['same'] += 1
                        else:
                            conv['farther'] += 1

                    prev_ham = ham

                    # Constraint violations (R2+, non-winning)
                    if r > 1 and not is_win:
                        if is_wordle:
                            v = tracker.check(guess)
                            if any(v.values()):
                                ag['violations'] += 1
                                ar['violations'] += 1
                        else:
                            v = tracker.check(guess)
                            if v.get('inconsistent', 0):
                                ag['violations'] += 1
                                ar['violations'] += 1

                    # Update constraints
                    if is_wordle:
                        tracker.add_feedback(guess, fb)
                    else:
                        tracker.add_feedback(guess, fb)

    return metrics


def print_report(m):
    """Print a formatted report for one testbed."""
    domain = m['domain']
    total = m['total_games']
    wins = m['total_wins']

    print(f"\n{'='*80}")
    print(f"  {domain.upper().replace('_', ' ')} — {total:,} games, {wins:,} wins ({100*wins/total:.1f}%)")
    print(f"{'='*80}")

    # Direction effect
    print(f"\n  --- Direction Effect ---")
    print(f"  {'Direction':<14} {'Games':>8} {'Wins':>8} {'Win%':>8} {'Avg Att':>9}")
    for d in ['llm_first', 'algo_first']:
        dd = m['by_direction'][d]
        if dd['games'] == 0:
            continue
        wr = 100 * dd['wins'] / dd['games']
        avg_att = dd['attempts_sum'] / dd['games']
        print(f"  {d:<14} {dd['games']:>8,} {dd['wins']:>8,} {wr:>7.1f}% {avg_att:>9.2f}")

    # Per-agent metrics
    print(f"\n  --- Per-Agent Metrics ---")
    print(f"  {'Agent':<10} {'Guesses':>10} {'Avg Ham':>9} {'Avg Lev':>9} {'Violations':>12} {'Viol%':>8}")
    for agent in sorted(m['by_agent'].keys()):
        if not agent or agent == 'unknown':
            continue
        a = m['by_agent'][agent]
        if a['guesses'] == 0:
            continue
        avg_ham = a['ham_sum'] / a['guesses']
        avg_lev = a['lev_sum'] / a['guesses']
        # Violation rate: violations / (guesses that could violate, i.e. R2+)
        # We count violations only for R2+ guesses, so use violations directly
        r2_guesses = a['guesses'] - m['by_agent_round'][agent].get(1, {}).get('guesses', 0)
        viol_rate = 100 * a['violations'] / r2_guesses if r2_guesses > 0 else 0
        print(f"  {agent:<10} {a['guesses']:>10,} {avg_ham:>9.2f} {avg_lev:>9.2f} {a['violations']:>12,} {viol_rate:>7.1f}%")

    # Convergence
    print(f"\n  --- Convergence (round-over-round Hamming distance change) ---")
    print(f"  {'Agent':<10} {'Transitions':>12} {'Closer':>10} {'Same':>10} {'Farther':>10} {'Avg Delta':>10}")
    for agent in sorted(m['convergence_by_agent'].keys()):
        if not agent or agent == 'unknown':
            continue
        c = m['convergence_by_agent'][agent]
        if c['total'] == 0:
            continue
        print(f"  {agent:<10} {c['total']:>12,} {c['closer']:>5,} ({100*c['closer']/c['total']:4.1f}%) "
              f"{c['same']:>5,} ({100*c['same']/c['total']:4.1f}%) "
              f"{c['farther']:>5,} ({100*c['farther']/c['total']:4.1f}%) "
              f"{c['delta_sum']/c['total']:>+10.3f}")

    # Per-round breakdown (agent)
    print(f"\n  --- Per-Round Metrics (LLM only) ---")
    print(f"  {'Round':<7} {'Guesses':>9} {'Avg Ham':>9} {'Violations':>12} {'Viol%':>8}")
    for r in sorted(m['by_agent_round'].get('LLM', {}).keys()):
        ar = m['by_agent_round']['LLM'][r]
        if ar['guesses'] == 0:
            continue
        avg_ham = ar['ham_sum'] / ar['guesses']
        viol_rate = 100 * ar['violations'] / ar['guesses'] if ar['guesses'] > 0 and r > 1 else 0
        print(f"    R{r:<4} {ar['guesses']:>9,} {avg_ham:>9.2f} {ar['violations']:>12,} {viol_rate:>7.1f}%")

    # Per-model direction
    print(f"\n  --- Per-Model Direction Effect ---")
    print(f"  {'Model':<22} {'LLMf Win%':>10} {'ALGf Win%':>10} {'Gap':>8}")
    for model in sorted(m['by_model_direction'].keys()):
        md = m['by_model_direction'][model]
        lf = md.get('llm_first', {'games': 0, 'wins': 0})
        af = md.get('algo_first', {'games': 0, 'wins': 0})
        if lf['games'] == 0 and af['games'] == 0:
            continue
        lf_wr = 100 * lf['wins'] / lf['games'] if lf['games'] > 0 else 0
        af_wr = 100 * af['wins'] / af['games'] if af['games'] > 0 else 0
        gap = lf_wr - af_wr
        short = get_model_short(model)
        print(f"  {short:<22} {lf_wr:>9.1f}% {af_wr:>9.1f}% {gap:>+7.1f}pp")


def print_cross_testbed_summary(all_metrics):
    """Print cross-testbed comparison table."""
    print(f"\n{'='*80}")
    print(f"  CROSS-TESTBED COMPARISON")
    print(f"{'='*80}")

    print(f"\n  --- Direction Effect ---")
    print(f"  {'Testbed':<22} {'LLMf Win%':>10} {'ALGf Win%':>10} {'Gap':>8}")
    for m in all_metrics:
        lf = m['by_direction']['llm_first']
        af = m['by_direction']['algo_first']
        if lf['games'] == 0 or af['games'] == 0:
            continue
        lf_wr = 100 * lf['wins'] / lf['games']
        af_wr = 100 * af['wins'] / af['games']
        name = m['domain'].replace('_', ' ').title()
        print(f"  {name:<22} {lf_wr:>9.1f}% {af_wr:>9.1f}% {lf_wr-af_wr:>+7.1f}pp")

    print(f"\n  --- Constraint Violations (LLM, R2+ guesses) ---")
    print(f"  {'Testbed':<22} {'LLM Guesses':>12} {'Violations':>12} {'Rate':>8}")
    for m in all_metrics:
        a = m['by_agent'].get('LLM', {'guesses': 0, 'violations': 0})
        r1 = m['by_agent_round'].get('LLM', {}).get(1, {}).get('guesses', 0)
        r2_plus = a['guesses'] - r1
        rate = 100 * a['violations'] / r2_plus if r2_plus > 0 else 0
        name = m['domain'].replace('_', ' ').title()
        print(f"  {name:<22} {r2_plus:>12,} {a['violations']:>12,} {rate:>7.1f}%")

    print(f"\n  --- Convergence (Avg Hamming delta per transition) ---")
    print(f"  {'Testbed':<22} {'LLM':>10} {'CSS':>10} {'VOI':>10}")
    for m in all_metrics:
        vals = {}
        for agent in ['LLM', 'CSS', 'VOI']:
            c = m['convergence_by_agent'].get(agent, {'total': 0, 'delta_sum': 0})
            vals[agent] = c['delta_sum'] / c['total'] if c['total'] > 0 else 0
        name = m['domain'].replace('_', ' ').title()
        print(f"  {name:<22} {vals['LLM']:>+10.3f} {vals['CSS']:>+10.3f} {vals['VOI']:>+10.3f}")

    print(f"\n  --- Average Hamming Distance (all guesses) ---")
    print(f"  {'Testbed':<22} {'LLM':>10} {'CSS':>10} {'VOI':>10}")
    for m in all_metrics:
        vals = {}
        for agent in ['LLM', 'CSS', 'VOI']:
            a = m['by_agent'].get(agent, {'guesses': 0, 'ham_sum': 0})
            vals[agent] = a['ham_sum'] / a['guesses'] if a['guesses'] > 0 else 0
        name = m['domain'].replace('_', ' ').title()
        print(f"  {name:<22} {vals['LLM']:>10.2f} {vals['CSS']:>10.2f} {vals['VOI']:>10.2f}")


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    all_metrics = []

    # Wordle
    print("Loading Wordle data...")
    files, domain = load_wordle_data()
    print(f"  {len(files)} files")
    m = analyze_testbed(files, domain, max_rounds=6)
    print_report(m)
    all_metrics.append(m)

    # Mastermind Classic
    print("\nLoading Mastermind Classic data...")
    files, domain = load_mastermind_data('classic')
    print(f"  {len(files)} files")
    m = analyze_testbed(files, domain, max_rounds=10)
    print_report(m)
    all_metrics.append(m)

    # Mastermind Extended
    print("\nLoading Mastermind Extended data...")
    files, domain = load_mastermind_data('extended')
    print(f"  {len(files)} files")
    m = analyze_testbed(files, domain, max_rounds=10)
    print_report(m)
    all_metrics.append(m)

    # Cross-testbed comparison
    print_cross_testbed_summary(all_metrics)

    print(f"\n{'='*80}")
    print("  DONE")
    print(f"{'='*80}")
