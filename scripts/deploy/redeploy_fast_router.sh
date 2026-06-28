#!/usr/bin/env bash
set -euo pipefail
if [[ -z "${VERCEL_TOKEN:-}" ]]; then
  echo "VERCEL_TOKEN not set; skipping fast-router redeploy."
  exit 0
fi
npx vercel deploy --prod --token "$VERCEL_TOKEN" --yes
