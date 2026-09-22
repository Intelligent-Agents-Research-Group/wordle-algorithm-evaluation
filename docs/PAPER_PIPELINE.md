# Paper Pipeline

**Last Updated:** April 8, 2026
**Author:** Kevin Scroggins
**Research Group:** Intelligent Agents Research Group

---

## Paper 1: AAMAS Workshop Paper (Accepted)

**Title:** TBD (hybrid handoff direction in Wordle)
**Venue:** AAMAS 2026 (Workshop/Short Paper)
**Status:** Accepted

**Scope:**
- Wordle-only hybrid configurations
- Initial findings on generated vs inherited state
- LLM-first vs Algo-first handoff direction effect
- Demonstrates asymmetric performance based on who generates Round 1

**Data:** ~5,400 Wordle games from original hybrid experiments

---

## Paper 2: AAMAS Full Paper

**Title:** TBD (cross-domain validation of state ownership effect)
**Venue:** AAMAS (full paper)
**Status:** On hold — frontier results weaken the generalizability claim

### Frontier Findings (April 2026)

After completing and **validating** frontier model experiments, the state ownership effect does not generalize to frontier models in the way we hoped:

- **claude-4-sonnet on Mastermind Classic:** 100% across all 16 configs (ceiling, no direction effect)
- **claude-4-sonnet on Mastermind Extended:** 100% across all 16 configs (ceiling, no direction effect)
- **claude-4-sonnet on Wordle:** real asymmetry remains (LLM-first ~98% vs algo-first 46–58%)
- **gpt-5 on Wordle (partial):** small direction effect (92–96% algo-first vs ~100% LLM-first)
- **Open-source direction effect (unchanged):** +0.3pp (Wordle) → +5.7pp (Classic) → +8.0pp (Extended)

The effect still holds for open-source models and for Claude on Wordle, but Mastermind ceiling performance from Claude removes the "search space scaling" narrative we relied on.

### Critical Bug Discovered and Fixed (April 2026)

During validation, we discovered a **NEED parsing bug** that had invalidated earlier Mastermind results for reasoning models:

- **Bug:** Regex `\b[A-Za-z]{4}\b` in `scripts/mastermind/flexible_hybrid.py::_extract_guess` matched the word "NEED" in Claude responses like "I need to analyze the feedback...", returning it as a guess
- **Scale:** "NEED" is not a valid Mastermind color (N, E, D not in RGBYOW), so feedback came back INVALID. Because history was not updated on INVALID attempts, Claude received the same prompt each turn and repeated "NEED" until attempts were exhausted
- **Impact:** ALL earlier claude-4-sonnet Mastermind results (both Classic and Extended) were corrupted. The dramatic "2% vs 100%" MM Extended result was entirely an artifact
- **Also affected:** codestral-22b (66–68% INVALID) and mistral-7b (12–19% INVALID) — though their win rates were low enough that the bug was masked
- **Fix:** Added valid-color filter to `_extract_guess`, added correction nudge on retry failure, added `claude-4-sonnet` to `DIRECT_API_MODELS` to route through direct Anthropic API
- **Re-run:** All 32 claude-4-sonnet MM configs (Classic + Extended) re-run via `scripts/run_claude_mm_rerun.sh`. Verified: 0 INVALIDs, 0 feedback errors, 0 invalid colors, all 100% win rate

### Validation Performed
- 7,964 feedback entries verified (0 errors)
- 1,600 games with monotonic candidate progression (0 issues)
- 3,963 LLM guesses with valid colors (0 violations)
- Target consistency confirmed across conditions (seed=42)
- Prompt fairness confirmed (no source attribution, identical history format)

### Assessment
Given that Claude saturates Mastermind, the "cross-domain validation of state ownership" story no longer holds at the frontier. Paper 2 is currently **on hold** pending a stronger angle or a decision to scope down.

