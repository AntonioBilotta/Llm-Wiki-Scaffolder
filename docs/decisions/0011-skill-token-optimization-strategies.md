# ADR-0011: Skill token optimization strategies (deferred)

## Status
Proposed (2026-07)

## Context

Under Model D ([ADR-0009](0009-evaluate-user-level-vault-operational-customizations.md)), every wiki operation orchestrated by a user-level prompt or vault-level agent invokes multiple user-level skills in sequence. Each skill invocation carries a fixed cost:

- The skill's `SKILL.md` body is loaded into the model's context (typically 500–2000 tokens per skill).
- Execution overhead is small (a few filesystem reads and a JSON return).

For typical workflows orchestrated by user-level prompts:

| Workflow | Skill invocations | Estimated skill overhead |
|---|---|---|
| `/wiki-query "question"` | `wiki-detect-vault` → `wiki-search` → `wiki-read-page` × 3-5 → optional archive chain (3 skills) | ~4000 tokens |
| `/wiki-ingest raw/file.md` | `wiki-detect-vault` → `wiki-summarize-source` → `wiki-write-source-page` → `wiki-update-index` → `wiki-append-log` (+ N cross-ref edits via platform `edit`) | ~3500 tokens |
| `/wiki-lint` | `wiki-detect-vault` → `wiki-lint-check` × 2 (JSON + MD) → N frontmatter edits → `wiki-append-log` | ~2500 tokens |

The design already optimizes the "orchestrated workflow" case: prompts invoke `wiki-detect-vault` **once** and pass `vault_path=<...>` explicitly to subsequent skills, so detect is not re-invoked per skill call.

Residual token waste comes from three scenarios:

1. **Autonomous invocation from free chat.** If the user asks a wiki-related question directly (not via a prompt), Copilot may auto-invoke `wiki-search` for description matching. Without an explicit `vault_path`, the skill falls back on `wiki-detect-vault`. Ambiguous inputs may fire detect 2–3 times per session redundantly (~1200–1800 wasted tokens).

2. **Batch or CLI operations.** 10 sequential `/wiki-query` invocations = 10 × detect load = ~6000 wasted tokens for detect alone.

3. **Multi-vault workspaces.** In our multi-root setups, the disambiguation loop (ask-user on multiple vault candidates) adds ask/answer round-trips beyond the base skill cost.

The order of magnitude is not catastrophic: a typical Copilot chat exchange is 5–10k tokens, so an added 4k is ~40–80% workflow overhead. But it accumulates for power users and CI/batch scenarios.

## Decision

**Defer the implementation of skill token optimizations until the pilot (per ADR-0009 Follow-up) generates real cost data.** Meanwhile, document the identified optimizations and their trade-offs in this ADR, so we can implement them targeted at observed cost hotspots rather than speculatively.

The current Phase A/B/C implementation is *not* wasteful in absolute terms — the concern is cumulative cost for repetitive workflows.

## Identified optimizations

Ordered by ROI × non-breaking status (highest first).

### 1. `LLM_WIKI_ACTIVE_VAULT` environment variable

**Implementation:** `wiki-detect-vault` reads `$LLM_WIKI_ACTIVE_VAULT` first (env var pointing to an absolute vault path). If set and the target contains the `LLM Wiki` marker file, the skill returns immediately without any filesystem walk or ambiguity handling.

**Trade-off:** zero cost, opt-in via user's `.zshrc` / shell config or a `.env` at workspace root. Optimizes scenarios 2 and 3 completely. Adds ~5 lines to the skill body and a small env-check clause in whatever detection script/logic the skill uses.

**Verdict:** recommended MVP optimization.

### 2. `disable-model-invocation: true` on `wiki-detect-vault`

**Implementation:** add the frontmatter field to `skills/wiki-detect-vault/SKILL.md`. The skill becomes explicit-only — it no longer surfaces in the `/` slash-command picker and is not auto-invocable by description matching. It fires only when another skill/prompt/agent explicitly calls it.

**Trade-off:** appropriate for an internal primitive that users never invoke manually. Removes it from the slash-picker (micro loss of discoverability that doesn't matter). Prevents scenario 1 waste. Zero functional loss for orchestrated workflows.

**Verdict:** recommended MVP optimization, pairs naturally with #1.

### 3. Trim `wiki-detect-vault` SKILL.md body via `references/`

**Implementation:** move the detailed algorithm (5-step upward walk, ambiguity handling logic, marker file parsing) to `references/detection.md`. `SKILL.md` body shrinks from ~50 to ~20 lines. The reference file loads on demand only when the skill actually runs the full walk (progressive disclosure pattern from Anthropic's skill design).

**Trade-off:** ~300 tokens saved per invocation on average. Splits one file into two — slightly harder to review at a glance. Worth doing if detect fires often after optimizations 1+2; less urgent if 1+2 cut most invocations.

**Verdict:** second-tier optimization, apply if pilot shows detect still fires often even with 1+2 in place.

### 4. Consolidate hot paths into composite skills

**Implementation:** create `wiki-search-in-vault` = detect + search fused into a single SKILL.md. Similarly for read-page (`wiki-lookup-in-vault`).

**Trade-off:** loses composability with OpenSpec and other external skills that want to pass `vault_path` explicitly. Violates the "atomic capabilities" principle of Model D. Fewer skill loads but larger per-skill bodies. Net saving is unclear.

**Verdict:** **rejected**. The atomic-skill model is core to ADR-0009's composability rationale.

### 5. Cross-invocation state cache

**Implementation:** a stateful "vault context" primed at conversation start and referenced by subsequent skills without re-detection.

**Trade-off:** Copilot does not currently expose persistent state that skills can share across invocations. Would require platform-level support (e.g. a "session vars" API).

**Verdict:** **not applicable** with current Copilot API. Revisit if the platform evolves.

## Consequences

**If we implement 1 + 2 (recommended MVP), post-pilot if warranted:**

- Env-var users: near-zero detect cost per workflow.
- Autonomous-invocation scenarios: detect fires only when a skill explicitly requests it (i.e. always with intent).
- Combined impact: 70–80% reduction of the residual detect waste identified above.
- Cost to implement: ~15 lines of new code + a few lines in the skill description and body + brief documentation in [README.md](../../README.md) mentioning the env var.

**If we additionally implement 3:**

- Extra ~300 tokens saved per invocation, for the fraction of workflows where detect still runs the full walk.
- Cost: refactor `wiki-detect-vault/SKILL.md` into 2 files, update tests.

**If we do nothing (status quo, Phase A/B/C shipped as-is):**

- Token cost stays in the ~40–80% workflow-overhead range.
- Pilot may or may not reveal this as a real user-facing issue. Cheaper Claude/GPT models handle it fine; expensive models feel the friction.

## Follow-up

- After the ADR-0009 pilot: if token cost is flagged as an issue in real use, implement optimizations 1 and 2 first, measure improvement, then decide on 3.
- If pilot shows no perceived issue, leave the current architecture as-is and treat this ADR as a documented deferral rather than a to-do.
- If we do implement any of these, this ADR becomes `Superseded by ADR-NNNN` with the concrete implementation ADR.

## References

- [ADR-0009](0009-evaluate-user-level-vault-operational-customizations.md) — Model D architecture that introduced multi-skill orchestration
- [skills/wiki-detect-vault/SKILL.md](../../skills/wiki-detect-vault/SKILL.md) — the primary optimization target
- Anthropic's [progressive disclosure pattern for skills](https://code.claude.com/docs/en/skills) — reference for optimization #3
