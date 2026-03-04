# tmux Cheatsheet

All commands start with the **prefix**: `Ctrl+b`

## Sessions
| Action | Command |
|--------|---------|
| New session | `tmux` or `tmux new -s name` |
| List sessions | `tmux ls` |
| Attach to session | `tmux a` or `tmux a -t name` |
| Detach (leave running) | `Ctrl+b d` |
| Kill session | `tmux kill-session -t name` |

## Windows (tabs)
| Action | Keys |
|--------|------|
| New window | `Ctrl+b c` |
| Next window | `Ctrl+b n` |
| Previous window | `Ctrl+b p` |
| Switch to window # | `Ctrl+b 1`, `Ctrl+b 2`, etc. |
| Rename window | `Ctrl+b ,` |
| Close window | `Ctrl+b &` |

## Panes (splits)
| Action | Keys |
|--------|------|
| Split side-by-side | `Ctrl+b |` |
| Split top/bottom | `Ctrl+b -` |
| Move between panes | `Ctrl+b` + arrow keys (or click) |
| Close pane | `Ctrl+b x` |
| Zoom pane (fullscreen toggle) | `Ctrl+b z` |
| Resize pane | `Ctrl+b` hold, then arrow keys |

## Other
| Action | Keys |
|--------|------|
| Reload config | `Ctrl+b r` |
| Scroll mode | `Ctrl+b [` then arrow/pgup/pgdn, `q` to exit |
| Copy in scroll mode | Select with mouse, or `Space` to start, `Enter` to copy |
