# Formal Framework: Alignment-Modulated Logarithmic Opinion Pooling

## Overview

We model how LLMs process algorithmic reasoning signals as an instance of **logarithmic opinion pooling** with an alignment-sensitive mixing weight. The core question is not whether LLMs "use" signals, but *when algorithmic advice changes decisions* — and what governs the degree of influence. We derive observable consequences of the model, compare against a simpler constant-weight baseline, and identify three behavioral regimes grounded in specific empirical patterns.

## 1. Setup and Notation

Consider a hybrid reasoning system where an LLM $L$ and a classical algorithm $A$ jointly solve a sequential decision problem over $T$ rounds. At round $t$, the LLM receives:

- Game history $H_t = \{(g_1, f_1), \ldots, (g_{t-1}, f_{t-1})\}$ — prior guesses and feedback
- Candidate set $C_t \subseteq C_0$ — remaining valid candidates
- Algorithmic signal $S_t$ — a ranked list of candidates with associated scores (CSS information gain or VOI expected payoff)

The LLM must select a guess $g_t \in C_0$.

We define two probability distributions over the candidate space:

- **LLM prior** $\pi_L(g \mid H_t)$: the distribution the LLM would produce *without* the algorithmic signal, reflecting learned heuristics, lexical knowledge, and in-context reasoning. This is estimated empirically from the baseline (no-signal) condition at matched game states.
- **Signal distribution** $\pi_S(g \mid S_t)$: a softmax distribution over candidates derived from algorithmic scores:

$$\pi_S(g \mid S_t) = \frac{\exp(s(g) / \lambda)}{\sum_{g' \in C_t} \exp(s(g') / \lambda)}$$

where $s(g)$ is the algorithm's score for candidate $g$ and $\lambda > 0$ is a temperature parameter controlling signal concentration. For candidates not included in the presented ranking, $s(g) = 0$. This avoids the degeneracy of a point-mass recommendation: all candidates retain positive probability, but the signal distribution is concentrated on highly-scored candidates.

**Score specification.** CSS scores are expected information gain in bits (range: typically 0–4 bits for Wordle, 0–6 bits for Mastermind). VOI scores are expected payoff values (range depends on remaining game rounds). Because CSS and VOI scores live on different scales, $\pi_S$ is not directly comparable across algorithm types without normalization. We standardize scores within each algorithm-domain pair to zero mean and unit variance before computing $\pi_S$, so that $\lambda$ has a consistent interpretation across conditions.

**Temperature-integration tradeoff.** Substituting $\pi_S$ into the log-odds equation (§2.2) yields:

$$\log \frac{\pi(g)}{\pi(h)} = (1 - \alpha_t) \log \frac{\pi_L(g)}{\pi_L(h)} + \frac{\alpha_t}{\lambda} [s(g) - s(h)]$$

The effective signal strength is $\alpha_t / \lambda$: a high integration weight with broad temperature produces the same log-odds shift as a low integration weight with sharp temperature. This means $\alpha_t$ and $\lambda$ cannot be independently identified from choice data alone. We address this by fixing $\lambda$ at a value determined independently from the score presentation format (the ratio of the top-ranked to median score in the presented list), then estimating $(b, \beta)$ conditional on that fixed $\lambda$. We report sensitivity of the $(b, \beta)$ estimates across a range of plausible $\lambda$ values (0.5× to 2× the fixed value) to assess robustness.

## 2. Core Model

### 2.1 Logarithmic Opinion Pooling

The LLM's effective decision distribution is modeled as a logarithmic pool (weighted geometric mean) of the prior and signal (Genest & Zidek, 1986):

$$\pi(g \mid H_t, S_t) \propto \pi_L(g \mid H_t)^{1 - \alpha_t} \cdot \pi_S(g \mid S_t)^{\alpha_t}$$

where $\alpha_t \in [0, 1]$ is the **integration weight** at round $t$. When $\alpha_t = 0$, the LLM ignores the signal entirely; when $\alpha_t = 1$, it defers completely to the algorithm.

This is logarithmic pooling, not Bayesian updating — combining two distributions through a weighted geometric mean does not require either distribution to represent a likelihood or that the combination follows from Bayes' rule. The family is well-studied in the opinion pooling literature (Genest & Zidek, 1986; Dietrich & List, 2016) and has the useful property of preserving the support of both component distributions for $\alpha_t \in (0, 1)$.

