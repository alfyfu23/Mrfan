#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if command -v latexmk >/dev/null 2>&1; then
  # 1) build main body (counted pages)
  latexmk -xelatex -latexoption=-shell-escape -interaction=nonstopmode -halt-on-error main.tex
  # 2) build full API appendix
  latexmk -xelatex -latexoption=-shell-escape -interaction=nonstopmode -halt-on-error api_full.tex
  # 3) stitch into final report.pdf
  latexmk -xelatex -interaction=nonstopmode -halt-on-error report.tex
  echo "Built: $(pwd)/report.pdf"
  exit 0
fi

if command -v xelatex >/dev/null 2>&1; then
  # 1) main body
  xelatex -shell-escape -interaction=nonstopmode -halt-on-error main.tex
  xelatex -shell-escape -interaction=nonstopmode -halt-on-error main.tex
  # 2) full API
  xelatex -shell-escape -interaction=nonstopmode -halt-on-error api_full.tex
  xelatex -shell-escape -interaction=nonstopmode -halt-on-error api_full.tex
  # 3) stitch
  xelatex -interaction=nonstopmode -halt-on-error report.tex
  xelatex -interaction=nonstopmode -halt-on-error report.tex
  echo "Built: $(pwd)/report.pdf"
  exit 0
fi

echo "Error: latexmk/xelatex not found. Please install TeX Live or MacTeX." >&2
exit 1
