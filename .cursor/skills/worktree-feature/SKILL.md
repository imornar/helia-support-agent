---
name: worktree-feature
description: Creates, lists, and cleans up git worktrees so every feature or agent runs in its own isolated checkout. Use when starting any new feature, fix, or experiment, when the current branch is main, when running several agents or models in parallel, or when the user mentions worktrees.
---

# Worktree per feature

## Start a feature

1. Run `git rev-parse --show-toplevel` and `git worktree list`. Find the main checkout (the entry on `main`).
2. Pick names:
   - slug: short kebab-case (`refund-tier-cap`)
   - branch: `<type>/<team>/<slug>`, where type is `feat`, `fix`, `chore`, `docs`, or `design`, and team is `payments`, `accounts`, or `platform`
   - path: `<parent-of-main>/<repo>-worktrees/<slug>`
3. Create the worktree from a fresh `main`:

```bash
MAIN=$(git worktree list | awk '$3=="[main]"{print $1}')
REPO=$(basename "$MAIN")
git -C "$MAIN" fetch origin main
git -C "$MAIN" worktree add -b "<branch>" "$(dirname "$MAIN")/$REPO-worktrees/<slug>" origin/main
```

4. Opt in to the hooks once per clone. The config is shared by all worktrees:

```bash
git -C "$MAIN" config core.hooksPath .githooks
```

5. Do all further work, commands, and file edits inside the new path. Tell the user the path and branch.

## Rules

- One agent per worktree. Never touch files under another worktree's path.
- If a worktree for the same slug exists, reuse it only if you created it in this session. Otherwise pick a new slug.
- Do not run `git stash`, `reset --hard`, or `checkout <other-branch>` inside someone else's worktree.
- Parallel model comparison: give each model its own slug, for example `design/<model-name>`.

## Clean up after merge

```bash
git worktree remove "<path>"     # refuses if there are uncommitted changes; that is intended
git branch -d "<branch>"
git worktree prune
```

Never pass `--force` without asking the user.