### 2.2 Log-Odds Consequence

For any two actions $g, h$ with positive probability under both distributions, the pooling model implies:

$$\log \frac{\pi(g)}{\pi(h)} = (1 - \alpha_t) \log \frac{\pi_L(g)}{\pi_L(h)} + \alpha_t \log \frac{\pi_S(g)}{\pi_S(h)}$$

The log-odds of the combined distribution are a convex combination of the log-odds under the prior and signal. This is the key estimable equation: it connects the integration weight to **changes in relative action preferences** rather than to absolute follow rates.

This formulation makes clear why raw follow rate is insufficient as an estimator of $\alpha_t$. A model can exhibit high follow rate with zero integration weight if its prior $\pi_L$ already favors the recommended action. Conversely, meaningful integration ($\alpha_t > 0$) can shift the distribution toward the signal without changing the modal action. The baseline condition is essential for separating agreement from influence.

### 2.3 Influence Measure and Identifiability Boundary

We define the **signal influence** $I_t$ as the shift in log-odds toward the signal's top recommendation $g_S$ relative to the LLM's baseline-preferred action $g_L$:

$$I_t = \log \frac{\pi(g_S)}{\pi(g_L)} - \log \frac{\pi_L(g_S)}{\pi_L(g_L)}$$

Substituting from §2.2:

$$I_t = \alpha_t \left( \log \frac{\pi_S(g_S)}{\pi_S(g_L)} - \log \frac{\pi_L(g_S)}{\pi_L(g_L)} \right)$$

Signal influence is zero when $\alpha_t = 0$ (rejection), when the prior and signal agree on the ranking of $g_S$ vs $g_L$ (no conflict to resolve), or when $g_S = g_L$ (recommendation matches baseline preference). It is maximal when $\alpha_t$ is large and the signal strongly favors $g_S$ over the model's preferred $g_L$.

**Identifiability boundary.** When $\pi_L = \pi_S$, the pooling model reduces to:

$$\pi(g) \propto \pi_L(g)^{1-\alpha_t} \cdot \pi_L(g)^{\alpha_t} = \pi_L(g)$$

for every $\alpha_t$. Perfect prior-signal agreement makes integration behaviorally unidentifiable — the model could fully incorporate the signal or completely ignore it and produce identical choices. This has a concrete methodological consequence: **diagnostic experiments require game states where the prior and signal disagree.** Estimation of $(b, \beta)$ is informative only at states where $\pi_L$ and $\pi_S$ produce different action rankings.

In practice, we do not observe the full distributions $\pi$ and $\pi_L$ — only discrete actions. We estimate influence by comparing the frequency with which the LLM selects the algorithm's top recommendation in the informed condition versus the baseline condition at matched game states:

$$\hat{I} = P(\text{select } g_S \mid \text{informed}, \text{state } H_t) - P(\text{select } g_S \mid \text{baseline}, \text{state } H_t)$$

This **baseline-corrected follow rate** separates signal-induced behavior change from pre-existing agreement. Both probabilities must refer to the same game state and recommendation. Note that $\hat{I}$ is a useful outcome measure but does not by itself distinguish alignment-modulated integration ($\beta > 0$) from constant-weight integration ($\beta = 0$): even with $\beta = 0$, changing the alignment between conditions changes the pooled distribution and therefore $\hat{I}$. The discriminating test is whether an alignment-dependent model predicts held-out choices better than a constant-weight model, after accounting for baseline preferences and signal scores (§5.1).

### 2.4 Alignment-Modulated Integration Weight

The key empirical finding — particularly the claude-4-sonnet selective integration pattern — is that $\alpha_t$ is not constant within a model. It varies with how well the signal aligns with the LLM's prior. We model this as:

$$\alpha_t = \sigma(b + \beta \cdot A_t)$$

where:

