# Fix: Collection UUID Error

## Problem
The chatbot is returning: `Error: Collection [0b8b9d08-4fd3-4472-877f-34e11647524b] does not exist.`

This UUID suggests that `langchain_chroma.Chroma` is trying to use a UUID-based collection ID instead of the collection name `10k2k_transcripts`.

## Root Cause
1. **Cached State**: `langchain_chroma.Chroma` may have cached metadata pointing to a UUID-based collection from a previous run
2. **Local Storage**: If there's any local ChromaDB state, it might contain references to old collections
3. **Collection Creation**: Langchain might be creating a new collection with a UUID instead of using the existing named collection

## ChatGPT's Recommendations - Analysis

### ✅ Step 1: Delete Local ChromaDB State
**Will this help?** YES - This removes any cached metadata or local state that might reference UUID-based collections.

**Action Required:**
```bash
# In chatbot-api Shell on Render:
rm -rf /app/chroma
rm -rf /app/storage/chroma
rm -rf /app/chroma_db  # if it exists
```

### ✅ Step 2: Update Vectorstore Initialization  
**Will this help?** PARTIALLY - Our code already uses `HttpClient` and `collection_name`, but we've added verification to ensure langchain uses the correct collection.

**What we changed:**
- Added explicit collection verification before passing to langchain
- Added test query to verify langchain is using the correct collection
- Ensured collection exists with correct metadata before langchain initialization

### ✅ Step 3: Redeploy chatbot-api
**Will this help?** YES - Critical to clear any in-memory state and apply code changes.

### ✅ Step 4: Test Again
**Will this help?** YES - Use the verification script to confirm connection.

## Code Changes Made

### Updated `serve.py`:
1. **Added collection verification** before passing to langchain
2. **Added test query** to verify langchain is using the correct collection
3. **Improved error messages** to help diagnose collection mismatches

### Key Changes:
```python
# Ensure collection exists BEFORE langchain uses it
collection = get_collection_with_retry(client)

# Verify collection exists
count = collection.count()
logger.info(f"✓ Verified collection '{COLLECTION_NAME}' exists with {count} document(s)")

# Create vectorstore - langchain will use existing collection by name
vectorstore = Chroma(
    client=client,
    collection_name=COLLECTION_NAME,  # Explicit name, not UUID
    embedding_function=embeddings,
)

# Verify langchain can access the collection
test_results = vectorstore.similarity_search_with_score("test", k=1)
```

## Recommended Steps (In Order)

### 1. Delete Local ChromaDB State (In Render Shell)
```bash
# Connect to chatbot-api shell on Render
rm -rf /app/chroma
rm -rf /app/storage/chroma
rm -rf /app/chroma_db
```

### 2. Verify Code Changes Are Deployed
- Check that `serve.py` has the updated `initialize_vectorstore()` function
- Ensure the code uses `HttpClient` and `collection_name=COLLECTION_NAME`

### 3. Redeploy chatbot-api Service
- This clears any in-memory state
- Applies the new code changes
- Ensures fresh initialization

### 4. Test Connection (In Render Shell)
```bash
# Run verification script
python3 verify_chatbot_api_chromadb.py

# Or test manually:
python3 << 'EOF'
import os
from chromadb import HttpClient

host = os.getenv("CHROMA_HOST", "chromadb-w5jr")
port = int(os.getenv("CHROMA_PORT", "8000"))
collection_name = os.getenv("COLLECTION_NAME", "10k2k_transcripts")

client = HttpClient(host=host, port=port)
col = client.get_or_create_collection(collection_name, metadata={"hnsw:space": "cosine"})
print(f"Collection '{collection_name}' has {col.count()} documents")
EOF
```

### 5. Check Logs
After redeploy, check startup logs for:
- `✓ Connected to remote ChromaDB at chromadb-w5jr:8000`
- `✓ Verified collection '10k2k_transcripts' exists with X document(s)`
- `✓ Vector store verified and ready (collection: 10k2k_transcripts)`

### 6. Test Chatbot
- Send a test message from the web interface
- Should no longer see UUID collection error

## Why These Steps Will Work

1. **Deleting local state** removes any cached references to UUID-based collections
2. **Code changes** ensure langchain uses the collection by name, not by UUID
3. **Redeploy** clears in-memory state and applies fresh initialization
4. **Verification** confirms the correct collection is being used

## Expected Outcome

After these steps:
- ✅ No more UUID collection errors
- ✅ Chatbot uses collection `10k2k_transcripts` correctly
- ✅ All queries work properly
- ✅ No local storage is used

## If Error Persists

If you still see UUID errors after these steps:

1. **Check Render Environment Variables:**
   ```bash
   # In Render dashboard, verify:
   CHROMA_HOST=chromadb-w5jr
   CHROMA_PORT=8000
   COLLECTION_NAME=10k2k_transcripts
   ```

2. **Verify Collection Exists:**
   ```bash
   # In chromadb service shell:
   python3 -c "from chromadb import HttpClient; c = HttpClient(host='localhost', port=8000); print([col.name for col in c.list_collections()])"
   ```

3. **Check Logs:**
   - Look for any errors during `initialize_vectorstore()`
   - Check if collection name is being logged correctly

4. **Contact Support:**
   - Share the error message and logs
   - Include the verification script output

