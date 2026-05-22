#!/usr/bin/env bash
# Stop hook: warn on large turns and high context usage.
# Outputs a systemMessage injected into the next turn's context.

input=$(cat)
TRANSCRIPT=$(echo "$input" | jq -r '.transcript_path // empty')
PERCENT=$(echo "$input" | jq -r '.context_window.used_percentage // 0' | cut -d. -f1)

[[ -z "$TRANSCRIPT" || ! -f "$TRANSCRIPT" ]] && exit 0

LAST_OUTPUT=$(jq -s 'last(.[] | select(.type == "assistant")) | .message.usage.output_tokens // 0' "$TRANSCRIPT" 2>/dev/null)

WARNINGS=()

if [[ -n "$LAST_OUTPUT" ]] && (( LAST_OUTPUT > 2000 )); then
  WARNINGS+=("⚠️  Last turn: ${LAST_OUTPUT} output tokens — large response")
fi

if (( PERCENT >= 70 )); then
  WARNINGS+=("⚠️  Context ${PERCENT}% full — consider /compact")
fi

[[ ${#WARNINGS[@]} -eq 0 ]] && exit 0

MSG=$(printf '%s\n' "${WARNINGS[@]}")

jq -cn --arg msg "$MSG" '{
  hookSpecificOutput: {
    hookEventName: "Stop",
    systemMessage: $msg
  }
}'