- $b \in \mathbb{R}$ — **base integration tendency**: the model's default willingness to integrate when alignment is at the neutral point ($A_t = 0$). Captures both overall openness and default bias in a single identifiable parameter.
- $\beta \geq 0$ — **alignment sensitivity**: how strongly prior-signal agreement modulates integration. When $\beta = 0$, integration is constant; when $\beta$ is large, integration depends strongly on alignment.
- $\sigma(\cdot)$ — logistic function, bounding $\alpha_t$ to $(0, 1)$
- $A_t \in [-1, 1]$ — **prior-signal alignment score** at round $t$

This two-parameter model ($b, \beta$) is identified from data with variation in $A_t$: a minimum of two alignment levels suffice (e.g., CSS vs VOI conditions, which produce different $A_t$ values because VOI recommendations tend to align with learned heuristics while CSS recommendations sometimes conflict). The constant-weight model $\alpha_t = \sigma(b)$ is nested as the special case $\beta = 0$, enabling direct model comparison.

### 2.5 Alignment Score

The alignment score $A_t = A(\pi_L, \pi_S)$ quantifies agreement between the LLM's prior and the algorithmic signal at a given game state. Crucially, $A_t$ is defined entirely from the **no-signal baseline** and the **algorithmic distribution** — it does not depend on the model's behavior in the informed condition. This prevents alignment from becoming a retrospective explanation of following.

We define:

$$A_t = A(\hat{\pi}_L, \pi_S) = 2 \cdot \mathbb{P}_{g \sim \hat{\pi}_L}[\text{rank}_{\pi_S}(g) \leq k] - 1$$

where $k$ is the number of candidates presented in the signal (typically $k = 5$), $\hat{\pi}_L$ is estimated from baseline-condition behavior at matched game states, and $\pi_S$ is determined by the algorithm. This equals $+1$ when the LLM's baseline-preferred candidates are all top-ranked by the algorithm, $-1$ when there is no overlap, and $0$ at chance level. The scale is fixed by the choice of $k$.

**Estimation uncertainty.** Because $\hat{\pi}_L$ is estimated from a finite sample of baseline games ($\leq 100$ per model-domain pair), the per-state alignment score carries substantial uncertainty, especially for game states that appear rarely in the baseline. We pool across game states within each algorithm-domain condition to obtain a condition-level alignment estimate $\bar{A}$ with standard error, rather than relying on per-turn estimates. When matched-state baseline samples are sparse (fewer than 5 observations at a given game state), we report the alignment estimate as unreliable and exclude those states from model fitting.

At the condition level, the CSS vs. VOI distinction provides natural variation in $\bar{A}$: VOI recommendations tend to align with learned heuristics (e.g., diverse-color guesses in Mastermind), while CSS recommendations are purely information-theoretic and sometimes conflict with model priors, producing systematically different $\bar{A}$ values across the two algorithm types.

## 3. Behavioral Regimes

We observe three distinct behavioral responses to algorithmic signals, characterized by the parameters $(b, \beta)$. These describe **how the model changes its decisions in response to signals**, which is distinct from trace observability (§3.4).

### 3.1 Integration (granite-3.3-8b)

**Characterization**: High baseline-corrected follow rate, approximately constant across signal types. Consistent with $\sigma(b) \gg 0$ and $\beta \approx 0$.

When $\beta$ is near zero, $\alpha_t \approx \sigma(b) = \text{const}$, and the model integrates signals at a roughly uniform rate independent of alignment:

- **Wordle**: CSS follow 83%, VOI follow 67% (CoT); CSS 40%, VOI 51% (informed condition)
- **Mastermind**: CSS follow 40%, VOI follow 57% (CoT); CSS 41%, VOI 50% (informed)

The cross-domain variation (Wordle ~75% → Mastermind ~48% in CoT traces) likely reflects changes in $\pi_L$ across domains. In Mastermind, where the model lacks lexical priors, the baseline distribution $\pi_L$ is more diffuse, which changes the signal's ability to shift the modal action even at the same $\alpha_t$. This is a consequence of the pooling model: a fixed integration weight produces different observed follow rates depending on how concentrated $\pi_L$ and $\pi_S$ are.

Additionally, within the integration regime, the *mechanism* of integration varies. The shuffled-ranking diagnostic reveals that llama-3.1-8b engages in **score reasoning** (TrueTop1 25% vs DispTop1 0–1%), while codestral-22b exhibits **rank imitation** (DispTop1 26% vs TrueTop1 13%). Both produce non-zero influence, but through different cognitive strategies.

