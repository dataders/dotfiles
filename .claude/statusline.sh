#!/bin/bash
input=$(cat)

MODEL=$(echo "$input" | jq -r '.model.display_name')
PERCENT=$(echo "$input" | jq -r '.context_window.used_percentage // 0' | cut -d. -f1)
TRANSCRIPT=$(echo "$input" | jq -r '.transcript_path // empty')
SESSION_ID=$(echo "$input" | jq -r '.session_id // empty')

REPO=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null)
BRANCH=$(git branch --show-current 2>/dev/null)

if [[ -n "$REPO" && -n "$BRANCH" ]]; then
  GIT_INFO=" ${REPO}·${BRANCH} |"
elif [[ -n "$REPO" ]]; then
  GIT_INFO=" ${REPO} |"
else
  GIT_INFO=""
fi

# Compute cumulative session cost from transcript (cached by mtime)
COST_STR=""
if [[ -n "$TRANSCRIPT" && -f "$TRANSCRIPT" && -n "$SESSION_ID" ]]; then
  CACHE="${TMPDIR:-/tmp}/cc-cost-${SESSION_ID}"
  T_MTIME=$(stat -f %m "$TRANSCRIPT" 2>/dev/null)
  if [[ -f "$CACHE" && "$(head -1 "$CACHE" 2>/dev/null)" == "$T_MTIME" ]]; then
    COST_STR=$(tail -1 "$CACHE" 2>/dev/null)
  else
    # Sonnet 4.6: input $3/MTok, output $15/MTok, cache_read $0.30/MTok, cache_create $3.75/MTok
    COST=$(jq -s '
      [.[] | select(.type == "assistant") | .message.usage] |
      (
        (map(.input_tokens // 0)                | add // 0) * 3.0    +
        (map(.output_tokens // 0)               | add // 0) * 15.0   +
        (map(.cache_read_input_tokens // 0)     | add // 0) * 0.30   +
        (map(.cache_creation_input_tokens // 0) | add // 0) * 3.75
      ) / 1000000
    ' "$TRANSCRIPT" 2>/dev/null)
    if [[ -n "$COST" ]] && awk "BEGIN{exit !($COST > 0.005)}"; then
      COST_STR=$(awk "BEGIN{printf \"\$%.2f\", $COST}")
    fi
    printf '%s\n%s\n' "$T_MTIME" "$COST_STR" > "$CACHE" 2>/dev/null
  fi
  [[ -n "$COST_STR" ]] && COST_STR=" | ${COST_STR}"
fi

echo "[$MODEL]${GIT_INFO} Context: ${PERCENT}%${COST_STR}"
