# RTK - Rust Token Killer (Codex CLI)

**Usage**: Optional CLI proxy for noisy shell output.

## When to use it

Use `rtk` only when installed and a compact summary will answer the question. Run commands directly when exact output matters, especially searches, diffs, test failures, and diagnostics. Do not stop to install or locate RTK when it is unavailable.

Examples:

```bash
rtk git status
```

## Meta Commands

```bash
rtk gain            # Estimated shell-output reduction, not bill savings
rtk gain --history  # Recent command savings history
rtk proxy <cmd>     # Run raw command through RTK when needed
```

Check `command -v rtk` once if availability is unclear; otherwise proceed with the command directly.
