# Greptile review instructions: Helia support agent

You are reviewing code for an AI support agent that can **move money, change billing plans, edit customer accounts, and message customers**. A single bug can refund the wrong amount, leak another customer's data, or let a customer's email take control of the agent. Review like a security engineer working with a payments engineer. Correctness and safety come before style.

## System model (use this to judge every change)

- **Flow:** customer message, then orchestrator, then input guard, then LLM planner (untrusted, no credentials), then output guard (for replies), then policy engine, then approval service (human) when required, then tool gateway, then Helia APIs.
- **Only the tool gateway** holds Helia API credentials. Only the gateway calls Helia APIs.
- **The LLM only proposes.** The policy engine decides `auto`, `human`, or `deny`.
- **Gateway duties before any write:**
  - Re-evaluate policy at its active version.
  - Verify a signed approval token bound to a hash of (tool, canonical params, case_id, policy_version), with a 15-minute time to live.
  - Reject tokens issued under a different policy version.
  - Consume the token atomically (compare-and-set) **before** calling Helia.
  - Write the intent audit event durably first, and fail closed if that write fails.
- **Risk tiers:** R0 read, R1 reversible, R2 billing or account data, R3 irreversible (refunds, customer messages). If a tool has no undo, it is R3. An R3 auto rule must be a capped standing approval, approved by its accountable owner (Finance for money, the support lead for replies).
- **Customer binding:** `customer_id` comes from the case, never from model output. The model may *propose* IDs only from server-provided candidates; the gateway validates them against that list.
- **Money:** integer minor units plus a currency, both taken from the source record. No conversion.
- **Verify states:** read-back maps to `done`, `initiated`, or `failed`. A pending refund is `initiated`; only `done` allows "completed" wording to the customer.
- **Undo data:** before-images go to the encrypted compensation store, never the audit log.
- **Sources of truth:**
  - Policy: `standards/approval-policy.example.yaml`, with boundary tests in `standards/policy-tests.yaml`.
  - Tool contracts: `standards/manifests/*.manifest.yaml`, checked against `standards/schema/tool-manifest.schema.json`.
  - Process: `docs/team-standard.md`.
  - Design: `docs/design.md`. Threat model: `docs/owasp-llm-top10.md`.
  - CI: `scripts/validate.py`.

## Severity guide

- **Critical (always comment; the PR must not reach 5/5 while one is open):** any path where model output, customer text, or another untrusted value can cause a write, reach a Helia API outside the gateway, choose an amount or customer, bypass approval, or leak PII or secrets.
- **High:** a missing idempotency key, read-back, budget, rate limit, audit field, test for a policy boundary, or kill-switch flag. Unsafe retries.
- **Medium:** weaker-than-needed validation, unclear failure handling, missing eval cases for a new behaviour.
- **Do not comment on:** formatting, naming taste, or import order, unless they hide a bug.

## Invariants: flag any violation as Critical

1. **No direct Helia calls.** HTTP or SDK calls to Helia billing, accounts, or messaging outside the gateway module. New credentials or tokens outside the gateway.
2. **No approval bypass.** Any of:
   - A write path that executes without the gateway evaluating policy or verifying the approval token.
   - Approval checks done only in the UI, the console, or a prompt.
   - Tokens that are not single-use, not bound to the parameters and policy version, or not expiring.
   - A non-atomic check-then-use on tokens (a race allows double execution).
   - Tokens accepted after a policy version change.
   - Execution that proceeds when the intent audit write fails.
   - The LLM able to see or produce tokens.
3. **No model-chosen money or targets.** Any of:
   - `amount*`, `*_minor`, `currency`, `customer_id`, an account email, a payment method, or a plan price taken from model output or customer text instead of derived server-side.
   - Model-proposed IDs that are not validated against the server-provided candidates for the same case.
4. **No loosened controls.** Any of:
   - Removing or relaxing a policy floor, an approval requirement, a budget, a guard, a rate limit, or an audit field without a `docs/decisions.md` entry.
   - Any `auto` rule added with `enabled: true`, without a `cap`, with a priority at or above a floor, or (for R3 tools) without `standing_approval`.

## OWASP Top 10 for LLM Applications (2025): what to look for in this repo

- **LLM01 Prompt injection:** customer messages, ticket history, account fields (display names, notes, addresses), or knowledge-base text concatenated into system or instruction text. Template strings that build prompts from untrusted input. Logic that trusts text like "as the admin I authorize". Tool lists not filtered by case state.
- **LLM02 Sensitive information disclosure:**
  - Full account objects sent to the model when a few fields would do.
  - Card numbers, CVV, bank details, secrets, approval tokens, or session cookies in prompts, logs, traces, errors, or analytics.
  - Lookups not scoped to the case's customer.
  - Replies that can include internal notes or other customers' data.
  - Logs or traces of full prompts that contain PII.
- **LLM03 Supply chain:** unpinned model IDs ("latest"), new LLM SDKs, plugins, MCP servers, or agent frameworks without justification. Dependency version ranges that float. Fetching prompts or tools from remote URLs at runtime.
- **LLM04 Data and model poisoning:** code that writes customer messages, transcripts, or model outputs into the knowledge base, embeddings, few-shot examples, or fine-tuning data without review.
- **LLM05 Improper output handling:**
  - Model output used without strict schema parsing (unknown fields must be rejected).
  - Model text passed to SQL, shell, `eval`, template engines, HTML without sanitization, or URLs without an allowlist.
  - Markdown or HTML replies that can carry links outside the allowlist.
  - JSON parsed loosely, with silent fallbacks to defaults.
