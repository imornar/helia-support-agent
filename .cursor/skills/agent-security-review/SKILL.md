---
name: agent-security-review
description: Reviews the current branch diff against the OWASP LLM Top 10 (2025) and the Helia team standard before a merge request is opened. Use before shipping any change to tools, prompts, models, policy, guards, retrieval, the gateway, or the approval flow, or when the user asks for an agent or LLM security review.
---

# Agent security review

## Steps

1. Get the diff: `git diff origin/main...HEAD` and `git diff --stat origin/main...HEAD`. Run `python3 scripts/validate.py`; any failure is a blocker.
2. Classify the changed areas: tool or manifest, policy, gateway or credentials, prompt or model, guard, retrieval or knowledge base, console or approval, logging, or the safety net (docs, standards, rules, skills, Greptile, CI). Changes to the safety net are reviewed like code: does the change loosen a control or create drift between files?
3. Read the matching sections of `docs/team-standard.md` and `docs/owasp-llm-top10.md`.
4. Check every item below that applies, citing `file:line` evidence.
5. Report findings using the format at the end. Fix blockers before `ship-change`.

## Checklist

**Invariants (any failure is a blocker)**
- [ ] No Helia API call outside the gateway. No new credentials outside the gateway.
- [ ] No write executes without the gateway checking policy or a signed token bound to the parameters and policy version. The token is consumed atomically before the call. A stale policy version is rejected. The intent audit write fails closed.
- [ ] Amounts, currency, and customer IDs are derived. Model-proposed IDs are validated against server-provided candidates.
- [ ] Replies pass the output guard. The model cannot set `guard_passed`, `claims_verified`, or `topics`. Pending states never produce "done" wording.
- [ ] Before-images go to the compensation store, never the audit log.
- [ ] No approval check, budget, guard, rate limit, or audit field is removed or loosened without a matching decision record and code-owner sign-off.

**OWASP LLM**
- [ ] LLM01: untrusted text stays in data slots, not instructions. The tool list is filtered by state.
- [ ] LLM02: no new PII, card data, secrets, or tokens sent to the model or written to logs.
- [ ] LLM03: model IDs pinned. New dependencies, SDKs, plugins, or MCP servers justified and locked.
- [ ] LLM04/LLM08: no path that writes customer text into the knowledge base or embeddings.
- [ ] LLM05: model output parsed with a strict schema. Replies sanitized, links allowlisted. No model text in queries, shell, or templates.
- [ ] LLM06: new capability has a risk tier, defaults to human, and its flag is off.
- [ ] LLM07: nothing in prompts that is security-relevant and not enforced in code.
- [ ] LLM09: reply claims trace to tool results or knowledge-base passage IDs.
- [ ] LLM10: budgets, retry limits (no retry on uncertainty), input caps, and rate limits are intact.

**Reliability and audit**
- [ ] Idempotency key on writes. Read back after the write. Unknown outcome leads to a read before any retry.
- [ ] Partial failure: reversible steps first, compensation defined, escalation includes the timeline.
- [ ] Audit event fields complete (see the team standard).

**Tests**
- [ ] Policy allow and deny cases at the boundaries. Contract tests cover failure paths.
- [ ] Prompt or model change: golden and adversarial evals pass, and a shadow replay is planned.

## Report format

```
Agent security review: <branch>
Blockers (must fix):
- [LLM06] src/tools/refund.ts:42 - amount read from proposal.amount; derive from charge.
Warnings:
- [LLM10] src/orchestrator/loop.ts:88 - new step not counted against the call budget.
Passed: invariants 3/4, OWASP 8/9, reliability 3/3, tests 2/2
Verdict: BLOCKED | READY FOR MR
```
