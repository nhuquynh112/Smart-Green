#!/usr/bin/env bash
# Host-only: never opens Serial, network, GPIO or persistent device storage.
set -euo pipefail
cd "$(dirname "$0")/.."
audit_tmp=$(mktemp -d)
trap 'rm -rf "$audit_tmp"' EXIT
g++ -std=c++17 -Wall -Wextra -Werror -Ifirmware/include firmware/test/native/test_auto_audit.cpp -o "$audit_tmp/auto-audit"
"$audit_tmp/auto-audit"
