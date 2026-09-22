# Coordination Strategy for Hybrid Reasoning Systems

## A Principled Approach to LLM-Algorithm Task Allocation

### Design Principle

**State Ownership Principle:** In hybrid LLM-algorithm systems, assign control based on the *type* of reasoning required at each phase:

- **LLMs → Trajectory generation** (exploration): LLMs should operate in early rounds where they generate reasoning trajectories from scratch, leveraging learned priors (lexical knowledge, pattern heuristics) to make plausible first moves.
- **Classical algorithms → Constraint satisfaction** (exploitation): Algorithms should operate in later rounds where the task reduces to systematic elimination over a well-defined candidate space.

The reverse assignment — algorithms generating initial state that LLMs must inherit — degrades LLM performance because LLMs cannot reliably reconstruct the constraint history that produced the inherited state.

### Empirical Basis

This principle is grounded in three converging lines of evidence across three domains (Wordle: 18,600 games; Mastermind Classic: 15,300 games; Mastermind Extended: ~15,300 games; 7 open-source LLM architectures + 4 frontier models in progress).

#### Evidence 1: Asymmetric Direction Effect

The performance gap between LLM-first and algorithm-first configurations is statistically significant and consistent across domains:

| Domain | LLM→Algo Win% | Algo→LLM Win% | Difference | p-value |
|--------|---------------|---------------|------------|---------|
| Wordle | 95.9% | 95.6% | +0.3 pp | 0.050 |
| Mastermind Classic | 99.9% | 94.2% | +5.7 pp | <0.001 |
| Mastermind Extended | 99.9% | 91.9% | +8.0 pp | <0.001 |

The effect scales with search space size: +0.3pp in Wordle (5,629 words, semantic priors available) → +5.7pp in Classic (1,296 codes, no priors) → +8.0pp in Extended (4,096 codes, no priors). This confirms the effect stems from constraint reasoning difficulty and intensifies as the search space grows.

#### Evidence 2: Dose-Response Relationship

When varying the number of algorithm rounds before LLM handoff (k=1, 2, 3), Mastermind shows a highly significant dose-response pattern (Kruskal-Wallis H=49.3, p<0.001 for CSS; H=27.8, p<0.001 for VOI):

| k (CSS rounds) | Win Rate | Avg Search Space | Avg Invalid Guesses |
|----------------|----------|-----------------|-------------------|
| k=1 | 91.1% | 188.4 candidates | 0.80 |
| k=2 | 96.6% | 24.9 candidates | 0.42 |
| k=3 | 98.6% | 3.3 candidates | 0.21 |

Paradoxically, more algorithm rounds *improve* LLM performance — because more pruning leaves the LLM with a smaller, more tractable search space. The critical variable is not the number of inherited rounds but the *size of the inherited search space*. When algorithms prune to ≤10 candidates, LLMs achieve near-perfect performance; when they hand off 100+ candidates with implicit constraint history, LLMs degrade.

#### Evidence 3: Algorithm Invariance

Classical algorithms are completely invariant to inherited state:

| Domain | Direction | Win Rate | Attempts | Search Space Effect |
|--------|-----------|----------|----------|-------------------|
| Wordle | LLM→Algo | 96.0% | 4.26 | r=−0.037, p=0.002 |
| Mastermind | LLM→Algo | **100.0%** | 4.85 | No variance (all wins) |

In Mastermind, algorithms achieve 100% win rate regardless of whether they inherit a search space of 10 or 1,000 candidates. This invariance is *not* because the task is easy — Algo→LLM configurations achieve only 95.7% under identical conditions. The asymmetry is fundamental: algorithms maintain explicit belief states and systematically eliminate candidates, while LLMs must infer constraint history from limited context.

### Per-Model Generalization

The direction effect holds across all 7 tested architectures in Mastermind (all achieve 100% LLM→Algo), with significant individual effects for 4 of 7 models (p<0.001):

| Model | Algo→LLM | LLM→Algo | Gap |
|-------|----------|----------|-----|
| codestral-22b | 74.7% | 100.0% | +25.3 pp*** |
| granite-8b | 97.7% | 100.0% | +2.3 pp*** |
| llama-3.1-8b | 97.4% | 100.0% | +2.6 pp*** |
| mistral-7b | 98.3% | 100.0% | +1.7 pp*** |
| gemma-27b | 99.7% | 100.0% | +0.3 pp |
| llama-3.1-70b | 99.8% | 100.0% | +0.2 pp |
| llama-3.3-70b | 99.6% | 100.0% | +0.4 pp |

