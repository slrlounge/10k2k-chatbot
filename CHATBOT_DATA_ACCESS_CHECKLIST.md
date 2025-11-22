# Chatbot Data Access Checklist

## ✅ Ensure chatbot-api Can Access All Ingested Data

After ingestion is complete, follow these steps to verify the chatbot can access all data:

---

## Step 1: Verify Environment Variables in chatbot-api

Go to Render → `chatbot-api` service → Environment tab, verify these are set:

### Required Variables:
- ✅ `CHROMA_HOST=chromadb-w5jr` (or your ChromaDB service name)
- ✅ `CHROMA_PORT=8000`
- ✅ `COLLECTION_NAME=10k2k_transcripts`
- ✅ `OPENAI_API_KEY=your-key` (REQUIRED for embeddings and LLM)

### Optional Variables:
- `ENVIRONMENT=production` (if you want production mode)
- `ENABLE_AUTH=false` (or `true` if using authentication)
- `ALLOWED_ORIGINS=your-domain.com` (for CORS in production)

---

## Step 2: Verify ChromaDB Connection

In `chatbot-api` service Shell, run:

```bash
python3 ingestion/verify_chatbot_access.py
```

This will:
- ✅ Check environment variables
- ✅ Test ChromaDB connection
- ✅ Verify collection exists and has data
- ✅ Test LangChain vectorstore (same method chatbot uses)
- ✅ Test sample queries

**Expected Output:**
```
✓ Connected to chromadb-w5jr:8000
✓ Collection '10k2k_transcripts' exists
✓ Document count: X,XXX
✓ Vectorstore initialized
✓ Search successful
```

---

## Step 3: Test Health Endpoint

In `chatbot-api` service Shell, test the health endpoint:

```bash
curl http://localhost:8000/health
```

Or from your local machine (replace with your chatbot-api URL):

```bash
curl https://your-chatbot-api.onrender.com/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "vectorstore_initialized": true,
  "llm_initialized": true,
  "environment": "production"
}
```

If `vectorstore_initialized` is `false`, check the logs for connection errors.

---

## Step 4: Test API Endpoint Directly

Test the `/ask` endpoint:

```bash
curl -X POST "https://your-chatbot-api.onrender.com/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "What does W.A.V.E. stand for?"}'
```

**Expected Response:**
```json
{
  "answer": "...",
  "sources": [
    {
      "filename": "...",
      "type": "document",
      "content": "...",
      "score": 0.123
    }
  ]
}
```

---

## Step 5: Test Web Interface

1. Open your chatbot web interface:
   ```
   https://your-chatbot-api.onrender.com/web/chat.html
   ```

2. Test queries:
   - "What does W.A.V.E. stand for?"
   - "What is the 10K to 2K system?"
   - "Tell me about sales"

3. Verify:
   - ✅ Answers are returned
   - ✅ Source citations are shown
   - ✅ Answers are relevant to your content

---

## Step 6: Verify Data Completeness

In `ingest-chromadb` Shell, check what was ingested:

```bash
python3 ingestion/show_ingested_files.py
```

Compare with your source files to ensure everything was ingested.

---

## Troubleshooting

### Problem: "Collection does not exist"

**Solution:**
- Verify collection name matches: `10k2k_transcripts`
- Check ChromaDB service is running
- Verify ingestion completed successfully

### Problem: "vectorstore_initialized: false"

**Possible causes:**
1. ChromaDB not accessible
2. Wrong `CHROMA_HOST` or `CHROMA_PORT`
3. Network connectivity issues

**Solution:**
- Check `CHROMA_HOST` matches your ChromaDB service name
- Verify ChromaDB service is running
- Check logs: Render → chatbot-api → Logs

### Problem: "No results found" for queries

**Possible causes:**
1. Data not ingested
2. Embedding model mismatch
3. Query too specific

**Solution:**
- Verify ingestion completed: `python3 ingestion/show_ingested_files.py`
- Check document count: `python3 ingestion/check_ingestion_status.py`
- Try broader queries first

### Problem: "OPENAI_API_KEY not set"

**Solution:**
- Go to Render → chatbot-api → Environment
- Add `OPENAI_API_KEY=your-key`
- Redeploy service

---

## Quick Verification Commands

### Check document count:
```bash
# In ingest-chromadb Shell:
python3 ingestion/check_ingestion_status.py
```

### Verify chatbot can access data:
```bash
# In chatbot-api Shell:
python3 ingestion/verify_chatbot_access.py
```

### Test API endpoint:
```bash
curl -X POST "https://your-chatbot-api.onrender.com/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "test"}'
```

---

## ✅ Success Criteria

Your chatbot is ready when:

- [x] Environment variables set correctly
- [x] ChromaDB connection works
- [x] Collection exists with documents
- [x] Vectorstore initialized successfully
- [x] Health endpoint returns `vectorstore_initialized: true`
- [x] `/ask` endpoint returns answers with sources
- [x] Web interface works and shows answers

---

## Summary

Once all checks pass, your chatbot can access all ingested data. The data is stored on the persistent disk in ChromaDB, so it will persist across restarts and deploys.

**Key Points:**
- ✅ Data is stored in ChromaDB (persistent disk)
- ✅ chatbot-api connects to ChromaDB via HTTP
- ✅ Same collection name (`10k2k_transcripts`) is used
- ✅ Same embedding model (`text-embedding-3-small`) is used
- ✅ Data persists across restarts

You're all set! 🚀

