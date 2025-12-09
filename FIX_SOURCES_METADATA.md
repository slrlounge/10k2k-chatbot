# Fix Sources Showing as "Unknown"

This document provides solutions for fixing sources that display as "UNKNOWN Unknown" in the chatbot.

## Problem

Sources in the chatbot are displaying as "UNKNOWN Unknown" instead of showing proper filenames and document types.

## Root Cause

The issue occurs when:
1. Documents in ChromaDB are missing metadata fields (`filename`, `type`)
2. Metadata fields exist but have different names (`file_source`, `original_file` instead of `filename`)
3. The server code wasn't checking all possible metadata field names

## Solutions

### ✅ Solution 1: Code Fix (Already Applied)

The `serve.py` file has been updated to:
- Check multiple metadata field names (`filename`, `file_source`, `original_file`, `source`)
- Extract filenames from document IDs if metadata is missing
- Infer document types from filenames
- Handle empty/null metadata gracefully

**Status**: ✅ Code changes applied to `serve.py`

### ✅ Solution 2: Fix Existing Documents in ChromaDB

A script has been created to check and update metadata for existing documents.

#### Run the Fix Script

```bash
# Make sure ChromaDB is accessible
python3 ingestion/fix_metadata.py
```

The script will:
1. Connect to ChromaDB
2. Check all documents for missing metadata
3. Extract filenames from document IDs if needed
4. Infer document types from filenames
5. Update documents with missing metadata

**Note**: This requires ChromaDB to be running and accessible.

### ✅ Solution 3: Restart/Redeploy Server

After applying the code fixes, you need to restart the server for changes to take effect.

#### Local Development

```bash
# Stop the current server (Ctrl+C)
# Then restart:
python3 serve.py

# Or if using uvicorn directly:
uvicorn serve:app --host 0.0.0.0 --port 8001 --reload
```

#### Render.com Deployment

1. **Manual Restart**:
   - Go to Render dashboard
   - Find your `chatbot-api` service
   - Click "Manual Deploy" → "Deploy latest commit"
   - Or click "Restart" button

2. **Auto-Deploy** (if enabled):
   - Push changes to your Git repository
   - Render will automatically deploy:
   ```bash
   git add serve.py
   git commit -m "Fix: Improve metadata extraction for sources"
   git push origin main
   ```

3. **Verify Deployment**:
   - Check Render logs for: `✓ Vector store connected to ChromaDB`
   - Test the `/health` endpoint
   - Try a query in the chatbot

#### Railway Deployment

1. **Manual Restart**:
   - Go to Railway dashboard
   - Find your service
   - Click "Redeploy"

2. **Auto-Deploy**:
   ```bash
   git add serve.py
   git commit -m "Fix: Improve metadata extraction for sources"
   git push origin main
   ```

#### Docker Deployment

```bash
# Rebuild and restart
docker-compose down
docker-compose up -d --build

# Or for production:
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build
```

## Verification

After restarting, test the chatbot:

1. Ask a question in the chatbot
2. Check the sources section
3. Sources should now show:
   - Proper filenames (e.g., "00-S1-ALL-IN-ONE_01.txt")
   - Document types (e.g., "transcript", "text", "pdf")

## Debugging

If sources still show "Unknown":

### Check Server Logs

In development mode, check logs for:
```
Sample document metadata keys: ['filename', 'type', ...]
Sample document metadata: {'filename': '...', 'type': '...'}
```

### Check ChromaDB Metadata

Run the inspection script:
```bash
python3 check_metadata.py
```

Or use the existing script:
```bash
python3 ingestion/show_ingested_files.py
```

### Check Ingestion Scripts

The following scripts set metadata correctly:
- ✅ `ingest_single_transcript_ultra_minimal.py` - Sets `filename`, `type`, `source`
- ✅ `ingest_single_transcript_adaptive.py` - Sets `filename`, `type`, `source`
- ✅ `ingest_one_file.py` - Sets `file_source`, `original_file`

**Note**: `ingest_one_file.py` uses `file_source` instead of `filename`, but the updated `serve.py` handles both.

## Prevention

To prevent this issue in the future:

1. **Always set metadata during ingestion**:
   ```python
   metadata = {
       "filename": file_path.name,
       "type": "transcript",
       "source": str(file_path)
   }
   ```

2. **Use consistent field names**:
   - Prefer `filename` over `file_source`
   - Always include `type` field

3. **Test after ingestion**:
   ```bash
   python3 ingestion/show_ingested_files.py
   ```

## Summary

1. ✅ **Code Fix**: Applied to `serve.py` - handles multiple metadata field names
2. ✅ **Metadata Fix Script**: Created `ingestion/fix_metadata.py` - updates existing documents
3. ✅ **Deployment Instructions**: Provided above for all deployment methods

**Next Step**: Restart your server to apply the code changes!

