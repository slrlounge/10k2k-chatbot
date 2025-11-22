# Manual Ingestion Instructions for Render Shell

## Step 1: Connect to Render Shell

1. Go to Render Dashboard → `ingest-chromadb` service
2. Click **"Shell"** tab (or look for "Shell" button)
3. Wait for the shell to connect

## Step 2: Run Ingestion

Once connected to the shell, you have two options:

### Option A: Ingest Pre-Split Files (Recommended)
If your files are already split into 0.01MB segments locally:

```bash
python3 ingestion/ingest_pre_split_files.py
```

### Option B: Ingest All Files (with checkpoint system)
This will process all files, skipping already-processed ones:

```bash
python3 ingestion/ingest_all_transcripts.py
```

## Step 3: Monitor Progress

The script will output progress messages. You'll see:
- Files being processed
- Success/failure status
- Final summary

## Step 4: Check Results

After ingestion completes, verify files are in ChromaDB:

```bash
python3 ingestion/find_missing_in_chromadb.py
```

This will show which files are missing from ChromaDB.

## Troubleshooting

### If you get "directory does not exist" error:
Check the environment variable:
```bash
echo $TRANSCRIPTS_DIR
```

It should show: `/app/10K2Kv2`

If it shows `/app/10K2K v2` (with space), update it in Render Dashboard → Environment tab.

### If ingestion fails for specific files:
Check logs:
```bash
tail -f /app/logs/ingest_*.log
```

### To stop ingestion:
Press `Ctrl+C` in the shell

## Notes

- Ingestion runs in the foreground, so keep the shell open
- Each file is processed in a separate subprocess to manage memory
- Progress is checkpointed, so you can restart if needed
- The script will skip files already marked as processed

