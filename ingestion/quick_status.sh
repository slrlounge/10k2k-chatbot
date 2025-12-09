#!/bin/bash
# Quick status check - works in Render Shell

echo "=================================="
echo "INGESTION STATUS CHECK"
echo "=================================="
echo ""

# Check if queue file exists
if [ -f "/app/checkpoints/file_queue.json" ]; then
    echo "📋 Queue file exists"
    python3 -c "
import json
q = json.load(open('/app/checkpoints/file_queue.json'))
print(f\"  Pending: {len(q.get('pending', []))}\")
print(f\"  Processing: {len(q.get('processing', []))}\")
print(f\"  Completed: {len(q.get('completed', []))}\")
print(f\"  Failed: {len(q.get('failed', []))}\")
if q.get('processing'):
    print(f\"\\n  ⏳ Currently processing:\")
    for f in q['processing'][:3]:
        print(f\"    • {f.split('/')[-1]}\")
"
else
    echo "⚠️  No queue file found"
    echo "   Run: python3 ingestion/generate_file_queue.py"
fi

echo ""
echo "=================================="