### 3.2 Selective Integration (claude-4-sonnet)

**Characterization**: Follow rate varies sharply by signal type. Consistent with moderate $b$ and $\beta \gg 0$.

When $\beta$ is large, $\sigma(b + \beta A_t)$ acts as a soft gate:

- High alignment ($A_t > 0$): $\alpha_t \approx 1$, strong integration
- Low alignment ($A_t < 0$): $\alpha_t \approx 0$, effective rejection

Empirical pattern:

- **Mastermind VOI**: 80% follow — VOI recommendations tend to align with claude-4-sonnet's internal heuristic favoring diverse-color guesses → high $A_t$ → high $\alpha_t$
- **Mastermind CSS**: 23% follow — CSS sometimes recommends repeated-color guesses that conflict with the diversity heuristic → low $A_t$ → low $\alpha_t$

The 57 percentage-point gap is the empirical signature of alignment sensitivity. However, cross-algorithm follow variance alone does not identify $\beta$: prior preferences and signal concentration also affect observed follow rates (see §2.2). Confirming that $\beta > 0$ requires comparing a fitted alignment model against the constant-weight baseline on held-out data (§5.1).

**Cross-generational observation**: claude-4.6-sonnet shows a narrower gap (~24pp vs 57pp). This is *consistent with* decreasing alignment sensitivity as priors improve, but could also reflect changes in $\pi_L$ or $\pi_S$ concentration. We treat the extrapolation that future models will show <10pp gaps as a prospective hypothesis, not a derived prediction.

### 3.3 Rejection (llama-3.3-70b, codestral-22b)

**Characterization**: Near-zero baseline-corrected follow rate across all signal types. Consistent with $b \ll 0$ (strong negative base tendency), making $\alpha_t \approx 0$ regardless of $\beta$.

When $\sigma(b + \beta A_t) \approx 0$ for all observed $A_t$ values, the signal term effectively vanishes:

$$\pi(g) \approx \pi_L(g)$$

These models process the signal perceptually — CoT traces show reference rates of 77–100% — but do not change their decisions as a result:

- **llama-3.3-70b**: Baseline-corrected influence near zero. References scores at 93–100%, explicitly rejects at 70–93%. Follow rates: 3–23%.
- **codestral-22b**: References at 77–97%, rejects at 83–93%. Follow rates: 0–27%.

### 3.4 Trace Observability as an Orthogonal Axis

The three regimes above describe **behavioral response** — whether and how the signal changes decisions. A separate axis is **trace observability** — whether the model's reasoning about the signal is visible in its output.

gpt-oss-120b illustrates this distinction. It shows moderate follow rates (10–57%) but near-zero signal reference in visible output (0–13%) and zero explicit rejection. The behavioral response is *some form of integration or selective integration*, but the reasoning is hidden inside the model's internal chain-of-thought.

This represents a **methodological boundary**: as reasoning models with hidden scratchpads become prevalent, trace-based approaches to studying signal integration lose diagnostic power. An opaque model could exhibit any of the three behavioral regimes. Classifying it requires outcome-based methods (baseline-corrected follow rate) rather than trace analysis.

We report gpt-oss-120b as a separate empirical profile but do not treat opacity as a fourth behavioral regime — it belongs on a different dimension of the taxonomy.

### 3.5 Reference Rate Decomposition

CoT traces provide a secondary observable: the **reference rate** $R$, the fraction of traces that mention the algorithmic signal. For traces where reference is present, we can further classify each trace into one of three mutually exclusive categories over all $N$ turns:

$$N = N_{\text{follow}} + N_{\text{reject}} + N_{\text{no-ref}}$$

where:
- $N_{\text{follow}}$: traces that reference the signal and select the recommended action
- $N_{\text{reject}}$: traces that reference the signal and select a different action
- $N_{\text{no-ref}}$: traces that do not reference the signal

The reference rate is $R = (N_{\text{follow}} + N_{\text{reject}}) / N$. This decomposition separates reported acknowledgment from decisional integration. High $R$ with low $N_{\text{follow}} / N$ indicates that the model attends to the signal in its output but does not change its decision — the hallmark of the rejection regime. Note that explicit reference in the output establishes reported acknowledgment, not necessarily that the signal causally influenced the model's internal processing.

