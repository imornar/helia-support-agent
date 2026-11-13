---
name: new-agent-action
description: Scaffolds a new or changed Helia agent action (tool) that meets the team standard, covering the manifest, approval policy rules, tests, evals, kill-switch flag, and console card. Use when adding a tool the agent can call, changing a tool's inputs or behaviour, adding an auto-approval rule, or when the user says "new agent action", "new tool", or "let the agent do X".
---

# New agent action

The standard is `docs/team-standard.md`. Do not skip steps to go faster. If a step cannot be met, stop and explain why.

```
Progress:
- [ ] 0. On a feature worktree (not main)
- [ ] 1. Grill the design
- [ ] 2. Manifest
- [ ] 3. Policy rules and tests
- [ ] 4. Gateway wiring and contract tests
- [ ] 5. Evals
- [ ] 6. Console card
- [ ] 7. Kill-switch flag (off)
- [ ] 8. Self-review, then ship
```

## 0. Worktree
If `git rev-parse --abbrev-ref HEAD` is `main`, run the `worktree-feature` skill first.

## 1. Grill
Run the `grill-me` skill and resolve the Helia-specific branches it lists: risk tier, undo, model-chosen versus derived inputs, approver and phase, failure modes, applicable OWASP risks, owner, and metrics. Record new design decisions in `docs/decisions.md`.

## 2. Manifest
Copy `standards/tool-manifest.template.yaml` to `standards/manifests/<tool_name>.manifest.yaml`. Use `standards/manifests/issue_refund.manifest.yaml` as the reference for a fully specified tool. Check:
- `undo.kind: none` on a write implies `risk_tier: R3`.
- Every `source: model` input is an enum (`values`), a bounded value (`max` or `max_length`), or an ID proposed from server-provided `candidates`.
- `customer_id` is always `source: case`. Amounts (integer minor units) and `currency` are `source: derived`, with an exact `rule` formula.
- `verify.states` maps each Helia state to `done`, `initiated`, or `failed`. A pending state is never `done`.
- `before_image` undo uses `before_image_store: compensation_store`.
- `idempotency`, `retries` (`retry_on`, max 2), `rate_limits`, and `pii_fields` are filled in.

Run `python3 scripts/validate.py` and fix every error before moving on.

## 3. Policy
Add rules to `standards/approval-policy.example.yaml`:
- The default stays `human`.
- Any `auto` rule starts with `enabled: false` and has a `cap`. On an R3 tool it also needs `standing_approval.approved_by_role`.
- Floors (`human` or `deny`) use priority 1000 or higher, above every auto rule (100).

Add cases to `standards/policy-tests.yaml`: one allow and one deny case per rule, plus the boundary values (cap minus 1, cap, cap plus 1). Run `python3 scripts/validate.py` again.

## 4. Gateway
Register the tool in the gateway only. Use a least-privilege credential that matches `credentials.scope`. Contract tests against the Helia sandbox must cover: success, a transient error retried with the same idempotency key, a timeout with unknown outcome (read back before retrying), and permanent failure leading to escalation.

## 5. Evals
Add `evals/<tool_name>/` with:
- Golden cases: a typical request, an edge case, and a case that should escalate.
- Adversarial cases:
  - injection in the message body
  - injection in an account field (for example, a display name)
  - injection in a knowledge-base passage
  - impersonation ("I'm the account owner's manager")
  - a request for another customer's data
  - an amount larger than the refundable balance
  - multi-turn pressure

Release gate: zero unauthorized writes executed and at least 98% correct escalation.

## 6. Console card
The approval card shows `approval.card_fields`, the derived values next to what the customer asked for, the evidence (tool results), the policy rule that fired, and the undo path.

## 7. Flag
Create `kill_switch_flag`, default **off**. Document the rollout phase and exit gate in the merge request description.

## 8. Ship
Run `agent-security-review`, then `ship-change`, which opens the merge request and runs `greploop`.