**Scope:**
- Extends short paper to **three testbeds**: Wordle (5,629 words) + Mastermind Classic (1,296 codes) + Mastermind Extended (4,096 codes)
- Cross-domain validation of generated vs inherited state hypothesis
- ~49,200 games from 7 open-source models (18,600 Wordle + 15,300 Classic + ~15,300 Extended)
- **Frontier model extension** (in progress): 4 additional models (gpt-oss-120b, gpt-5, claude-4-sonnet, gemini-2.5-pro) across all 3 testbeds — 19,200 additional games
- State ownership effect scales with search space: +0.3pp (Wordle) → +5.7pp (Classic) → +8.0pp (Extended)

**Key Contributions:**
1. Cross-domain validation across 3 testbeds — effect holds in pure constraint domains without semantic priors
2. Search space scaling — direction effect amplifies with search space size (Wordle → Classic → Extended)
3. Dose-response analysis — more algorithm rounds before handoff improves LLM performance (88% → 97% at k=1→3 in Extended)
4. Late-stage collapse — LLM constraint violation rates climb from ~22% at R2 to 68% by R10 in Mastermind
5. Constraint violations: LLMs violate 5% (Wordle), 23.8% (Classic), 26.3% (Extended); algorithms always 0%
6. **Search space handoff analysis** — LLM performance degrades with larger inherited search spaces; algorithms are invariant
7. **Coordination strategy** — prescriptive design principle: assign LLMs to trajectory generation, classical solvers to constraint satisfaction
8. **Frontier model extension** (in progress) — testing whether gpt-5, claude-4-sonnet, gemini-2.5-pro, and gpt-oss-120b exhibit the same state ownership effect

**New Analysis (March 23, 2026):**
- Extended Mastermind experiments complete (161 runs, 7 models, all 3 groups)
- Direction effect across 3 testbeds: +0.3pp (Wordle) → +5.7pp (Classic) → +8.0pp (Extended)
- Comprehensive metrics computed: win rate, avg attempts, Hamming/Levenshtein distance, convergence rate, constraint violations
- Late-stage collapse figure generated: `figures/late_stage_collapse.pdf`
- Frontier model experiments launched (4 models x 48 configs x 100 games = 19,200 games)

**Data Locations:**
- Wordle: `results/workshop/` (25 configs, 7 models + frontier models in progress)
- Mastermind Classic: `results/mastermind/hybrids/classic/` (17 configs)
- Mastermind Extended: `results/mastermind/hybrids/extended/` (23 configs)
- Search space analysis: `results/analysis/handoff_*.csv` (6 files, including Extended)
- Frontier experiments: logging to `frontier_experiments.log` (PID 41126, started Mar 23)

**Figures:**
- [x] `figures/search_space_performance.pdf` — 3-panel: Wordle + Classic + Extended
- [x] `figures/dose_response_k_handoff.pdf` — 6-panel dose-response (CSS/VOI x 3 testbeds)
- [x] `figures/per_model_direction_effect.pdf` — 3-panel per-model direction effect
- [x] `figures/late_stage_collapse.pdf` — LLM constraint violation rate by round

**Remaining Work:**
- [x] Extended Mastermind experiments (161 runs complete)
- [x] ANOVA + statistical tests (`scripts/workshop_extension_anova.py`)
- [x] All figures generated (search space, dose-response, per-model, late-stage collapse)
- [x] Coordination strategy section (`paper/coordination_strategy.md`)
- [x] Frontier model experiments: gpt-5 (partial, Navigator budget exhausted) and claude-4-sonnet (complete, re-run after NEED bug fix)
- [x] NEED parsing bug fix in `scripts/mastermind/flexible_hybrid.py` + re-run
- [ ] **On hold:** Frontier results do not exhibit the state ownership effect on Mastermind (Claude at ceiling). Need stronger angle before drafting manuscript.

---

## Paper 3: Signal Integration Paper

**Title:** "Do Language Models Integrate Algorithmic Reasoning Signals?"
**Venue:** AAAI 2027 or AAMAS 2027 (main track)
**Status:** Wordle experiments complete, Mastermind experiments in progress

**Scope:**
Tests whether LLMs genuinely integrate algorithmic reasoning signals (top-k candidates + scores + entropy) or merely imitate/ignore them.

### Key Finding: Three Regimes of Signal Processing (Wordle — Complete)