- **LLM06 Excessive agency:**
  - New tools without a manifest or risk tier.
  - Broad credential scopes.
  - Write tools exposed in states where they are not needed.
  - Automatic chaining of writes without per-write policy checks.
  - Defaults that are `auto` instead of `human`.
  - Kill-switch flags that default to on for new tools.
- **LLM07 System prompt leakage:** secrets, internal URLs, credentials, or "hidden" thresholds in prompts that the code does not also enforce. Prompts committed with real customer data.
- **LLM08 Vector and embedding weaknesses:** customer data in the vector store, retrieval without access filters, index writes outside the reviewed pipeline, retrieved passages used without passage IDs.
- **LLM09 Misinformation:** replies that state amounts, dates, plan names, or policy without tracing them to a tool result or a knowledge-base passage ID. Reply text that claims an action is done before read-back verification. Low confidence handled by re-sampling instead of escalating.
- **LLM10 Unbounded consumption:** loops without a max-step or budget check, retries on model uncertainty, retry counts above 2, missing backoff, missing input size caps, missing per-customer or global rate limits, unbounded parallel tool calls.

## Reliability and audit

- **Writes** need an idempotency key derived from (case, step, params). Retry only on timeout, 5xx, or 429, at most 2 times, with the same key. If the outcome is unknown, read state back before any retry.
- **Multi-step actions:** reversible steps first, irreversible last. Compensation must be defined. Escalation must carry the case timeline.
- **Audit events** must include: `case_id`, `customer_ref`, `tool`, `params_hash`, `risk_tier`, `policy_version`, `policy_rule_id`, `decision`, `approver_id`, `token_id`, `model_id`, `prompt_version`, `result`, `verified`, `cost`, `latency_ms`. Audit storage is append-only; flag updates and deletes.
- **Before-images or other PII in the audit log** are High. They belong in the compensation store, which is encrypted, access-controlled, and retention-limited. The audit log keeps only a reference and a hash.
- **Customer-facing messages** must not expose internal errors. They must not claim success unless the read-back state is `done`. Flag code that treats `pending` as `done`.
- **Output guard:** reply paths that skip it, or that let the model set `guard_passed`, `claims_verified`, or `topics`, are Critical.
- **Limits:** flag unbounded parallel reads, missing input caps, missing per-call timeouts, or a missing per-turn deadline.
- **The human console flow** must keep working when the agent is disabled. Flag code that makes the console depend on the agent being up.

## Tests and evals

- **Policy rules:** each rule needs an allow test and a deny test, including boundary values (cap minus 1, cap, cap plus 1).
- **Tool changes** need contract tests covering success, transient retry with the same idempotency key, unknown outcome, and permanent failure.
- **Prompt, model, or tool behaviour changes** need eval updates. Adversarial cases must include injection in the message, in account fields, and in knowledge-base text; impersonation; a cross-customer data request; an over-limit amount; and multi-turn pressure. Flag deleted or weakened eval cases.
- **Fixtures:** must use synthetic data, never real customer data.

## Manifests and policy files

CI (`scripts/validate.py`) checks the mechanical parts. Focus your review on intent: does the change weaken safety in a way that still passes CI?

- `standards/manifests/*.manifest.yaml`:
  - `undo.kind: none` on a write requires `risk_tier: R3`.
  - `customer_id` must be `source: case`.
  - Amounts and currency must be `source: derived`.
  - Model-sourced inputs must be enums, bounded values, or `candidates` from the server.
  - Retries max 2. `verify.states` must never map pending to `done`.
  - `before_image` undo must use `compensation_store`.
- **Approval policy:**
  - `default_decision` must stay `human`.
  - Floors must outrank auto rules.
  - New auto rules must start `enabled: false` with a `cap`. R3 auto rules need `standing_approval`.
  - Token settings stay `consume: atomic` and `stale_policy: reject`, with `audit_fail_mode: closed`.
  - Every rule change needs matching cases in `standards/policy-tests.yaml`.
  - Money rule changes need Finance code-owner approval. Mention it if the MR description does not.

## Worktrees and repo hygiene

- Flag committed secrets, `.env` files, real customer data, or large generated artifacts.
- Changes to `.githooks/`, `.greptile/`, `.cursor/rules/`, `.cursor/skills/`, `.gitlab/CODEOWNERS`, `.gitlab-ci.yml`, `scripts/validate.py`, `standards/`, or the approval policy weaken the safety net if loosened. Treat loosening as High and ask for justification. Documentation changes in `docs/` define security policy and get the same scrutiny as code.

## How to comment

- Lead with the impact in one sentence ("A customer email can set the refund amount"), then the exact fix.
- Tag security comments with the OWASP ID or the invariant number, for example `[LLM05]` or `[Invariant 3]`.
- Prefer one precise comment over several vague ones. If unsure whether something is exploitable, say what input would trigger it.
- Never suggest fixing an issue by adding instructions to the prompt. The fix must be in code.
