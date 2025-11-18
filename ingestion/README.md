# Ingestion Pipeline

This directory contains the final, production-ready ingestion pipeline for processing transcript files into the ChromaDB vector database.

## Architecture

The pipeline uses a **one-file-per-process** approach to prevent memory issues:

1. **`ingest_all_transcripts.py`** - Orchestrator that scans for transcript files and spawns subprocesses
2. **`ingest_single_transcript.py`** - Processes a single transcript file (runs in separate Python process)
3. **`utils_logging.py`** - Logging utilities (stdout + rotating log files)
4. **`utils_checkpoints.py`** - Checkpoint system for tracking processed files

## Key Features

- ✅ **Docker-ready** - Designed to run in Docker containers
- ✅ **Memory-safe** - Each file processed in a fresh Python process
- ✅ **Restart-safe** - Checkpoint system allows safe restarts
- ✅ **Lightweight** - Minimal dependencies, no heavy libraries
- ✅ **ChromaDB HttpClient** - Connects to Docker ChromaDB server (no in-memory loading)

## Usage

### Docker (Recommended)

1. **Start ChromaDB server:**
   ```bash
   docker-compose up -d chroma
   ```

2. **Run ingestion:**
   ```bash
   docker-compose up ingest
   ```

### Standalone (Local Development)

1. **Set up environment:**
   ```bash
   export OPENAI_API_KEY=your_key
   export TRANSCRIPTS_DIR=/path/to/transcripts
   export CHROMA_HOST=localhost
   export CHROMA_PORT=8000
   ```

2. **Run ingestion:**
   ```bash
   python3 ingestion/ingest_all_transcripts.py
   ```

## Environment Variables

See `.env.example` for all configuration options.

## Checkpoints

Processed files are tracked in `/app/checkpoints/ingest_transcripts.json` (or `./checkpoints/` locally).

The pipeline automatically skips already-processed files, making it safe to restart.

## Logs

Logs are written to:
- **Stdout** - Real-time progress
- **Log files** - `/app/logs/ingest_all.log` and `/app/logs/ingest_single.log` (rotating, max 10MB each)

