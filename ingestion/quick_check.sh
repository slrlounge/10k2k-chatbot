#!/bin/bash
# Quick check of ChromaDB ingestion status

echo "=========================================="
echo "CHROMADB INGESTION STATUS"
echo "=========================================="
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found"
    exit 1
fi

# Run the verification script
python3 ingestion/verify_chromadb_collection.py

echo ""
echo "=========================================="
echo "For detailed report, run:"
echo "  python3 ingestion/show_ingested_files.py"
echo "=========================================="

