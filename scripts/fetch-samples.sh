#!/usr/bin/env bash
# 실문서 테스트용 공개 샘플(hwpxlib testFile/error, Apache-2.0)을 받는다.
#   bash scripts/fetch-samples.sh [대상 폴더]   (기본: .samples)
#   HWPPIPE_SAMPLES=.samples uv run pytest
set -euo pipefail
DEST="${1:-.samples}"
COMMIT="f9fd2255ac0fc57414e0b657d115e7de51d31c65"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
git init -q "$TMP/hwpxlib"
git -C "$TMP/hwpxlib" fetch -q --depth 1 https://github.com/neolord0/hwpxlib "$COMMIT"
git -C "$TMP/hwpxlib" checkout -q FETCH_HEAD
mkdir -p "$DEST"
cp -R "$TMP/hwpxlib/testFile/error/." "$DEST/"
cp "$TMP/hwpxlib/license.txt" "$DEST/LICENSE-hwpxlib.txt"
echo "$(find "$DEST" -name '*.hwpx' | wc -l | tr -d ' ')개 문서를 ${DEST}에 받음"
