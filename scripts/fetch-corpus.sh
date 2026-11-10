#!/usr/bin/env bash
# 대량 검사용 공개 HWPX 말뭉치(약 3,200개)를 받는다. 한글로 저장한 문서와 공공기관 결재 문서가 많다.
#   python-hwpx(Apache-2.0)와 rhwp(MIT) 저장소의 .hwpx 파일만 고정 커밋으로 받는다.
#   bash scripts/fetch-corpus.sh [대상 폴더]   (기본: .samples/corpus)
#   HWPPIPE_SAMPLES=.samples uv run pytest tests/test_real_docs.py -q   (기본 샘플과 함께 검사, 몇 분 걸림)
set -euo pipefail
DEST="${1:-.samples/corpus}"

fetch() {
  local repo="$1" commit="$2" dir="$DEST/$3"
  if [ -d "$dir/.git" ]; then rm -rf -- "${dir:?}"; fi   # 받다가 멈춘 폴더는 처음부터 다시 받는다
  if [ -d "$dir" ]; then echo "이미 있음: $dir"; return; fi
  git init -q "$dir"
  git -C "$dir" remote add origin "https://github.com/$repo"
  git -C "$dir" sparse-checkout set --no-cone '*.hwpx' '*.HWPX'
  git -C "$dir" fetch -q --depth 1 --filter=blob:none origin "$commit"
  git -C "$dir" checkout -q FETCH_HEAD
  rm -rf "$dir/.git"
}

mkdir -p "$DEST"
fetch airmang/python-hwpx 168fe9815b769e706e25b242ad9ea5c1a1531ca8 python-hwpx
fetch edwardkim/rhwp 7213ed1f96266b95e22cd5645a07851c9c18298e rhwp
echo "$(find "$DEST" -iname '*.hwpx' | wc -l | tr -d ' ')개 문서를 ${DEST}에 받음"
