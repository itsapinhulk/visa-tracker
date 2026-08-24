#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

cd ${SCRIPT_DIR}

# With --fallback the downloader clears travel.state.gov's Cloudflare "Verify you
# are human" (Turnstile) challenge by driving a real (headed) Chromium via
# patchright, which has to be installed for it. On a headless machine it also
# needs a virtual X server, which it starts for itself if it ever gets as far as
# launching the browser.
if [[ " $* " == *" --fallback "* ]]; then
  uv run --frozen patchright install chromium
fi

(
  set -x
  uv run --frozen python -m src.downloader.download \
    --cache_dir ./cache --data_dir ./data "$@"
)
