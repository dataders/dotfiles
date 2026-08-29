---
description: Create a Worktrunk lane and delegate work there
argument-hint: "<branch-name> <task>"
---
Create a delegated implementation lane for branch `$1` and task `${@:2}`.

Load the `worktrunk` skill. Use `wt switch --create $1`; never call `git worktree add` and never use pi-subagents managed `worktree` or `isolation: worktree`. Resolve exact created path from Worktrunk output or `wt list`. Launch one `worker` subagent with that path as `cwd`, fresh context, and no managed-worktree isolation. Require focused validation plus handoff listing changed files, tests, risks, branch, and worktree path. Do not merge, push, remove worktree, or apply patch without explicit user direction.
