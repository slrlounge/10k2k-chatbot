# Render Ingestion Worker Instructions

## Overview

This pipeline processes files **one at a time** to avoid memory spikes on Render's 4GB RAM limit. Each execution processes exactly one file, then exits.

## Architecture

1. **Queue System**: JSON file tracks pending/completed/failed files
2. **Single File Processing**: Each run processes exactly one file
3. **Automatic Splitting**: Large files are automatically split on failure
4. **Checkpointing**: Fully resumable and idempotent
5. **Memory Optimized**: Uses OpenAI embeddings only, no local models

## Setup Steps

### 1. Generate Initial Queue

First time setup - scan files and create queue:

```bash
python3 ingestion/generate_file_queue.py
```

This creates `/app/checkpoints/file_queue.json` with all pending files.

### 2. Process Files

**Option A: Manual Execution (Recommended for Testing)**

Run one file at a time manually:

```bash
python3 ingestion/ingest_one_file.py
```

This processes exactly one file, then exits. Repeat until queue is empty.

**Option B: Worker Script (Process Multiple Files)**

Process multiple files in one run:

```bash
MAX_ITERATIONS=5 python3 ingestion/process_queue_worker.py
```

This processes up to 5 files, then exits.

**Option C: Render Cron Job (Automated)**

Set up a Render Cron Job to run every 5 minutes:

1. Go to Render Dashboard → Your Service → Cron Jobs
2. Add new cron job:
   - **Schedule**: `*/5 * * * *` (every 5 minutes)
   - **Command**: `python3 /app/ingestion/process_queue_worker.py`
   - **Environment**: `MAX_ITERATIONS=1`

This will automatically process one file every 5 minutes until queue is empty.

### 3. Monitor Progress

Check queue status:

```bash
python3 -c "import json; q=json.load(open('/app/checkpoints/file_queue.json')); print(f\"Pending: {len(q['pending'])}\nCompleted: {len(q['completed'])}\nFailed: {len(q['failed'])}\")"
```

### 4. Handle Failed Files

If a file fails due to size, it will be automatically split:

```bash
python3 ingestion/auto_chunker.py <file_path>
```

Or manually retry failed files by moving them back to pending in the queue JSON.

### 5. Optimize ChromaDB (After All Files Processed)

Once all files are ingested, optimize the database:

```bash
python3 ingestion/optimize_chromadb.py
```

This will:
- Deduplicate embeddings
- Validate metadata
- Add RAG-specific flags for strict retrieval

## Environment Variables

Set these in Render Dashboard → Environment:

```
TRANSCRIPTS_DIR=/app/10K2Kv2
CHROMA_HOST=chromadb-w5jr
CHROMA_PORT=8000
COLLECTION_NAME=10k2k_transcripts
QUEUE_FILE=/app/checkpoints/file_queue.json
CHECKPOINT_FILE=/app/checkpoints/ingest_checkpoint.json
OPENAI_API_KEY=your_key_here
MAX_ITERATIONS=1  # Files per run
```

## File Structure

```
/app/
├── ingestion/
│   ├── ingest_one_file.py          # Main ingestion script (one file)
│   ├── generate_file_queue.py      # Generate initial queue
│   ├── process_queue_worker.py     # Worker that processes multiple files
│   ├── auto_chunker.py              # Split large files
│   └── optimize_chromadb.py         # Optimize database
├── checkpoints/
│   ├── file_queue.json              # Queue state
│   └── ingest_checkpoint.json       # Processing checkpoint
└── 10K2Kv2/                         # Transcript files
```

## Memory Optimization Features

1. **Single File Processing**: Only loads one file at a time
2. **Small Chunks**: 500 tokens max per chunk
3. **Batch Embeddings**: Processes embeddings in batches of 10
4. **Aggressive GC**: Forces garbage collection after each batch
5. **No Local Models**: Uses OpenAI API only (no PyTorch/transformers)

## Troubleshooting

### Queue Stuck

If queue seems stuck, check processing status:

```bash
cat /app/checkpoints/file_queue.json | python3 -m json.tool
```

Move files from `processing` back to `pending` if needed.

### Memory Errors

If still getting OOM errors:
1. Reduce `MAX_CHUNK_TOKENS` in `ingest_one_file.py` (currently 500)
2. Reduce batch size in `ingest_file_chunks()` (currently 10)
3. Pre-split large files using `auto_chunker.py`

### Failed Files

Failed files are tracked in queue. To retry:

1. Edit `/app/checkpoints/file_queue.json`
2. Move file from `failed` to `pending`
3. Re-run ingestion

## RAG Configuration

After optimization, ChromaDB will have:
- `rag_strict: true` - No hallucination allowed
- `source_only: true` - Only use stored data
- Complete metadata: `file_source`, `original_file`, `section`

Your chatbot should check these flags and refuse to answer if data isn't in ChromaDB.

## Completion

When queue shows `pending: []`, all files are processed. Run optimization:

```bash
python3 ingestion/optimize_chromadb.py
```

Then verify:

```bash
python3 ingestion/find_missing_in_chromadb.py
```

This should show 0 missing files.

