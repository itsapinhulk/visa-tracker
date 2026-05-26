#!/usr/bin/env bash
cd "$(dirname "$0")/src/web" && bun install && bun run start -- --host
