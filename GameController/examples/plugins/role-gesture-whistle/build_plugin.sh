#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
GC_DIR="$(cd "$ROOT_DIR/../../.." && pwd)"
OUT_DIR="$ROOT_DIR/out"
JAR_PATH="$ROOT_DIR/role-gesture-whistle-plugin.jar"

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

javac -encoding UTF-8 \
  -cp "$GC_DIR/TeamCommunicationMonitor.jar:$GC_DIR/plugins/common.jar" \
  -d "$OUT_DIR" \
  $(find "$ROOT_DIR/src" -name "*.java")

jar cf "$JAR_PATH" -C "$OUT_DIR" .

echo "Built: $JAR_PATH"
