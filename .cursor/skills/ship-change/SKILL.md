---
name: ship-change
description: Takes a finished change from a feature worktree to a review-ready GitLab merge request, covering preflight checks, the agent security review, pushing, opening the MR with the project template, and running greploop until Greptile gives 5/5. Use when the user says ship it, open an MR, open a PR, or when work on a feature branch is done.
---

# Ship a change

```
Progress:
- [ ] 1. Preflight
- [ ] 2. Agent security review
- [ ] 3. Commit and push
- [ ] 4. Open the merge request
- [ ] 5. Greploop to 5/5
- [ ] 6. Hand off to human code owners
```

## 1. Preflight
- The current branch is not `main`, and the working directory is a worktree under `<repo>-worktrees/`.
- Rebase on `origin/main` and resolve conflicts.
- Run `python3 scripts/validate.py` (the same checks CI runs).
- Run the project's lint, unit, policy, and contract tests. If prompts, models, policy, or tools changed, also run the evals. Stop on any failure.

## 2. Security review
Run the `agent-security-review` skill. If the verdict is BLOCKED, fix the blockers and run it again.

Never skip it for changes to `docs/`, `standards/`, `.cursor/`, `.greptile/`, `.gitlab/`, `.githooks/`, `scripts/`, or `.gitlab-ci.yml`. These files define security policy. Only typo-level changes elsewhere (for example, a README wording fix) may skip it, and the MR description must say so.

## 3. Commit and push
Use small, descriptive commits. Never commit secrets, `.env` files, or real customer data in fixtures.
```bash
git push -u origin HEAD
```

## 4. Open the merge request (self-hosted GitLab)
```bash
GITLAB_HOST=git.toptal.com glab mr create \
  --target-branch main \
  --title "<type>(<team>): <summary>" \
  --description "$(cat .gitlab/merge_request_templates/Default.md)" \
  --remove-source-branch
```
Fill in every template section: risk tier, approval change, OWASP impact, rollout gate, and the kill-switch flag. Leave unchecked any box that does not apply and explain why in the description.

## 5. Greptile
Run the `greploop` skill on the new merge request. Respect its Helia overrides: never weaken a control to please the reviewer, and leave security threads unresolved for a human if you disagree with them.

## 6. Hand off
Report the MR link, the greploop result (score, iterations, remaining threads), and which code owners must approve: the owning team plus Platform, Finance for money rules, and Security for the gateway, credentials, or guards. Do not merge yourself.
