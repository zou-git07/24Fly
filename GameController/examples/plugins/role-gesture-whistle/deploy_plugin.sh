#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "用法: $0 <team_number>"
  exit 1
fi

TEAM_NUM="$1"
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
GC_DIR="$(cd "$ROOT_DIR/../../.." && pwd)"
PLUGIN_JAR="$ROOT_DIR/role-gesture-whistle-plugin.jar"
TARGET_DIR="$GC_DIR/plugins/$TEAM_NUM"
TARGET_JAR="$TARGET_DIR/role-gesture-whistle-plugin.jar"

if [[ ! -f "$PLUGIN_JAR" ]]; then
  echo "未找到插件 jar，先构建..."
  "$ROOT_DIR/build_plugin.sh"
fi

mkdir -p "$TARGET_DIR"
cp -f "$PLUGIN_JAR" "$TARGET_JAR"

echo "已部署到: $TARGET_JAR"
echo "重启 TCM 后生效。"
