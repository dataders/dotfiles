#!/bin/bash
input=$(cat)

MODEL=$(echo "$input" | jq -r '.model.display_name')
PERCENT=$(echo "$input" | jq -r '.context_window.used_percentage // 0' | cut -d. -f1)

REPO=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null)
BRANCH=$(git branch --show-current 2>/dev/null)

if [[ -n "$REPO" && -n "$BRANCH" ]]; then
  GIT_INFO=" ${REPO}·${BRANCH} |"
elif [[ -n "$REPO" ]]; then
  GIT_INFO=" ${REPO} |"
else
  GIT_INFO=""
fi

echo "[$MODEL]${GIT_INFO} Context: ${PERCENT}%"
