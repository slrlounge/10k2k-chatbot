# Create File Search Store - Manual Steps

Since the programmatic API isn't working, let's create the File Search Store via Google AI Studio (which is actually easier!):

## Steps:

1. **Go to Google AI Studio**
   - Visit: https://aistudio.google.com/

2. **Navigate to File Search**
   - Look for "File Search" in the left sidebar
   - Click on it

3. **Create a New Store**
   - Click "Create" or "New Store" button
   - Name it: `Kajabi_Knowledge_Base`
   - Click "Create"

4. **Get the Store ID**
   - After creation, you'll see your store listed
   - Click on the store name
   - Look for the Store ID (it will look like: `fileSearchStores/1234567890`)
   - **Copy this Store ID**

5. **Add Store ID to .env**
   - Open `.env` file
   - Find the line: `GEMINI_STORE_ID=your_file_search_store_id_here`
   - Replace `your_file_search_store_id_here` with your Store ID
   - Save the file

6. **Connect Your GCS Bucket**
   - Still in Google AI Studio, in your File Search Store
   - Click "Add files" or "Connect GCS bucket"
   - Select your bucket: `gs://slr-rag-gemini`
   - Wait for files to be indexed (this may take a few minutes)

## Alternative: Use the script below

If you prefer, I can create a script that uses the REST API directly.

