#!/bin/bash
input=$(cat)

MODEL=$(echo "$input" | jq -r '.model.display_name')
PERCENT=$(echo "$input" | jq -r '.context_window.used_percentage // 0' | cut -d. -f1)
COST_USD=$(echo "$input" | jq -r '.cost.total_cost_usd // 0')

# Credits → bales of hay (5 USD = 1 bale 🌾)
BALES=$(awk -v c="$COST_USD" 'BEGIN { b = c / 5.0; if (b >= 10) printf "%.1f", b; else printf "%.2f", b }')

REPO=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null)
BRANCH=$(git branch --show-current 2>/dev/null)

if [[ -n "$REPO" && -n "$BRANCH" ]]; then
  GIT_INFO=" ${REPO}·${BRANCH} |"
elif [[ -n "$REPO" ]]; then
  GIT_INFO=" ${REPO} |"
else
  GIT_INFO=""
fi

echo "[$MODEL]${GIT_INFO} Context: ${PERCENT}% | ${BALES} 🌾"
