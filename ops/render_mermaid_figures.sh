#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FIG_DIR="$ROOT/22.01paper/Pictures/professor_preview"
CONFIG="$FIG_DIR/mermaid_config.json"

if ! command -v mmdc >/dev/null 2>&1; then
  echo "Error: mmdc not found. Install with: npm install -g @mermaid-js/mermaid-cli" >&2
  exit 1
fi

if [ ! -f "$CONFIG" ]; then
  echo "Error: Mermaid config not found at $CONFIG" >&2
  exit 1
fi

count=0
for mmd in "$FIG_DIR"/*.mmd; do
  [ -e "$mmd" ] || continue
  base="${mmd%.mmd}"
  echo "Rendering $(basename "$mmd")"
  mmdc -c "$CONFIG" -i "$mmd" -o "$base.svg"
  mmdc -c "$CONFIG" -i "$mmd" -o "$base.png"
  mmdc -c "$CONFIG" -i "$mmd" -o "$base.pdf"

  if command -v gs >/dev/null 2>&1 && command -v pdfcrop >/dev/null 2>&1; then
    pages=$(gs -q -dNOSAFER -dNODISPLAY -c "($base.pdf) (r) file runpdfbegin pdfpagecount = quit" 2>/dev/null || echo "0")
    if [ "$pages" = "1" ]; then
      pdfcrop "$base.pdf" "$base.cropped.pdf" >/dev/null 2>&1 || true
      if [ -f "$base.cropped.pdf" ]; then
        mv "$base.cropped.pdf" "$base.pdf"
      fi
    else
      echo "Warning: $(basename "$base.pdf") has $pages page(s); skipping pdfcrop and keeping PDF for inspection." >&2
      echo "Action required: do NOT include $(basename "$base.pdf") directly in LaTeX while it is multi-page. Fix the Mermaid layout first or use a temporary PNG fallback until the PDF is single-page." >&2
    fi
  fi

  count=$((count + 1))
done

echo "Rendered $count Mermaid figure(s) in $FIG_DIR (svg/png/pdf)"
