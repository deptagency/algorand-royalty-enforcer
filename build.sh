#!/usr/bin/env bash

set -e

echo "Building enforcer contract..."
poetry run python royalty_enforcer/contracts/enforcer.py

echo "Building enforcer placeholder contract..."
poetry run python royalty_enforcer/contracts/enforcer_placeholder.py

echo "Building marketplace contract..."
poetry run python royalty_enforcer/contracts/marketplace.py

echo "Done."