The effect is largest for smaller and code-specialized models, suggesting that larger models partially compensate through stronger in-context reasoning — but none fully overcome the inherited state disadvantage.

### Formal Framework

Let a hybrid system alternate between an LLM agent $L$ and a classical algorithm $A$ over $T$ rounds. At each round $t$, the active agent receives:
- The game history $H_t = \{(g_1, f_1), \ldots, (g_{t-1}, f_{t-1})\}$ (prior guesses and feedback)
- A candidate set $C_t \subseteq C_0$ (remaining valid candidates)

We define the **state reconstruction difficulty** for agent $X$ at round $t$ as:

$$D_X(t) = \mathbb{E}\left[\text{KL}\left(P_X(C_t | H_t) \,\|\, P^*(C_t | H_t)\right)\right]$$

where $P^*$ is the true posterior over candidates and $P_X$ is the agent's inferred posterior.

For classical algorithms: $D_A(t) = 0$ for all $t$, since they maintain exact belief states.

For LLMs: $D_L(t) > 0$ when $t > 1$ and prior rounds were generated by $A$, because $L$ must reconstruct *why* certain candidates were eliminated without access to $A$'s internal scoring.

The **coordination principle** follows directly: assign $L$ to rounds where $D_L(t) = 0$ (round 1, or rounds where $L$ generated all prior history) and $A$ to remaining rounds.

### Practical Implications

1. **Default to LLM-first**: In hybrid systems where both components take turns, have the LLM generate the opening move. This costs nothing in algorithm performance (invariant) but can gain up to +25pp for the LLM.

2. **If algorithm-first is required**, ensure sufficient pruning before handoff. In our data, LLMs reach >97% win rate only when the search space is pruned below ~25 candidates — roughly $\log_2(25) \approx 4.6$ bits of entropy.

3. **The coordination principle generalizes beyond games**: Any hybrid system combining neural and symbolic reasoning should consider state ownership. Neural components should generate trajectories; symbolic components should refine and verify them. This aligns with emerging patterns in tool-augmented LLMs, where the LLM generates queries and the tool executes precise operations.

4. **Model selection matters at the boundary**: Smaller models (8B parameters) show 3–25× larger degradation from inherited state than larger models (70B). If algorithm-first is unavoidable, prefer larger LLMs for the receiving end.

### Cross-Domain Validation

The graded effect across three testbeds — +0.3pp (Wordle) → +5.7pp (Classic) → +8.0pp (Extended) — reveals two compounding factors:

1. **Semantic compensation**: Wordle provides lexical priors that partially mask constraint reasoning failures. Mastermind strips this away, amplifying the effect ~19×.
2. **Search space scaling**: Extended triples Classic's search space (4,096 vs 1,296) while preserving identical mechanics, producing a further 1.4× amplification. This confirms the effect scales with constraint reasoning burden.

This cross-domain pattern predicts that the effect will be *strongest* in domains where:
- The search space is abstract (no learned priors to compensate)
- The search space is large (more candidates to track)
- Constraints are cumulative (each round's feedback depends on all prior guesses)
- The optimal strategy requires precise belief maintenance (not just plausible heuristics)

### Late-Stage Collapse

In algo-first Mastermind configurations, LLM constraint violation rates increase dramatically over rounds — from ~22% at Round 2 to 68% by Round 10 in Extended. This "late-stage collapse" shows that LLMs do not merely fail to integrate inherited state at handoff; they progressively lose coherence as the game continues, accumulating errors that compound with each additional round of inherited constraint history.

### Frontier Model Extension (In Progress)

To test whether the state ownership effect is a limitation of model scale or a structural property of LLM reasoning, we are extending the evaluation to 4 frontier models: gpt-oss-120b, gpt-5, claude-4-sonnet, and gemini-2.5-pro. These models represent the current state-of-the-art across major providers. If frontier models exhibit the same direction effect, it strengthens the argument for the coordination principle as a fundamental design constraint rather than a temporary limitation that will be resolved by scaling.
