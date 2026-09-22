# Experimental Setup

## Testbed Domains

We evaluate hybrid LLM-algorithm systems across two sequential reasoning domains that share structural properties but differ in whether domain knowledge can compensate for reasoning deficits.

### Wordle

Wordle is a word-guessing game where the player must identify a hidden 5-letter English word within 6 attempts. After each guess, the game provides per-position feedback: *green* (correct letter, correct position), *yellow* (correct letter, wrong position), or *gray* (letter not in word). The search space comprises 5,629 valid English words. Crucially, LLMs possess lexical priors over this space — they know which letter combinations form plausible words — enabling partial compensation for constraint reasoning failures.

### Mastermind

Mastermind is a code-breaking game where the player must identify a hidden 4-position code within 10 attempts. Repetitions are allowed. Feedback is given as aggregate counts: *black pegs* (correct color in correct position) and *white pegs* (correct color, wrong position). Unlike Wordle, codes carry no semantic structure — LLMs have no prior knowledge to distinguish plausible from implausible codes. This makes Mastermind a purer test of constraint satisfaction reasoning.

We evaluate two Mastermind variants that differ only in search space size:

- **Classic**: 6 colors (Red, Green, Blue, Yellow, Orange, White), yielding $6^4 = 1{,}296$ possible codes.
- **Extended**: 8 colors (adding Purple, blacK), yielding $8^4 = 4{,}096$ possible codes.

The Extended variant triples the search space while preserving identical game mechanics, feedback structure, and algorithms. This enables a controlled test of whether the state ownership effect scales with search space complexity: if LLMs degrade more when inheriting larger search spaces, the Extended variant should amplify the direction effect beyond what Classic shows.

### Domain Comparison

| Property | Wordle | Mastermind Classic | Mastermind Extended |
|----------|--------|-------------------|-------------------|
| Search space | 5,629 words | 1,296 codes | 4,096 codes |
| Max attempts | 6 | 10 | 10 |
| Feedback granularity | Per-position (5 signals) | Aggregate (2 counts) | Aggregate (2 counts) |
| Colors/Letters | 26 letters | 6 colors (RGBYOW) | 8 colors (RGBYOWPK) |
| Semantic structure | Yes (English words) | None | None |
| LLM prior knowledge | Strong (lexical) | None | None |

The three testbeds create a graded comparison: Wordle provides semantic priors that may compensate for constraint reasoning failures; Mastermind Classic removes semantic structure; Mastermind Extended further increases the constraint reasoning burden via a larger search space. If the state ownership effect strengthens from Wordle → Classic → Extended, it is driven by constraint reasoning difficulty rather than domain-specific factors.

## Models

We evaluate 7 open-source LLMs and 4 frontier models spanning a range of architectures and scales, accessed via the Navigator API (University of Florida).

### Open-Source Models (Primary)

| Model | Parameters | Family |
|-------|-----------|--------|
| llama-3.3-70b-instruct | 70B | Meta LLaMA 3.3 |
| llama-3.1-70b-instruct | 70B | Meta LLaMA 3.1 |
| llama-3.1-8b-instruct | 8B | Meta LLaMA 3.1 |
| mistral-7b-instruct | 7B | Mistral |
| codestral-22b | 22B | Mistral (code) |
| granite-3.3-8b-instruct | 8B | IBM Granite |
| gemma-3-27b-it | 27B | Google Gemma |

### Frontier Models (Extension)

| Model | Family | Notes |
|-------|--------|-------|
| gpt-oss-120b | Open-source GPT | 120B reasoning model |
| gpt-5 | OpenAI | Reasoning model (extended thinking) |
| claude-4-sonnet | Anthropic | Claude 4 Sonnet |
| gemini-2.5-pro | Google | Gemini 2.5 Pro |

The frontier models test whether the state ownership effect persists in significantly more capable systems. If frontier models still degrade when inheriting algorithmic state, this strengthens the claim that the effect is structural rather than a limitation of model scale.

