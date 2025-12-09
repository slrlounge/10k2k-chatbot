# 🔄 Data Flow: Split Files → ChromaDB

## ❌ Common Misconception

**WRONG:** Split files go directly into chromadb

**CORRECT:** Split files are processed by ingest-chromadb, which generates embeddings and stores ONLY the embeddings in chromadb

---

## ✅ Correct Flow

### Step 1: Local File Splitting
```
Local Machine:
  sales.txt (large file)
    ↓ split_files_locally.py
  sales_01.txt (0.01MB)
  sales_02.txt (0.01MB)
  sales_03.txt (0.01MB)
```

### Step 2: Git Commit & Push
```
Local → Git → GitHub
  • All split files committed
  • Pushed to repository
```

### Step 3: Render Deployment
```
GitHub → Render Build → Docker Image
  • Render pulls latest code
  • Builds Docker image
  • Copies files to: /app/10K2K v2/
  • Files are now in ingest-chromadb container
```

### Step 4: ingest-chromadb Processes Files
```
ingest-chromadb reads files:
  /app/10K2K v2/sales_01.txt
  /app/10K2K v2/sales_02.txt
  /app/10K2K v2/sales_03.txt

For each file:
  1. Read text content
  2. Split into chunks (500 tokens each)
  3. Generate embeddings using OpenAI
  4. Store embeddings in chromadb
```

### Step 5: chromadb Stores Embeddings
```
chromadb receives:
  • Vector embeddings (not files!)
  • Metadata (filename, chunk number)
  • Document IDs

chromadb stores:
  ✓ Vector embeddings (for similarity search)
  ✓ Metadata (filename, chunk info)
  ✗ NOT the actual text files
```

---

## 📊 What Goes Where?

| Location | What's Stored | Purpose |
|----------|---------------|---------|
| **Local Machine** | Split `.txt` files | Source files |
| **GitHub** | Split `.txt` files | Version control |
| **ingest-chromadb** | Split `.txt` files | Processing |
| **chromadb** | **Vector embeddings only** | Similarity search |

---

## 🔍 Detailed Process

### When ingest-chromadb processes a file:

```python
# 1. Read file
content = read_file("sales_01.txt")

# 2. Chunk text
chunks = chunk_text(content, chunk_size=500)

# 3. Generate embeddings for each chunk
for chunk in chunks:
    embedding = openai.embeddings.create(
        model="text-embedding-3-small",
        input=chunk
    )
    
    # 4. Store in chromadb
    chromadb.collection.add(
        embeddings=[embedding],
        documents=[chunk],  # Text stored for retrieval
        metadatas=[{"filename": "sales_01.txt", "chunk": 1}],
        ids=["sales_01_chunk_1"]
    )
```

### What chromadb actually stores:

```json
{
  "id": "sales_01_chunk_1",
  "embedding": [0.123, -0.456, 0.789, ...],  // Vector (1536 dimensions)
  "document": "This is the text content...",  // Original text (for retrieval)
  "metadata": {
    "filename": "sales_01.txt",
    "chunk": 1
  }
}
```

**Key Point:** chromadb stores:
- ✅ **Embeddings** (vectors for search)
- ✅ **Documents** (text content for retrieval)
- ✅ **Metadata** (filename, chunk info)
- ❌ **NOT the original .txt files**

---

## 🎯 Why This Architecture?

### Files Stay in ingest-chromadb:
- Files are only needed during ingestion
- After processing, files aren't needed
- Saves storage space in chromadb

### Only Embeddings Go to chromadb:
- chromadb is optimized for vector search
- Stores embeddings + text for retrieval
- Doesn't need original file structure

### Separation of Concerns:
- **ingest-chromadb**: File processing, embedding generation
- **chromadb**: Vector storage, similarity search
- **chatbot-api**: Query processing, answer generation

---

## 🔄 Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    LOCAL MACHINE                            │
│  sales.txt → split → sales_01.txt, sales_02.txt, ...      │
└────────────────────┬───────────────────────────────────────┘
                      │ git commit & push
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                      GITHUB                                 │
│  Repository with split files                                │
└────────────────────┬───────────────────────────────────────┘
                      │ Render pulls & builds
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              ingest-chromadb (Render)                       │
│  /app/10K2K v2/sales_01.txt                                │
│  /app/10K2K v2/sales_02.txt                                │
│                                                             │
│  Reads files → Chunks → Generates embeddings               │
└────────────────────┬───────────────────────────────────────┘
                      │ HTTP POST (embeddings)
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  chromadb (Render)                          │
│  Stores:                                                    │
│  • Vector embeddings                                        │
│  • Text documents                                           │
│  • Metadata                                                 │
│                                                             │
│  Does NOT store:                                            │
│  • Original .txt files                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## ✅ Summary

**Answer to your question:**

> "Should split files enter chromadb prior to ingest-chromadb?"

**NO!** The correct flow is:

1. **Split files** → Created locally
2. **Git** → Committed and pushed
3. **Render** → Deployed to ingest-chromadb service
4. **ingest-chromadb** → Reads files, processes them
5. **chromadb** → Receives embeddings (not files)

**Files never go directly into chromadb!**

Only **embeddings** (vector representations) go into chromadb, and they're generated by ingest-chromadb when it processes the split files.

