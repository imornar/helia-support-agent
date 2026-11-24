# Contributing

## One-time setup

```bash
git clone git@git.toptal.com:screening-ops/Ivan-Mornar.git
cd Ivan-Mornar
git config core.hooksPath .githooks    # blocks commits on main
glab auth login --hostname git.toptal.com
```

Greptile must be installed on the GitLab project for reviews and `greploop` to work.

## Validate locally

```bash
pip install pyyaml jsonschema
python3 scripts/validate.py
```

The validator checks manifests against the schema and semantic rules, policy invariants, the boundary tests in `standards/policy-tests.yaml`, that the design table, policy, and manifests agree, audit-field sync between the standard and the Greptile prompt, relative links, and em dashes. CI runs the same script.

## Workflow for every change

| Step | What | Skill |
|---|---|---|
| 1 | Create a worktree and branch off `origin/main` | `worktree-feature` |
| 2 | Resolve the design: tier, approval, failure modes, OWASP risks | `grill-me` |
| 3 | Build. For agent actions, follow the scaffold | `new-agent-action` |
| 4 | Self-review against the standard and OWASP LLM Top 10 | `agent-security-review` |
| 5 | Push, open the merge request with the template | `ship-change` |
| 6 | Iterate until Greptile gives 5/5 with zero unresolved threads | `greploop` |
| 7 | Human code owners approve; merge; remove the worktree | `worktree-feature` |

In Cursor, ask for a skill by name, for example "use ship-change".

## Worktrees

```bash
git worktree add -b feat/payments/refund-tier-cap ../Ivan-Mornar-worktrees/refund-tier-cap origin/main
cd ../Ivan-Mornar-worktrees/refund-tier-cap
# ...work, commit, ship...
git worktree remove ../Ivan-Mornar-worktrees/refund-tier-cap && git branch -d feat/payments/refund-tier-cap
```

- **Branch names:** `<type>/<team>/<slug>`. Types: `feat`, `fix`, `chore`, `docs`, `design`. Teams: `payments`, `accounts`, `platform`.
- **Isolation:** one person or agent per worktree. To compare models, give each model its own worktree, for example `design/<model-name>`.

## Review rules

- **Greptile:** reads `.greptile/rules.md`. Do not loosen it in the same merge request that needs it. Code owners for `.greptile/` include Security.
- **greploop:** never weakens a control to satisfy a comment. Security threads it disagrees with stay open for a human.
- **Code owners** (`.gitlab/CODEOWNERS`):
  - The owning team and Platform, always.
  - Finance, for money rules.
  - Security, for the gateway, credentials, guards, and prompts.
- **Server-side protection:** set `main` as protected in GitLab, with code-owner approval required. The local hook is a convenience, not the control.

## Writing docs

Short beats long. Lead with the decision and the trade-off. Architecture changes update the diagram in `docs/design.md` and add a row to `docs/decisions.md`. No em dash characters.