All models are queried at temperature 0.7 via the same API endpoint and identical prompt templates. Open-source models use max 150-200 tokens per response. Reasoning models (gpt-oss-120b, gpt-5) use 2048 max tokens to accommodate internal chain-of-thought reasoning that consumes tokens before producing visible output.

## Classical Algorithms

### CSS (Constraint Satisfaction Scoring)

CSS combines information-theoretic candidate selection with reward-based scoring. For each candidate guess $g$, it computes:

$$\text{score}(g) = H(g) + 0.5 \cdot R(g)$$

where $H(g)$ is the expected entropy reduction (computed by simulating feedback against a sample of remaining candidates and measuring how evenly $g$ partitions the candidate space) and $R(g)$ is the expected reward (incorporating attempt penalty and probability of an immediate win). CSS maintains an exact belief state — after each guess-feedback pair, it deterministically filters the candidate set to retain only codes consistent with all observed feedback.

### VOI (Value of Information)

VOI extends CSS with probabilistic belief weighting and letter-frequency priors. It scores candidates using a weighted combination of positional match quality, expected reward, and frequency bonuses for common letters (in Wordle) or colors. VOI maintains the same deterministic candidate filtering as CSS but additionally tracks per-position frequency distributions to bias toward statistically favorable guesses. Both algorithms achieve optimal or near-optimal play when given full control.

## Hybrid Configurations

Each hybrid configuration specifies a **schedule**: a mapping from round number to agent type (LLM or algorithm). At each round, the designated agent receives the full game history (prior guesses and feedback) and produces the next guess. We organize configurations into three experimental groups.

### Group A: Handoff Direction (7 configurations)

These configurations test the core hypothesis by varying who goes first:

| Config | Schedule | Direction |
|--------|----------|-----------|
| C_to_L | Round 1: CSS, Rounds 2+: LLM | Algo-first |
| V_to_L | Round 1: VOI, Rounds 2+: LLM | Algo-first |
| L_to_C | Round 1: LLM, Rounds 2+: CSS | LLM-first |
| L_to_V | Round 1: LLM, Rounds 2+: VOI | LLM-first |
| L_to_C_alt | Alternating LLM/CSS, LLM starts | LLM-first |
| L_to_C_then_V | LLM → CSS → VOI (sequential) | LLM-first |
| L_to_V_then_C | LLM → VOI → CSS (sequential) | LLM-first |

### Group B: Dose-Response (12 configurations)

These configurations vary the number of algorithm rounds $k$ before handing off to the LLM (and vice versa), testing whether the state ownership effect is graded:

| Config | Schedule | Dose |
|--------|----------|------|
| css1_to_L | 1 round CSS, then LLM | k=1 |
| css2_to_L | 2 rounds CSS, then LLM | k=2 |
| css3_to_L | 3 rounds CSS, then LLM | k=3 |
| voi1_to_L | 1 round VOI, then LLM | k=1 |
| voi2_to_L | 2 rounds VOI, then LLM | k=2 |
| voi3_to_L | 3 rounds VOI, then LLM | k=3 |
| L1_to_css | 1 round LLM, then CSS | k=1 |
| L2_to_css | 2 rounds LLM, then CSS | k=2 |
| L3_to_css | 3 rounds LLM, then CSS | k=3 |
| L1_to_voi | 1 round LLM, then VOI | k=1 |
| L2_to_voi | 2 rounds LLM, then VOI | k=2 |
| L3_to_voi | 3 rounds LLM, then VOI | k=3 |

### Group C: Alternation with Prompting Variants (4 Wordle / 3 Mastermind)

These configurations test alternating control with two prompting strategies:

- **Zero-shot**: The LLM receives game history and remaining candidates, and must produce a single guess.
- **Chain-of-thought (CoT)**: The LLM is additionally instructed to produce explicit reasoning (`THINKING: <reasoning>`) before its guess (`FINAL: <word>`).

