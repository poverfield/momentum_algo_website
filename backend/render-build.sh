#!/usr/bin/env bash
set -euo pipefail

# Upgrade Python packaging tools
pip install -U pip setuptools wheel

# Build React frontend
(cd ../frontend && npm ci && npm run build)

# Install backend dependencies
pip install --no-build-isolation -r requirements.txt
