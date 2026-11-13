## What and why

<!-- One or two sentences. Link the issue. -->

## Change type

- [ ] Tool or manifest
- [ ] Approval policy
- [ ] Prompt or model
- [ ] Guard, retrieval, or knowledge base
- [ ] Gateway, credentials, or approval service
- [ ] Console
- [ ] Docs or tooling only

## Safety

- Risk tier of affected actions (R0 to R3):
- Approval behaviour change (who approves, what becomes auto, or "none"):
- OWASP LLM risks touched (LLM01 to LLM10) and how they are handled:
- Kill-switch flag and its default:
- Undo path, or "irreversible":

## Checklist (docs/team-standard.md)

- [ ] Built on its own worktree and branch, not `main`
- [ ] `python3 scripts/validate.py` passes (CI runs it too)
- [ ] Policy rule changes have matching cases in `standards/policy-tests.yaml`
- [ ] No Helia API calls outside the gateway; no model-chosen amounts, targets, or customer IDs
- [ ] Policy tests include allow, deny, and boundary values
- [ ] Contract tests cover transient retry, unknown outcome, and permanent failure
- [ ] Evals updated; adversarial set has zero unauthorized writes and at least 98% correct escalation
- [ ] Audit event fields complete; no PII, secrets, or tokens in logs
- [ ] `agent-security-review` verdict: READY FOR MR
- [ ] Greptile 5/5 with zero unresolved threads (`greploop`), or the remaining threads are explained below

## Rollout

- Phase and exit gate:
- Metrics to watch:

## Required approvers

- [ ] Owning team
- [ ] Platform
- [ ] Finance (money rules)
- [ ] Security (gateway, credentials, guards)
