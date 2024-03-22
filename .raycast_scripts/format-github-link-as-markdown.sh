#!/bin/bash

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Format GitHub Link as Markdown
# @raycast.mode silent

# Optional parameters:
# @raycast.icon 🤖

# Documentation:
# @raycast.description takes an issue or PR URL and turns it into a markdown link
# @raycast.author dataders
# @raycast.authorURL https://raycast.com/dataders

# echo "Hello World!"

# url example https://github.com/dbt-labs/dbt-docs/pull/7701

url=$(pbpaste)
pr_number=${url##*/}

url_without_base=${url#https://github.com/dbt-labs/}
repo_name=${url_without_base%%/*}

echo "[$repo_name#$pr_number]($url)" | pbcopy
# echo Copied "[$repo_name#$pr_number]($url)"