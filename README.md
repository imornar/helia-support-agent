# Helia support agent

Agreed design for the Helia support agent: the model proposes, deterministic code decides, humans approve what cannot be undone, and one tool gateway is the only caller of Helia's APIs.

Feature work belongs on its own git worktree. `main` stays the anchor so parallel agents can each check out a branch without sharing a working tree.

**Scope:** this is a design repository, not the bot itself. CI validates that the policy, manifests, and docs are consistent, and runs the policy boundary tests against a reference evaluator. Runtime security and performance (gateway behaviour, latency, cost) can only be validated once the runtime exists, through the contract tests, evals, and shadow phase described in the design.

## Read in this order

1. [docs/draft-review.md](docs/draft-review.md): what is wrong with the original draft and what replaces it
2. [docs/design.md](docs/design.md): architecture diagram, agent loop, human-in-the-loop line, failure handling, guardrails, rollout
3. [docs/team-standard.md](docs/team-standard.md): one-page standard every agent action must meet
4. [docs/owasp-llm-top10.md](docs/owasp-llm-top10.md): threat model mapped to controls
5. [docs/decisions.md](docs/decisions.md): decisions, trade-offs, assumptions to confirm

## Repo map

| Path | Purpose |
|---|---|
| `standards/` | Approval policy and its boundary tests, the six tool manifests, the manifest template and JSON Schema (sources of truth) |
| `scripts/validate.py` | Consistency checks run by CI and before every MR |
| `.gitlab-ci.yml` | Runs the validator and renders every Mermaid diagram |
| `.cursor/rules/` | Agent rules: project invariants, worktrees, agent actions, LLM security, docs |
| `.cursor/skills/` | `worktree-feature`, `grill-me`, `new-agent-action`, `agent-security-review`, `ship-change`, `greploop` |
| `.greptile/` | `rules.md` (the custom review prompt) and `config.json` |
| `.gitlab/` | Merge request template and CODEOWNERS |
| `.githooks/` | Opt-in hook that blocks commits on `main` |

## Getting started

See [CONTRIBUTING.md](CONTRIBUTING.md).
