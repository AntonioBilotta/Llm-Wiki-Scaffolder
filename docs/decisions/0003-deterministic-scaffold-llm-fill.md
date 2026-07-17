# ADR-0003: Deterministic scaffold + LLM semantic fill split

## Status
Accepted (2026-07)

## Context

Scaffolding an LLM Wiki vault involves a mix of two very different kinds of work:

1. **Structural**: create a fixed directory tree, copy templates, substitute placeholders, enforce invariants (never write into `raw/`, keep `wiki/` content folders empty, keep the signpost minimal).
2. **Semantic**: write 4–5 project-specific "suggested first questions" in `wiki/overview.md`; optionally add short domain-specific notes to one of the three agent files.

Both must happen in one invocation of `/new_llm_wiki_vault`. Two extreme designs are possible:

- **Fully deterministic**: a script does everything, including generating the seed questions from a template. Downside: seed questions become generic ("What are the main entities?"), losing the whole point of tailoring them to the user's specific project.
- **Fully LLM-driven**: the LLM creates directories, writes files, substitutes placeholders. Downside: non-deterministic output, no guaranteed reproducibility, high risk of quietly violating Karpathy invariants (e.g. pre-populating `wiki/entities/` "helpfully").

## Decision

Split the work along the structural/semantic boundary:

- **Deterministic** (`scaffold.py`, Python stdlib):
  - Directory creation
  - Template copy
  - Placeholder substitution (`{{PROJECT_NAME}}`, `{{DOMAIN_TYPE}}`, `{{LANGUAGE}}`, `{{DOMAIN_SPECIFIC_CONVENTIONS}}`, `{{DOMAIN_EXTRA_TYPES}}`)
  - State detection (`absent | existing_llm_wiki | existing_non_wiki`)
  - Karpathy invariants (enforced with `if/raise`, not hoped for)
  - Structured JSON output for the orchestrator

- **LLM-driven** (orchestration prompt):
  - Intent parsing from natural language
  - Wizard for missing parameters (`vscode_askQuestions`)
  - Post-scaffold semantic fill: 4–5 seed questions + optional domain notes on agents

The LLM never touches directory creation or template copy. The script never generates semantic content.

## Consequences

**Positive**
- Reproducibility guarantee: two `scaffold.py` runs with identical flags produce byte-identical output. Critical for `--upgrade` mode, which must be safely re-runnable.
- Karpathy invariants cannot be violated by construction. An LLM that "helpfully" pre-fills `wiki/entities/` is out of scope — the script refuses.
- The script can be tested independently of the LLM.
- The script can be invoked standalone from the CLI, from CI, or from any other agent host that can execute a subprocess. Not locked to Copilot.
- Semantic quality preserved where it matters: seed questions are tailored to the user's project name and domain description, which no template could achieve.
- The prompt file stays small because it delegates the heavy lifting.

**Negative**
- Two artifacts to keep in sync (the script's flag set + the prompt's invocation grammar). Mitigated by the prompt referencing `scaffold.py --help` for the source of truth.
- Some redundancy: the Karpathy invariants are documented both in the script (`if/raise`) and in the prompt (`## Karpathy pattern` section). Kept as belt-and-suspenders: if a future prompt refactor bypasses the script, the invariants remain as LLM behavior rules.

**Neutral**
- The split enforces a discipline: any new scaffold feature must be classified as structural (goes to script) or semantic (goes to prompt). This is often the right signal to catch feature creep.

## Alternatives considered

- **Fully deterministic** — rejected because generic seed questions defeat the "vault feels tailored" experience that motivates using the scaffolder over manual setup.
- **Fully LLM-driven** — rejected for the reproducibility, invariant enforcement, and standalone-CLI reasons above.
- **Script emits placeholders for seed questions; LLM fills them in a second pass** — approximately what we do. The distinction is whether the LLM does the filling in the same conversation turn (yes, current design) or via a separate later invocation (rejected — worse UX).
