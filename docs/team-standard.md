# Team standard: building an agent action

Every engineer on Payments, Accounts, or Platform follows this when adding or changing an agent action (a tool, prompt, model, or policy rule). Merge requests that miss an item do not merge. Exceptions need a written sign-off from Platform and Security in the merge request.

**Sources of truth:**

- Approval rules and thresholds: `standards/approval-policy.example.yaml`.
- Tool contracts: `standards/manifests/`.
- Process: this page.

Rules, skills, and the Greptile prompt point here instead of restating numbers. CI (`scripts/validate.py`) checks that they agree.

## The non-negotiables

1. **The model proposes; code decides.** No model output reaches a Helia API without passing through the output guard (for replies), the policy engine, and the tool gateway.
2. **Prompts are not controls.** Any rule that matters (limits, who can approve, which customer) is enforced in code. Leaking the system prompt must be harmless.
3. **Untrusted by default.** Customer messages, account fields, ticket history, knowledge-base text, and model output are all untrusted input.
4. **One way in.** Every tool is registered with a manifest and called only through the gateway. Unregistered tools return 403.
5. **Every irreversible action has a named human approver.** That is either the person who approved that action, or the accountable owner who approved the capped standing rule that allowed it.

## What needs a human

| Risk tier | Definition | Approval |
|---|---|---|
| R0 | Read-only, bound to the case's customer | Auto |
| R1 | Reversible, no money or identity impact | Auto, once the rollout gates are passed |
| R2 | Reversible, with billing or account-data impact | Human, unless an explicit, capped policy rule allows auto |
| R3 | Irreversible: money out, customer-visible messages | Human, unless a capped standing rule allows auto. The standing rule must be approved by its accountable owner (Finance for money, the support lead for replies), who is recorded as the approver of every action it authorizes |

New auto rules start `enabled: false`. If you cannot write an undo, the action is R3.

## How the gateway enforces approval

- **Policy re-check:** the gateway re-evaluates policy itself. `deny` stops the action. `human` requires a token.
- **Token checks:**
  - Signed, bound to a hash of (tool, canonical params, case ID, policy version), with a 15-minute time to live.
  - Consumed atomically (compare-and-set) before the Helia call. Any reuse is rejected.
  - If the policy version has changed since approval, the token is rejected and the action goes back for re-approval.
- **Audit fails closed:** the intent audit event is written durably before execution. If that write fails, nothing executes.

## What each tool may do

- **Least privilege:** one credential per tool, scoped to its endpoints. `customer_id` always comes from the case binding.
- **Model-chosen fields:** only these three kinds:
  - enums
  - bounded values
  - IDs proposed from **server-provided candidates** (for example, charge IDs that `look_up_account` returned in this case), which the gateway validates against that list

  Amounts, currency, and limits are always `source: derived`.
- **Money:** integer minor units plus an ISO 4217 currency, both taken from the source record. No currency conversion.
- **Writes:**
  - An idempotency key is required.
  - Retry only transient errors, at most 2 times, with the same key.
  - Read back after writing and map the result to `done`, `initiated`, or `failed`. Only `done` allows "completed" wording; a pending refund is `initiated`.
- **Undo data:** before-images go to the encrypted compensation store (gateway write, compensation-flow read, retention of the undo window plus 30 days). Never to the audit log, which keeps only a reference and a hash.
- **Reply text:** passes the output guard: sanitized, free of PII and foreign identifiers, links only to allowlisted domains, and every factual claim traced to a tool result or knowledge-base passage ID.
- **Rate and budget:**
  - Each manifest declares per-customer and global rate limits.
  - The orchestrator enforces per-model budgets, input caps, bounded parallel reads, and a 20 s deadline per turn (design section 2).

## What must be logged

Write one append-only audit event per step with these fields: `case_id`, `customer_ref`, `tool`, `params_hash`, `risk_tier`, `policy_version`, `policy_rule_id`, `decision`, `approver_id`, `token_id`, `model_id`, `prompt_version`, `result`, `verified`, `cost`, `latency_ms`.

`customer_ref` is pseudonymised. PII is redacted. Never log tokens, secrets, card data, before-images, or full prompts that contain customer data.

## What must pass before it ships

- [ ] Manifest in `standards/manifests/` passes CI: schema, tier, bounds, model-chosen versus derived fields, currency, idempotency, verify states, undo, rate limits, PII fields, owner team.
- [ ] Policy boundary tests in `standards/policy-tests.yaml`: an allow and a deny case per rule, at the cap minus 1, the cap, and the cap plus 1.
- [ ] Contract tests against the Helia sandbox, including timeout, unknown outcome, and pending states.
- [ ] Evals: golden set has no regression above 2 points. Adversarial set: zero unauthorized writes, at least 98% correct escalation. The set covers injection in the message, in account fields, and in knowledge-base documents. The worst-case cost check is under the cap.
- [ ] Kill-switch flag exists and defaults to **off** for new tools.
- [ ] Console card shows the action, the derived values, the evidence, and the undo path.
- [ ] `agent-security-review` passes. This applies to policy, standards, rules, skills, and architecture docs too.
- [ ] Greptile 5/5 with zero unresolved threads, via the `greploop` skill.
- [ ] Human approval from code owners: the owning team plus Platform. Finance for money rules. Security for the gateway, credentials, guards, prompts, `.cursor/`, and `.greptile/`.
- [ ] Shadow run on real traffic before any traffic sees it, and a rollout plan with exit gates.

## How work flows

Use one git worktree per feature (`worktree-feature` skill). Design with `grill-me`, scaffold with `new-agent-action`, self-check with `agent-security-review`, open the merge request with `ship-change`, then run `greploop` until 5/5. See [CONTRIBUTING.md](../CONTRIBUTING.md).

## Why this does not slow teams down

The scaffold skill generates the manifest, tests, and flag. CI catches drift before review. The approval UI, audit log, and evals come free with the gateway. Autonomy is earned with data, per action type, by enabling one policy rule, not by re-architecting.
