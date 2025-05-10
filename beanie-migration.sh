#!/bin/bash

# GlobeCo Security Service - Beanie Migration Runner
# Author: Noah Krieger

set -e

for migration in migrations/*.py; do
    echo "Running migration: $migration"
    uv python "$migration"
done 