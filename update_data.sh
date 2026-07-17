#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

cd ${SCRIPT_DIR}

# With --fallback the downloader clears travel.state.gov's Cloudflare "Verify you
# are human" (Turnstile) challenge by driving a real (headed) Chromium via
# patchright. That needs the browser installed and, on a headless machine (no
# $DISPLAY), a virtual X server -- the challenge only clears in headed mode.
PREFIX=()
if [[ " $* " == *" --fallback "* ]]; then
  uv run --frozen patchright install chromium
  if [ -z "${DISPLAY:-}" ] && command -v xvfb-run >/dev/null 2>&1; then
    PREFIX=(xvfb-run -a)
  fi
fi

(
  set -x
  "${PREFIX[@]}" uv run --frozen python -m src.downloader.download \
    --cache_dir ./cache --data_dir ./data "$@"
)