## 4. Connection to Paper 2: State Reconstruction Difficulty

Paper 2 defines the **state reconstruction difficulty** $D_L(t)$ as the KL divergence between the LLM's inferred posterior and the true posterior over candidates:

$$D_L(t) = \mathbb{E}\left[\text{KL}\left(P_L(C_t \mid H_t) \,\|\, P^*(C_t \mid H_t)\right)\right]$$

This connects to the present framework through the prior $\pi_L$, but the connection requires care: high $D_L(t)$ does not *necessarily* make $\pi_L$ more diffuse. It could also make $\pi_L$ confidently wrong — concentrated on incorrect candidates. The two cases have different implications for signal integration:

1. **Diffuse prior** (high entropy $H(\pi_L)$, high $D_L$): Alignment score $A_t$ is driven by chance overlap. For selective integrators (high $\beta$), integration fluctuates unpredictably. The pooling model produces a distribution dominated by $\pi_S$, effectively delegating to the algorithm.

2. **Confidently wrong prior** (low entropy $H(\pi_L)$, high $D_L$): The model is certain but incorrect. If $\pi_L$ is concentrated on candidates the algorithm ranks poorly, alignment $A_t$ is strongly negative, and selective integrators will reject the signal — precisely when they should not.

The relationship between $D_L(t)$ and the baseline action distribution $\pi_L$ is ultimately an empirical question. Our data provide some evidence: in Mastermind (where $D_L$ is generally high due to abstract codes), granite-8b shows *higher* follow rates than in Wordle, consistent with the diffuse-prior pathway. But confirming this interpretation requires measuring both $D_L$ and $H(\pi_L)$ at matched game states, which we leave to future work.

The conceptual link between the two papers: Paper 2's coordination principle (assign LLMs to low-$D_L$ phases) determines *when* the LLM acts; the present framework determines *how* the LLM incorporates algorithmic guidance during those phases. A fully unified account awaits an explicit model of how $D_L(t)$ shapes the baseline distribution.

## 5. Testable Predictions

### 5.1 Alignment Model vs. Constant-Weight Baseline

**Statement**: A fitted alignment-modulated model ($\alpha_t = \sigma(b + \beta A_t)$) predicts held-out LLM decisions better than a constant-weight model ($\alpha_t = \sigma(b)$), specifically in game states where the algorithm's recommendation conflicts with the model's baseline preference.

**Rationale**: If $\beta > 0$ matters, the alignment model should capture systematic variation in when the LLM follows vs. overrides the signal. The constant-weight model, by construction, cannot explain condition-dependent follow rates (e.g., CSS vs VOI differences within a model).

**Test protocol**: For each of 8 models (7 open-source + claude-4-sonnet), we pool per-turn binary follow outcomes across domains (Wordle, Mastermind, Mastermind Hard) and algorithms (CSS, VOI) in the informed condition. Each (domain, algorithm) combination has a distinct alignment score $\bar{A}$ estimated from baseline data (§2.5). We split games 1–50 (train) and 51–100 (test), fit both models on training turns, and evaluate held-out log-likelihood on test turns. The likelihood ratio test ($\chi^2$, 1 df) assesses whether the alignment model significantly improves over the nested constant-weight model ($\beta = 0$).

**Result**: Under zero-shot prompting, $\beta$ is not significantly different from zero for any model, including claude-4-sonnet ($\beta = -0.05$, $p = 0.48$). The constant-weight model is sufficient across all eight models:

| Model | $b$ (const) | $b$ (align) | $\beta$ | $\beta$ SE | $p$ | $\Delta$LL (test) |
|-------|:-----------:|:-----------:|:-------:|:----------:|:---:|:-----------------:|
| claude-4-sonnet | $-0.17$ | $-0.20$ | $-0.05$ | $0.94$ | $.48$ | $0.16$ |
| granite-3.3-8b | $-0.11$ | $-0.09$ | $0.06$ | $0.36$ | $.49$ | $0.29$ |
| gemma-3-27b | $1.75$ | $1.69$ | $-0.30$ | $0.52$ | $<.001$ | $6.97$ |
| mistral-7b | $0.95$ | $0.92$ | $-0.11$ | $0.46$ | $.20$ | $0.88$ |
| llama-3.3-70b | $-2.02$ | $-2.01$ | $0.10$ | $0.68$ | $.27$ | $0.67$ |
| llama-3.1-70b | $-1.93$ | $-1.91$ | $0.11$ | $0.65$ | $.20$ | $1.14$ |
| llama-3.1-8b | $-1.50$ | $-1.48$ | $0.08$ | $0.51$ | $.35$ | $0.53$ |
| codestral-22b | $-0.47$ | $-0.47$ | $0.03$ | $0.36$ | $.74$ | $0.13$ |

