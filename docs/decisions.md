# Decision log

Decisions agreed during the design interview (grill-me), with the trade-off each one accepts. To change a decision, add a new entry; do not edit old ones.

| # | Decision | Chosen | Trade-off accepted |
|---|---|---|---|
| D1 | Autonomy for side effects | Phased. Every write needs a human at launch. Low-risk tiers become auto per action type once metrics pass, through a versioned policy. | Slower money cases early, in exchange for evidence-based autonomy. |
| D2 | Refund approvers | Flat. Any trained support agent with `action_approver` may approve any amount. | Weaker separation of duties on large refunds. Mitigated by per-approver daily digests to Finance and nightly reconciliation. |
| D3 | Stack for standards | Stack-agnostic, with TypeScript examples | Examples may need translation if a team uses another language. |
| D4 | AI tooling | Cursor only: `.cursor/rules` and `.cursor/skills` | Other agents (Claude Code, Codex) will not pick up the rules automatically. |
| D5 | Greptile config | One prompt file, `.greptile/rules.md`, plus a small `.greptile/config.json` for settings. Auto-approve is off. | Rules are prose, not individually disableable by ID. |
| D6 | Worktree enforcement | Always-on rule, `worktree-feature` skill, and an opt-in git hook that blocks commits on `main` | The hook is opt-in locally; the real enforcement is GitLab's protected branch. |
| D7 | Diagram format | Mermaid in markdown, with OWASP tags on components | Layout control is limited compared with a drawing tool. |
| D8 | Approval for irreversible actions (review fix) | A human approves each action, **or** the accountable owner approves a capped standing rule (Finance for refunds, the support lead for replies). That owner is recorded as the approver on every action the rule authorizes. | Small automatic refunds have no per-action human. Accepted for capped, reconciled amounts. |
| D9 | Undo data (review fix) | Before-images live in an encrypted, access-controlled compensation store with retention of the undo window plus 30 days. The audit log keeps only a reference and a hash. | One more store to run and secure. |
| D10 | Money representation (review fix) | Integer minor units plus ISO 4217 currency, taken from the source record. Caps are in USD; other currencies stay human until per-currency caps exist. | Non-USD customers get slower refunds until caps are defined. |
| D11 | Latency and cost budgets (review fix) | Budgets are set per model. Automated latency is measured separately from human approval wait. The worst-case cost check at release replaces a single token number. | Budgets must be re-derived when model prices change. |
| D12 | Drift control (review fix) | Policy YAML, manifests, and the team standard are the sources of truth. CI (`scripts/validate.py` plus Mermaid render) enforces consistency. | Small amount of tooling code in a design repo. |

## Assumptions to confirm with stakeholders

- **Volume and latency:** about 5,000 cases a day. p95 under 10 s of automated latency for read-only answers.
- **Budget:** $0.10 of model spend per case (Finance to confirm).
- **Earned-auto refund ceiling:** $50 (Finance to confirm).
- **Data:** the model provider has zero data retention and does not train on our data (Legal to confirm).
- **Console:** the existing console can host an agent side panel (console team to confirm).
- **Code owners:** the GitLab groups in `.gitlab/CODEOWNERS` are placeholders until real group names are known.
