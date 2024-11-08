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


# Get the URL from the clipboard
url=$(pbpaste)

# get required components
pr_number=${url##*/}
url_without_base=${url#https://github.com/}
org_name=${url_without_base%%/*}
repo_name=${url_without_base#*/}; repo_name=${repo_name%%/*}

# format as markdown link
# exclude org name if it's dbt-labs
if [ "$org_name" == "dbt-labs" ]; then
    echo "[$repo_name#$pr_number]($url)" | pbcopy
else
    echo "[$org_name/$repo_name#$pr_number]($url)" | pbcopy
fi