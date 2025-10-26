#!/bin/bash
# Run linting and type checking
cd "$(dirname "$0")/.."
echo "Running ruff..."
ruff check app/ || true
echo "Running mypy..."
mypy app/ --ignore-missing-imports || true



