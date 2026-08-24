#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

cd ${SCRIPT_DIR}

# Checks the stored CSVs against what each source produces now. Checks the last
# few stored months unless --start_date says otherwise, and shares ./cache with
# update_data.sh so neither re-downloads what the other already has.
# --fallback drives a real browser for the Cloudflare challenge on the HTML
# pages, exactly as update_data.sh does.
if [[ " $* " == *" --fallback "* ]]; then
  uv run --frozen patchright install chromium
fi

mkdir -p ./cache

(
  set -x
  uv run --frozen python -m src.downloader.verify \
    --cache_dir ./cache --data_dir ./data "$@"
)
