---
description: Adversarial read-only review of current diff or named PR
argument-hint: "[PR URL or review scope]"
---
Review ${@:-the current branch diff} read-only. Establish exact diff and ancestry first. Inspect CI, callers, parallel runtime paths, compatibility seams, and tests. Produce only concrete current findings with file and line evidence, ordered by severity. Include executable counterexamples where useful. Do not edit, comment, approve, merge, or push.
