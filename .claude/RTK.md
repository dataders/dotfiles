# RTK - Rust Token Killer

**Usage**: Optional CLI proxy for noisy shell output. Output reduction does not imply lower session cost.

Use RTK only when installed and a compact summary is sufficient. Run commands directly for exact search results, diffs, test failures, and diagnostics. Do not stop to install or locate RTK when it is unavailable.

## Meta Commands

```bash
rtk gain              # Estimate shell-output reduction, not bill savings
rtk gain --history    # Show command usage history with savings
rtk discover          # Analyze Claude Code history for missed opportunities
rtk proxy <cmd>       # Execute raw command without filtering (for debugging)
```

Check `command -v rtk` once if availability is unclear; otherwise proceed with the command directly. Automatic rewriting is disabled.
