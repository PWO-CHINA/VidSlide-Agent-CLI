#!/bin/bash
# Helper script to run vidslide CLI during development

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$SCRIPT_DIR/src"

python "$SCRIPT_DIR/src/vidslide/cli.py" "$@"
