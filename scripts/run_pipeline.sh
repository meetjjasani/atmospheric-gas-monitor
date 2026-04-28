#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec prl-pipeline --config config/config.json
