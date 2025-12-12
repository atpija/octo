#!/bin/bash
# smoketest.sh - Führt Smoke Tests aus

cd "$(dirname "$0")"

echo "🧪 Running Smoke Tests..."
pytest -s smoketest.py

if [ $? -eq 0 ]; then
    echo "✅ Smoke Tests passed!"
    exit 0
else
    echo "❌ Smoke Tests failed!"
    exit 1
fi
