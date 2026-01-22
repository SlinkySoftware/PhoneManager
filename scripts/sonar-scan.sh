#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SONAR_HOST_URL="${SONAR_HOST_URL:-https://sonarqube.juneks.com.au}"
SONAR_PROJECT_KEY="${SONAR_PROJECT_KEY:-Phone-Manager}"

if [[ -z "${SONAR_TOKEN:-}" ]]; then
  echo "Error: SONAR_TOKEN is required (export SONAR_TOKEN=... or pass via task input)." >&2
  exit 1
fi

if ! command -v sonar-scanner >/dev/null 2>&1; then
  echo "Error: sonar-scanner command not found. Install it or add it to PATH." >&2
  exit 1
fi

exec sonar-scanner \
  -Dsonar.host.url="${SONAR_HOST_URL}" \
  -Dsonar.projectKey="${SONAR_PROJECT_KEY}" \
  -Dsonar.token="${SONAR_TOKEN}" \
  -Dsonar.projectBaseDir="${ROOT_DIR}"
