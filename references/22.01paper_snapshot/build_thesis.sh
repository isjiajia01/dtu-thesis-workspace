#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAIN_TEX="${ROOT}/main.tex"

if [[ ! -f "${MAIN_TEX}" ]]; then
  echo "Missing main.tex in ${ROOT}" >&2
  exit 1
fi

cd "${ROOT}"

case "${1:-build}" in
  build)
    latexmk -xelatex -interaction=nonstopmode -synctex=1 main.tex
    ;;
  clean)
    latexmk -C
    ;;
  rebuild)
    latexmk -C
    latexmk -xelatex -interaction=nonstopmode -synctex=1 main.tex
    ;;
  open)
    latexmk -xelatex -interaction=nonstopmode -synctex=1 main.tex
    open main.pdf
    ;;
  *)
    echo "Usage: $(basename "$0") [build|clean|rebuild|open]" >&2
    exit 1
    ;;
esac
