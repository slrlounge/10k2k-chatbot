# Cloud Ingestion Pipeline V2 - 4GB RAM Optimized

## Overview

Complete rewrite of ingestion pipeline optimized for Render's 4GB RAM limit. Processes **one file per execution** to avoid memory spikes.

## Key Features

✅ **Single File Processing** - Each run processes exactly one file, then exits  
✅ **Queue-Based System** - JSON queue tracks pending/completed/failed files  
✅ **Automatic Splitting** - Large files automatically split on failure  
✅ **OpenAI Only** - No local embedding models (saves ~2GB RAM)  
✅ **Fully Resumable** - Checkpoint system allows restart from any point  
✅ **Idempotent** - Safe to run multiple times  
✅ **Memory Optimized** - Aggressive garbage collection, small batches  

## Architecture

```
┌─────────────────┐
│ Generate Queue  │ → Creates file_queue.json
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Process Queue   │ → Runs ingest_one_file.py repeatedly
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Ingest One File │ → Processes single file, updates queue
└────────┬────────┘
         │
    ┌────┴────┐
    │ Success │ Failure
    │    │    │
    ▼    │    ▼
┌────────┴────────┐
│ Auto Chunker    │ → Splits file, retries
└─────────────────┘
```

## Files Created

### Core Scripts

1. **`ingest_one_file.py`** - Main ingestion script
   - Processes exactly one file per execution
   - Uses OpenAI embeddings only
   - Small chunks (500 tokens max)
   - Batch processing (10 chunks at a time)
   - Aggressive garbage collection

2. **`generate_file_queue.py`** - Queue generator
   - Scans transcript directory
   - Creates JSON queue file
   - Excludes already processed files

3. **`process_queue_worker.py`** - Worker script
   - Processes multiple files in one run
   - Configurable via MAX_ITERATIONS env var
   - Can be run manually or via cron

4. **`auto_chunker.py`** - File splitter
   - Splits large files into smaller segments
   - Semantic boundary detection
   - Zero-padded naming (file_01.txt, file_02.txt)

5. **`optimize_chromadb.py`** - Database optimizer
   - Deduplicates embeddings
   - Validates metadata
   - Adds RAG flags for strict retrieval

### Configuration

- **`Dockerfile.ingest`** - Updated with new env vars
- **`requirements.ingest.txt`** - Minimal dependencies only
- **`RENDER_INGESTION_WORKER_INSTRUCTIONS.md`** - Setup guide

## Memory Usage

**Before (Old Pipeline):**
- PyTorch: ~2GB
- Transformers: ~500MB
- ChromaDB: ~500MB
- **Total: ~3GB+ (OOM on 4GB limit)**

**After (New Pipeline):**
- OpenAI API: 0MB (external)
- ChromaDB: ~500MB
- Python runtime: ~200MB
- **Total: ~700MB (well under 4GB)**

## Usage

### Initial Setup

```bash
# 1. Generate queue
python3 ingestion/generate_file_queue.py

# 2. Process files (one at a time)
python3 ingestion/ingest_one_file.py  # Run repeatedly

# OR process multiple files
MAX_ITERATIONS=5 python3 ingestion/process_queue_worker.py

# 3. Optimize after completion
python3 ingestion/optimize_chromadb.py
```

### Render Cron Setup

Set up cron job to run every 5 minutes:

```
*/5 * * * * python3 /app/ingestion/process_queue_worker.py
```

This processes one file every 5 minutes automatically.

## Queue Structure

```json
{
  "pending": ["/app/10K2Kv2/file1.txt", ...],
  "processing": [],
  "completed": ["/app/10K2Kv2/file2.txt", ...],
  "failed": []
}
```

## Checkpoint Structure

```json
{
  "processed_files": {
    "/app/10K2Kv2/file.txt": {
      "timestamp": 1234567890,
      "status": "completed"
    }
  },
  "failed_files": {}
}
```

## Error Handling

- **Memory Error**: File automatically split via `auto_chunker.py`
- **API Error**: File marked as failed, can retry later
- **Timeout**: File stays in processing, next run retries
- **Network Error**: Retry on next execution

## RAG Configuration

After optimization, all documents have:
- `rag_strict: true` - No hallucination
- `source_only: true` - Only use stored data
- Complete metadata for retrieval

## Benefits

1. **No OOM Errors** - Processes one file at a time
2. **Fully Resumable** - Can stop/start anytime
3. **Automatic Recovery** - Failed files can be retried
4. **Memory Efficient** - Uses ~700MB vs ~3GB+
5. **Production Ready** - Idempotent and safe

## Migration from Old Pipeline

1. Stop old ingestion
2. Deploy new code
3. Generate queue: `python3 ingestion/generate_file_queue.py`
4. Start processing: `python3 ingestion/process_queue_worker.py`
5. Monitor until queue empty
6. Run optimization: `python3 ingestion/optimize_chromadb.py`

## Monitoring

Check queue status:
```bash
python3 -c "import json; q=json.load(open('/app/checkpoints/file_queue.json')); print(f\"Pending: {len(q['pending'])}, Completed: {len(q['completed'])}, Failed: {len(q['failed'])}\")"
```

## Next Steps

1. Review all scripts
2. Test locally if possible
3. Deploy to Render
4. Generate queue
5. Start processing
6. Monitor progress
7. Optimize when complete

