#!/bin/bash

if [ -z "$(which ruff)" ]; then
  echo "ruff is not installed. Please install it usising 'pip install ruff'"
  exit 1
fi

files="$(find . -maxdepth 1 -type f -name "*.py"  -printf '%P\n')"

if ! ruff format --line-length 120 $files; then
  echo "Formatting failed. Please check the errors above."
  exit 1
fi