| Config | Pattern | Prompt |
|--------|---------|--------|
| alt_css_start_zs | CSS/LLM alternating, CSS starts | Zero-shot |
| alt_css_start_cot | CSS/LLM alternating, CSS starts | CoT |
| alt_voi_start_zs | VOI/LLM alternating, VOI starts | Zero-shot |
| alt_voi_start_cot | VOI/LLM alternating, VOI starts | CoT |

## Test Sets

To ensure comparability across all conditions, we use fixed canonical test sets:

- **Wordle**: 100 target words sampled from the 5,629-word vocabulary using a deterministic procedure, stratified across difficulty tiers. All 7 models play the same 100 words in every configuration.
- **Mastermind Classic**: 100 target codes sampled uniformly from the 1,296-code space using a fixed random seed (42). All models solve the same 100 codes in every configuration.
- **Mastermind Extended**: 100 target codes sampled uniformly from the 4,096-code space using the same seed (42). The target set is independent of Classic (different codes drawn from the larger space).

Using identical targets across conditions enables paired statistical comparisons.

## Data Collection

Each game produces a per-round record including:
- The guess produced and by which agent (LLM or CSS/VOI)
- The feedback received
- Distance metrics (Hamming distance, Levenshtein distance for Wordle)
- Win/loss outcome and total attempts

For Mastermind, we additionally record `candidates_N` — the number of remaining valid codes after round $N$ — enabling direct measurement of search space size at handoff points. For Wordle, we reconstruct candidate counts by replaying feedback through the constraint filter against the full word list.

## Scale

| Domain | Configurations | Models | Games/Config/Model | Total Games |
|--------|---------------|--------|-------------------|-------------|
| Wordle | 25 | 7 open-source | 100 | 18,600 |
| Mastermind Classic | 17 | 7 open-source | 100 | 15,300 |
| Mastermind Extended | 23 | 7 open-source | 100 | ~15,300 |
| **Open-source subtotal** | **65** | **7** | | **~49,200** |
| Wordle | 16 | 4 frontier | 100 | 6,400 |
| Mastermind Classic | 16 | 4 frontier | 100 | 6,400 |
| Mastermind Extended | 16 | 4 frontier | 100 | 6,400 |
| **Frontier subtotal** | **48** | **4** | | **19,200** |
| **Grand Total** | | **11** | | **~68,400** |

The three testbeds share identical hybrid configurations, models, and evaluation procedures, differing only in the underlying game domain and search space size. The frontier model extension tests the same 16 core configurations (Group A direction + Group B dose-response) across all 3 testbeds, enabling direct comparison of open-source and frontier model behavior under identical conditions.

## Search Space Handoff Analysis

To measure performance as a function of inherited state complexity, we identify the handoff point in each game — the round where control transfers from one agent type to another — and record the remaining candidate count at that moment. We then analyze performance (win rate, attempts, invalid guesses) as a function of $\log_2(\text{candidates})$ at handoff, bucketed into ranges. Across Wordle and Mastermind Classic, this yields 32,187 handoff observations; the Extended variant will add a comparable number.

## Statistical Methods

We employ the following tests:
- **Chi-square / Fisher's exact test**: For comparing win rates between conditions
- **Welch's t-test**: For comparing mean attempts (unequal variances)
- **Kruskal-Wallis H-test**: For dose-response analysis across $k$ levels (ordinal)
- **Spearman rank correlation**: For monotone trend in dose-response
- **One-way ANOVA**: For comparing attempts across dose levels
- **Pearson / point-biserial correlation**: For search space size vs. performance regression
- **Cohen's $d$**: For effect sizes between handoff directions

All tests use $\alpha = 0.05$ with no correction for multiple comparisons at the exploratory level; key results are confirmed at $p < 0.001$.
