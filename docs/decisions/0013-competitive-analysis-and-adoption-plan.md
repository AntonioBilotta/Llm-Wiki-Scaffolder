# ADR-0013: Competitive analysis (vanillaflava, nvk, InfraNodus) and idea-adoption ranking

## Status
Accepted (2026-07)

## Context

Three third-party projects overlap with `llm-wiki-scaffolder`'s scope. Each takes a different position on the same design space (Karpathy LLM-wiki pattern), and each ships ideas we do not currently implement. This ADR records the comparison, the decision to keep the current project rather than migrate, and a ranked adoption plan for the ideas worth cannibalizing.

### The three projects at a glance

| Project | Category | Runtime target | Scope | Signal (2026-07) |
|---|---|---|---|---|
| [`vanillaflava/llm-wiki-skills`](https://github.com/vanillaflava/llm-wiki-skills) | Peer skill pack (6 `.skill` bundles under [agentskills.io](https://agentskills.io/specification)) | Claude Desktop GUI first; Claude Code, Codex, Gemini, Copilot | Comparable to ours: config, ingest, query, lint, integrate, crystallize | 58★, 5 releases |
| [`nvk/llm-wiki`](https://github.com/nvk/llm-wiki) | Superset product (30+ commands, native Claude/Codex plugin, benchmarks harness) | Claude Code source of truth; Codex, OpenCode, Pi/DS4 generated mirrors | Far broader: multi-agent research, thesis, collect, inventory, dataset, archive, retract, assess, session capture | 903★, 91 forks, 52 releases, 4 contributors, product website |
| [`infranodus/skill-llm-wiki`](https://github.com/infranodus/skills/blob/master/skill-llm-wiki/SKILL.md) | Vertical commercial layer (single Claude Skill + MCP server) | Claude Skill format (Code/Web/Desktop/OpenClaw) | Narrow but deep: gap analysis, ontology triples, GraphRAG, structural diagnostics via commercial InfraNodus MCP | Freemium commercial dependency |

### Where our project is defensibly different

- **VS Code Copilot Agent Mode as first-class target** — none of the three build for this runtime with the same fidelity (correct `tools:` frontmatter, `user-invocable`, `applyTo:` instructions, agent-mode vs ask-mode discipline; see [userMemory](../../README.md) notes).
- **Multi-role restricted agents** (`@wiki-reader` / `@wiki-maintainer` / `@wiki-auditor`) with tool-restriction per role. No comparable pattern in the three.
- **Deterministic Python scaffolder** ([bin/scaffold.py](../../bin/scaffold.py)) with `--json-out`, `--detect-only`, `--upgrade`, `--force-retype`. `nvk/llm-wiki`'s `/wiki init` is LLM-driven; the others have no scaffolder.
- **Domain-type presets** ([templates/overview/](../../templates/overview/)) with pre-configured folder taxonomy and page types for 8 domains. None of the three ship domain presets.
- **ADR trail + `AGENTS.md` multi-assistant bridge** for Codex/Aider/Cursor.

### Where the three each beat us

**vanillaflava (peer):**
- `wiki-crystallize` as a first-class operation for distilling long sessions into wiki pages — a pattern Karpathy calls out explicitly.
- `reliability: high/medium/low` frontmatter + auto-generated `## Pending Review` section flagging low-confidence claims.
- Schema-driven: `wiki-schema.md` + template registry editable *by the user* instead of hard-coded in Python.

**nvk (superset):**
- Parallel multi-agent research (`/wiki:research --deep/--retardmax`, 5/8/10 agents).
- Thesis-driven investigation with balanced pro/contra agents + anti-confirmation-bias.
- Automated session capture with rehydrate and digest promotion.
- Feedback curator (`.sessions/feedback/`) for high-signal corrections.
- Collector / inventory / dataset as distinct layers.
- `/wiki:retract` with blast-radius map of downstream claims.
- `/wiki:assess <repo>` gap analysis (repo vs wiki vs market).
- Query-lite split (~2.8 KB) vs full skill (~25 KB) with documented ~70% instruction reduction.
- Dual-linking: every cross-reference is `[[wikilink]] ([label](../path.md))`.
- Confidence scoring on articles.
- Fuzzy intent router (`/wiki <NL>` → subcommand).
- Deterministic CLI companion (`./scripts/llm-wiki lint/schema/archive`) parallel to the LLM skills.

**InfraNodus (vertical):**
- Content gap analysis (`generate_content_gaps`) — genuinely unique across the field.
- Ontology folder with `[[a]] [relation] [[b]]` triples as bridge between markdown and graph engine.
- Structural diagnostics per page (`biased / focused / diversified / dispersed`).
- GraphRAG retrieval instead of top-k chunk RAG.
- Gap → todos (`generate_research_questions/ideas`) making the wiki self-directing.
- Latent topics detection (concepts implicit in text but not yet pages).
- Named persistent memory graphs across sessions.
- Tier classification at setup time (Light/Medium/Heavy).

### Forces at play

- **Cost of migration.** Adopting any of the three as base means losing domain presets, restricted role agents, deterministic scaffolder, ADR discipline. High.
- **Cost of doing nothing.** We keep shipping without gap analysis, without session distillation, without token-optimized query lite, without dual-linking. Users comparing us to the three see visible feature gaps.
- **Cost of cannibalizing selectively.** Each idea below is portable to our architecture without external dependencies (except one InfraNodus-inspired feature, which we replicate with pure LLM reasoning rather than the commercial MCP).
- **Runtime lock-in.** vanillaflava spans agents; nvk is Claude-first; InfraNodus needs their commercial MCP. Our VS Code Copilot depth is a moat only if we don't dilute it.

## Decision

**Keep `llm-wiki-scaffolder` as the base.** Do not migrate to any of the three. The differentiators (VS Code Copilot Agent Mode + multi-role restricted agents + deterministic scaffolder + domain presets + ADR trail) occupy a defensible niche none of them cover.

**Cannibalize selectively.** Adopt the ideas below, ranked by ROI (value delivered ÷ implementation cost). Each adoption gets its own follow-up ADR (or is folded into an existing atomic skill's evolution) before implementation — this ADR is the anchor, not the design.

### Ranked adoption plan

**Tier 1 — Adopt next (high value, low-to-medium cost, no external dependencies)**

| # | Idea | Source | ROI rationale | Implementation sketch |
|---|---|---|---|---|
| 1 | **Dual-linking on every cross-reference** | nvk | Portability across Obsidian / VS Code / GitHub / plain reader with ~zero code | Extend [skills/wiki-write-source-page/scripts/write_source_page.py](../../skills/wiki-write-source-page/scripts/write_source_page.py) and [skills/wiki-write-analysis/scripts/write_analysis.py](../../skills/wiki-write-analysis/scripts/write_analysis.py) to emit `[[slug]] ([label](../path.md))` |
| 2 | **`reliability:` frontmatter + `## Pending Review` section** | vanillaflava | Quality signal on ingested pages; near-zero infra cost | Add to `wiki-summarize-source` (assess `high/medium/low`) and `wiki-write-source-page` (emit frontmatter + optional section) |
| 3 | **`wiki-crystallize` skill (session distillation)** | vanillaflava | Karpathy-canonical pattern; closes the "chat history disappears" gap | New atomic skill `skills/wiki-crystallize/`; composes `wiki-write-analysis` + `wiki-update-index` + `wiki-append-log`. Explicit user invocation, not auto |
| 4 | **`wiki/ontology/` folder with append-only triples** | InfraNodus | Bridge to Obsidian graph view / [infranodus.com](https://infranodus.com/) *without* commercial dependency | Side-effect of `wiki-write-source-page` and `wiki-write-analysis`: append `[[a]] --relation--> [[b]]` lines to `wiki/ontology/<section>.md`. Never overwrite |

**Tier 2 — Adopt soon (medium value, medium cost)**

| # | Idea | Source | ROI rationale | Implementation sketch |
|---|---|---|---|---|
| 5 | **`wiki-gap-check` skill** | InfraNodus (replicated w/o MCP) | Turns the wiki into a self-directing research partner; killer differentiator vs vanillaflava | New skill: read `wiki/ontology/*.md` + `wiki/index.md`, identify under-bridged clusters via LLM reasoning, write `wiki/todos/gaps.md` with research questions. Zero external deps |
| 6 | **Query-lite split** | nvk | ~70% token reduction on the common lookup path; measurable win | Fork `skills/wiki-query/` into `wiki-query` (full, with archival) and `wiki-query-lite` (read-only, no `wiki-write-analysis` composition). Both visible in `/` picker |
| 7 | **Latent-topics + structural diagnostics as new audits in `wiki-lint-check`** | InfraNodus (replicated) | Extends existing skill; no new surface area | Add audits: `latent_topics` (entities cited N+ times without own page), `structural_state` per page (`biased/focused/diversified/dispersed`) |
| 8 | **Tier classification at scaffold time** | InfraNodus | Better first-run UX, adapts index structure to expected volume | Add `--tier {light,medium,heavy}` flag to `bin/scaffold.py`; wizard asks; `heavy` adds `wiki/index/by-cluster/` scaffold |

**Tier 3 — Consider later (high value, high cost)**

| # | Idea | Source | Deferral reason |
|---|---|---|---|
| 9 | **`/wiki-retract <source>` with blast-radius map** | nvk | Requires cross-reference tracking not currently in our atomic skills; nontrivial design |
| 10 | **Automated session capture (light)** | nvk | Depends on Copilot Chat hooks that are not stable API; revisit when VS Code exposes them |
| 11 | **Multi-topic hub model (`hub/topics/<slug>/`)** | nvk | Changes the whole "one vault per project" mental model. Deep design decision, not a bolt-on |
| 12 | **Parallel multi-agent research** | nvk | Requires subagent orchestration patterns we haven't validated at scale on Copilot; deferred until agent-of-agents plumbing is stable |

**Rejected (not adopted)**

| # | Idea | Source | Rejection reason |
|---|---|---|---|
| — | Migrate base to vanillaflava, nvk, or InfraNodus | all | Loses our differentiators (VS Code Copilot depth, restricted role agents, deterministic scaffolder, domain presets). Documented above |
| — | Depend on InfraNodus MCP server directly | InfraNodus | Commercial lock-in; freemium rate limits; runs against our zero-runtime-dependency principle ([ADR-0001](0001-python-stdlib-only.md)). Replicate the ideas with pure LLM reasoning instead |
| — | Adopt `.skill` bundle packaging | vanillaflava, InfraNodus | Our skill layout is already installable to `~/.copilot/`, `~/.claude/`, `~/.agents/` — the three-way mirror gives us broader coverage than a single bundle format |
| — | Retardmax mode | nvk | Cute but out of scope for a knowledge-base scaffolder aimed at durable synthesis |

## Consequences

**Positive:**
- Documented, ranked plan means Tier 1 items can move to implementation ADRs (0014, 0015, 0016, 0017) without re-litigating the base direction.
- Rejecting migration is now traceable: future contributors asking "why not just use nvk?" get a concrete answer.
- Cannibalization is bounded: 8 concrete ideas across two tiers, not open-ended.
- The rejected InfraNodus MCP dependency preserves the [ADR-0001](0001-python-stdlib-only.md) "zero runtime dependency" invariant.

**Negative:**
- Tier 1 alone is 4 new/extended skills — a nontrivial workload before pilot data can validate the choices.
- Some ideas (gap analysis without the InfraNodus MCP) require the LLM to do graph reasoning without a real graph engine backing it; quality may be lower than the commercial reference. Mitigated by keeping the `wiki/ontology/` folder Obsidian- and InfraNodus-compatible so users *can* opt in to their MCP or graph plugin externally.
- Continued divergence from the three peers means our users can't trivially switch to them and back — we accept this as the cost of a defensible niche.

**Neutral:**
- Tier 3 items remain parked. If pilot use surfaces demand for `/wiki-retract` or multi-topic hub, we revisit here.
- No changes to installer, prompt format, or vault layout are triggered by this ADR alone. Each adopted idea comes with its own ADR that decides layout impact.

## Alternatives considered

1. **Migrate wholesale to `nvk/llm-wiki`.** Rejected: Claude-first runtime, no VS Code Copilot depth, no restricted role agents, and the "hub + topics" model breaks our "one vault per project" mental model.
2. **Migrate wholesale to `vanillaflava/llm-wiki-skills`.** Rejected: comparable scope but no domain presets, no restricted role agents, no deterministic scaffolder — we would lose more than we gain, in exchange for slightly better cross-agent distribution.
3. **Add `infranodus/skill-llm-wiki` as a required dependency.** Rejected: commercial MCP, freemium rate limits, violates [ADR-0001](0001-python-stdlib-only.md).
4. **Do nothing.** Rejected: visible feature gaps (no session distillation, no gap analysis, no dual-linking) become adoption blockers over time.
5. **Adopt all Tier 1 + Tier 2 + Tier 3 immediately.** Rejected: Tier 3 items each need their own design ADR and validation; bundling them here would violate the "one decision per file" convention documented in [README.md](README.md).

## Follow-ups

Tier 1 adoptions get their own ADRs before implementation:

- ADR-0014: Dual-linking on every cross-reference
- ADR-0015: `reliability:` frontmatter + `## Pending Review` section
- ADR-0016: `wiki-crystallize` skill
- ADR-0017: `wiki/ontology/` folder with append-only triples

Tier 2 items are captured here and may either get their own ADR later or be folded into an evolution of the existing skill (e.g. #7 folds into `wiki-lint-check`). Tier 3 items remain parked until pilot data justifies the effort.
