#!/usr/bin/env bash
#
# verify-ios-project.sh — detect an Xcode project/workspace, list schemes, and (optionally)
# run a SAFE xcodebuild build or test. Build/test only runs when you provide SCHEME and
# DESTINATION via environment variables, so the script never guesses and never mutates state.
#
# Usage:
#   scripts/verify-ios-project.sh
#       Discover project/workspace + schemes. No build.
#
#   SCHEME=MyGame DESTINATION='platform=iOS Simulator,name=iPhone 15' \
#     scripts/verify-ios-project.sh
#       Discover, then `xcodebuild build`.
#
#   ACTION=test SCHEME=MyGame DESTINATION='platform=iOS Simulator,name=iPhone 15' \
#     scripts/verify-ios-project.sh
#       Discover, then `xcodebuild test`.
#
# Env vars:
#   ROOT        Directory to search (default: current directory)
#   SCHEME      Scheme to build/test (required to build/test)
#   DESTINATION xcodebuild -destination string (required to build/test)
#   ACTION      build | test            (default: build)
#
set -euo pipefail

ROOT="${ROOT:-$(pwd)}"
ACTION="${ACTION:-build}"

echo "== Environment =="
if command -v xcodebuild >/dev/null 2>&1; then
  xcodebuild -version || true
else
  echo "warning: xcodebuild not found. Discovery only; cannot build/test here." >&2
fi
echo

echo "== Discovering Xcode project/workspace under: ${ROOT} =="
# Prefer a workspace if present, else a project. Ignore CocoaPods/SwiftPM build dirs.
WORKSPACE="$(find "${ROOT}" -maxdepth 3 -name '*.xcworkspace' -not -path '*/.*' 2>/dev/null | head -n 1 || true)"
PROJECT="$(find "${ROOT}" -maxdepth 3 -name '*.xcodeproj' -not -path '*/.*' 2>/dev/null | head -n 1 || true)"

CONTAINER_FLAG=""
CONTAINER_PATH=""
if [[ -n "${WORKSPACE}" ]]; then
  echo "Found workspace: ${WORKSPACE}"
  CONTAINER_FLAG="-workspace"
  CONTAINER_PATH="${WORKSPACE}"
elif [[ -n "${PROJECT}" ]]; then
  echo "Found project:   ${PROJECT}"
  CONTAINER_FLAG="-project"
  CONTAINER_PATH="${PROJECT}"
else
  echo "No .xcworkspace or .xcodeproj found under ${ROOT}."
  echo "If this is a Swift Package, try: swift build / swift test"
  exit 0
fi
echo

if command -v xcodebuild >/dev/null 2>&1; then
  echo "== Schemes / targets =="
  xcodebuild -list ${CONTAINER_FLAG} "${CONTAINER_PATH}" || \
    echo "warning: could not list schemes (project may need resolving)." >&2
  echo
fi

# Only build/test when BOTH SCHEME and DESTINATION are supplied.
if [[ -z "${SCHEME:-}" || -z "${DESTINATION:-}" ]]; then
  echo "No SCHEME/DESTINATION provided — skipping build/test (discovery only)."
  echo "To build:  SCHEME=<scheme> DESTINATION='platform=iOS Simulator,name=iPhone 15' $0"
  echo "To test:   ACTION=test SCHEME=<scheme> DESTINATION='platform=iOS Simulator,name=iPhone 15' $0"
  exit 0
fi

if ! command -v xcodebuild >/dev/null 2>&1; then
  echo "error: xcodebuild unavailable; cannot ${ACTION}." >&2
  exit 1
fi

case "${ACTION}" in
  build) XCODE_ACTION="build" ;;
  test)  XCODE_ACTION="test" ;;
  *) echo "error: ACTION must be 'build' or 'test' (got '${ACTION}')." >&2; exit 2 ;;
esac

echo "== Running: xcodebuild ${XCODE_ACTION} (scheme=${SCHEME}) =="
set -x
xcodebuild "${XCODE_ACTION}" \
  ${CONTAINER_FLAG} "${CONTAINER_PATH}" \
  -scheme "${SCHEME}" \
  -destination "${DESTINATION}" \
  CODE_SIGNING_ALLOWED=NO
set +x

echo "Done."
