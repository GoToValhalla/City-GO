#!/bin/bash

set -e

echo "🔍 Validating seeds..."
python data/scripts/validate_seeds.py

echo "📥 Loading seeds..."
python data/scripts/load_seeds.py

echo "✅ Done"
