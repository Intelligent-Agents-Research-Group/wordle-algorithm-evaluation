# VOI-Informed Integration (Option 4)

Implements VOI-informed integration for the AAAI 2027 paper, where the LLM receives algorithmic analysis (top-k candidates ranked by VOI/CSS score + entropy context) in its prompt, enabling shared reasoning rather than blind switching.

## Quick Start

### Wordle
```bash
# Smoke test (2 games)
NUM_GAMES=2 CONDITION=voi_informed ALGORITHM=css \
  ./venv/bin/python voi_integration/scripts/voi_informed_hybrid.py

# Full experiment (48 runs: 8 models x 2 algos x 3 conditions)
./voi_integration/scripts/run_voi_experiment.sh

# Analyze results
./venv/bin/python voi_integration/scripts/analyze_voi_results.py
```

### Mastermind
```bash
# Smoke test (2 games)
NUM_GAMES=2 CONDITION=voi_informed ALGORITHM=css VARIANT=classic \
  ./venv/bin/python voi_integration/scripts/voi_informed_mastermind.py

# Full experiment (48 runs: 8 models x 2 algos x 3 conditions)
./voi_integration/scripts/run_voi_mastermind_experiment.sh

# Analyze results
./venv/bin/python voi_integration/scripts/analyze_mastermind_results.py
```

## Structure

```
voi_integration/
├── scripts/
│   ├── voi_informed_hybrid.py              # Wordle experiment script
│   ├── voi_informed_mastermind.py           # Mastermind experiment script
│   ├── run_voi_experiment.sh               # Wordle experiment matrix
│   ├── run_voi_mastermind_experiment.sh     # Mastermind experiment matrix
│   ├── analyze_voi_results.py              # Wordle statistical analysis
│   └── analyze_mastermind_results.py        # Mastermind statistical analysis
├── results/
│   ├── wordle/                             # Wordle experiment outputs
│   └── mastermind/                         # Mastermind experiment outputs
├── docs/
│   └── experiment_design.md                # Detailed experimental design
└── README.md
```

## Design

See [docs/experiment_design.md](docs/experiment_design.md) for full experimental design, hypotheses, and expected outcomes.