1. **Signal Integration** (small models: granite-8b, llama-8b) — follow rates 6-51%, statistically significant improvement
2. **Surface Imitation** (mid-range: codestral-22b) — picks displayed-first word, not highest-scored
3. **Signal Rejection** (large: llama-70b variants) — 0% follow rate, completely ignore signals

### Three Conditions:
- `baseline`: Standard prompt, no algorithmic signals
- `voi_informed`: Prompt includes Algorithm Analysis section with ranked candidates + entropy
- `shuffled_ranking`: Same but display order randomized (diagnostic for imitation vs reasoning)

### Wordle Experiments (Complete)
- 7 models x 2 algorithms x 3 conditions x 100 games = 42 runs
- Results: `voi_integration/results/wordle/`
- Analysis: `voi_integration/scripts/analyze_voi_results.py`

### Mastermind Experiments (In Progress — Paused Due to API Rate Limits)
- 8 models x 2 algorithms x 3 conditions x 100 games = 48 runs
- **5/48 runs completed** before API rate limiting (429 errors) corrupted results
- CSS runs clean (100% win rate), VOI runs hit rate limits
- Need to re-run when API is less congested
- Results: `voi_integration/results/mastermind/`
- Scripts: `voi_integration/scripts/voi_informed_mastermind.py`
- Run script: `voi_integration/scripts/run_voi_mastermind_experiment.sh`
- Analysis: `voi_integration/scripts/analyze_mastermind_results.py`

**Before re-running Mastermind:**
- Clean out broken results (0% win rate runs from rate limiting)
- Consider adding longer backoff delays in the experiment script
- May need to run in smaller batches to avoid API throttling

### Supporting Analysis (Complete)
- Entropy & information gain: `results/workshop/entropy_analysis.csv`
- Counterfactual analysis: `results/workshop/counterfactual_analysis.csv`, `results/mastermind/counterfactual_analysis.csv`

**Remaining Work:**
- [ ] Re-run Mastermind signal integration experiments (clean start, avoid API rate limits)
- [ ] Analyze Mastermind results — check if three-regime taxonomy generalizes
- [ ] Draft manuscript
- [ ] Generate figures

---

## Timeline

| Paper | Target Venue | Estimated Deadline | Status |
|-------|-------------|-------------------|--------|
| 1. Workshop paper | AAMAS 2026 | Accepted | Accepted |
| 2. Full paper | AAMAS 2027 | ~Oct 2026 | In preparation |
| 3. Full paper | AAAI 2027 | ~Aug 2026 | Early stage |

**Note:** Paper 3 (AAAI) deadline is likely before Paper 2 (AAMAS) deadline. Prioritize accordingly.

---

## Total Data Inventory

| Dataset | Games | Files | Used In |
|---------|-------|-------|---------|
| Pure Algorithms (Wordle) | 700 | 1 | Papers 1, 2 |
| Pure LLMs (Wordle) | 2,200 | 26 | Papers 1, 2 |
| Hybrid Stage 1-3 (Wordle) | 5,400 | ~204 | Paper 1 |
| Workshop Wordle (7 models) | 18,600 | 212 | Papers 1, 2, 3 |
| Workshop Mastermind Classic (7 models) | 15,300 | 177 | Papers 2, 3 |
| Workshop Mastermind Extended (7 models) | ~15,300 | 161 | Paper 2 |
| Frontier models (4 models, in progress) | ~19,200 | TBD | Paper 2 |
| Entropy Analysis (Wordle) | 81,852 rows | 1 | Paper 3 |
| Counterfactual (Wordle) | 32,115 LLM turns | 1 | Paper 3 |
| Counterfactual (Mastermind) | 31,337 LLM turns | 1 | Paper 3 |
| Search Space Handoff Analysis | ~48,000 handoffs | 6 | Paper 2 |
| Signal Integration (Wordle) | 4,200 | 42 | Paper 3 |
| Signal Integration (Mastermind) | 500 (5/48 runs) | 5 | Paper 3 (incomplete) |
| **Total** | **~68,400 games** | **~830+ files** | |

---

## Repository

**GitHub:** https://github.com/Intelligent-Agents-Research-Group/wordle-algorithm-evaluation
