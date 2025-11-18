#!/bin/bash
# Wrapper script to run ingestion and send notification on completion

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "Starting ingestion pipeline..."
echo "This will process all transcript files and notify you when complete."
echo ""

# Run ingestion in Docker
docker run --rm --network host \
  --name ingest-$(date +%s) \
  -v "$(pwd)/10K2K v2:/app/transcripts:ro" \
  -v "$(pwd)/chroma:/app/chroma" \
  -v "$(pwd)/logs:/app/logs" \
  -v "$(pwd)/checkpoints:/app/checkpoints" \
  --env-file .env \
  -e CHROMA_HOST=localhost \
  -e CHROMA_PORT=8000 \
  10k2kchatbot-ingest:latest

EXIT_CODE=$?

# Check results
TOTAL=$(find "10K2K v2" -name "*.txt" -type f | wc -l | tr -d ' ')
PROCESSED=$(cat checkpoints/ingest_transcripts.json 2>/dev/null | grep -o '"/app/transcripts' | wc -l | tr -d ' ' || echo "0")
FAILED=$(cat checkpoints/ingest_transcripts.json 2>/dev/null | grep -o '"/app/transcripts' | wc -l | tr -d ' ' || echo "0")

# Send macOS notification
if [[ "$OSTYPE" == "darwin"* ]]; then
    if [ $EXIT_CODE -eq 0 ] && [ "$PROCESSED" -eq "$TOTAL" ]; then
        osascript -e "display notification \"Successfully processed all $PROCESSED files\" with title \"✅ Ingestion Complete\" sound name \"Glass\""
        echo -e "${GREEN}✅ Ingestion completed successfully!${NC}"
    else
        osascript -e "display notification \"Processed $PROCESSED of $TOTAL files. Check logs for details.\" with title \"⚠️ Ingestion Complete\" sound name \"Basso\""
        echo -e "${YELLOW}⚠️ Ingestion completed with some issues. Check logs for details.${NC}"
    fi
else
    echo "Ingestion completed. Exit code: $EXIT_CODE"
fi

# Print summary
echo ""
echo "============================================================"
echo "Summary:"
echo "  Total files: $TOTAL"
echo "  Processed: $PROCESSED"
echo "============================================================"
echo ""
echo "Check logs: tail -f logs/ingest_all.log"
echo "Check progress: cat checkpoints/ingest_transcripts.json"

exit $EXIT_CODE