The one significant result (gemma-3-27b, $p < .001$) shows *negative* $\beta$: gemma follows *less* when alignment is higher, likely reflecting a ceiling effect (gemma's 86% follow rate leaves little room for upward modulation). Held-out $\Delta$LL values are uniformly small, confirming that the alignment predictor adds negligible out-of-sample explanatory power.

**Interpretation**: Two factors explain the null result for claude-4-sonnet:

1. *Narrow alignment range under zero-shot.* Claude-4-sonnet's alignment scores cluster tightly ($\bar{A} \in [-0.85, -0.70]$), providing insufficient predictor variance for $\beta$ to be identified. In contrast, the CoT traces (§3.2) reveal a 57pp CSS-VOI gap under chain-of-thought prompting — suggesting that explicit reasoning expands the effective alignment range by enabling the model to evaluate signal-prior agreement more finely.

2. *Algorithm-type insensitivity under zero-shot.* CSS-VOI follow rate gaps are negligible under zero-shot for all models (claude-4-sonnet: 31.9% CSS vs 32.9% VOI in Wordle; 51.2% CSS vs 49.4% VOI in Mastermind). The cross-domain transfer analysis confirms this is systematic: CSS-VOI gap correlations across domains are near zero ($r \approx 0$, n.s.), meaning algorithm-type sensitivity is not a stable trait under zero-shot prompting.

This establishes a **prompting-modality boundary**: the constant-weight special case ($\beta = 0$) adequately describes integration behavior under zero-shot conditions, while the full alignment-modulated model captures variation that only emerges under chain-of-thought reasoning. The selective integration regime (§3.2) is real but *reasoning-dependent* — it requires the model to explicitly evaluate prior-signal agreement, a process that zero-shot prompting does not reliably elicit.

**Supporting evidence — regime stability**: Despite $\beta \approx 0$, the constant-weight parameter $b$ varies substantially across models (from $b = -2.02$ for llama-3.3-70b to $b = 1.75$ for gemma-3-27b), and these base integration tendencies are highly stable across domains. Follow rate correlations between domain pairs exceed $r = 0.93$ ($p < 10^{-20}$), and 7 of 8 models maintain the same regime classification across all three domains. Integration tendency is a stable model-level property, not a task-specific behavior.

**Supporting evidence — performance conditioning**: Following signals confers heterogeneous benefit. Claude-4-sonnet gains +47.4pp win rate when following ($97.6\%$ vs $50.2\%$), while open-source models at ceiling show minimal gains ($\leq 5$pp). Across all models, following helps more when alignment is low ($+15.2$pp) than when alignment is high ($+1.3$pp), indicating that signals are most valuable precisely when they push the model away from its prior — consistent with the pooling model's prediction that influence requires prior-signal disagreement (§2.3).

**Connection to deeper integration (future work)**: The prompting-modality boundary motivates architectural interventions that implement the alignment-modulated weight directly rather than relying on emergent reasoning to discover it. If $\alpha_t = \sigma(b + \beta A_t)$ is computed at the system level — e.g., through constrained decoding that blends the LLM's logits with algorithmic scores at each token position — the selective integration regime becomes available by construction, independent of whether the model's reasoning explicitly evaluates signal quality. This is the subject of planned follow-up work.

### 5.2 Controlled Alignment Variation

**Purpose**: The observational CSS vs. VOI comparison confounds alignment with other signal properties (score scale, recommendation concentration, domain-specific factors). A controlled experiment that directly manipulates $A_t$ while holding other signal properties constant provides stronger identification of $\beta$.

**Design**: For a given algorithm (e.g., CSS), filter the presented recommendations to create two conditions:
- **High-alignment**: present only candidates that appear in the model's baseline top-$k$
- **Low-alignment**: present only candidates outside the model's baseline top-$k$

Both conditions use the same algorithm, score format, and presentation structure — only the overlap with $\hat{\pi}_L$ differs.

**What the model comparison predicts**: Fit the alignment model ($\alpha_t = \sigma(b + \beta A_t)$) and the constant-weight model ($\alpha_t = \sigma(b)$) to the combined data from both conditions. If the alignment model significantly outperforms the constant-weight model in predicting held-out choices, this confirms that $\beta > 0$ after controlling for confounds present in the observational CSS-VOI comparison.

**Important caveat**: Raw follow rate and even baseline-corrected $\hat{I}$ will differ between conditions for *any* positive $\alpha_t$, regardless of $\beta$. This is because changing the alignment changes the pooled distribution even at constant weight. The discriminating evidence is not whether $\hat{I}$ differs across conditions, but whether the *pattern* of differences across states is better captured by an alignment-modulated weight than a constant one.

**Protocol**: Run claude-4-sonnet, granite-8b, and llama-70b under both conditions ($n \geq 50$ games each). Evaluate models via held-out log-likelihood as in §5.1.

### 5.3 Cross-Generational Hypothesis

**Observation**: claude-4-sonnet shows a 57pp CSS-VOI follow gap in Mastermind; claude-4.6-sonnet shows approximately 24pp.

**Prospective hypothesis** (not a derived prediction): Successive model generations within a family will show convergence of follow rates across signal types. If this pattern holds, it would be consistent with decreasing $\beta$ or with improving prior calibration that raises $A_t$ for previously misaligned signal types.

**Why this is not a prediction from the model**: The narrowing gap could reflect changes in $\pi_L$, $\pi_S$ concentration, or other factors outside the framework. Extrapolating a two-point trajectory to claim future models will fall below 10pp is not warranted. We report this as a suggestive observation that motivates longitudinal study.

## 6. Design Implications

### Principle 1: Match Signal Type to Model Behavioral Response

Not all models benefit from the same signals. The behavioral regime determines signal provision strategy:

| Behavioral Response | Recommended Strategy |
|---------------------|---------------------|
| Integration | Provide highest-quality signal available; model will use it |
| Selective Integration | Prefer signal types that tend to align with model priors (e.g., VOI over CSS for claude-4-sonnet in Mastermind) |
| Rejection | Signal provision has negligible effect on decisions; computational cost may not be justified |

**Empirical grounding**: In Mastermind with claude-4-sonnet, switching from CSS to VOI signals increases follow rate from 23% to 80%. The practical relevance depends on whether this increased integration also improves task performance — which is an outcome-level question that the follow rate alone does not answer.

### Principle 2: Consider Uncertainty and Signal Reliability Jointly

The value of providing algorithmic advice depends on at least two factors:

1. **LLM uncertainty**: When the model is already confident in its decision (low $H(\pi_L)$), additional signals are unlikely to change behavior — and for high-$\beta$ models, a conflicting signal may trigger explicit rejection.
2. **Signal reliability**: A high-quality signal (large search space reduction, high information gain) is more likely to produce beneficial influence than a low-quality one.

A defensible decision rule is: provide the signal when its estimated benefit (given the model's behavioral regime and current uncertainty) exceeds its cost (compute for generating the signal + risk of detrimental influence). We do not formalize a specific threshold, as the cost-benefit tradeoff depends on deployment context.

Our data provide partial support: in Wordle, granite-8b follow rates are highest in early rounds (high entropy, ~5,000 candidates remaining) and decline as the game progresses. However, high uncertainty does not guarantee useful advice, and low uncertainty can reflect confident error.

### Principle 3: Regime Estimation Protocol

Before deploying a hybrid system, run a small diagnostic to estimate the model's behavioral response. We suggest:

1. **Baseline run** ($n \geq 30$ games): Establish $\pi_L$ from the model's unassisted behavior
2. **Informed run** ($n \geq 30$ games per signal type): Provide algorithmic signals, measure baseline-corrected follow rate $\hat{I}$
3. **Estimate regime**: Report $\hat{I}$ with confidence intervals rather than crisp classification thresholds. Models near regime boundaries (e.g., $\hat{I}$ between 5–15%) may require larger samples or additional diagnostics.

This protocol classifies the model's behavioral response at lower cost than a full evaluation, but the classification is a point estimate with associated uncertainty — it should not be treated as a permanent label for the model.

## 7. Motivating Analogies from Cognitive Science

The framework is motivated by — but does not depend on — parallels to human information processing:

**Reliability-weighted cue integration** (Ernst & Banks, 2002; Körding & Wolpert, 2004): Humans integrate multisensory cues by weighting each source approximately proportional to its reliability. Our logarithmic pool has a similar functional form, with $\alpha_t$ playing the role of a reliability-based weight. However, human cue integration is driven by sensory noise statistics, while our alignment modulation is driven by distributional agreement — a different mechanism. The analogy motivates the functional form but does not establish that LLMs integrate signals for the same computational reasons humans do.

**Anchoring effects** (Tversky & Kahneman, 1974): The rank imitation pattern (codestral-22b copying the first-listed candidate regardless of scores) resembles anchoring on presented information. The shuffled-ranking diagnostic is designed precisely to detect this — separating responses to signal *format* from responses to signal *content*.

**Dual-process analogy**: The LLM prior $\pi_L$ resembles fast, heuristic-based processing (System 1), while the algorithmic signal $\pi_S$ resembles slow, deliberate computation (System 2). That larger models show lower integration rates parallels the observation that domain expertise increases reliance on trained intuition. This remains an analogy, not a mechanistic claim.

## 8. Limitations

**Identifiability from observational data**: The parameters $(b, \beta)$ are identified only at game states where $\pi_L \neq \pi_S$ (§2.3). When prior and signal agree, integration is behaviorally invisible. Our baseline estimates of $\hat{\pi}_L$ are noisy (based on $\leq 100$ games per model-domain pair), and $A_t$ is estimated from these baselines rather than experimentally controlled, propagating uncertainty into parameter estimates. The controlled alignment variation experiment (§5.2) would provide stronger identification.

**Temperature-integration tradeoff**: Because the effective signal strength is $\alpha_t / \lambda$ (§1), the integration weight and signal temperature cannot be independently identified from choice data. We fix $\lambda$ from signal presentation properties and report sensitivity of $(b, \beta)$ estimates across plausible $\lambda$ values. This reduces but does not eliminate the identifiability concern — readers should interpret $\alpha_t$ as an effective integration weight conditional on the assumed $\lambda$, not as an absolute quantity.

**Trace observability**: For reasoning models with hidden chain-of-thought (gpt-oss-120b), trace-based diagnostics (reference rate, rejection rate) are uninformative. Behavioral regime classification must rely entirely on outcome-based measures ($\hat{I}$), which provide less interpretive richness.

**Stationarity**: We assume $(b, \beta)$ are fixed within a session. Models may adapt their integration behavior as context accumulates over the course of a game. Within-game variation in follow rates could reflect either non-stationarity or natural variation in $A_t$ across game states.

**Geometric pooling assumption**: The log-linear combination rule assumes multiplicative interaction in log-probability space. Alternative combination rules (arithmetic mixture, max-entropy fusion) would produce different predictions, particularly when $\pi_L$ and $\pi_S$ have near-disjoint support. We adopt logarithmic pooling because of its established theoretical properties (external Bayesianity, marginalization commutativity; Genest & Zidek, 1986), not because we have evidence ruling out alternatives.

## References

- Dietrich, F., & List, C. (2016). Probabilistic opinion pooling. In A. Hájek & C. Hitchcock (Eds.), *The Oxford Handbook of Probability and Philosophy*. Oxford University Press.
- Ernst, M. O., & Banks, M. S. (2002). Humans integrate visual and haptic information in a statistically optimal fashion. *Nature*, 415(6870), 429–433.
- Genest, C., & Zidek, J. V. (1986). Combining probability distributions: A critique and an annotated bibliography. *Statistical Science*, 1(1), 114–135.
- Körding, K. P., & Wolpert, D. M. (2004). Bayesian integration in sensorimotor learning. *Nature*, 427(6971), 244–247.
- Tversky, A., & Kahneman, D. (1974). Judgment under uncertainty: Heuristics and biases. *Science*, 185(4157), 1124–1131.
