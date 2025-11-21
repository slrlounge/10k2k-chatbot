# Diagnosing WAVE Retrieval Issue

## Problem

The chatbot says "I couldn't find any relevant information" when asked about WAVE, but we know:
- ✅ **59 source files** contain WAVE content
- ✅ Files explicitly define WAVE as "Wall Art Vision Exercise"
- ❌ Documents may not be in ChromaDB, OR retrieval isn't working

## Quick Check: Are WAVE Files Ingested?

### Option 1: Check via Render Shell (if using cloud)

1. Go to Render Dashboard → `ingest-chromadb` → Shell
2. Run:
```python
python3 << 'EOF'
import chromadb
client = chromadb.HttpClient(host='chromadb-w5jr', port=8000)
collection = client.get_collection(name='10k2k_transcripts')

# Search for WAVE in documents
results = collection.get(limit=1000)
wave_count = 0
for doc in results.get('documents', []):
    if doc and ('wave' in doc.lower() or 'wall art vision' in doc.lower()):
        wave_count += 1

print(f"Found {wave_count} documents containing 'WAVE' out of {len(results.get('documents', []))} checked")
EOF
```

### Option 2: Run Test Script Locally

```bash
python3 test_wave_retrieval.py
```

This will:
- Check if WAVE documents are in ChromaDB
- Test similarity search queries
- Show what's being retrieved

## Likely Causes

### 1. Files Not Ingested Yet

**Solution**: Ingest the WAVE files

The files that should contain WAVE:
- `10K2Kv2/14_STEP FOURTEEN/14 - SALES HOW TO CLOSE EVERY CLIENT v2_1.txt`
- `10K2Kv2/14_STEP FOURTEEN/s14-02-the-wave-exercise_01.txt`
- `10K2Kv2/14_STEP FOURTEEN/00-S14-ALL-IN-ONE_*.txt`
- And 56+ other files

**To ingest**:
```bash
# If using the ingestion pipeline
python3 ingestion/ingest_pre_split_files.py

# Or ingest specific files
python3 ingestion/ingest_single_transcript_ultra_minimal.py "10K2Kv2/14_STEP FOURTEEN/14 - SALES HOW TO CLOSE EVERY CLIENT v2_1.txt"
```

### 2. Retrieval Not Finding Documents

**Possible issues**:
- Query "What does W.A.V.E. stand for?" might not match "wall art vision exercise"
- Similarity search might need better query formulation
- Score threshold might be filtering out relevant docs

**Solution**: Improve query handling

We can:
1. Add query expansion (expand "WAVE" to "wall art vision exercise")
2. Lower the relevance score threshold
3. Try different query formulations

### 3. Documents Filtered Out

**Check**: The relevance filtering we added might be too strict

Current code filters out documents with score > 1.5. If WAVE documents have scores > 1.5, they're being filtered out.

**Solution**: Adjust threshold or check scores

## Immediate Actions

1. **Check if files are ingested**:
   ```bash
   python3 test_wave_retrieval.py
   ```

2. **If not ingested, ingest them**:
   ```bash
   # Check which files need ingestion
   python3 ingestion/show_ingested_files.py | grep -i "14_STEP FOURTEEN"
   ```

3. **If ingested but not retrieved, improve query**:
   - Add query expansion for acronyms
   - Lower relevance threshold
   - Try hybrid search

## Next Steps

Based on test results:
- **If 0 WAVE documents found**: Need to ingest files
- **If WAVE documents found but not retrieved**: Need to fix retrieval/query
- **If retrieved but filtered out**: Need to adjust score threshold

