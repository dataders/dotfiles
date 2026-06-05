#!/usr/bin/env bash
# Import the git-tracked Raycast snippets (raycast/snippets.json) into Raycast.
#
# Source of truth is snippets.json; this script builds Raycast's import deeplink
# and opens it so you confirm with a single "Import Snippets" dialog. Raycast
# skips any snippet whose name/text/keyword already exists, so re-running is safe.
set -euo pipefail

dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
json="$dir/snippets.json"

# Raycast's deeplink takes a repeated singular `snippet=` param (one URL-encoded
# JSON object each), NOT a single `snippets=[...]` array.
query="$(jq -r '[.[] | "snippet=" + ({name, text, keyword} | tojson | @uri)] | join("&")' "$json")"

open "raycast://snippets/import?${query}"
echo "Opened Raycast import for $(jq 'length' "$json") snippet(s) from $json"
