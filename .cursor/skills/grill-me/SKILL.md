---
name: grill-me
description: Interview the user relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree. Use when adding a new feature or agent action, stress-testing a plan, grilling a design, or when the user mentions "grill me".
---

Interview the user relentlessly about every aspect of their plan until you reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one.

## How to ask questions

Use the **AskQuestion tool** for every question. Never pose questions as plain text.

Ask **one question at a time** by default. If the user asks for all questions up front, batch the independent ones into a single AskQuestion form and keep dependent ones for a follow-up round.

For each question give 2 to 4 concrete options. Put your recommended option **first** and suffix it with "(Recommended)". The user always has "Other".

## Flow

1. Explore the codebase and `docs/` first. Never ask what the repo already answers.
2. After each answer, acknowledge in 1 to 2 sentences, then ask the next question.
3. Continue until every branch is resolved.
4. Finish with a concise summary of decisions and the trade-off each accepts. For design-level decisions, append rows to `docs/decisions.md`.

## Helia-specific branches to always cover for agent work

- Risk tier (R0 to R3) and whether the action can be undone.
- Which inputs the model chooses and which are derived server-side.
- Approval: who approves, and in which rollout phase it may become auto.
- Failure: idempotency, partial failure, what the customer and the support agent see.
- Which OWASP LLM risks apply (`docs/owasp-llm-top10.md`).
- Owning team, kill-switch flag, and the metrics that gate rollout.
