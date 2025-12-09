# Fix: Out of Memory Error During Startup

## Problem
The chatbot-api service is crashing during startup with:
```
==> Out of memory (used over 512Mi)
```

## Root Causes

### 1. Too Many Gunicorn Workers
- **Current**: 4 workers (`-w 4`)
- **Issue**: Each worker initializes its own vectorstore, loading embeddings into memory
- **Memory**: 4 workers × ~150MB each = ~600MB (exceeds 512MB limit)

### 2. Test Query Loading Data
- **Issue**: The test query `similarity_search_with_score("test", k=1)` was loading data during startup
- **Impact**: Additional memory usage during initialization

## Solutions Implemented

### 1. Reduced Gunicorn Workers
**Changed**: `Dockerfile` from `-w 4` to `-w 2`
- **Memory**: 2 workers × ~150MB each = ~300MB (within 512MB limit)
- **Trade-off**: Slightly lower concurrent request capacity, but service stays within memory limits

### 2. Removed Test Query
**Changed**: Removed `similarity_search_with_score("test", k=1)` from startup
- **Before**: Test query loaded data into memory during startup
- **After**: Only verify vectorstore object exists (no data loading)

## Additional Issue: Empty Collection

The logs show:
```
✓ Created collection '10k2k_transcripts' with cosine similarity
✓ Verified collection '10k2k_transcripts' exists with 0 document(s)
```

**This means**:
- The collection was just created (404 Not Found, then created)
- The collection is empty (0 documents)
- Either:
  1. Persistent disk isn't working
  2. Data was lost
  3. Ingestion hasn't run yet

## Next Steps

### 1. Deploy Memory Fix
- The reduced workers and removed test query should fix the OOM error
- Deploy and monitor memory usage

### 2. Check Persistent Disk
```bash
# In chromadb service shell on Render:
ls -la /chroma/chroma
# Should show database files if persistent disk is working
```

### 3. Run Ingestion
If collection is empty, you need to ingest data:
```bash
# In ingest-chromadb service shell:
python3 ingestion/add_new_files_to_queue.py
python3 ingestion/process_queue_worker.py
```

### 4. Verify Collection Has Data
```bash
# In chatbot-api shell:
python3 verify_chatbot_api_chromadb.py
# Should show document count > 0
```

## Expected Behavior After Fix

✅ **Before Fix**: 
- Out of memory error
- Service crashes during startup
- Collection empty (0 documents)

✅ **After Fix**:
- Service starts successfully
- Memory usage stays under 512MB
- Collection should have documents (after ingestion)

## Monitoring

After deployment, check:
1. **Memory usage**: Should stay under 512MB
2. **Startup logs**: Should show successful initialization
3. **Collection count**: Should show documents if ingestion has run

## If Memory Issue Persists

If you still see OOM errors:

1. **Reduce to 1 worker** (single-threaded, but lowest memory):
   ```dockerfile
   CMD sh -c "gunicorn serve:app -w 1 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:${PORT:-8000} --timeout 120"
   ```

2. **Check what's using memory**:
   - Vectorstore initialization
   - LLM model loading
   - Other dependencies

3. **Consider upgrading Render plan**:
   - Current: 512MB limit
   - Upgrade: More memory available

